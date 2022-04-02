#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : m3u8_6.py
@Author     : LeeCQ
@Date-Time  : 2020/8/27 22:33

"""

import logging
import threading

from typing import Union
from queue import Queue

import ffmpeg
from m3u8 import M3U8 as _M3U8, Key as M3U8_Key

from error import *
from http_client import *
from m3u8_sql import M3U8SQL


class M3U8Combine:
    """合并m3u8"""

    def __init__(self, seg, db: M3U8SQL):
        self.db = db
        self.seg = seg


class M3U8(_M3U8):
    """Main"""

    def __init__(self, m3u8_uri, http_client: Union[HttpClient, AsyncHttpClient] = HttpClient(), trace_variant=True):
        logger.debug(f'开始解析： M3u8:{m3u8_uri}, 自动跟踪异型：{trace_variant}')
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

    def dumps_from_sql(self, sql: M3U8SQL, table_name=None):
        _table_name = table_name or [i for i in sql.tables_name() if i.startswith("segments_")][0]

        for _s in self.segments:
            _s.keys = None
            _s.uri = sql.select(_table_name, 'segment_name', WHERE=f'`uri`={_s.absolute_uri}')

        return self.dumps()


class BaseM3U8Down(M3U8):
    """m3u8"""

    def __init__(self, db: M3U8SQL, m3u8_uri, http_client: Union[HttpClient, AsyncHttpClient] = HttpClient(), key=None,
                 thread=8):
        super().__init__(m3u8_uri, http_client, trace_variant=True)
        self.db = db
        self.key = key
        self.save_path = self.db.save_path
        self.combine_path = self.save_path.with_suffix('.ts')
        self.transcode_path = self.save_path.with_suffix('.mp4')
        self.save_path.mkdir(exist_ok=True, parents=True)
        self.thread = thread

    def download_queue(self):
        logger.debug(f'准备多线程下载队列')
        _queue = Queue() if isinstance(self.http_client, Client) else asyncio.Queue()
        [_queue.put_nowait(_) for _ in enumerate(self.segments)]
        logger.info(f'协程队列已创建，共计{_queue.qsize()} 个元素')
        return _queue

    def resolver_keys(self):
        for item in self.keys:
            _res = self.http_client.sync_get(item.absolute_uri)
            self.keys[item.absolute_uri] = _res.content if _res.status_code == 200 else None

    def get_key(self, key_url, key=None) -> str or None:
        """"""
        _key = self.keys.get(key_url) or key or self.key
        if _key:
            return _key

        _no = [b'{', b':', b'<']
        try:
            logger.debug('开始从网络获取Key.')
            _r = self.http_client.sync_get(key_url, timeout=3)
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
            return decode_aes128(_ts, key, _key_obj.iv[2:] if _key_obj.iv else '')
        elif _key_obj.method is None:
            return _ts

        raise EncryptMethodNotImplemented(f'加密方式{_key_obj.method}  的解码未实现。')


class AsyncM3U8Down(BaseM3U8Down):
    """"""

    async def _async_ts_download(self, segment) -> bool:
        """

        :param segment:
        :return:
        """
        if self.save_path.joinpath(segment.renamed_uri).exists():
            logger.info(f'{segment.renamed_uri} 已经存在')
            return True
        logger.debug(f'下载, {type(self.http_client)}, {type(self.http_client.get)} {segment.absolute_uri}')
        try:
            self.http_client: AsyncHttpClient
            _ts_content = await self.http_client.get(segment.absolute_uri)
            logger.debug(f'{_ts_content}')
            _ts_content = _ts_content.content

            if segment.key is not None:
                _ts_content = self.ts_decode(segment.key, _ts_content)
                segment.key = None
            self.save_path.joinpath(segment.renamed_uri).write_bytes(_ts_content)
            segment.uri = segment.renamed_uri
            return True
        except Exception as _e:
            logger.error(f'下载失败！{_e}', exc_info=_e)
            return False

    async def async_down_task(self, task_name, queue: asyncio.Queue):
        while queue.qsize():
            index, seg = await queue.get()
            seg.renamed_uri = f'ts_{index:05d}.ts'
            logger.debug(f"{task_name}正在处理：{index} - {seg.uri}", )
            # await asyncio.sleep(2)
            if not await self._async_ts_download(seg):
                queue.put_nowait((index, seg))
            queue.task_done()

    async def _async_download(self):
        logger.debug('正在准备协程队列')

        download_queue = self.download_queue()

        tasks = [asyncio.create_task(self.async_down_task(f'协程下载-{i}', download_queue))
                 for i in range(self.thread)
                 ]
        logger.info(f'task 已经创建 {len(tasks)}')
        logger.debug('Queue Join, 等待队列全部执行完毕')
        await download_queue.join()
        logger.debug('开始取消已经玩的task')
        [task.cancel() for task in tasks]
        logger.debug('等待直到所有工作任务都被取消。')
        await asyncio.gather(*tasks, return_exceptions=True)

    def async_download(self):
        logger.info('开始执行 Async Download ... ')
        logger.info(f"保存位置：{self.save_path}")
        logger.debug(f'{self.key}')
        logger.info(f'M3U8SQL Hash -> {self.db.prefix}  {self.db.m3u8_name}')

        asyncio.run(self._async_download(), debug=True)


class SyncM3U8Down(BaseM3U8Down):
    def _thread_ts_download(self, segment):
        if self.save_path.joinpath(segment.renamed_uri).exists():
            logger.info(f'{segment.renamed_uri} 已经存在')
            return True
        logger.debug(f'下载, {type(self.http_client)}, {type(self.http_client.get)} {segment.absolute_uri}')
        try:
            _ts_content = self.http_client.get(segment.absolute_uri)
            _ts_content = _ts_content.content

            if segment.key is not None:
                _ts_content = self.ts_decode(segment.key, _ts_content)
                segment.key = None
            self.save_path.joinpath(segment.renamed_uri).write_bytes(_ts_content)
            segment.uri = segment.renamed_uri
            return True
        except Exception as _e:
            logger.error(f'下载失败！{_e}', exc_info=_e)
            return False

    def thread_down_task(self, task_name, queue: Queue):
        while queue.qsize():
            index, seg = queue.get()
            seg.renamed_uri = f'ts_{index:05d}.ts'
            logger.debug(f"{task_name}正在处理：{index} - {seg.uri}", )
            if not self._thread_ts_download(seg):
                queue.put_nowait((index, seg))
            queue.task_done()

    def sync_download(self):
        logger.info('开始执行 Thread Download ...')

        download_queue = self.download_queue()

        tasks = [threading.Thread(target=self.thread_down_task, args=(f'Thread-{i:02d}', download_queue))
                 for i in range(self.thread)
                 ]
        [t.run() for t in tasks]
        [t.join() for t in tasks]


class M3U8Down(AsyncM3U8Down, SyncM3U8Down):

    def download(self):
        if isinstance(self.http_client, AsyncHttpClient):
            self.async_download()
        elif isinstance(self.http_client, HttpClient):
            self.sync_download()

        self.save_path.joinpath('index.m3u8').write_text(self.dumps())

    def combine(self):
        """"""
        if self.combine_path.exists():
            raise FileExistsError()
        with self.combine_path.open('ab') as cf:
            for item in self.save_path.iterdir():
                if item.suffix == '.ts':
                    cf.write(item.read_bytes())

    def clean_segments(self):
        for _i in self.save_path.iterdir():
            _i.unlink()
        self.save_path.rmdir()

    def clean_combine(self):
        self.combine_path.unlink(missing_ok=True)


def transcode_ffmpeg(in_file, out_file, ffmpeg_path=''):
    """使用ffmpeg转码文件

    :param in_file: 完整的转码前的文件路径
    :param out_file：输出文件路径
    :param ffmpeg_path:
    """
    logger.info('转码文件 ... ')
    ffmpeg.input(in_file).output(out_file).run(cmd=ffmpeg_path, overwrite_output=True)
