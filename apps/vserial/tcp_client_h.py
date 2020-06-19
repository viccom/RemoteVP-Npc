import logging
import threading
import socket
import select
import time
from apps.vserial.handler import Handler


class TcpClientHander(Handler, threading.Thread):
    def __init__(self, port_key, host, port, info):
        Handler.__init__(self, port_key)
        threading.Thread.__init__(self)
        self._host = host
        self._port = port
        self._info = info
        self._sock_host = None
        self._sock_port = 0
        self._peer_host = None
        self._peer_port = 0
        self._thread_stop = False
        self._peer_send_count = 0
        self._peer_recv_count = 0
        self._peer_state = ''
        self._socket = None

    def start(self):
        Handler.start(self)
        threading.Thread.start(self)

    def stop(self):
        self._thread_stop = True
        self.join(2)
        Handler.stop(self)

    def run(self):
        while not self._thread_stop:
            try:
                self._peer_state = 'CONNECTING'
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((self._host, self._port))
                s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 0)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, 0)
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                # s.settimeout(0.1)
                logging.info("TCP Client Connected! {0}:{1}".format(self._host, self._port))
                self._sock_host, self._sock_port = s.getsockname()
                self._peer_host, self._peer_port = s.getpeername()
                self._peer_state = 'CONNECTED'
                self._socket = s

                self.run_select()

                if not self._thread_stop:
                    self._sock_host, self._sock_port = None, 0
                    self._peer_host, self._peer_port = None, 0
                    time.sleep(3)
            except Exception as ex:
                logging.exception(ex)
                self._peer_state = 'ERROR'
                if self._socket:
                    self._socket.close()
                    self._socket = None
                time.sleep(3)
                continue

        if self._socket:
            self._socket.close()
            self._socket = None

    def run_select(self):
        inputs = [self._socket]

        while not self._thread_stop:
            readable, writeable, exeptional = select.select(inputs, [], inputs, 1)
            for s in readable:
                if s == self._socket:
                    data = s.recv(1024)
                    if data is not None:
                        if data == b'':
                            raise RuntimeError("socket connection broken")
                        # logging.info("TCP Got: {0}".format(len(data)))
                        self.send(data)
                        self._peer_recv_count += len(data)
                        self.socket_in_pub(data)
                    else:
                        logging.error("Client [{0}:{1}] socket closed!!".format(self._host, self._port))
                        return

            for s in exeptional:
                logging.debug("handling exception for {0}".format(s.getpeername()))
                break

    def peer_dict(self):
        return {
            'type': 'tcp_client',
            'host': self._host,
            'port': self._port,
            'info': self._info,
            'sock_host': self._sock_host,
            'sock_port': self._sock_port,
            'peer_host': self._peer_host,
            'peer_port': self._peer_port,
            'peer_state': self._peer_state,
            'peer_recv_count': self._peer_recv_count,
            'peer_send_count': self._peer_send_count
        }

    def clean_count(self):
        Handler.clean_count()
        self._peer_send_count = 0
        self._peer_recv_count = 0

    def on_recv(self, data):
        if self._socket:
            sent_size = self._socket.send(data)
            # logging.debug("TCP Send: {0} - {1}".format(len(data), sent_size))
            self._peer_send_count += sent_size
            if sent_size == len(data):
                self.socket_out_pub(data)
            else:
                logging.error("Failed to send msg, left data length: {0} ".format(len(data) - sent_size))
                self.socket_out_pub(data[0:sent_size])
        else:
            logging.warning("Socket is not connected!")
