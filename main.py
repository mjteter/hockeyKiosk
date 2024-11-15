import requests

from time import time as _time
from time import sleep
import datetime as dt

import threading
import queue

import logging


logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(__name__)
# logger levels: NOTSET   =  0
#                DEBUG    = 10
#                INFO     = 20
#                WARN     = 30
#                ERROR    = 40
#                CRITICAL = 50

# TIME_ZONE = dt.datetime.now(dt.timezone.utc).astimezone().tzinfo

class League(threading.Thread):
    def __init__(self, req_queue, period_days=7, tod=dt.timedelta(hours=4, minutes=0)):
        threading.Thread.__init__(self, daemon=True)

        self.req_queue = req_queue
        self.period_days = period_days
        self.tod = tod

        self.next_get_time = (dt.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) +
                              dt.timedelta(self.period_days) + self.tod)

        _logger.info('Initialize League() thread')
        return

    def get_standings(self, pass_data=False):
        _logger.info('Get League standings')

        response = requests.get('https://api-web.nhle.com/v1/standings/now').json()

        standings = {'Central': [], 'Pacific': [], 'Atlantic': [], 'Metropolitan': [], 'Western': [], 'Eastern': []}
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
            self.req_queue.put(standings)
            pass
        return

    def load_standings(self):
        return

    def save_standings(self):
        return

    def run(self):
        _logger.info('Start League() thread running')

        while True:
            current_dt = dt.datetime.now()

            if (self.next_get_time - current_dt) < dt.timedelta(0):
                _logger.info('Trigger League standings request')

                self.get_standings(pass_data=True)
                self.next_get_time = self.next_get_time + dt.timedelta(self.period_days)


class Bank(threading.Thread):
    def __init__(self, req_queue, gui_queue):
        threading.Thread.__init__(self)

        self.req_queue = req_queue
        self.gui_queue = gui_queue

        _logger.info('Initialize Bank() thread')
        return

    def run(self):
        _logger.info('Start Bank() thread')

        return


def main():
    # queue to pass api responses to local bank
    req_to_bank_queue = queue.Queue()

    # queue to pass gui requests to bank
    gui_to_bank_queue = queue.Queue()

    # initialize threads
    league_thread = League(req_to_bank_queue)
    bank_thread = Bank(req_to_bank_queue, gui_to_bank_queue)

    # start threads
    league_thread.start()
    bank_thread.start()


    # sleep for testing
    sleep(5)

    return


if __name__ == '__main__':
    main()
