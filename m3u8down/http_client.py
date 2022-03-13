#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : http_client.py
@Author     : LeeCQ
@Date-Time  : 2022/3/13 16:17
"""
import abc
import time
import asyncio

from m3u8.parser import urljoin as m3u8_urljoin
from m3u8down.small_tools import *
from httpx import AsyncClient, Client, Response


def async_run(main, *, debug=None):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main)


class BaseHttpClient(abc.ABC):

    def __init__(self, retry=3):
        self.retry = retry
        self.headers = {}

    def set_header(self, header=None):
        """设值请求头"""
        if header is None:
            header = dict()
        header.setdefault("User-Agent",
                          "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.25 Safari/537.36 Core/1.70.3741.400 QQBrowser/10.5.3863.400")
        header.setdefault("Accept", "*/*")
        header.setdefault("Connection", "keep-alive")
        self.headers.update(header)

    @abc.abstractmethod
    def get(self, *args, **kwargs):
        """"""
        pass


class HttpClient(Client, BaseHttpClient):
    """客户端模组"""

    def __init__(self, retry=3, follow_redirects=True, **kwargs):
        super(HttpClient, self).__init__(follow_redirects=follow_redirects, **kwargs)
        self.set_header()
        self.retry = retry

    def m3u8_download(self, url, timeout=None, headers={}, params={}):
        """下载M3UU8文档  -

        :return: M3u8内容, M3u8前缀
        """
        response = self.get(url, timeout=timeout, headers=headers, params=params)
        return response.text, m3u8_urljoin(str(response.url), '.')

    def request_retry(self, response: Response):
        _retry = self.retry if self.retry >= 1 else 1
        while _retry:
            _retry -= 1
            if response.is_success:
                return response
            time.sleep(3)
            response = self.send(response.request)


class AsyncHttpClient(AsyncClient, BaseHttpClient):
    def __init__(self, retry=3, follow_redirects=True, **kwargs):
        super(AsyncHttpClient, self).__init__(follow_redirects=follow_redirects, **kwargs)
        self.set_header()
        self.retry = retry

    def m3u8_download(self, url, timeout=None, headers={}, params={}, debug=None):
        """下载M3UU8文档  -

        :return: M3u8内容, M3u8前缀
        """
        _l = []

        async def _down():
            _l.append(await self.get(url, timeout=timeout, headers=headers, params=params))

        async_run(_down())

        response = _l[0]
        return response.text, m3u8_urljoin(str(response.url), '.')

    async def request_retry(self, response: Response):
        _retry = self.retry if self.retry >= 1 else 1
        while _retry:
            _retry -= 1
            if response.is_success:
                return response
            await asyncio.sleep(3)
            response = await self.send(response.request)


if __name__ == '__main__':
    logger.addHandler(console_handler)

