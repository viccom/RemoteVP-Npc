import logging
import pythoncom
import win32com.client
import time
from apps.vserial import *


class VSPort():
    def __init__(self):
        self._vsport = None
        self._thread_stop = False

    def init(self):
        try:
            pythoncom.CoInitialize()
            self._vsport = win32com.client.Dispatch(VSPort_ActiveX_ProgID)
        except Exception as ex:
            logging.exception(ex)

    def close(self):
        self._vsport.Delete()

    def ResetBus(self):
        if not self._vsport:
            return False
        self._vsport.ResetBus()

    def ListVir(self):
        if not self._vsport:
            return []
        ports = []
        for i in range(0, self._vsport.CountVirtualPort):
            ports.append(self._vsport.EnumVirtualPort(i))

        return ports
