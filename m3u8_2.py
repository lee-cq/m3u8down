#!/usr/bin/python3 
# -*- coding: utf-8 -*-
"""
@File Name  : m3u8_2.py
@Author     : LeeCQ
@Date-Time  : 2019/12/22 22:04

"""
import sys, logging

logger = logging.getLogger("logger")  # 创建实例
formatter = logging.Formatter("[%(asctime)s] < %(threadName)s: %(thread)d > [%(levelname)s] %(message)s")
# 终端日志
consle_handler = logging.StreamHandler(sys.stdout)
consle_handler.setFormatter(formatter)  # 日志文件的格式
logger.setLevel(logging.DEBUG)  # 设置日志文件等级
logger.addHandler(consle_handler)  #

import os
import urllib3
import requests
import time


class M3U8Error(Exception): pass
class IndexFileError(M3U8Error): pass
class TSFileError(M3U8Error): pass
#


class M3U8:
    """下载一个M3U8文件列表中的所有文件。

    包含：playlist.m3u8 && *.ts
        -> 一个文件夹中；
        —> 创建idd与视频名称的映射；
    """
    HEADER = dict()

    def __init__(self, url_m3u8: str, local_path='./sup/', verify=False,
                 retry=5, timeout=90,
                 ):
        self.url_m3u8 = url_m3u8
        self.retry = retry
        self.timeout = timeout
        self.verify = verify

        self.local_path = local_path if local_path.endswith('/') else local_path + '/'
        os.makedirs(self.local_path, exist_ok=True)

        self.ts_list = []

    def __request_get(self, _url, _header: dict):
        """取得requests.get和所用的时间；

        :return: response对象, 运行时间
        """
        _retry = self.retry
        start: float = time.time()
        _header.setdefault('User-Agent',
                           'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18362')

        urllib3.disable_warnings()
        while _retry:
            _retry -= 1
            try:
                _res = requests.get(_url, headers=_header, verify=self.verify, timeout=self.timeout)
                if _res.status_code == 200:
                    return _res, time.time() - start
                else:
                    logger.warning(f'No.{self.retry-_retry} URL: {_url} - 非200返回[{_res.status_code}]')
            except:
                logger.warning(f'No.{self.retry-_retry} URL: {_url} - 请求超时 - TIMEOUT={self.timeout}')
        logger.error(f'URL: {_url} 经过[{self.retry}]次，依旧下载失败！')
        return 'Error', -1

    def parse_m3u8(self, text: str):
        """

        :return:
        """
        _list, _ts = text.splitlines(), []
        for __ts in _list:
            if not __ts.strip().startswith('#'):
                if __ts.upper().startswith('HTTP'):
                    self.ts_list.append(__ts)
                else:
                    self.ts_list.append(
                        '/'.join(self.url_m3u8.split('/')[:-1]) + '/' + __ts
                        )

    def index(self):
        """下载保存并解析M3U8

        :return:
        """
        __m3u8, _ = self.__request_get(self.url_m3u8, _header={})   # 下载
        if _ >= 0:
            self.parse_m3u8(__m3u8.text)  # 解析
            file_name = self.local_path + 'playlist.m3u8'
            with open(file_name, 'w', encoding='utf8') as f:    # 保存
                f.write(__m3u8.text)
        else:
            raise IndexFileError(f'Index File Download Error.')

    def ts_one(self, url, header):
        """下载并保存 ts文件

        :return:
        """
        __ts, _ = self.__request_get(url, _header=header)
        if _ >= 0:
            file_name = '/'.join((self.local_path, url.split('/')[-1])).replace('//', '/')
            with open(file_name, 'wb') as f:
                f.write(__ts.content)

    def ts_all(self):
        """

        :return:
        """
        for url in self.ts_list:
            self.ts_one(url, header={'Connection': 'Keep-Alive', 'Cache-Control': 'no-cache'})

    def run(self):
        """

        :return:
        """
        logger.info(f'开始解析：{self.url_m3u8}')
        self.index()
        self.ts_all()


if __name__ == '__main__':
    M3U8('https://video1.posh-hotels.com:8091/99920191215/Heyzo-1819/index.m3u8').run()
