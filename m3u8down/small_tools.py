#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : small_tools.py
@Author     : LeeCQ
@Date-Time  : 2022/2/26 18:16
"""
import logging
import sys
import time
from pathlib import Path
from hashlib import md5 as hash_md5
from urllib.parse import quote, unquote
from Crypto.Cipher import AES

__all__ = ['Bytes', 'sum_prefix_md5', 'sum_file_md5', 'URLDisassemble', 'now_timestamp', 'decode_aes128',
           'logger', 'console_handler'
           ]

logger = logging.getLogger("logger")  # 创建实例
formatter = logging.Formatter("[%(asctime)s] < %(filename)s: %(lineno)d > [%(levelname)s] %(message)s")
# 终端日志
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)  # 日志文件的格式


class Bytes:
    B = 1
    KB = B * 1024
    MB = KB * 1024
    GB = MB * 1024
    TB = GB * 1024


def encode_obj(_s) -> bytes:
    if isinstance(_s, bytes):
        return _s
    _s = str(_s)
    return _s.encode()


def sum_file_md5(file: Path, *args, **kwargs):
    """采用等分法，保证无论多大的文件都以相似的时间完成Hash"""
    return sum_file_md5_2(file, *args, **kwargs)


def sum_file_md5_1(file: Path, _gap=5 * Bytes.MB, _piece=10 * Bytes.KB):
    """快速计算文件的md5， 定长间隔法

    :param file: 文件路径
    :param _gap: 检索间隔
    :param _piece: 每个间隔的检索长度
    """
    _stat_size = file.stat().st_size
    if _stat_size < 10 * Bytes.MB:
        _gap = 0
    _md5_obj = hash_md5()
    with file.open('rb') as ff:
        while True:
            _bytes = ff.read(_piece)
            if not _bytes:
                break
            ff.seek(_gap, 1)
            _md5_obj.update(_bytes)

    return _md5_obj.hexdigest()


def sum_file_md5_2(file: Path, times=10, _price=10 * Bytes.KB):
    """等分法"""
    _stat_size = file.stat().st_size
    if _stat_size <= _price * times:
        return hash_md5(file.read_bytes()).hexdigest()

    _chuck = _stat_size // times
    _md5_obj = hash_md5()
    with file.open('rb') as ff:
        for i in range(times):
            ff.seek(_chuck * i)
            _md5_obj.update(ff.read(_price))
    return _md5_obj.hexdigest()


def sum_prefix_md5(uri, path):
    """计算 Md5 前缀"""

    uri = encode_obj(uri)
    path = encode_obj(path)
    return hash_md5(encode_obj(uri) + encode_obj(path)).hexdigest()


def now_timestamp():
    return int(time.time() * 1000)


def decode_aes128(data: bytes, key, iv='') -> bytes:
    """AES128解密"""
    logger.debug(f'解码AES-128： {key},  iv={iv}')
    if iv:
        ASE128 = AES.new(key if isinstance(key, bytes) else bytes(key, encoding='utf8'),
                         AES.MODE_CBC,
                         bytes(iv[-16:], encoding='utf8'))
    else:
        ASE128 = AES.new(key if isinstance(key, bytes) else bytes(key, encoding='utf8'),
                         AES.MODE_CBC)
    return ASE128.decrypt(data)


class URLDisassemble:

    def __init__(self, url, _query={}):
        self._url = url

        self.protocol, _o1 = self._parse_(url, '://', 'http')
        self.domain, _o2 = self._parse_(_o1, '/')
        self.path, _o3 = self._parse_(_o2 if _o2.startswith('/') else '/' + _o2, '?')
        self.query = self._parse_query(_o3)
        self.query.update(_query)

    def dict(self):
        return {'protocol': self.protocol, 'domain': self.domain, 'path': self.path, 'query': self.query}

    def tuple(self):
        return self.protocol, self.domain, self.path, self.query

    def new_url(self, url_encode=True):
        _host = f"{self.protocol}://{self.domain}"
        _path = f"{self.path}?{'&'.join(f'{k}={v}' for k, v in self.query.items())}" if self.query else self.path
        if url_encode:
            _path = quote(_path, safe='~:/&=?')
        return _host + _path

    def __str__(self):
        return self.new_url()

    def _parse_query(self, _query_str):
        """解析查询"""
        _query_dict = {}
        for kv in _query_str.split("&"):
            if not kv:
                continue

            key, value = self._parse_(kv, '=')
            if key != '':
                key = unquote(key)
                value = unquote(value)
            _query_dict.update({key: value})
        return _query_dict

    @staticmethod
    def _parse_(_str: str, _split: str, _default=None):
        spl = _str.split(_split, 1)
        if len(spl) > 1:
            return spl[0], spl[1]
        else:
            if _default:
                return _default, spl[0]
            else:
                return spl[0], ''
