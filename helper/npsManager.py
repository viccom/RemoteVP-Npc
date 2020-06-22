#!/usr/bin/python
# -*- coding: UTF-8 -*-
import re
import logging
import binascii
from Crypto.Cipher import AES
import requests


class npsApiv1():
	def __init__(self, api_srv):
		self.base_srv = api_srv
		self.session = None

	def create_session(self):
		session = requests.session()
		session.headers['Accept'] = 'application/json'
		return session

	def nps_api_get(self, url_path):
		if not self.session:
			self.session = self.create_session()
		try:
			r = self.session.get(self.base_srv + url_path, allow_redirects=True, timeout=3)
			# print("@@@@@@", r.status_code, r.json())
			assert r.status_code == 200, logging.error("返回值不是期望的")
			if r.status_code == 200:
				return r.json()
			else:
				return {}
		except Exception as ex:
			logging.error(ex)
			return {}

	def nps_api_post(self, url_path, data):
		if not self.session:
			self.session = self.create_session()
		try:
			# print("@@@@@@@@@@@@@@@---------------", self.base_srv + url_path)
			r = self.session.post(self.base_srv + url_path, allow_redirects=False, timeout=3, data=data)
			# print("@@@@@@", r.status_code, r.is_redirect, r.is_permanent_redirect)
			assert r.status_code == 200, logging.error("返回值不是期望的")
			if r.status_code == 200:
				return r.json()
			else:
				return {}
		except Exception as ex:
			logging.error(ex)
			return {}


class npsCryp:
	def __init__(self, key=None):
		self.__key = key or "viccom@@dongbala"  # 密钥（长度必须为16、24、32）
		self.__mode = AES.MODE_CBC
		self.__bs = 16  # block size
		self.__PADDING = lambda s: s + (self.__bs - len(s) % self.__bs) * chr(self.__bs - len(s) % self.__bs)

	def add_to_16(self, value):
		while len(value) % 16 != 0:
			value += '\0'
		return str.encode(value)

	def encrypt(self, plainStr):
		aes = AES.new(self.add_to_16(self.__key), self.__mode, self.add_to_16(self.__key))
		encrypt_aes = aes.encrypt(self.add_to_16(plainStr))
		# result = str(base64.encodebytes(encrypt_aes), encoding='utf-8')
		result = binascii.b2a_hex(encrypt_aes).decode()
		return result

	def decrypt(self, securityStr):
		aes = AES.new(self.add_to_16(self.__key), self.__mode, self.add_to_16(self.__key))
		# base64_decrypted = base64.decodebytes(securityStr.encode(encoding="utf-8"))
		# result = str(aes.decrypt(base64_decrypted), encoding='utf-8').replace('\0', '')
		decrpyt_bytes = binascii.a2b_hex(securityStr)
		try:
			result = re.compile('[\\x00-\\x08\\x0b-\\x0c\\x0e-\\x1f\n\r\t]').sub('',
			                                                                     aes.decrypt(decrpyt_bytes).decode())
		except Exception:
			logging.error('解码失败，请重试!')
			result = None
		return result
