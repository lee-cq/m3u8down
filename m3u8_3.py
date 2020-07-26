#!/usr/bin/python3 
# -*- coding: utf-8 -*-
"""
@File Name  : m3u8_3.py
@Author     : LeeCQ
@Date-Time  : 2020/1/5 12:46

"""

import logging
import sys

logger = logging.getLogger("logger")  # 创建实例
formatter = logging.Formatter("[%(asctime)s] < %(threadName)s: %(funcName)s > [%(levelname)s] %(message)s")
# 终端日志
consle_handler = logging.StreamHandler(sys.stdout)
consle_handler.setFormatter(formatter)  # 日志文件的格式
logger.setLevel(logging.DEBUG)  # 设置日志文件等级

__all__ = []

import requests, urllib3
import os, threading, json
import time


class M3U8Error(Exception): pass
class HTTPGetError(M3U8Error): pass
class PlayListError(M3U8Error): pass
class M3U8KeyError(PlayListError): pass
#


class M3U8:
    """下载m3u8视频

    m3u8文件格式的详解：https://www.jianshu.com/p/e97f6555a070

    组织结构：
        1. 构建config.json配置文件    -> {}

        2. 读取配置文件并下载。

    类属性的组织方式：
        1. 得到一个m3u8的URL         < URL
        2. 下载m3u8文件
        3. 解析m3u8文件             --> 生成配置文件
            3.1. 判断选择清晰度页面  --> 生成playlist.json文件。
            3.2. 判断ts内容页       --> 生成tsList.json文件。
                3.2.1 判断是否有Key --> 下载并解析key文件。

    config.json 数据结构：
        1.1 inputURL:           -> str
        1.2 m3u8Root:           -> str
        1.3 saveName:           -> str
        1.4 updateTime:         -> int 时间戳
        1.5  masterList:        -> [{m3u8Info}, ...]
            -> m3u8Info <-
            1.3.1 URL           -> str playlist URL
            1.3.2 BANDWIDTH     -> str 比特率
            1.3.3 RESOLUTION    -> str 分辨率
            1.3.4 burstCount    -> int 总分片数
            1.3.5 targetDuration-> float 最大分片持续时长
            1.3.6 totalDuration -> float 总持续时长
            1.3.7 playList      -> [{fragment}, ...]
                -> fragment <-
                1.3.7.1 index   -> int 索引编码
                1.3.7.2 method  -> str 可选 - None AES-128
                1.3.7.3 key     -> str 解密key
                1.3.7.4 iv      -> str 解密iv
                1.3.7.5 duration-> float 持续时长
                1.3.7.6 absUri  -> str ts文件的绝对路径

    文件组织结构：
        /root/saveName/fragment_`int`/*.ts + playlist.m3u8
        /root/saveName/config.json
        /root/saveName/`saveName.*`  <- output video files

    """

    def __init__(self, url_m3u8: str, verify=False,
                 local_root='./down/', file_name='',
                 retry=5, timeout=90, threads=5,
                 debug_level=3, strict_mode=True,

                 ):
        self.url_m3u8 = url_m3u8
        self.retry, self.timeout, self.threads = retry, timeout, threads
        self.debug_level, self.strictMode = debug_level, strict_mode
        # 构建本地文件
        self.local_path = local_root if local_root.endswith('/') else local_root + '/'
        os.makedirs(self.local_path, exist_ok=True)
        self.fileName = file_name
        # 模拟HTTP客户端
        self.client = requests.Session()
        self.client.verify = verify
        self.client_setHeader()
        urllib3.disable_warnings()
        #
        self.root_m3u8 = url_m3u8[:url_m3u8.rfind('/')+1]
        self.configuration = dict()
        self.config_init()

    def config_init(self):
        self.configuration.setdefault('inputURL', self.url_m3u8)
        self.configuration.setdefault('m3u8Root', self.root_m3u8)
        self.configuration.setdefault('fileName', self.fileName)
        self.configuration.setdefault('updateTime', int(time.time()))

    def client_setHeader(self, header=None):
        if header is None: header = dict()
        header.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.25 Safari/537.36 Core/1.70.3741.400 QQBrowser/10.5.3863.400",)
        header.setdefault("Accept", "*/*")
        header.setdefault("Connection", "keep-alive")
        self.client.headers.update(header)

    def client_setCookie(self, cookie=None):
        self.client.cookies(cookie)

    def __requests_get(self, url: str, header: dict):
        """"""
        n = self.retry
        while n:
            n -= 1
            try:
                _data = self.client.get(url=url, headers=header, timeout=self.timeout)
                if _data.status_code == 200:
                    if self.debug_level >= 2:
                        logger.info(f'HTTP正常返回 [200]: {url}')
                    return _data
                else:
                    if self.debug_level >= 2:
                        logger.warning(f'HTTP异常返回 [{_data.status_code}]: {url}')
            except:
                logger.warning(f'HTTP请求异常: {sys.exc_info()}')
        logger.error(f'经过{self.retry}次尝试依旧失败。')
        if self.strictMode:
            raise HTTPGetError(f'经过{self.retry}次尝试依旧失败。')
        return -1

    # 下载并解析 m3u8
    def m3u8_master(self):
        """"""
        m3u8 = self.__requests_get(self.url_m3u8, {})
        if m3u8 is -1:
            raise PlayListError("m3u8文件获取失败")
        lines = m3u8.text.split('\n')
        for index, line in enumerate(lines):
            if line.startswith('#EXT-X-STREAM-INF'):
                if lines[index + 1].upper().startswith('HTTP'):
                    URL = lines[index + 1]
                else:
                    URL = self.root_m3u8 + lines[index + 1]
                self.m3u8_playlist()
            else:
                URL = self.url_m3u8

    # playlist的生成器
    def m3u8_playlist(self, text):
        """playlist的生成器

        :return {}
        """
        lines, n = text.split('/'), 0
        key = dict()
        for i, line in enumerate(lines):
            dic = dict()
            if '#EXT-X-KEY' in line:
                key = self.playlist_key(line[line.index(':')+1:])
            # 添加一个 fragment
            if '#EXTINF' in line:
                dic.setdefault('index', n)
                dic.setdefault('method', key.get('METHOD'))
                dic.setdefault('key', key.get('KEY'))
                dic.setdefault('iv', '')
                if lines[i+1].upper().startswith('HTTP'):
                    dic.setdefault('absURL', lines[i+1])
                else:
                    dic.setdefault('absURL', self.root_m3u8 + lines[i+1])
                yield dic
                n += 1


    def playlist_key(self, text):
        key = dict()
        for an in text.split(','):
            an = an.split('=')
            key[an[0]] = an[1]
            if an[0] is 'URI':
                _k = self.__requests_get(self.root_m3u8 + an[1], {})
                if _k is -1:
                    logger.error(f'Key文件获取失败，下载的m3u8视频会无法解析！URL:{self.root_m3u8 + an[1]}')
                    if self.strictMode:
                        raise M3U8KeyError(f'Key文件获取失败，下载的m3u8视频会无法解析！URL:{self.root_m3u8 + an[1]}')
                else:
                    key['KEY'] = _k.text
        return key

    # 尝试递归 - 失败
    def parse_m3u8(self, url, header=None):
        """构建masterList中的全部内容 - 会递归

        1.5  masterList:        -> [{m3u8Info}, ...]
            -> m3u8Info <-
            1.3.1 URL           -> str playlist URL
            1.3.2 BANDWIDTH     -> str 比特率
            1.3.3 RESOLUTION    -> str 分辨率
            1.3.4 burstCount    -> int 总分片数
            1.3.5 targetDuration-> float 最大分片持续时长
            1.3.6 totalDuration -> float 总持续时长
            1.3.7 playList      -> [{fragment}, ...]
                -> fragment <-
                1.3.7.1 index   -> int 索引编码
                1.3.7.2 method  -> str 可选 - None AES-128
                1.3.7.3 key     -> str 解密key
                1.3.7.4 iv      -> str 解密iv
                1.3.7.5 duration-> float 持续时长
                1.3.7.6 absUri  -> str ts文件的绝对路径
        """
        m3u8 = self.__requests_get(url, header)
        if m3u8 is -1:
            raise PlayListError("m3u8文件获取失败")  #
        lines = m3u8.text.split('\n')
        for index, line in enumerate(lines):
            if line.startswith('#EXT-X-STREAM-INF'):
                if lines[index + 1].upper().startswith('HTTP'):
                    URL = lines[index + 1]
                else:
                    URL = self.root_m3u8 + lines[index+1]
                self.parse_m3u8(URL)
            if line.startswith('#EXT-X-TARGETDURATION'):
                targetDuration = line.split(':')[-1]
            if line.startswith(''):
                pass


if __name__ == '__main__':
    logger.addHandler(consle_handler)  #
