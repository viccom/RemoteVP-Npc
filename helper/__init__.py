import ctypes, sys
import socket
import os
import re
import base64
from urllib.parse import urlsplit
from configparser import ConfigParser


def to_dict(str):
	import ast
	r = None
	try:
		r = ast.literal_eval(str)
	except Exception as ex:
		pass
	finally:
		if type(r) is dict:
			return r
		else:
			return {}


def failure(id, error_msg, extra=None):
	assert (id is not None)
	assert (error_msg is not None)
	return {"id": str(id), "result": False, "error": error_msg, "extra": extra}


def success(id, data, extra=None):
	assert (id is not None)
	assert (data is not None)
	return {"id": str(id), "result": True, "data": data, "extra": extra}


class _dict(dict):
	"""dict like object that exposes keys as attributes"""

	def __getattr__(self, key):
		ret = self.get(key)
		if not ret and key.startswith("__"):
			raise AttributeError()
		return ret

	def __setattr__(self, key, value):
		self[key] = value

	def __getstate__(self):
		return self

	def __setstate__(self, d):
		self.update(d)

	def update(self, d):
		"""update and return self -- the missing dict feature in python"""
		super(_dict, self).update(d)
		return self

	def copy(self):
		return _dict(dict(self).copy())



class APPCtrl:

	def get_heartbeat(self):
		config = ConfigParser()
		if os.access(os.getcwd() + '\\config.ini', os.F_OK):
			config.read('config.ini')
			if config.has_option('system', 'enable_heartbeat'):
				if config.getint('system', 'enable_heartbeat') == 0:
					return False
				else:
					return True
			else:
				return True

	def get_packetheader(self):
		config = ConfigParser()
		if os.access(os.getcwd() + '\\config.ini', os.F_OK):
			config.read('config.ini')
			if config.has_option('system', 'enable_packetheader'):
				if config.getint('system', 'enable_packetheader') == 0:
					return False
				else:
					return True
			else:
				return True

	def get_accesskey(self):
		config = ConfigParser()
		if os.access(os.getcwd() + '\\config.ini', os.F_OK):
			config.read('config.ini')
			if config.has_option('thingscloud', 'accesskey'):
				if len(config.get('thingscloud', 'accesskey')) == 48:
					return base64.b64decode(config.get('thingscloud', 'accesskey').encode()).decode()
			else:
				return None
		else:
			return None


def is_admin():
	try:
		return ctypes.windll.shell32.IsUserAnAdmin()
	except:
		return False

def is_ipv4(ip):
	try:
		socket.inet_pton(socket.AF_INET, ip)
	except AttributeError:  # no inet_pton here, sorry
		try:
			socket.inet_aton(ip)
		except socket.error:
			return False
		return ip.count('.') == 3
	except socket.error:  # not a valid ip
		return False
	return True


class urlCheck:
	__pattern = re.compile(r'^(([a-zA-Z]{1})|([a-zA-Z]{1}[a-zA-Z]{1})|'
	                     r'([a-zA-Z]{1}[0-9]{1})|([0-9]{1}[a-zA-Z]{1})|'
	                     r'([a-zA-Z0-9][-_.a-zA-Z0-9]{0,61}[a-zA-Z0-9]))\.'
	                     r'([a-zA-Z]{2,13}|[a-zA-Z0-9-]{2,30}.[a-zA-Z]{2,3})$')

	def __init__(self, n):
		self.name = n

	def get_url(self):
		ret = None
		if self.is_domain():
			ret = "http://" + self.name
		elif self.is_ipv4():
			ret = "http://" + self.name
		else:
			parsed = urlsplit(self.name)
			if not parsed.path == self.name:
				ret = parsed.scheme + "://" + parsed.netloc
		return ret

	def get_host(self):
		ret = None
		if self.is_domain():
			ret = self.name
		elif self.is_ipv4():
			ret = self.name.split(":")[0]
		else:
			parsed = urlsplit(self.name)
			if not parsed.path == self.name:
				ret = parsed.netloc.split(":")[0]
		return ret

	def is_domain(self):
		return True if self.__pattern.match(self.name) else False

	def is_ipv4(self):
		try:
			socket.inet_pton(socket.AF_INET, (self.name))
		except AttributeError:
			try:
				socket.inet_aton(self.name)
			except socket.error:
				return False
			return self.name.count('.') == 3
		except socket.error:
			return False
		return True
