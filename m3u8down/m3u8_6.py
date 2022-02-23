#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : m3u8_6.py
@Author     : LeeCQ
@Date-Time  : 2020/8/27 22:33

m3u8_6 全新架构，单文件完成全部的需求，一站式解决方案。

1. 存储文件结构：
        /<Root>/.allInfo.sqlite
        /<Root>/<movie>/*.m3u8
        /<Root>/<movie>/*.ts
        /<Root>/<movie>.mp4

2. SQLite数据结构：
    _main: moviesHeaders
        _id | name | m3u8Url | Description | is_parse | is_down | is_combine
    names: everyMovie - > 表名 = <name>
              "idd      INTEGER PRIMARY KEY AUTOINCREMENT, "
              "abs_uri  varchar(160) not null UNIQUE, "
              "segment_name varchar(50) , "
              "duration float, "
              "key      blob, "
              "key_uri   varchar(160), "
              "key_name varchar(50), "
              "method   varchar(10), "
              "iv       varchar(50)"

3. 接口函数：
    m3u8down: 接一个m3u8的连接下载一个视频
    m3u8downs: 接受一个m3u8down的配置文件（包含下载的Root | m3u8列表 | Key如果有）

4. 实现方法接口：
    4.0. def load(uri, timeout=None,
                       headers={},
                       custom_tags_parser=None,
                       http_client=DefaultHTTPClient(),
                       verify_ssl=True
                       ) -> M3U8 : <- m3u8.load
        Retrieves the content from a given URI and returns a M3U8 object.
        Raises ValueError if invalid content or IOError if request fails.
        从给定的URI中检索内容并返回M3U8对象；
        内容无效ValueError，请求失败返回IOError。
        :return M3U8

    4.1. class HttpClient(retry=3,
                          timeout=30,
                          *args,
                          **kwargs
                          ) -> requests.Session:
        创建一个HTTP客户端用于同一的调度下载文件。
        :return requests.Session

    4.2. class SQL():
        负责运行过程中的SQL操作。
        :return sql操作句柄

    4.3. class M3U8Down():
        负责下载m3u8和ts文件。

    4.4. class M3U8Combine():
        负责合并ts文件。

    4.5. class M3U8Reload:
        重载M3U8文件

5. 其他辅助方法实现：
    5.1. 打印输出接口 - 实现在不同位置有不同的输出。
    5.2. 配置文件解析接口 -
    5.3. 配置文件模板输出接口 -
    5.4. 命令行启动 -
    5.5. 命令行配置文件校验 -

6. 实现的功能：
    6.1. 下载并解析m3u8文件。
    6.2. 根据解析得到的m3u8对象，下载ts文件。
    6.3. 合并ts文件得到mp4文件。
    6.4. 根据配置文件批量得到下载列表。


* 操作日志
    2020-8-28：完成m3u8down模块的主体架构，详细需求文档、完成大概的搭建架构。


"""
from hashlib import md5 as hash_md5
from pathlib import Path
from typing import Text, Union
from urllib.parse import quote, unquote

from m3u8 import load as m3u8_load
from requests import Session, Response
from sqllib import SQLiteAPI
from sqllib.common.error import SqlWriteError

from m3u8down.Error import *


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
        _host = f'{self.protocol}://{self.domain}'
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
            if not kv: continue
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


class HttpClient(Session):
    """客户端模组"""

    def __init__(self, headers=dict(), query=dict(), cookies=dict(), retry=3):
        super().__init__()
        self.retry = retry
        self.set_header(headers)
        self.cookies.update(cookies)
        self._query = query

    def set_header(self, header=None):
        """设值请求头"""
        if header is None:
            header = dict()
        header.setdefault("User-Agent",
                          "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.25 Safari/537.36 Core/1.70.3741.400 QQBrowser/10.5.3863.400")
        header.setdefault("Accept", "*/*")
        header.setdefault("Connection", "keep-alive")
        self.headers.update(header)

    def request(self, method: str, url: Union[str, bytes, Text], *args, allow_query=True, **kwargs):
        url = URLDisassemble(url=url, _query=self._query).new_url() if allow_query else url
        if 'retry' in kwargs:
            _retry = kwargs.pop('retry')

        _response = super(HttpClient, self).request(method, url, *args, **kwargs)
        for i in range(self.retry):
            if self._is_2xx(_response):
                return _response
        raise RetryError(f'在允许的重试次数({self.retry})中, 已经没有有效的返回！'
                         f'{_response.url}')

    @staticmethod
    def _is_2xx(_response: Response):
        if 200 <= _response.status_code < 300:
            return True
        else:
            raise M3U8IOError(f'非2xx响应：{_response.status_code}')


