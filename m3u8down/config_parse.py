#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : config_parse.py
@Author     : LeeCQ
@Date-Time  : 2022/2/24 1:09

配置文件：
m3u8-conf: m3u8在下载过程中的配置。
    need_combine: False
    save_path: D:/Temp
    threads: 20
    http_client_class: AsyncHttpClient if > 3.7 else HttpClient


transcode-conf: 转码配置
    need_transcode: False
    ffmpeg_path:
    encode:
    resolution: None
    fps: None


m3u8-list: 需要下载的m3u8列表
    - uri: 下载地址
      name: 保存的名字
      key: (可选) 视频加密的密钥
    -
      ...

"""
import sys
import warnings
from pathlib import Path
from typing import Union

from m3u8down import http_client


class M3U8Config:
    def __init__(self, need_combine=False, save_path='.', threads=5, http_client_class=None):
        self.need_combine: bool = need_combine
        self.save_path = save_path
        self.threads = threads
        self.http_client_class = getattr(http_client, http_client_class) or (
            http_client.AsyncHttpClient if sys.version_info >= (3, 7) else http_client.HttpClient)


class TranscodeConfig:
    def __init__(self,
                 need_transcode=False,
                 ffmpeg_path='',
                 encode: str = '',
                 resolution=None,
                 fps=None,
                 ):
        self.need_transcode = need_transcode
        self.ffmpeg_path = ffmpeg_path
        self.encode: str = encode
        self.resolution = resolution
        self.fps = fps


class M3U8Item:
    def __init__(self, uri, name, key=None):
        self.uri: str = uri
        self.name: str = name
        self.key: Union[str, bytes, bytearray] = key


class Config:

    def __init__(self, config_dict: dict):
        self.config_dict = config_dict

        self.m3u8_db = None

        _m3u8_conf = config_dict.get('m3u8-conf', config_dict.get('m3u8-config', dict()))
        self.m3u8_config = M3U8Config(
            need_combine=_m3u8_conf.get('need_combine', False),
            save_path=_m3u8_conf.get('save_path', '.'),
            threads=_m3u8_conf.get('threads', 5),
            http_client_class=_m3u8_conf.get('http_client_class')
        )

        _transcode_conf: dict = config_dict.get('transcode-conf', config_dict.get('transcode-config', dict()))
        self.transcode_config = TranscodeConfig(
            need_transcode=_transcode_conf.get('need_transcode', False),
            ffmpeg_path=_transcode_conf.get('ffmpeg_path', ),
            encode=_transcode_conf.get('encode', ''),  # TODO
            resolution=_transcode_conf.get('resolution', ),
            fps=_transcode_conf.get('fps', ),
        )

        self.m3u8_list = [M3U8Item(uri=i['uri'], name=i.get('name'), key=i.get('key'))
                          for i in self.config_dict['m3u8-list']
                          ]

        self.check_config()

    def check_config(self):
        """"""
        if self.transcode_config.need_transcode:
            warnings.warn(f'转码使用Ffmpeg实现，且为实验体特性！')
            if self.transcode_config.ffmpeg_path is None:
                raise ValueError(f'需要转码时，必须手动指定ffmpeg的位置')
            elif Path(self.transcode_config.ffmpeg_path).is_file():
                raise ValueError(f'指定的ffmpeg_path={self.transcode_config.ffmpeg_path} 不是一个文件')


def parse_config_file(config_file):
    """"""
    config_file = Path(config_file)
    if config_file.suffix == '.json':
        from json import loads
        _config = loads(config_file.read_text())
    elif config_file.suffix in ['.yaml', '.yml']:
        from yaml import safe_load
        _config = safe_load(config_file.open())

    else:
        raise TypeError(f'错误的文件类型{config_file.suffix}, 仅支持yaml, json')
