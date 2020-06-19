import threading
import time
from cores.log import log_set, configure_logger
from helper import is_ipv4, APPCtrl
from helper.thingscloud import CloudApiv1


class Manager(threading.Thread):
	def __init__(self, appname):
		threading.Thread.__init__(self)
		self.TRAccesskey = None
		self.TRCloudapi = None
		self._thread_stop = False
		self._appname = appname
		self._log = configure_logger('default', 'logs/service.log')

	def start(self):
		threading.Thread.start(self)

	def run(self):
		while not self._thread_stop:
			time.sleep(1)
		self._log.warning("Close COMMON!")

	def stop(self):
		self._thread_stop = True
		self.join()

	def gatelist(self):
		if not self.TRCloudapi:
			self.TRCloudapi = CloudApiv1(self.TRAccesskey)
		return self.TRCloudapi.get_gate_list()

	def online(self, sn):
		if not self.TRCloudapi:
			self.TRCloudapi = CloudApiv1(self.TRAccesskey)
		return self.TRCloudapi.get_gate_status(sn)