class M3U8SQL(SQLiteAPI):
    """SQL相关操作"""
    prefix_map = 'prefix_map'

    def __init__(self, db, m3u8_name: Path, **kwargs):
        self._db = db
        self._kwargs = kwargs
        self.m3u8_name = m3u8_name
        self.prefix = self._sum_md5()
        self.no_prefix_api = SQLiteAPI(db, **kwargs)
        self._make_prefix()
        super().__init__(db, prefix=self.prefix, **kwargs)

    def _sum_md5(self):
        _name = self.m3u8_name.name.encode()
        _text_bytes = self.m3u8_name.read_bytes()
        return hash_md5(_name + _text_bytes).hexdigest(),

    def _make_prefix(self):
        """"""
        self._create_prefix_table()
        try:
            _s = self.no_prefix_api.insert(self.prefix_map,
                                           prefix_md5=self.prefix,
                                           m3u8_name=self.m3u8_name.name,
                                           m3u8_text=self.m3u8_name.read_text(encoding='utf8')
                                           )
            self.is_new = True
        except SqlWriteError:
            # 重复
            self.is_new = False

    def _create_prefix_table(self):
        """前缀映射表"""
        _c = (
            "prefix_md5   varchar(32) not null unique , -- MD5表前缀\n "  # TODO 表前缀的MD5计算方法
            "m3u8_name  varchar(256) not null ,         -- 下载视频的名字\n"
            "m3u8_uri VARCHAR(512) not null,            -- 下载视频的原始URI地址\n"
            "m3u8_text  TEXT ,                          -- 下载的m3u8文档原文\n"
            "m3u8_parse  TEXT,                          -- M3U8解析结果 JSON"  # TODO 目前只考虑1层播放列表的情况
            "create_time INT ,                          -- 此条记录的创建时间\n"
            "need_combine bool ,                        -- 是否需要合并单一文件\n"
            "combined_md5 varchar(32),                  -- 已经合并单一文件MD5值\n"  # TODO 大文件的MD5计算方法
            "need_transcode bool,                       -- 是否需要转码文件 \n"
            "transcode_args TEXT,                       -- 转码参数 JSON "
            "transcode_md5 varchar(32) ,                -- 转码后的文件的MD5值\n "
            "completed_time int                         --是否已经完成"
        )
        return self.no_prefix_api.create_table(table_name=self.prefix_map, cmd=_c, exists_ok=True)

    def create_master(self):
        """创建表: master"""
        _c = ("abs_uri      varchar(150) not null unique, "
              "resolution   int, "  # 长 * 宽
              "audio        varchar(100) "
              )
        return self.create_table(table_name='master', cmd=_c, exists_ok=True)

    def create_segments(self, table_name):
        """创建表: segments"""
        _c = ("idd      INTEGER PRIMARY KEY AUTOINCREMENT, "
              "abs_uri  varchar(160) not null UNIQUE, "
              "segment_name varchar(50) , "
              "duration float, "
              "key      blob, "
              "key_uri   varchar(160), "
              "key_name varchar(50), "
              "method   varchar(10), "
              "iv       varchar(50)"
              )
        self.create_table(table_name=table_name, cmd=_c, exists_ok=True)
        # self.sql.write_db(f"UPDATE sqlite_sequence SET seq=0 WHERE name=`{table_name}`")

    def create_config(self):
        """创建表 - 配置文件"""
        _c = "key_ varchar(50) not null unique, value_ VARCHAR(100)"
        return self.create_table(table_name='config', cmd=_c, exists_ok=True)


class M3U8Down(object):
    """m3u8"""

    def __init__(self, db: M3U8SQL):
        self.db = db


class M3U8Combine:
    """合并m3u8"""

    def __init__(self, seg, db: M3U8SQL):
        self.db = db
        self.seg = seg


class M3U8Reload:
    """重写M3U8 File"""

    def __init__(self, db: M3U8SQL):
        self.db = db


class M3U8CMD:
    """命令行程序"""


class M3U8:
    """Main"""

    def __init__(self, m3u8_uri):
        self.m3u8_uri = m3u8_uri
        self.m3u8_obj = m3u8_load(m3u8_uri)


def m3u8down():
    """接口1"""


def m3u8downs():
    """接口2"""


if __name__ == '__main__':
    cli = URLDisassemble(url='https://leecq.cn', _query={'ss': 'qq'}).new_url()
    print(cli)
