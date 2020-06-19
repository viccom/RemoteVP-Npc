import logging
import threading
import struct
import binascii
import pythoncom
import win32com.client
from apps.vserial import *
from helper import _dict, APPCtrl
from apps.vserial.com_worker import COM_Worker

BaudRate_map = {"110": 1, "300": 2, "600": 3, "1200": 4, "2400": 5, "4800": 6, "9600": 7, "19200": 8, "38400": 9,
    "57600": 10, "115200": 11, "460800": 12, "921600": 13}


class VSPortEventHandler:
    def OnBaudRate(self, lBaudRate): pass
    def OnDTR(self, bOn): pass
    def OnHandFlow(self, lControlHandleShake, lFlowReplace, lXonLimit, lXOffLimit): pass
    def OnLineControl(self, cStopBits, cParity, cWordLength): pass
    def OnOpenClose(self, bOpened): pass
    def OnRxChar(self, lCount): pass
    def OnRTS(self, bOn): pass
    def OnSpecialChars(self, cEofChar, cErrorChar, cBreakChar, cEventChar, cXOnChar, cXoffChar): pass
    def OnTimeouts(self,  lReadIntervalTimeout, lReadTotalTimeoutMultiplier, lReadTotalTimeoutConstant, lWriteTotalTimeoutMultiplier, lWriteTotalTimeoutConstant): pass
    def OnEvent(self, EvtMask): pass
    def OnBreak(self, bOn): pass


