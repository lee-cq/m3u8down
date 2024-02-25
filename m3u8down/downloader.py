#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : downloader.py
@Author     : LeeCQ
@Date-Time  : 2023/12/3 00:11

下载器

"""
import asyncio
import json
import logging
import subprocess
from pathlib import Path
from urllib.parse import urljoin

from m3u8 import M3U8, Key as M3U8Key, Segment
from httpx import AsyncClient as _AsyncClient, Response, ReadTimeout
from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn, \
    ProgressColumn, SpinnerColumn

from m3u8down.error import EncryptMethodNotImplemented
from m3u8down.small_tools import decode_aes128
from m3u8down.models import MetaInfo

logger = logging.getLogger('m3u8down.downloader')


class AsyncClient(_AsyncClient):
    __ua = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.203')

    def __init__(self, ua=None, verify=True, /, **kwargs):
        super().__init__(verify=verify, **kwargs)
        self.headers.update({
            'User-Agent': ua if ua else self.__ua
        })

    async def request(
            self,
            method: str,
            url,
            *,
            retry: int = 5,
            follow_redirects=True,
            **kwargs
    ) -> Response:
        try:
            return await super().request(method, url, follow_redirects=follow_redirects,
                                         **kwargs)
        except ReadTimeout as _e:
            await asyncio.sleep(5)
            if retry:
                logger.warning(f'超时重试：{url}')
                return await self.request(method, url,
                                          follow_redirects=follow_redirects,
                                          retry=retry - 1, **kwargs)
            raise _e

    async def download(self, uri, timeout=None, headers=None):
        if headers is None:
            headers = {}
        _s = await self.get(uri, timeout=timeout, headers=headers,
                            follow_redirects=True)
        return urljoin(_s.request.url.__str__(), '.'), _s.text


class Downloader:
    exec_ffmpeg = Path(__file__).parent.joinpath('ffmpeg')

    def __init__(self, uri, save_path, *, max_thread=10, **kwargs):
        self.max_thread = max_thread
        self.client = AsyncClient(**kwargs)
        self.uri = uri
        self.save_path = Path(save_path).absolute()
        if not self.save_path.exists():
            self.save_path.mkdir(parents=True)
        if not self.save_path.is_dir():
            raise ValueError(f'{save_path} 不是一个目录')

        self.download_index = 0
        self.meta_file = self.save_path.joinpath('meta_info.json')
        self.meta: MetaInfo = MetaInfo(uri=uri)
        self.progress: Progress = Progress()
        self.progress_task = self.progress.add_task(
            f"[red]{self.save_path.name} Downloading...", total=None)
        self.downloaded_files = [i.name for i in self.save_path.iterdir() if
                                 i.is_file()]
        self.load_meta()

    def __del__(self):
        self.progress.stop()

    def run(self):
        asyncio.run(self.async_run())

    async def async_run(self):

        await self._load_m3u8()

        self.progress.start_task(self.progress_task)
        self.progress.update(
            self.progress_task,
            advance=len(self.downloaded_files),
            total=len(self.m3u8.segments),
        )
        await self.downloader()
        self.dump_m3u8()
        self.to_mp4()

    def load_meta(self):
        if self.meta_file.exists():
            self.meta = MetaInfo(
                **json.loads(self.meta_file.read_text(encoding='utf-8')))
        else:
            self.meta = MetaInfo(uri=self.uri)
            self.save_meta()

    def save_meta(self):
        self.meta_file.write_text(self.meta.model_dump_json(), encoding='utf-8')
        logger.info(f'保存Meta信息到 {self.meta_file}')

    async def _load_m3u8(self):
        if self.meta.m3u8_name is None or self.meta.m3u8_rewrites is True:
            _base_uri, _content = await self.client.download(self.uri)
            self.m3u8 = M3U8(_content, base_uri=_base_uri)
            await self._update_key()
            self.meta.m3u8_name = self.meta.uri.split('/')[-1]
            self.meta.base_uri = _base_uri
            self.save_meta()
            self.save_path.joinpath(self.meta.m3u8_name).write_text(_content,
                                                                    encoding='utf-8')
            self.meta.m3u8_rewrites = False
            logger.info('从网络加载M3U8文件： %s', self.meta.uri)
        else:
            self.m3u8 = M3U8(
                self.save_path.joinpath(self.meta.m3u8_name).read_text(
                    encoding='utf-8'),
                base_uri=self.meta.base_uri
            )
            logger.info('从本地加载M3U8文件： %s, base_uri: %s', self.meta.m3u8_name,
                        self.meta.base_uri)

    def dump_m3u8(self):
        """保存M3U8文件"""
        self.save_path.joinpath(self.meta.m3u8_name).write_text(self.m3u8.dumps(),
                                                                encoding='utf-8')
        logger.info(f'保存M3U8文件到 {self.save_path.joinpath(self.meta.m3u8_name)}')
        self.meta.m3u8_rewrites = True
        self.save_meta()

    async def _update_key(self):
        """更新Key"""
        for _key_obj in self.m3u8.keys:
            if _key_obj is None:
                continue
            if self.meta.keys.get(_key_obj.uri) is not None:
                _key_obj.data = self.meta.keys[_key_obj.uri]
                continue

            res = await self.client.get(_key_obj.absolute_uri)
            if res.status_code == 200:
                _key_obj.data = res.content
                self.meta.keys[_key_obj.uri] = res.content
                self.save_meta()
            else:
                _key_obj.data = None

    def ts_decode(self, _key_obj: M3U8Key, _ts) -> bytes:
        """解码Ts

        :param _key_obj: M3U8 Key 对象
        :param _ts: TS 视频二进制编码
        :return: bytes 解码后的ts
        """
        key = self.meta.keys.get(_key_obj.uri)

        if _key_obj.method == 'AES-128':
            return decode_aes128(
                _ts,
                key,
                _key_obj.iv[2:] if _key_obj.iv else ''
            )
        elif _key_obj.method is None:
            return _ts

        raise EncryptMethodNotImplemented(f'加密方式{_key_obj.method}  的解码未实现。')

    async def _async_ts_download(self, segment: Segment,
                                 semaphore: asyncio.Semaphore) -> bool:
        """异步下载TS
        :param segment:
        :return:
        """
        async with semaphore:

            self.download_index += 1
            all_s = len(self.m3u8.segments)
            down_s = len(
                [i.name for i in self.save_path.iterdir() if i.name.endswith('.ts')])

            segment_name = segment.uri.split('/')[-1]
            if segment_name in self.downloaded_files:
                logger.info(f'{segment_name} 已经存在')
                segment.uri = segment_name
                segment.key = None
                return True
            try:
                logger.info(f'正在下载：%s, %s, ([%04d]%04d/%04d)',
                            self.save_path.name,
                            segment.absolute_uri,
                            down_s / all_s * 100,
                            down_s,
                            all_s
                            )
                _ts_content = await self.client.get(segment.absolute_uri)
                _ts_content = _ts_content.content
                self.progress.update(self.progress_task, advance=1)

                if segment.key is not None:
                    _ts_content = self.ts_decode(segment.key, _ts_content)
                    segment.key = None
                self.save_path.joinpath(segment_name).write_bytes(_ts_content)
                segment.uri = segment_name
                return True
            except Exception as _e:
                logger.error(f'下载失败！{_e}', exc_info=_e)
                return False

    async def downloader(self):
        """下载器"""
        _all_tasks = []
        _down_semaphore = asyncio.Semaphore(self.max_thread)
        for _segment in self.m3u8.segments:
            _all_tasks.append(
                asyncio.create_task(
                    self._async_ts_download(_segment, _down_semaphore),
                    name=f"{id(self)}_down_{_segment.uri}"
                )
            )
        await asyncio.gather(*_all_tasks)

    def to_mp4(self):
        """将合并后的ts文件转换为mp4文件"""
        if not self.exec_ffmpeg.exists():
            raise FileNotFoundError(f"ffmpeg 未找到: {self.exec_ffmpeg}")
        subprocess.run(
            [str(self.exec_ffmpeg),
             '-i', self.save_path.joinpath(self.meta.uri.split('/')[-1]).as_posix(),
             '-c', 'copy',
             self.save_path.with_suffix('.mp4').as_posix()
             ],
            cwd=self.save_path.parent,
            check=True
        )


if __name__ == '__main__':
    pass
