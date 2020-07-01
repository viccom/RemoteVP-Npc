#!/usr/bin/python
# -*- coding: UTF-8 -*-
import threading
import logging
import time
import json
import subprocess


class SpeedBench(threading.Thread):
	def __init__(self, manager):
		threading.Thread.__init__(self)
		self._manager = manager
		self._start_bench = False
		self._host = None
		self._port = None
		self._size = None
		self._direct = 'upload'
		self._bench_result = None
		self._thread_stop = False

	def start_bench(self, host, port, size=10, direct=False):
		self._start_bench = True
		self._host = host
		self._port = port
		self._direct = direct
		self._size = size
		if size < 1:
			self._size = 1
		if size > 1024:
			self._size = 1024

	def get_result(self):
		if not self._start_bench:
			if self._bench_result:
				return {"result": True, "data": self._bench_result}
			else:
				return {"result": False, "data": None}
		else:
			return {"result": False, "data": 'speedbench is proceeding'}


	def is_bench(self):
		return self._start_bench

	def run(self):
		while not self._thread_stop:
			if not self._start_bench:
				time.sleep(1)
				continue
			benchCMD = r"vnet\iperf3 -c " + self._host + " -p " + str(self._port) + " -J -n " + str(self._size) + "M"
			if self._direct == 'download':
				benchCMD = r"vnet\iperf3 -c " + self._host + " -p " + str(self._port) + " -J -R -n " + str(self._size) + "M"
			try:
				start_time = int(time.time())
				bench_result = bytes.decode(subprocess.check_output(benchCMD, timeout=30, shell=True))
				bench_result = json.loads(bench_result)
				end_time = int(time.time())
				self._bench_result = {"host": self._host, "dir": self._direct, "data": bench_result, "error": None}
			except Exception as ex:
				logging.error(ex)
				self._bench_result = {"host": self._host, "dir": self._direct, "data": None, "error": "超时30秒或其他原因：" + str(ex)}
			self._start_bench = False

	def stop(self):
		self._thread_stop = True
		self.join()