class Handler:
    def __init__(self, port_key):
        self._port_key = port_key
        self._recv_count = 0
        self._send_count = 0
        self._stream_pub = None
        self._com_params = [0] * 6
        self._enable_packetheader = APPCtrl().get_packetheader()
        self._com_worker = COM_Worker(self)

    def start(self):
        self._com_worker.start()

    def stop(self):
        self._com_worker.stop()

    def init_vsport(self):
        this_handler = self

        class innerHandler:
            def __init__(self):
                self._handler = this_handler

            def OnBaudRate(self, lBaudRate):
                pass #print('OnBaudRate', lBaudRate)

                return self._handler.OnBaudRate(lBaudRate)

            def OnDTR(self, bOn):
                pass #print('OnDTR', bOn)
                #return self._handler.OnDTR(bOn)

            def OnHandFlow(self, lControlHandleShake, lFlowReplace, lXonLimit, lXOffLimit):
                pass #print('OnHandFlow', lControlHandleShake, lFlowReplace, lXonLimit, lXOffLimit)
                #return self._handler.OnHandFlow(lControlHandleShake, lFlowReplace, lXonLimit, lXOffLimit)

            def OnLineControl(self, cStopBits, cParity, cWordLength):
                pass  # print('OnLineControl', cStopBits, cParity, cWordLength)
                return self._handler.OnLineControl(cStopBits, cParity, cWordLength)

            def OnOpenClose(self, bOpened):
                pass  # print('OnOpenClose', bOpened)
                #return self._handler.OnOpenClose(bOpened)

            def OnRxChar(self, lCount):
                pass #print('OnRxChar', lCount)
                return self._handler.OnRxChar(lCount)

            def OnRTS(self, bOn):
                pass  #  print('OnRTS', bOn)
                #return self._handler.OnRTS(bOn)

            def OnSpecialChars(self, cEofChar, cErrorChar, cBreakChar, cEventChar, cXOnChar, cXoffChar):
                pass  #  print('OnSpecialChars', cEofChar, cErrorChar, cBreakChar, cEventChar, cXOnChar, cXoffChar)
                #return self._handler.OnSpecialChars(cEofChar, cErrorChar, cBreakChar, cEventChar, cXOnChar, cXoffChar)

            def OnTimeouts(self, lReadIntervalTimeout, lReadTotalTimeoutMultiplier, lReadTotalTimeoutConstant,
                           lWriteTotalTimeoutMultiplier, lWriteTotalTimeoutConstant):
                pass # print('OnTimeouts', lReadIntervalTimeout, lReadTotalTimeoutMultiplier, lReadTotalTimeoutConstant, lWriteTotalTimeoutMultiplier, lWriteTotalTimeoutConstant)

            def OnEvent(self, EvtMask):
                pass  # print('OnEvent', EvtMask)
                #return self._handler.OnEvent(EvtMask)

            def OnBreak(self, bOn):
                pass  # print('OnBreak', bOn)
                #return self._handler.OnBreak(bOn)
        try:
            pythoncom.CoInitialize()
            self._vsport = win32com.client.DispatchWithEvents(VSPort_ActiveX_ProgID, innerHandler)
            logging.info("VSPort create port: {0}".format(self._port_key))
            bRet = self._vsport.CreatePort(self._port_key)
            if not bRet:
                logging.info("Already created, try to Attach to port: {0}".format(self._port_key))
                bRet = self._vsport.Attach(self._port_key)
            if not bRet:
                logging.error("Attach to port: {0} failed!!!".format(self._port_key))
                self._vsport.Delete()
                return False
            else:
                logging.info("Attached to port: {0}".format(self._port_key))
            self._vsport.SetWiring(0x20, 0x10, 0, 0)
            self._vsport.PurgeQueue()
            if self._stream_pub:
                self._stream_pub.vspax_notify(self._port_key, 'ADD', {"name": self._port_key})
            return True
        except Exception as ex:
            logging.exception(ex)
            return False

    def close_vsport(self):
        try:
            logging.info("VSPort remove port: {0}".format(self._port_key))
            if self._stream_pub:
                self._stream_pub.vspax_notify(self._port_key, 'REMOVE', {"name": self._port_key})
            self._vsport.Delete()
        except Exception as ex:
            logging.exception(ex)

    def is_port(self, name):
        return self._port_key == name or str(self._port_key) == name

    def get_port_key(self):
        return self._port_key

    def set_stream_pub(self, stream_pub):
        self._stream_pub = stream_pub

    def socket_out_pub(self, data):
        if self._stream_pub:
            self._stream_pub.socket_out_pub(self._port_key, data)

    def socket_in_pub(self, data):
        if self._stream_pub:
            self._stream_pub.socket_in_pub(self._port_key, data)

    def peer_dict(self):
        pass

    def on_recv(self, data):
        pass

    def as_dict(self):
        data = _dict({})
        data['name'] = self._port_key
        data['port_name'] = self._port_key
        data['pid'] = self._vsport.PortOpenAppId
        data['app_path'] = self._vsport.PortOpenAppPath
        data['recv_count'] = self._recv_count
        data['send_count'] = self._send_count
        data['BaudRate'] = self._vsport.Baudrate
        data['DataBits'] = self._vsport.Databits
        data['Parity'] = self._vsport.Parity
        data['StopBits'] = self._vsport.StopBits
        peer_data = self.peer_dict() or {}
        data.update(peer_data)
        return data

    def clean_count(self):
        self._recv_count = 0
        self._send_count = 0

    def send(self, data):
        #logging.info("Serial Write: {0}".format(len(data)))
        ret = self._vsport.WriteArray(bytearray(data))
        if ret > 0:
            self._send_count += ret
            if self._stream_pub:
                self._stream_pub.vspax_out_pub(self._port_key, data)

            if ret != len(data):
                logging.error("Write Return is not equal to data length")
        return ret

    def OnRxChar(self, lCount):
        data = self._vsport.ReadArray(lCount)
        if data:
            data = data.tobytes()
            if self._enable_packetheader:
                fixedbin = b'\xfe'
                for v in self._com_params:
                    fixedbin = fixedbin + struct.pack('b', v)
                data = fixedbin + b'\xef' + data
            # print(self._com_params)
            # logging.info("Serial Got: {0}".format(len(data)))
            # print("send data to remote::", str(binascii.b2a_hex(fixedbin + data))[2:-1].upper())
            self.on_recv(data)
            # self.on_recv(data)
            if self._stream_pub:
                self._recv_count += len(data)
                self._stream_pub.vspax_in_pub(self._port_key, data)

    def OnBaudRate(self, lBaudRate):
        if lBaudRate < 110:
            lBaudRate = 110
        if BaudRate_map.get(str(lBaudRate)):
            self._com_params[0] = BaudRate_map.get(str(lBaudRate))
            if self._stream_pub:
                self._stream_pub.vspax_notify(self._port_key, 'CHANGE', {"name": self._port_key, "params": self._com_params})
        else:
            logging.info("This BaudRate {0} is unsupported".format(str(lBaudRate)))
            if self._stream_pub:
                self._stream_pub.vspax_notify(self._port_key, 'CHANGE', {"name": self._port_key, "error": "This BaudRate {0} is unsupported".format(str(lBaudRate))})
        # print("BaudRate change to::", self._com_params)

    def OnLineControl(self, cStopBits, cParity, cWordLength):
        self._com_params[1] = cStopBits
        self._com_params[2] = cParity
        self._com_params[3] = cWordLength
        if self._stream_pub:
            self._stream_pub.vspax_notify(self._port_key, 'CHANGE', {"name": self._port_key, "params": self._com_params})
        # print("params change to::", self._com_params)
