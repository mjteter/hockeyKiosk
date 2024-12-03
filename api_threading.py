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

class KillFlag(threading.Event):
    """A wrapper for the typical event class to allow for overriding the
    `__bool__` magic method, since it looks nicer.
    """
    def __bool__(self):
        return self.is_set()


class League(threading.Thread):
    def __init__(self, resp_queue, req_queue, team='PHI', period_hours=24,):
                 # standings_tod=dt.timedelta(minutes=0),
                 # sched_tod=dt.timedelta(minutes=5)):
        threading.Thread.__init__(self, daemon=True)

        self.resp_queue = resp_queue
        self.req_queue = req_queue
        self.team = team
        self.period_hours = period_hours
        self.standings_tod = dt.timedelta(minutes=0)
        self.sched_tod = dt.timedelta(minutes=2)  # offset to avoid pounding api
        self.roster_tod = dt.timedelta(minutes=4)  # offset to avoid pounding api

        start_delta = math.ceil(dt.datetime.now().astimezone(None).hour / period_hours) * period_hours


        self.standings_next_get_time = (dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).astimezone(None) +
                                        dt.timedelta(hours=start_delta) + self.standings_tod)
        self.sched_next_get_time = (dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).astimezone(None) +
                                        dt.timedelta(hours=start_delta) + self.sched_tod)
        self.roster_next_get_time = (dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).astimezone(None) +
                                        dt.timedelta(hours=start_delta) + self.roster_tod)

        _logger.info('Initialize League() thread')
        return

    def get_standings(self, delay=0):
        """
        Makes api call to get league standings

        :param delay:  time to delay request in minutes.   0 if no delay desired
        :return:
        """
        if delay > 0:
            _logger.info(f'Get League standings after delay of {delay}')
            self.standings_next_get_time = self.standings_next_get_time + dt.timedelta(minutes=delay)
            return

        _logger.info('Get League standings')

        try:
            response = requests.get('https://api-web.nhle.com/v1/standings/now').json()
        except requests.exceptions.JSONDecodeError:
            _logger.error('No response for standings API request!  Try again in 5 minutes.')
            self.standings_next_get_time = dt.datetime.now().astimezone(None) + dt.timedelta(minutes=5)
            # self.resp_queue.put(('save_standings', [None], {}))  # should failure be passed on or silent?
            return

        standings = {'requestTime': dt.datetime.now().strftime(TIME_FORMAT), 'Central': {}, 'Pacific': {},
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

        self.resp_queue.put(('save_standings', [standings], {}))

        return

    def get_schedule(self):  # , pass_data=False):
        _logger.info(f'Get {self.team} schedule')

        try:
            response = requests.get('https://api-web.nhle.com/v1/club-schedule-season/' + self.team + '/now').json()
        except requests.exceptions.JSONDecodeError:
            _logger.error('No response for schedule API request!  Try again in 5 minutes.')
            self.sched_next_get_time = dt.datetime.now().astimezone(None) + dt.timedelta(minutes=5)
            # self.resp_queue.put(('save_schedule', [None], {}))  # should failure be passed on or silent?
            return

        schedule = {'requestTime': dt.datetime.now().strftime(TIME_FORMAT), 'team': self.team, 'games': []}
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

        self.resp_queue.put(('save_schedule', [schedule], {}))

        return

    def get_roster(self):  # , pass_data=False):
        _logger.info(f'Get {self.team} roster')

        try:
            response = requests.get('https://api-web.nhle.com/v1/club-stats/' + self.team + '/now').json()
        except requests.exceptions.JSONDecodeError:
            _logger.error('No response for roster API request!  Try again in 5 minutes.')
            self.roster_next_get_time = dt.datetime.now().astimezone(None) + dt.timedelta(minutes=5)
            # self.resp_queue.put(('save_roster', [None], {}))  # should failure be passed on or silent?
            return

        roster = {'requestTime': dt.datetime.now().strftime(TIME_FORMAT), 'team': self.team, 'skaters': [],
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

        self.resp_queue.put(('save_roster', [roster], {}))

        return

    def get_game(self, game_id):  # , pass_data=False):
        _logger.debug(f'Get live data from game {game_id}')

        try:
            response = requests.get('https://api-web.nhle.com/v1/gamecenter/' + str(game_id) + '/play-by-play').json()
        except requests.exceptions.JSONDecodeError:
            _logger.error('No response for live game API request!  Try again in 5 minutes.')
            # self._next_get_time = dt.datetime.now().astimezone(None) + dt.timedelta(minutes=5)
            # self.resp_queue.put(('save_standings', [None], {}))  # should failure be passed on or silent?
            return

        game = {'id': response['id'],
                'awayTeam': response['awayTeam']['abbrev'], 'homeTeam': response['homeTeam']['abbrev'],
                'awayScore': response['awayTeam']['score'], 'homeScore': response['homeTeam']['score'],
                'awaySog': response['awayTeam']['sog'], 'homeSog': response['homeTeam']['sog'],
                'gameState': response['gameState'], 'period': response['periodDescriptor']['number'],
                'clock': response['clock']['timeRemaining'], 'inIntermission': response['clock']['inIntermission'],
                'plays': []}

        for play in response['plays']:
            try:
                if play['typeDescKey'] == 'goal':
                    game['plays'].append({'typeDescKey': 'goal', 'period': play['periodDescriptor']['number'],
                                          'timeInPeriod': play['timeInPeriod'],
                                          'scoringPlayerId': play['details']['scoringPlayerId']})
            except KeyError:
                _logger.error('KeyError in League().get_game()')

        # _logger.debug(f'league dump {game}')
        self.resp_queue.put(('update_live_game', [game], {}))

        return

    def run(self):
        _logger.info('Start League() thread running')

        while True:
            current_dt = dt.datetime.now().astimezone(None)

            # run regularly scheduled standings request
            if self.standings_next_get_time < current_dt:
                _logger.info('Trigger League standings request')

                self.get_standings()  # pass_data=True)
                self.standings_next_get_time = self.standings_next_get_time + dt.timedelta(hours=self.period_hours)
                sleep(0.1)

            if self.sched_next_get_time < current_dt:
                _logger.info(f'Trigger {self.team} schedule request')

                self.get_schedule()  # pass_data=True)
                self.sched_next_get_time = self.sched_next_get_time + dt.timedelta(hours=self.period_hours)
                sleep(0.1)

            if self.roster_next_get_time < current_dt:
                _logger.info(f'Trigger {self.team} roster request')

                self.get_roster()  # pass_data=True)
                self.roster_next_get_time = self.roster_next_get_time + dt.timedelta(hours=self.period_hours)
                sleep(0.1)

            # handle incoming immediate requests
            if not self.req_queue.empty():
                # !!! insert while queue not empty loop here
                func_and_args = self.req_queue.get()
                method = func_and_args[0]
                args = func_and_args[1]
                kwargs = func_and_args[2]
                try:
                    getattr(self, method)(*args, **kwargs)
                except AttributeError:
                    _logger.error(f'No such method {func_and_args[0]} in League() class!')

            sleep(0.1)

class Bank(threading.Thread):
    """
    Threading class that acts as intermediary between gui and requesting thread
    """
    def __init__(self, kill_flag, resp_queue, league_queue, gui_queue):
        threading.Thread.__init__(self)  # , daemon=True)

        self.kill_flag = kill_flag
        self.resp_queue = resp_queue
        self.league_queue = league_queue
        self.gui_queue = gui_queue

        # self.last_game_id = ''
        # self.current_game_id = ''
        # self.next_game_id = ''
        self.last_game = {}
        self.current_game = {}  # metadata from schedule
        self.next_game = {}
        self.game_update_time = dt.datetime.now().astimezone(None) + dt.timedelta(days=500)  # just set to now() to establish data type
        self.live_game = {}  # play by play api

        # load league standings
        try:
            _logger.debug('Bank().init retrieve standings.json')
            with open('resources/standings.json') as f:
                self.standings = json.load(f)
                # refresh standings if old
                if dt.datetime.now().astimezone(None) - dt.datetime.strptime(self.standings['requestTime'], TIME_FORMAT).astimezone(None) \
                        > dt.timedelta(hours=6):
                    self.league_queue.put(('get_standings', [], {}))  # 'pass_data': True}))
        except FileNotFoundError:
            _logger.debug('Bank().init standings.json does not exist, make request')
            self.standings = {}
            # make request to get league standings immediately rather than wait
            self.league_queue.put(('get_standings', [], {}))  # 'pass_data': True}))

        # load team schedule
        try:
            _logger.debug('Bank().init retrieve schedule.json')
            with open('resources/schedule.json') as f:
                self.schedule = json.load(f)
                # refresh schedule if old
                # !!! refresh if existing schedule is for team other than current active in settings
                if dt.datetime.now().astimezone(None) - dt.datetime.strptime(self.schedule['requestTime'], TIME_FORMAT).astimezone(None) \
                        > dt.timedelta(hours=6):
                    self.league_queue.put(('get_schedule', [], {}))  # 'pass_data': True}))

            # self.check_games_time = dt.datetime.now()
            self.set_game_ids()
        except FileNotFoundError:
            _logger.debug('Bank().init schedule.json does not exist, make request')
            self.schedule = {}
            # make request to get league standings immediately rather than wait
            self.league_queue.put(('get_schedule', [], {}))  # 'pass_data': True}))
            # if no schedule exists make sure to check for games in 5 seconds
            # self.check_games_time = dt.datetime.now().astimezone(None) + dt.timedelta(seconds=5)

        # load team roster
        try:
            _logger.debug('Bank().init retrieve roster.json')
            with open('resources/roster.json') as f:
                self.roster = json.load(f)
                # refresh roster if old
                # !!! refresh if existing roster if for team other than current active in settings
                if dt.datetime.now().astimezone(None) - dt.datetime.strptime(self.roster['requestTime'], TIME_FORMAT).astimezone(None) \
                        > dt.timedelta(hours=6):
                    self.league_queue.put(('get_roster', [], {}))  # 'pass_data': True}))
        except FileNotFoundError:
            _logger.debug('Bank().init roster.json does not exist, make request')
            self.roster = {}
            # make request to get league standings immediately rather than wait
            self.league_queue.put(('get_roster', [], {}))  # 'pass_data': True}))

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
        # if not os.path.isfile('resources/schedule.json'):
        #     first_time = True
        # else:
        #     first_time = False

        with open('resources/schedule.json', 'w') as f:
            json.dump(self.schedule, f, indent=2)  # noqa (ignore pycharm false pos)

        # if first_time:
        #     self.set_game_ids()
        # if current_game is not set, then it is safe to run and possibly update game_update_time
        # this should be run in case of schedule changes
        if not self.current_game:
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
        # if not self.schedule:
        #     self.check_games_time = dt.datetime.now().astimezone(None) + dt.timedelta(seconds=5)
        #     return

        current_dt = dt.datetime.now().astimezone(None)
        last_gt = current_dt - dt.timedelta(days=1)
        for ii, game in enumerate(self.schedule['games']):
            game_time = dt.datetime.strptime(game['startTimeUTC'], SCHED_TIME_FORMAT).astimezone(None)

            #  handle first game with no previous game
            try:
                self.last_game = self.schedule['games'][ii - 1]
                last_gt = dt.datetime.strptime(self.last_game['startTimeUTC'], SCHED_TIME_FORMAT).astimezone(None)
            except KeyError:
                self.last_game = {}
                pass

            # check if current time is in window where game is likely occurring
            if game_time - dt.timedelta(minutes=15) <= current_dt <= game_time + dt.timedelta(hours=6):
                # handle if last game with no more games
                try:
                    self.next_game = self.schedule['games'][ii + 1]
                    next_gt = dt.datetime.strptime(self.next_game['startTimeUTC'], SCHED_TIME_FORMAT).astimezone(None)
                except KeyError:
                    self.next_game = {}
                    next_gt = dt.datetime.now().astimezone(None) + dt.timedelta(days=500)

                try:
                    # check if game is over
                    if self.live_game['gameState'] in ('OFF', 'FINAL'):
                        self.live_game = {}
                        self.last_game = game
                        self.current_game = {}
                        self.game_update_time = next_gt - dt.timedelta(minutes=15)
                    else:
                        _logger.debug('Bank().set_game_ids: found likely live game, but live_game not set')
                        self.current_game = game
                        self.game_update_time = dt.datetime.now().astimezone(None) + dt.timedelta(minutes=1)
                except KeyError:
                    _logger.debug('Bank().set_game_ids: found likely live game')
                    # live_game hasn't been set yet, assume if killed elsewhere, then game_update_time would be in far
                    # future
                    self.current_game = game
                    self.game_update_time = dt.datetime.now().astimezone(None)  # + dt.timedelta(minutes=1)
                break

            elif last_gt <= current_dt <= game_time:  # in between games
                self.live_game = {}  # probably unnecessary
                self.current_game = {}
                self.next_game = game
                self.game_update_time = game_time - dt.timedelta(minutes=15)
                break
        else:
            self.last_game = self.schedule['games'][-1]  # last game of season
            self.live_game = {}  # probably unnecessary
            self.current_game = {}
            self.next_game = {}
            self.game_update_time = dt.datetime.now().astimezone(None) + dt.timedelta(days=500)

        return

    def update_live_game(self, game):
        _logger.debug('Bank(): update_live_game')
        intermission = 'Intermission' if game['inIntermission'] else 'Period'
        _logger.info(f'Bank().update_live_game: {game["awayTeam"]}: {game["awayScore"]} @ '
                     f'{game["homeTeam"]}: {game["homeScore"]} | {intermission} {game["period"]}, {game["clock"]} | '
                     f'{game["id"]}')
        # _logger.debug(f'bank dump {game}')

        if game['gameState'] in ('OFF', 'FINAL'):
            # game is over, set live_game (play by play) and current_game (metadata) to empty sets, set next time
            self.live_game = {}
            self.last_game = self.current_game
            self.current_game = {}

            try:
                next_game_time = dt.datetime.strptime(self.next_game['startTimeUTC'], SCHED_TIME_FORMAT).astimezone(None)
                self.game_update_time = next_game_time - dt.timedelta(minutes=15)
            except KeyError:
                self.game_update_time = dt.datetime.now().astimezone(None) + dt.timedelta(days=500)
            self.league_queue.put(('get_standings', [], {'delay': 15}))  # update standings in 15 minutes
        else:
            self.live_game = game
            self.game_update_time = dt.datetime.now().astimezone(None) + dt.timedelta(minutes=1)

        return

    def run(self):
        _logger.info('Start Bank() thread')
        try:
            while not self.kill_flag:
                current_dt = dt.datetime.now().astimezone(None)

                # handle incoming immediate requests
                if not self.resp_queue.empty():
                    # !!! add while queue not empty loop here
                    _logger.debug('League to Bank Queue has a response')
                    func_and_args = self.resp_queue.get()
                    method = func_and_args[0]
                    args = func_and_args[1]
                    kwargs = func_and_args[2]
                    try:
                        getattr(self, method)(*args, **kwargs)
                    except AttributeError:
                        _logger.debug(f'No such method {func_and_args[0]} in Bank() class!')

                if self.game_update_time < current_dt:
                    _logger.debug('Bank will make live game update request')
                    if not self.current_game:
                        # if for some reason self.current_game_id is not set, then make sure it is set or
                        # self.game_update_time is > current_dt
                        self.set_game_ids()
                    else:
                        self.league_queue.put(('get_game', [self.current_game['id']], {}))  # 'pass_data': True}))
                        # set to make next request in 5 minutes in case get_game doesn't get a response
                        self.game_update_time = dt.datetime.now().astimezone(None) + dt.timedelta(minutes=5)

                sleep(0.1)


        finally:
            _logger.debug(f'Thread {self.name} performing cleanup')
            # Perform any cleanup
            _logger.debug(f'Thread {self.name} stopped.')
