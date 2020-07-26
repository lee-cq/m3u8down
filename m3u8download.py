#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : m3u8download.py
@Author     : LeeCQ
@Date-Time  : 2019/12/11 12:38

"""

import os, sys
import requests
import time
import urllib3
import asyncio
import threading
import logging
import re

logger = logging.getLogger("logger")  # 创建实例
formatter = logging.Formatter("[%(asctime)s] < %(threadName)s: %(thread)d > [%(levelname)s] %(message)s")
# 终端日志
consle_handler = logging.StreamHandler(sys.stdout)
consle_handler.setFormatter(formatter)  # 日志文件的格式
logger.setLevel(logging.DEBUG)  # 设置日志文件等级
logger.addHandler(consle_handler)  #

from HTTP.Download_m3u8.Error import *


class M3U8Download:
    """
    下载m3u8视频，输出一个本地MP4（或者其他常用的视频）文件，
    """
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18362'
        }

    def __init__(self, _url: str):
        self.m3u8_url = _url
        self.dir_root = 'D:/temp/'
        self.m3u8_host = '/'.join(_url.split('/')[:-1]) + '/'
        self.HEADERS.setdefault('Host', _url.split('/')[2])

        self.retry_time = 5
        self.timeout = 60
        self.max_thread = 2
        self.event = threading.Event()

        if not os.path.exists(self.dir_root):
            os.mkdir(self.dir_root)

        self.ts_info = []
        self.download_file_list = self.__index_parse()

    def set_maxThread(self, max_thread: int):
        self.max_thread = max_thread

    def set_root_dir(self, dir):
        if os.path.exists(dir):
            self.dir_root = dir
            os.chdir(dir)
        else:
            raise NotFindDir('Not Find The DIR:' + dir)

    def set_retry(self, times: int):
        self.retry_time = times

    def __requests_get(self, _url, headers):
        """取得requests.get和所用的时间；

        :return: response 对象, 运行时间
        """
        start: float = time.time()
        urllib3.disable_warnings()
        return requests.get(_url, headers=headers, verify=False, timeout=self.timeout), time.time() - start

    def __index_download(self):
        """下载index.m3u8文件"""
        n = self.retry_time
        while n:
            n -= 1
            result, runtime = self.__requests_get(url, self.HEADERS)
            print(runtime)
            if result.status_code == 200:
                return result.text
            else:
                print(result.status_code)
        raise RetryError('retry times out, don\'t get a status code 200.')

    def __index_parse(self):
        """解析m3u8文件，把所有的块，加载到一个列表中返回"""
        # print("测试代码！__index_parse()")
        # return [x for x in open('./sup/local.m3u8').read().split('\n') if (not x.startswith('#')) and len(x) > 2]
        return [x for x in self.__index_download().split('\n') if (not x.startswith('#')) and len(x) > 2]

    async def __coroutine_ts_download(self, _url, headers):
        """下载一个块文件，并二进制保存到文件"""
        file_name = _url.split("/")[-1]
        print(f'[+] 正在下载 {_url}')
        async with self.__requests_get(_url, headers) as get_result:
            _ts, runtime = await get_result  # Download
        with open(self.dir_root + +file_name, 'wb') as f:
            f.write(_ts.content)
        self.ts_info.append((file_name, runtime))

    def __main_coroutine_ts_down(self):
        """协程在下载的启动函数；"""

        header = self.HEADERS
        tasks = [asyncio.ensure_future(self.__coroutine_ts_download(self.m3u8_host + x, header))
                 for x in self.__index_parse()]  # 创建列表task
        loop = asyncio.get_event_loop()  # 创建主循环
        loop.run_until_complete(asyncio.wait(tasks))  # 运行
        os.chdir(os.path.dirname(__file__))

    def __thread_ts_download(self, _url, header):
        """采用多线程, 下载！"""
        file_name = _url.split('/')[-1]
        n = self.retry_time
        dir_tmp = self.dir_root + 'tmp/'
        if not os.path.exists(dir_tmp): os.mkdir(dir_tmp)
        while n:
            n -= 1
            response, runtime = self.__requests_get(_url, header)
            if response.status_code == 200:
                self.ts_info.append((file_name, runtime))
                with open(dir_tmp + file_name, 'wb') as f:
                    f.write(response.content)
                    return 0
            logger.error(f'Error stat_code:{response.status_code}, The rest of retry times is {n}, retry litter 5s ...')
            time.sleep(5)
        # logging.error(f"线程下载时重试次数用尽，{file_name}")
        raise RetryError(f"线程下载时重试次数用尽，{file_name}")

    def __main_thread_ts_download(self):
        download_file_list = self.download_file_list
        len_file_list = len(download_file_list)
        for file_name in download_file_list:
            if file_name in os.listdir(self.dir_root + 'tmp/'):
                continue
            logger.info("有" + str(len(threading.enumerate())) + f"个线程在运行中。({threading.Thread().getName()})")  #
            threading.Thread(target=self.__thread_ts_download,
                             args=(self.m3u8_host + file_name, self.HEADERS),
                             name=file_name.split('.')[0]
                             ).start()
            while len(threading.enumerate()) >= self.max_thread + 1:
                print(f'\r[{time.strftime("%H:%M:%S")}]线程多了', end='')
                time.sleep(1)
        while len(os.listdir(self.dir_root)) <= len_file_list:
            print(f"[\r{time.strftime('%H:%M:%S')}] 主线程休眠...", end='')
            time.sleep(5)

    def __ts001_parse(self):
        """解析第一个ts文件，获取视频的编码，和拓展名"""
        with open(self.dir_root + 'tmp/' + self.download_file_list[0], 'rb') as f:
            content = f.read()
            print(content)
        # re.findall(r'.*', content)

    def package_to_mp4(self):
        """把所有的ts文件打包成MP4文件。"""
        os.chdir(self.dir_root + 'tmp/')

        with open('../' + self.m3u8_url.split('/')[-2] + '.ts', 'wb') as fw:
            for _ts in os.listdir('.'):
                with open(_ts, 'rb') as fo:
                    fw.write(fo.read())

    def test(self):
        return self.package_to_mp4()

    def run(self):
        self.__main_thread_ts_download()
        self.package_to_mp4()


if __name__ == '__main__':
    url = 'https://video2.gujianzhixiang.com:8091/81820191224/RY1220052/1000kb/hls/index.m3u8'
    a = M3U8Download(url)
    a.run()
    # a.test()
    # print(a)
