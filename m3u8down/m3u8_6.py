#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : m3u8_6.py
@Author     : LeeCQ
@Date-Time  : 2020/8/27 22:33

"""

import asyncio
import logging
import random

from pathlib import Path
from queue import Queue
from sqlite3 import Binary
from typing import Union

from m3u8 import M3U8 as _M3U8, Segment, Key as M3U8_Key

from m3u8down.error import *
from m3u8down.small_tools import *
from m3u8down.http_client import *
from m3u8down.m3u8_sql import M3U8SQL


class M3U8Combine:
    """合并m3u8"""

    def __init__(self, seg, db: M3U8SQL):
        self.db = db
        self.seg = seg


class M3U8(_M3U8):
    """Main"""

    def __init__(self, m3u8_uri, http_client: Union[HttpClient, AsyncHttpClient] = HttpClient(), trace_variant=True):
        logger.debug(f'M3u8: {m3u8_uri}, {trace_variant=}')
        self.http_client = http_client
        self.content_, self.base_uri_ = http_client.m3u8_download(m3u8_uri)

        super().__init__(content=self.content_, base_path=None, base_uri=self.base_uri_, strict=False, custom_tags_parser=None)
        if trace_variant:
            self._trace_variant()

        self.m3u8_uri = m3u8_uri
        self.keys = {}

    def _max_resolution(self):
        __resolution_list = {_p.stream_info.resolution[0] * _p.stream_info.resolution[1]: i
                             for i, _p in enumerate(self.playlists) if _p.stream_info}
        return __resolution_list.get(max(__resolution_list.keys()), 0)

    def _trace_variant(self):
        if not self.is_variant:
            return
        _max_ = self._max_resolution()
        #
        self.__dict__.update(
            M3U8(m3u8_uri=self.playlists[_max_].absolute_uri, http_client=self.http_client).__dict__
        )

    def resolver_keys(self):
        for item in self.keys:
            _res = self.http_client.get(item.absolute_uri)
            self.keys[item.absolute_uri] = _res.content if _res.status_code == 200 else None

    def insert_sql(self, sql: M3U8SQL, table_name=None, key=None):
        """插入SQL表"""
        _table_name = table_name or f'segments_{len([i for i in sql.tables_name() if i.startswith("segments_")])}'
        sql.create_segments(_table_name)

        if not key:
            self.resolver_keys()

        for _i, item in enumerate(self.segments):
            sql.insert(
                _table_name,
                uri=item.absolute_uri,
                segment_name=f'ts{_i:06.0f}.ts',
                duration=item.duration,
                key_uri=item.key.absolute_uri,
                key_value=Binary(self.keys.get(item.key.absolute_uri, key)),
                key_method=item.key.method if hasattr(item.key, 'method') else None,
                key_iv=item.key.iv if hasattr(item.key, 'iv') else None
            )

    def dumps_from_sql(self, sql: M3U8SQL, table_name=None):
        _table_name = table_name or [i for i in sql.tables_name() if i.startswith("segments_")][0]

        for _s in self.segments:
            _s.keys = None
            _s.uri = sql.select(_table_name, 'segment_name', WHERE=f'`uri`={_s.absolute_uri}')

        return self.dumps()


class M3U8Down(M3U8):
    """m3u8"""

    def __init__(self, db: M3U8SQL, m3u8_uri, http_client: Union[HttpClient, AsyncHttpClient] = HttpClient(), key=None,
                 thread=8):
        super().__init__(m3u8_uri, http_client, trace_variant=True)
        self.db = db
        self.key = key
        self.save_path = self._save_path
        self.thread = thread
        self.download_queue = Queue() if isinstance(http_client, Client) else asyncio.Queue()

    @property
    def _save_path(self) -> Path:
        # FIXME 收集错误
        return Path(self.db.prefix_map_select('save_path', prefix_md5=self.db.prefix)[0][0])

    def get_key(self, key_url, key=None) -> str or None:
        """"""
        _key = self.keys.get(key_url) or key or self.keys
        if _key:
            return _key

        _no = [b'{', b':', b'<']
        try:
            # self.http_client.verify = False
            _r = self.http_client.get(key_url, timeout=3)
            if _r.status_code == 200 and [1 for _ in _no if _ not in _r.content]:
                self.keys[key_url] = _r.content
                return self.keys[key_url]
            else:
                self.keys[key_url] = key or self.keys
        except Exception as _e:
            raise M3U8KeyError(f"Key 获取失败!\n {_e}")

    def ts_decode(self, _key_obj: M3U8_Key, _ts) -> bytes:
        """解码Ts

        :param _key_obj: M3U8 Key 对象
        :param _ts: TS 视频二进制编码
        :return: bytes 解码后的ts
        """
        key = self.get_key(_key_obj.absolute_uri)

        if _key_obj.method == 'AES-128':
            # logger.debug(f'解码参数：body_len: {len(_ts)} 参数：{segment}')
            return decode_aes128(_ts, key, _key_obj.iv[2:] if _key_obj.iv else '')
        elif _key_obj.method is None:
            return _ts

        raise EncryptMethodNotImplemented(f'加密方式{_key_obj.method}  的解码未实现。')

    async def _async_ts_download(self, segment: Segment) -> bool:
        """

        :param segment:
        :return:
        """
        try:
            _ts_content = await self.http_client.get(segment.absolute_uri)
            _ts_content = _ts_content.content
            if segment.key is not None:
                _ts_content = self.ts_decode(segment.key, _ts_content)
                segment.key = None
            self.save_path.joinpath(segment.uri).write_bytes(_ts_content)
            return True
        except Exception as _e:
            # TODO Error日志
            logger.error(f'下载失败！{_e}')
            return False

    async def async_ts_down(self, task_name, queue):
        while queue.qsize():
            index, seg = await queue.get()
            seg.uri = f'ts_{index:05d}.ts'
            logger.debug(f"{task_name}正在处理：{index} - {seg.uri}", )
            if not await self._async_ts_download(seg):
                queue.put_nowait((index, seg))
            queue.task_done()

    async def async_download(self):
        logger.debug('正在准备协程队列')
        [self.download_queue.put_nowait(_) for _ in enumerate(self.segments)]
        logger.info(f'协程队列已创建，共计{self.download_queue.qsize()} 个元素')

        tasks = [asyncio.create_task(self.async_ts_down(f'协程下载-{i}', self.download_queue))
                 for i in range(self.thread)
                 ]
        logger.info(f'task 已经创建 {len(tasks)}')
        logger.debug('Queue Join, 等待队列全部执行完毕')
        await self.download_queue.join()
        logger.debug('开始取消已经玩的task')
        [task.cancel() for task in tasks]
        logger.debug('等待直到所有工作任务都被取消。')
        await asyncio.gather(*tasks, return_exceptions=True)
        self.save_path.joinpath('index.m3u8').write_text(self.dumps())

    def download(self):
        logger.debug('Download')
        if isinstance(self.http_client, AsyncClient):
            logger.info('开始执行 Async Download ... ')
            if asyncio.get_event_loop():
                asyncio.get_event_loop().run_until_complete(self.async_download())
            else:
                asyncio.run(self.async_download())
        elif isinstance(self.http_client, Client):
            pass
        else:
            raise ValueError()


def m3u8down():
    """接口1"""


def m3u8downs():
    """接口2"""


if __name__ == '__main__':
    cli = URLDisassemble(url='https://leecq.cn', _query={'ss': 'qq'}).new_url()
    print(cli)
