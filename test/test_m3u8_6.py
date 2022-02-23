#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : test_m3u8_6.py
@Author     : LeeCQ
@Date-Time  : 2022/2/21 22:44
"""
import unittest

from m3u8down.m3u8_6 import *


class TestParseURL(unittest.TestCase):

    def test_url(self):
        """解析URL"""
        _urls = (
            ('test.com', ('http', 'test.com', '/', {})),
            ('https://www.baidu.com/s?wd=查询字符', ('https', 'www.baidu.com', '/s', {'wd': '查询字符'})),
            ('https://www.baidu.com/s?wd=%E6%9F%A5%E8%AF%A2%E5%AD%97%E7%AC%A6', ('https', 'www.baidu.com', '/s', {'wd': '查询字符'})),
            ('https://doc.leecq.cn/python/library/unittest.html?highlight=unittest', (
                'https', 'doc.leecq.cn', '/python/library/unittest.html', {'highlight': 'unittest'}
            )),
            ('https://support.huaweicloud.com/index.html', ('https', 'support.huaweicloud.com', '/index.html', {})),
            ('https://leecq.cn/?', ('https', 'leecq.cn', '/', {})),
            ('https://www.googletagmanager.com/gtm.js?id=GTM-KV8Z8NK', (
                'https', 'www.googletagmanager.com', '/gtm.js', {'id': 'GTM-KV8Z8NK'}
            )),
            (
                'https://cloud.tencent.com/login/queryWeappQrcodeStatus?callback=jQuery1123009431631297555265_1645456716643&token=8xlX7be4f69a47755c155204894d67498374BsKu61a9&_=1645456716678',
                ('https', 'cloud.tencent.com', '/login/queryWeappQrcodeStatus', {
                    '_': '1645456716678',
                    'callback': 'jQuery1123009431631297555265_1645456716643',
                    'token': '8xlX7be4f69a47755c155204894d67498374BsKu61a9'
                }
                 )),
        )

        for url, _s in _urls:
            with self.subTest('URL解析：', url=url):
                self.assertEqual(URLDisassemble(url).tuple(), _s, '异常')

    def test_add_query_without_encode(self):
        _urls = (  # old_url, query, new_url
            ('test.com', {'aa': 'bb'}, 'http://test.com/?aa=bb'),
            ('https://www.baidu.com/s?wd=查询字符', {'ok': 123}, 'https://www.baidu.com/s?wd=查询字符&ok=123')
        )
        for _o, _q, _n in _urls:
            with self.subTest("URL更新", o=_o, q=_q):
                self.assertEqual(URLDisassemble(url=_o, _query=_q).new_url(False), _n, '异常')

    def test_add_query_with_encode(self):
        _urls = (  # old_url, query, new_url
            ('test.com', {'aa': 'bb'}, 'http://test.com/?aa=bb'),
            ('https://www.baidu.com/s?wd=查询字符', {'ok': 123},
             'https://www.baidu.com/s?wd=%E6%9F%A5%E8%AF%A2%E5%AD%97%E7%AC%A6&ok=123')
        )
        for _o, _q, _n in _urls:
            with self.subTest("URL更新", o=_o, q=_q):
                self.assertEqual(URLDisassemble(url=_o, _query=_q).new_url(), _n, '异常')


# noinspection PyArgumentList
class TestHTTPClient(unittest.TestCase):
    """测试客户端"""

    def setUp(self) -> None:
        self.client = HttpClient(query={'ss': 'qq'})
        self.client.timeout = 2

    def test_query_true(self):
        res = self.client.get('https://leecq.cn', allow_query=True)
        self.assertEqual('https://leecq.cn/?ss=qq', res.url, '默认加载查询参数')

    def test_query_false(self):
        res = self.client.get('https://leecq.cn', allow_query=False)
        self.assertEqual('https://leecq.cn/', res.url, '不加载查询参数')
