# import requests
import json
# import os.path

# from time import time as _time
from time import sleep
# import datetime as dt
# import math

# import threading
import queue

from api_threading import League, Bank, KillFlag
import logging


logging.basicConfig(level=logging.DEBUG)
_logger = logging.getLogger(__name__)
# logger levels: NOTSET   =  0
#                DEBUG    = 10
#                INFO     = 20
#                WARN     = 30
#                ERROR    = 40
#                CRITICAL = 50


def get_settings():
    try:
        with open('resources/settings.json') as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {'team': 'PHI',
                    'period': 6,  # time in hours to routinely refresh standings, schedule, roster, etc
                    }

    return settings


def main():
    settings = get_settings()
    # standings_tod = dt.timedelta(hours=settings['period'])
    # sched_tod = dt.timedelta(hours=settings['schedule']['hour'], minutes=settings['schedule']['minute'])

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
        league_thread = League(resp_to_bank_queue, req_to_league_queue, team=settings['team'],
                               period_hours=settings['period'])  # , standings_tod=standings_tod,
                               # sched_period_days=settings['schedule']['period'], sched_tod=sched_tod)
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
