import requests
import json

from time import time as _time
from time import sleep
import datetime as dt

import threading
import queue

import logging


logging.basicConfig(level=logging.DEBUG)
_logger = logging.getLogger(__name__)
# logger levels: NOTSET   =  0
#                DEBUG    = 10
#                INFO     = 20
#                WARN     = 30
#                ERROR    = 40
#                CRITICAL = 50

# TIME_ZONE = dt.datetime.now(dt.timezone.utc).astimezone().tzinfo
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

class KillFlag(threading.Event):
    """A wrapper for the typical event class to allow for overriding the
    `__bool__` magic method, since it looks nicer.
    """
    def __bool__(self):
        return self.is_set()


class League(threading.Thread):
    def __init__(self, resp_queue, req_queue, team='PHI', standings_period_days=1,
                 standings_tod=dt.timedelta(hours=4, minutes=0), sched_period_days=7,
                 sched_tod=dt.timedelta(hours=4, minutes=5)):
        threading.Thread.__init__(self, daemon=True)

        self.resp_queue = resp_queue
        self.req_queue = req_queue
        self.team = team
        self.standings_period_days = standings_period_days
        self.standings_tod = standings_tod
        self.sched_period_days = sched_period_days
        self.sched_tod = sched_tod

        self.next_get_time = (dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) +
                              dt.timedelta(self.standings_period_days) + self.standings_tod)

        _logger.info('Initialize League() thread')
        return

    def get_standings(self, pass_data=False):
        _logger.info('Get League standings')

        response = requests.get('https://api-web.nhle.com/v1/standings/now').json()

        standings = {'RequestTime': dt.datetime.now().strftime(TIME_FORMAT), 'Central': [], 'Pacific': [],
                     'Atlantic': [], 'Metropolitan': [], 'Western': [], 'Eastern': []}
        for team in response['standings']:
            team_red = [team['teamName']['default'], team['teamAbbrev']['default'], int(team['gamesPlayed']),
                        int(team['wins']), int(team['losses']), int(team['otLosses']), int(team['points']),
                        float(team['pointPctg'])]
            if len(standings[team['divisionName']]) < 3:
                standings[team['divisionName']].append(team_red)
            else:
                standings[team['conferenceName']].append(team_red)

        for conf in standings:
            if conf in ('Western', 'Eastern'):
                standings[conf] = sorted(standings[conf], key=lambda x: (-x[6], -x[7]))

        if pass_data:
            self.resp_queue.put(('save_standings', [standings], {}))
            pass
        return

    # def load_standings(self):
    #     return

    # def save_standings(self):
    #     return

    def run(self):
        _logger.info('Start League() thread running')

        while True:
            # run regularly scheduled standings request
            current_dt = dt.datetime.now()
            if (self.next_get_time - current_dt) < dt.timedelta(0):  # noqa (ignore pycharm false pos)
                _logger.info('Trigger League standings request')

                self.get_standings(pass_data=True)
                self.next_get_time = self.next_get_time + dt.timedelta(self.standings_period_days)

            # handle incoming immediate requests
            if not self.req_queue.empty():
                func_and_args = self.req_queue.get()
                method = func_and_args[0]
                args = func_and_args[1]
                kwargs = func_and_args[2]
                try:
                    getattr(self, method)(*args, **kwargs)
                except AttributeError:
                    _logger.debug(f'No such method {func_and_args[0]} in League() class!')


class Bank(threading.Thread):
    def __init__(self, kill_flag, resp_queue, league_queue, gui_queue):
        threading.Thread.__init__(self)  # , daemon=True)

        self.kill_flag = kill_flag
        self.resp_queue = resp_queue
        self.league_queue = league_queue
        self.gui_queue = gui_queue

        try:
            with open('resources/standings.json') as f:
                self.standings = json.load(f)
                # refresh standings if old
                if dt.datetime.now() - dt.datetime.strptime(self.standings['RequestTime'], TIME_FORMAT) \
                        > dt.timedelta(days=1):
                    self.league_queue.put(('get_standings', [], {'pass_data': True}))
        except FileNotFoundError:
            self.standings = {}
            # make request to get league standings immediately rather than wait
            self.league_queue.put(('get_standings', [], {'pass_data': True}))

        _logger.info('Initialize Bank() thread')
        return

    def save_standings(self, standings):
        _logger.info('Save standings to file')
        self.standings = standings
        with open('resources/standings.json', 'w') as f:
            json.dump(self.standings, f, indent=2)  # noqa (ignore pycharm false pos)

        return

    def run(self):
        _logger.info('Start Bank() thread')
        try:
            while not self.kill_flag:
                # handle incoming immediate requests
                if not self.resp_queue.empty():
                    func_and_args = self.resp_queue.get()
                    method = func_and_args[0]
                    args = func_and_args[1]
                    kwargs = func_and_args[2]
                    try:
                        getattr(self, method)(*args, **kwargs)
                    except AttributeError:
                        _logger.debug(f'No such method {func_and_args[0]} in Bank() class!')
        finally:
            _logger.debug(f'Thread {self.name} performing cleanup')
            # Perform any cleanup
            _logger.debug(f'Thread {self.name} stopped.')


def main():
    # create event flag for terminating non-daemon threads
    kill_flag = KillFlag()
    non_daemon_threads = []

    try:
        # queue to pass api responses to local bank
        resp_to_bank_queue = queue.Queue()   # in triplet format: ('method_name', [arg_list], {'kwarg': 'dict'})

        # queue to pass requests to the league thread
        req_to_league_queue = queue.Queue()  # in triplet format: ('method_name', [arg_list], {'kwarg': 'dict'})

        # queue to pass gui requests to bank
        gui_to_bank_queue = queue.Queue()

        # initialize threads
        league_thread = League(resp_to_bank_queue, req_to_league_queue)
        bank_thread = Bank(kill_flag, resp_to_bank_queue, req_to_league_queue, gui_to_bank_queue)

        league_thread.name = 'League'
        bank_thread.name = 'Bank'

        # collect non daemon threads for careful termination
        non_daemon_threads.append(bank_thread)

        # start threads
        league_thread.start()
        bank_thread.start()

        # sleep for testing
        sleep(5)
    except KeyboardInterrupt:
        _logger.debug('Interrupt received, setting quit flag.')
        kill_flag.set()
    finally:
        _logger.debug('Starting termination, setting quit flag.')
        kill_flag.set()  # ensure flag is set

        # Join threads
        _logger.debug('Attempting to join threads')
        while non_daemon_threads:
            for thread in non_daemon_threads:
                thread.join(0.1)
                if thread.is_alive():
                    _logger.debug(f'Thread {thread.name} not ready to join.')
                else:
                    _logger.debug(f'Thread {thread.name} successfully joined.')
                    non_daemon_threads.remove(thread)
        _logger.debug('Program terminated')

    return


if __name__ == '__main__':
    main()
