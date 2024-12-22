import queue

import requests
import datetime as dt
from time import sleep
import math
import json
import threading

import logging


_logger = logging.getLogger(__name__)

TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
SCHED_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
MAX_REQUESTS_PER_MIN = 10

# list of keys for own dict matched to cascading list of keys from nhl api
GAME_MAP = {'id': ['id'],
            'awayTeam': ['awayTeam', 'abbrev'],
            'homeTeam': ['homeTeam', 'abbrev'],
            'awayScore': ['awayTeam', 'score'],
            'homeScore': ['homeTeam', 'score'],
            'awaySog': ['awayTeam', 'sog'],
            'homeSog': ['homeTeam', 'sog'],
            'gameState': ['gameState'],  # FINAL, OFF, LIVE, FUT, PRE, CRIT
            'period': ['periodDescriptor', 'number'],
            'clock': ['clock', 'timeRemaining'],
            'inIntermission': ['clock', 'inIntermission'],
            'awayStrength': ['situation', 'awayTeam', 'strength'],
            'homeStrength': ['situation', 'homeTeam', 'strength'],
            'awaySituation': ['situation', 'awayTeam', 'situationDescriptions'],
            'homeSituation': ['situation', 'homeTeam', 'situationDescriptions'],
            'situationClock': ['situation', 'timeRemaining']
            }


class KillFlag(threading.Event):
    """A wrapper for the typical event class to allow for overriding the
    `__bool__` magic method, since it looks nicer.
    """
    def __bool__(self):
        return self.is_set()


