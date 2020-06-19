import logging
import threading
import pythoncom
import win32com.client
import time
from apps.vserial import *


class COM_Worker(threading.Thread):
    def __init__(self, handler):
        threading.Thread.__init__(self)
        self._handler = handler
        self._thread_stop = False

    def run(self):
        try:
            self._handler.init_vsport()
            while not self._thread_stop:
                pythoncom.PumpWaitingMessages()
                time.sleep(0.001)

            # pythoncom.PumpMessages()
        except Exception as ex:
            logging.exception(ex)

        self._handler.close_vsport()

    def stop(self):
        self._thread_stop = True
        self.join(2)