class League(threading.Thread):
    def __init__(self, resp_queue, req_queue, team='PHI'):
        super().__init__(daemon=True)

        self.resp_queue = resp_queue
        self.req_queue = req_queue
        self.team = team

        self.requests_made = []
        self.delayed_requests = []
        #  each item of form:
        # {'func': {'method': method_name, 'args': args, 'kwargs': kwargs}, 'time_to_req': datetime}

        _logger.info('Initialize League() thread')
        return

    def _append_delayed_request(self, delayed_req):
        """
        adds delayed request if none exactly the same have been added, if not, check if new delay time is shorter than
        currently listed

        :param delayed_req: of form {'func': {'method': 'method_name', 'args': [args], 'kwargs': {kwargs}},
        'time_to_req': datetime}
        """
        found_prior_req = False
        for req in self.delayed_requests:
            if req['func'] == delayed_req['func']:
                if delayed_req['time_to_req'] < req['time_to_req']:
                    req['time_to_req'] = delayed_req['time_to_req']
                found_prior_req = True
                break

        if not found_prior_req:
            self.delayed_requests.append(delayed_req)

    def _len_requests_made(self) -> int:
        _logger.debug(f'Check set of requests made {self.requests_made}')
        current_dt_delta = dt.datetime.now().astimezone(None) - dt.timedelta(minutes=1)
        #  clear out old requests
        self.requests_made = [req for req in self.requests_made if req[1] > current_dt_delta]

        return len(self.requests_made)

    def get_standings(self):
        """
        Makes api call to get league standings

        :return:
        """
        _logger.info('Get League standings')

        current_dt = dt.datetime.now().astimezone(None)
        try:
            self.requests_made.append(['get_standings', current_dt])  # add to history
            response = requests.get('https://api-web.nhle.com/v1/standings/now').json()
        except requests.exceptions.JSONDecodeError:
            _logger.error('No response for standings API request!  Try again in 5 minutes.')
            self._append_delayed_request({'func': {'method': 'get_standings', 'args': [], 'kwargs': {}},
                                          'time_to_req': current_dt + dt.timedelta(minutes=5)})
            return

        standings = {'requestTime':current_dt.strftime(TIME_FORMAT), 'Central': {}, 'Pacific': {},
                     'Atlantic': {}, 'Metropolitan': {}, 'Western': {}, 'Eastern': {}}

        for team in response['standings']:
            if len(standings[team['divisionName']]) < 3:
                standings[team['divisionName']][team['teamAbbrev']['default']] = {'gamesPlayed': team['gamesPlayed'],
                                                                       'wins': team['wins'], 'losses': team['losses'],
                                                                       'otLosses': team['otLosses'],
                                                                       'points': team['points'],
                                                                       'pointPctg': team['pointPctg']}
            else:
                standings[team['conferenceName']][team['teamAbbrev']['default']] = {'gamesPlayed': team['gamesPlayed'],
                                                                         'wins': team['wins'], 'losses': team['losses'],
                                                                         'otLosses': team['otLosses'],
                                                                         'points': team['points'],
                                                                         'pointPctg': team['pointPctg']}

        for conf in standings:
            if conf in ('Western', 'Eastern'):
                standings[conf] = dict(sorted(standings[conf].items(),
                                              key=lambda item: (-item[1]['points'], -item[1]['pointPctg'])))

        self.resp_queue.put({'method': 'save_standings', 'args': [standings], 'kwargs': {}, 'delay': 0})

        return

    def get_schedule(self):
        _logger.info(f'Get {self.team} schedule')
        current_dt = dt.datetime.now().astimezone(None)

        try:
            self.requests_made.append(['get_schedule', current_dt])  # add to history
            response = requests.get('https://api-web.nhle.com/v1/club-schedule-season/' + self.team + '/now').json()
        except requests.exceptions.JSONDecodeError:
            _logger.error('No response for schedule API request!  Try again in 5 minutes.')
            self._append_delayed_request({'func': {'method': 'get_schedule', 'args': [], 'kwargs': {}},
                                         'time_to_req': current_dt + dt.timedelta(minutes=5)})
            return

        schedule = {'requestTime': current_dt.strftime(TIME_FORMAT), 'team': self.team, 'games': []}
        for gm in response['games']:
            schedule['games'].append({'id': gm['id'],
                                      'startTimeUTC': gm['startTimeUTC'],
                                      'gameType': gm['gameType'],  # 1: preseason, 2: regular
                                      'gameState': gm['gameState'],  # FINAL, OFF, LIVE, FUT, PRE
                                      'awayTeam': gm['awayTeam']['abbrev'],
                                      'homeTeam': gm['homeTeam']['abbrev']})
            try:
                schedule['games'][-1]['awayScore'] = gm['awayTeam']['score']
                schedule['games'][-1]['homeScore'] = gm['homeTeam']['score']
                schedule['games'][-1]['gameOutcome'] = gm['gameOutcome']['lastPeriodType']  # REG, OT, SO
            except KeyError:
                schedule['games'][-1]['awayScore'] = None
                schedule['games'][-1]['homeScore'] = None
                schedule['games'][-1]['gameOutcome'] = None

        self.resp_queue.put({'method': 'save_schedule', 'args': [schedule], 'kwargs': {}, 'delay': 0})

        return

    def get_roster(self):
        _logger.info(f'Get {self.team} roster')
        current_dt = dt.datetime.now().astimezone(None)

        try:
            self.requests_made.append(['get_roster', current_dt])  # add to history
            response = requests.get('https://api-web.nhle.com/v1/club-stats/' + self.team + '/now').json()
        except requests.exceptions.JSONDecodeError:
            _logger.error('No response for roster API request!  Try again in 5 minutes.')
            self._append_delayed_request({'func': {'method': 'get_roster', 'args': [], 'kwargs': {}},
                                         'time_to_req': current_dt + dt.timedelta(minutes=5)})
            return

        # roster = {'requestTime': dt.datetime.now().strftime(TIME_FORMAT), 'team': self.team, 'skaters': [],
        roster = {'requestTime': current_dt.strftime(TIME_FORMAT), 'team': self.team, 'skaters': [],
                  'goalies': []}
        for sktr in response['skaters']:
            roster['skaters'].append({'playerId': sktr['playerId'],
                                      'headshot': sktr['headshot'],
                                      'firstName': sktr['firstName']['default'],
                                      'lastName': sktr['lastName']['default'],
                                      'positionCode': sktr['positionCode'],
                                      'gamesPlayed': sktr['gamesPlayed'],
                                      'goals': sktr['goals'],
                                      'assists': sktr['assists'],
                                      'points': sktr['points']})

        for glie in response['goalies']:
            roster['goalies'].append({'playerId': glie['playerId'],
                                      'headshot': glie['headshot'],
                                      'firstName': glie['firstName']['default'],
                                      'lastName': glie['lastName']['default'],
                                      'gamesPlayed': glie['gamesPlayed'],
                                      'gamesStarted': glie['gamesStarted'],
                                      'wins': glie['wins'],
                                      'losses': glie['losses'],
                                      'ties': glie['ties'],
                                      'overtimeLosses': glie['overtimeLosses'],
                                      'savePercentage': glie['savePercentage'],
                                      'goals': glie['goals'],
                                      'assists': glie['assists'],
                                      'points': glie['points']})

        self.resp_queue.put({'method': 'save_roster', 'args': [roster], 'kwargs': {}, 'delay': 0})

        return

    def get_game(self, game_id):
        _logger.debug(f'League.get_game: Make API request for game: {game_id}')
        current_dt = dt.datetime.now().astimezone(None)

        try:
            self.requests_made.append(['get_game', current_dt])  # add to history
            response = requests.get('https://api-web.nhle.com/v1/gamecenter/' + str(game_id) + '/play-by-play').json()
        except requests.exceptions.JSONDecodeError:
            _logger.error('No response for live game API request!  Try again in 5 minutes.')
            self._append_delayed_request({'func': {'method': 'get_game', 'args': [game_id], 'kwargs': {}},
                                         'time_to_req': current_dt + dt.timedelta(seconds=45)})
            return

        # with open('resources/test_game.json', 'r') as f:
        #     response = json.load(f)
        # with open('resources/test_game.json', 'w') as f:
        #     json.dump(response, f, indent=2)  # noqa (ignore pycharm false pos)

        game = {'requestTime': current_dt.strftime(TIME_FORMAT)}

        for key, rkeys in GAME_MAP.items():
            temp_resp = response
            for rk in rkeys[:-1]:
                if rk not in temp_resp:
                    game[key] = ''
                    break
                else:
                    temp_resp = temp_resp[rk]  # let temp_resp be the sub dict in response
            else:
                if rkeys[-1] not in temp_resp:
                    game[key] = ''
                else:
                    game[key] = temp_resp[rkeys[-1]]  # get the last value

        # game = {'request_time': current_dt.strftime(TIME_FORMAT),'id': response['id'],
        #         'awayTeam': response['awayTeam']['abbrev'], 'homeTeam': response['homeTeam']['abbrev'],
        #         'awayScore': response['awayTeam']['score'], 'homeScore': response['homeTeam']['score'],
        #         'awaySog': response['awayTeam']['sog'], 'homeSog': response['homeTeam']['sog'],
        #         'gameState': response['gameState'], 'period': response['periodDescriptor']['number'],
        #         'clock': response['clock']['timeRemaining'], 'inIntermission': response['clock']['inIntermission'],
        #         'plays': []}
        #
        # # use if statements
        # try:
        #     sitch = response['situation']
        #
        #     if 'situationDescriptions' in sitch['awayTeam'].keys():
        #         game['homeSituation'] = ''
        #         game['awaySituation'] = sitch['awayTeam']['strength'] + 'v' + sitch['homeTeam']['strength']
        #     else:
        #         game['homeSituation'] = sitch['homeTeam']['strength'] + 'v' + sitch['awayTeam']['strength']
        #         game['awaySituation'] = ''
        #
        # except KeyError:
        #     game['awaySituation'] = ''
        #     game['homeSituation'] = ''

        game['plays'] = []
        for play in response['plays']:
            try:
                if play['typeDescKey'] == 'goal':
                    game['plays'].append({'typeDescKey': 'goal', 'period': play['periodDescriptor']['number'],
                                          'timeInPeriod': play['timeInPeriod'],
                                          'scoringPlayerId': play['details']['scoringPlayerId']})

                    for plyr in response['rosterSpots']:
                        if plyr['playerId'] == game['plays'][-1]['scoringPlayerId']:  # noqa (pycharm bs)
                            game['plays'][-1]['scoringPlayerName'] = plyr['firstName']['default'] + ' ' + \
                                                                     plyr['lastName']['default']
                            break
                    else:
                        game['plays'][-1]['scoringPlayerName'] = ''
            except KeyError:
                _logger.error('KeyError in League().get_game() plays')

        self.resp_queue.put({'method': 'update_live_game', 'args': [game], 'kwargs': {}, 'delay': 0})

        return

    def run(self):
        _logger.info('Start League() thread running')

        while True:
            current_dt = dt.datetime.now().astimezone(None)

            # handle incoming immediate requests
            if not self.req_queue.empty():
                func_and_args = self.req_queue.get()
                method = func_and_args['method']
                args = func_and_args['args']
                kwargs = func_and_args['kwargs']
                delay = func_and_args['delay']

                if hasattr(self, method):
                    if delay > 0:
                        _logger.debug(f'{method} is set to delay request {delay} minutes to '
                                      f'{current_dt + dt.timedelta(minutes=delay)}')
                        self._append_delayed_request({'func': {'method': method, 'args': args, 'kwargs': kwargs},
                                                      'time_to_req': current_dt + dt.timedelta(minutes=delay)})
                    else:
                        num_made_reqs = self._len_requests_made()
                        if num_made_reqs >= MAX_REQUESTS_PER_MIN:
                            _logger.debug(f'Making too many requests!  Delaying {method} request.')
                            self._append_delayed_request({'func': {'method': method, 'args': args, 'kwargs': kwargs},
                                                          'time_to_req': current_dt + dt.timedelta(minutes=1)})
                        else:
                            getattr(self, method)(*args, **kwargs)
                            sleep(0.1)
                else:
                    _logger.error(f'No such method {method} in League() class!')

            if self.delayed_requests:  # if there are any delayed reqs
                reqs_to_make = [req for req in self.delayed_requests if req['time_to_req'] < current_dt]
                self.delayed_requests = [req for req in self.delayed_requests if req not in reqs_to_make]
                for req in reqs_to_make:
                    method = req['func']['method']
                    args = req['func']['args']
                    kwargs = req['func']['kwargs']

                    num_made_reqs = self._len_requests_made()
                    if num_made_reqs >= MAX_REQUESTS_PER_MIN:
                        _logger.debug(f'Making too many requests!  Delaying {method} request.')
                        self._append_delayed_request({'func': {'method': method, 'args': args, 'kwargs': kwargs},
                                                      'time_to_req': current_dt + dt.timedelta(minutes=1)})
                    else:
                        getattr(self, method)(*args, **kwargs)
                        sleep(0.1)


class Bank(threading.Thread):
    """
    Threading class that acts as intermediary between gui and requesting thread
    """
    def __init__(self, kill_flag: KillFlag, resp_queue: queue.Queue, league_queue: queue.Queue,
                 gui_queue: queue.Queue, period_hours: int = 24):
        super().__init__()

        self.kill_flag = kill_flag
        self.resp_queue = resp_queue
        self.league_queue = league_queue
        self.gui_queue = gui_queue

        self.period_hours = period_hours
        self.standings_tod = dt.timedelta(minutes=0)
        self.sched_tod = dt.timedelta(minutes=2)  # offset to avoid pounding api
        self.roster_tod = dt.timedelta(minutes=4)  # offset to avoid pounding api
        self.game_tod = dt.timedelta(minutes=6)

        start_delta = math.ceil(dt.datetime.now().astimezone(None).hour / period_hours) * period_hours

        self.standings_next_get_time = (
                    dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).astimezone(None) +
                    dt.timedelta(hours=start_delta) + self.standings_tod)
        self.sched_next_get_time = (
                    dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).astimezone(None) +
                    dt.timedelta(hours=start_delta) + self.sched_tod)
        self.roster_next_get_time = (
                    dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).astimezone(None) +
                    dt.timedelta(hours=start_delta) + self.roster_tod)

        self.last_game = {}
        self.current_game = {}  # metadata from schedule
        self.next_game = {}
        self.game_update_time = dt.datetime.now().astimezone(None) + dt.timedelta(days=500)  # just set to now() to establish data type
        self.live_game_pbp = {}  # play by play api

        current_dt = dt.datetime.now().astimezone(None)

        # load league standings
        try:
            _logger.debug('Bank().init retrieve standings.json')
            with open('resources/standings.json') as f:
                self.standings = json.load(f)
                # refresh standings if old
                if current_dt - dt.datetime.strptime(self.standings['requestTime'], TIME_FORMAT).astimezone(
                        None) > dt.timedelta(hours=6):
                    self.league_queue.put({'method': 'get_standings', 'args': [], 'kwargs': {}, 'delay': 0})
        except FileNotFoundError:
            _logger.debug('Bank().init standings.json does not exist, make request')
            self.standings = {}
            # make request to get league standings immediately rather than wait
            self.league_queue.put({'method': 'get_standings', 'args': [], 'kwargs': {}, 'delay': 0})

        # load team schedule
        try:
            _logger.debug('Bank().init retrieve schedule.json')
            with open('resources/schedule.json') as f:
                self.schedule = json.load(f)
                self.set_game_ids()

                # refresh schedule if old
                # !!! refresh if existing schedule is for team other than current active in settings
                if current_dt - dt.datetime.strptime(self.schedule['requestTime'], TIME_FORMAT).astimezone(None) \
                        > dt.timedelta(hours=6):
                    self.league_queue.put({'method': 'get_schedule', 'args': [], 'kwargs': {}, 'delay': 0})
        except FileNotFoundError:
            _logger.debug('Bank().init schedule.json does not exist, make request')
            self.schedule = {}
            # make request to get league standings immediately rather than wait
            self.league_queue.put({'method': 'get_schedule', 'args': [], 'kwargs': {}, 'delay': 0})
            # game request will be triggered when response is passed to Bank.save_schedule()

            # if no schedule exists make sure to check for games in 5 seconds
            # self.check_games_time = dt.datetime.now().astimezone(None) + dt.timedelta(seconds=5)

        # load team roster
        try:
            _logger.debug('Bank().init retrieve roster.json')
            with open('resources/roster.json') as f:
                self.roster = json.load(f)
                # refresh roster if old
                # !!! refresh if existing roster if for team other than current active in settings
                if current_dt - dt.datetime.strptime(self.roster['requestTime'], TIME_FORMAT).astimezone(None) \
                        > dt.timedelta(hours=6):
                    self.league_queue.put({'method': 'get_roster', 'args': [], 'kwargs': {}, 'delay': 0})
        except FileNotFoundError:
            _logger.debug('Bank().init roster.json does not exist, make request')
            self.roster = {}
            # make request to get league standings immediately rather than wait
            self.league_queue.put({'method': 'get_roster', 'args': [], 'kwargs': {}, 'delay': 0})

        _logger.info('Initialize Bank() thread')
        return

    def save_standings(self, standings):
        _logger.info('Save standings to file')
        self.standings = standings
        with open('resources/standings.json', 'w') as f:
            json.dump(self.standings, f, indent=2)  # noqa (ignore pycharm false pos)

        return

    def save_schedule(self, schedule):
        _logger.info('Save schedule to file')
        self.schedule = schedule

        with open('resources/schedule.json', 'w') as f:
            json.dump(self.schedule, f, indent=2)  # noqa (ignore pycharm false pos)

        # if current_game is not set, then it is safe to run and possibly update game_update_time
        # this should be run in case of schedule changes
        # if not self.current_game:  # is this check necessary?
        _logger.debug('Call set_game_ids() from save_schedule')
        self.set_game_ids()

        return

    def save_roster(self, roster):
        _logger.info('Save roster to file')
        self.roster = roster
        with open('resources/roster.json', 'w') as f:
            json.dump(self.roster, f, indent=2)  # noqa (ignore pycharm false pos)

        return

    def set_game_ids(self):
        _logger.debug('Bank(): set_game_ids()')

        if not self.schedule:
            _logger.debug('Back().schedule not set for method Bank().set_game_ids()')
            self.league_queue.put({'method': 'get_schedule', 'args': [], 'kwargs': {}, 'delay': 0})

        current_dt = dt.datetime.now().astimezone(None)
        last_gt = current_dt - dt.timedelta(days=1)

        for ii, game in enumerate(self.schedule['games']):
            game_time = dt.datetime.strptime(game['startTimeUTC'], SCHED_TIME_FORMAT).astimezone(None)

            #  handle first game with no previous game
            if ii == 0:
                self.last_game = {}
            else:
                self.last_game = self.schedule['games'][ii - 1]
                last_gt = dt.datetime.strptime(self.last_game['startTimeUTC'], SCHED_TIME_FORMAT).astimezone(None)

            # check if current time is in window where game is likely occurring
            if game_time - dt.timedelta(minutes=15) <= current_dt <= game_time + dt.timedelta(hours=6):
                # handle if last game with no more games
                try:
                    self.next_game = self.schedule['games'][ii + 1]
                    # next_gt = dt.datetime.strptime(self.next_game['startTimeUTC'], SCHED_TIME_FORMAT).astimezone(None)
                except KeyError:
                    self.next_game = {}
                    # next_gt = current_dt + dt.timedelta(days=500)

                try:
                    # check if game is over
                    if self.live_game_pbp['gameState'] in ('OFF', 'FINAL'):
                        # self.live_game_pbp = {}
                        self.last_game = game
                        self.current_game = {}
                        gm_id = self.last_game['id']
                        # self.game_update_time = next_gt - dt.timedelta(minutes=15)
                    else:
                        _logger.debug('Bank().set_game_ids: found likely live game, but live_game not set')
                        self.current_game = game
                        gm_id = self.current_game['id']
                        # self.game_update_time = current_dt + dt.timedelta(minutes=1)
                except KeyError:
                    _logger.debug('Bank().set_game_ids: found likely live game')
                    # live_game hasn't been set yet, assume if killed elsewhere, then game_update_time would be in far
                    # future
                    self.current_game = game
                    gm_id = self.current_game['id']
                    # self.game_update_time = current_dt  # + dt.timedelta(minutes=1)
                break

            elif last_gt <= current_dt <= game_time:  # in between games
                # self.live_game_pbp = {}  # probably unnecessary
                self.current_game = {}
                self.next_game = game
                if self.last_game:
                    gm_id = self.last_game['id']
                else:
                    gm_id = self.next_game['id']
                # self.game_update_time = game_time - dt.timedelta(minutes=15)
                break
        else:
            self.last_game = self.schedule['games'][-1]  # last game of season
            gm_id = self.last_game['id']
            # self.live_game_pbp = {}  # probably unnecessary
            self.current_game = {}
            self.next_game = {}
            # self.game_update_time = current_dt + dt.timedelta(days=500)

        self.league_queue.put({'method': 'get_game', 'args': [gm_id], 'kwargs': {}, 'delay': 0})
        return

    def update_live_game(self, game):
        _logger.debug('Bank(): update_live_game')
        intermission = 'Intermission' if game['inIntermission'] else 'Period'
        _logger.info(f'Bank().update_live_game: {game["awayTeam"]}: {game["awayScore"]} @ '
                     f'{game["homeTeam"]}: {game["homeScore"]} | {intermission} {game["period"]}, {game["clock"]} | '
                     f'{game["id"]}')

        with open('resources/game_play-by-play.json', 'w') as f:
            json.dump(game, f, indent=2)  # noqa (ignore pycharm false pos)

        prior_state = self.live_game_pbp.get('gameState', 'OFF')
        current_dt = dt.datetime.now().astimezone(None)
        self.live_game_pbp = game

        if game['gameState'] in ('OFF', 'FINAL'):
            # game is over, set live_game (play by play) and current_game (metadata) to empty sets, set next time
            # self.live_game_pbp = {}
            if self.current_game:
                self.last_game = self.current_game
                self.current_game = {}

            try:
                next_game_time = dt.datetime.strptime(self.next_game['startTimeUTC'], SCHED_TIME_FORMAT).astimezone(None)
                self.game_update_time = next_game_time - dt.timedelta(minutes=15)
            except KeyError:
                self.game_update_time = current_dt + dt.timedelta(days=500)

            if prior_state not in ['OFF', 'FINAL']:
                # update standings in 15 minutes if game state has changed
                self.league_queue.put({'method': 'get_standings', 'args': [], 'kwargs': {}, 'delay': 15})
        else:
            # self.live_game_pbp = game
            self.game_update_time = current_dt + dt.timedelta(seconds=30)

        # need to run set_game_ids somewhere in here?

        return

    def run(self):
        _logger.info('Start Bank() thread')
        try:
            while not self.kill_flag:
                current_dt = dt.datetime.now().astimezone(None)

                # handle incoming immediate requests
                if not self.resp_queue.empty():
                    _logger.debug('League to Bank Queue has a response')
                    func_and_args = self.resp_queue.get()
                    method = func_and_args['method']
                    args = func_and_args['args']
                    kwargs = func_and_args['kwargs']
                    # delay = func_and_args['delay']   # !!! handle this

                    if hasattr(self, method):
                        getattr(self, method)(*args, **kwargs)
                        sleep(0.1)
                    else:
                        _logger.error(f'No such method {method} in Bank() class!')

                # run regularly scheduled standings request
                if self.standings_next_get_time < current_dt:
                    _logger.info('Bank passing standings request')

                    self.league_queue.put({'method': 'get_standings', 'args': [], 'kwargs': {}, 'delay': 0})
                    self.standings_next_get_time = self.standings_next_get_time + dt.timedelta(hours=self.period_hours)

                if self.sched_next_get_time < current_dt:
                    _logger.info(f'Bank() passing schedule request')

                    self.league_queue.put({'method': 'get_schedule', 'args': [], 'kwargs': {}, 'delay': 0})
                    self.sched_next_get_time = self.sched_next_get_time + dt.timedelta(hours=self.period_hours)

                if self.roster_next_get_time < current_dt:
                    _logger.info(f'Bank passing roster request')

                    self.league_queue.put({'method': 'get_roster', 'args': [], 'kwargs': {}, 'delay': 0})
                    self.roster_next_get_time = self.roster_next_get_time + dt.timedelta(hours=self.period_hours)

                # pass live game request to league
                if self.game_update_time < current_dt:
                    _logger.debug('Bank will make live game update request')
                    if not self.current_game:
                        # if for some reason self.current_game_id is not set, then make sure it is set or
                        # self.game_update_time is > current_dt
                        self.set_game_ids()
                    else:
                        self.league_queue.put({'method': 'get_game', 'args': [self.current_game['id']], 'kwargs': {}, 'delay': 0})
                        # set to make next request in 5 minutes in case get_game doesn't get a response
                        self.game_update_time = dt.datetime.now().astimezone(None) + dt.timedelta(minutes=5)

                sleep(0.1)


        finally:
            _logger.debug(f'Thread {self.name} performing cleanup')
            # Perform any cleanup
            _logger.debug(f'Thread {self.name} stopped.')
