#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : m3u8down_api.py
@Author     : LeeCQ
@Date-Time  : 2022/3/14 21:21
"""
import sys
from pathlib import Path
from typing import Union

from http_client import AsyncHttpClient, HttpClient
from m3u8_6 import M3U8Down
from m3u8_sql import M3U8SQL
from config_parse import parse_config_file


def m3u8down(uri,
             name,
             key=None,
             save_path='.',
             thread=5,
             http_client=None,
             headers=None,
             need_combine=False,
             need_clean_down=False,
             need_transcode=False,
             need_clean_combine=False,
             transcode_resolution=None,
             transcode_fps=None,
             transcode_encode=None,
             ):
    """下载一个m3u8内容"""
    http_client = http_client or (AsyncHttpClient() if sys.version_info >= (3, 7) else HttpClient())
    if headers:
        http_client.set_header(headers)
    _db = M3U8SQL(base_path=save_path, m3u8_uri=uri, m3u8_name=name)
    _m3 = M3U8Down(db=_db, m3u8_uri=uri, http_client=http_client, key=key, thread=thread)
    _m3.download()
    if need_combine:
        _m3.combine()
        if need_clean_down:
            _m3.clean_segments()
    if need_transcode:  # TODO
        pass
        if need_clean_combine:  # ToDO TransCode 确保已经完成
            _m3.clean_combine()


def m3u8downs(config_file: Union[str, Path]):
    """接口2"""
    _configs = parse_config_file(config_file)

    _db = M3U8SQL()


if __name__ == '__main__':
    import logging
    from small_tools import console_handler, formatter, logger

    m3u8_log = logging.getLogger('sqllib')
    console_handler.level = 0
    file_handler = logging.FileHandler('D:/temp/m3u8down_debug.log', encoding='utf8')
    file_handler.formatter = formatter
    file_handler.level = 0
    m3u8_log.addHandler(console_handler)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    m3u8down(uri='https://v.baoshiyun.com/resource/media-861644081561600/lud/672ab4cd174546f589d47bbfd6747b72.m3u8',
             name='1.1.【申论】基础精讲-3',
             key='0aac68f06b97d2b8')

    # _db = M3U8SQL(m3u8_uri='https://v.baoshiyun.com/resource/media-861644080513024/lud/b80373efc40a4574a7370e9a26f33a01.m3u8',
    #               m3u8_name='1.1.【申论】基础精讲-2',
    #               base_path='D:/Temp',
    #               )
    #
    # a = M3U8Down(_db, 'https://v.baoshiyun.com/resource/media-861644080513024/lud/b80373efc40a4574a7370e9a26f33a01.m3u8',
    #              http_client=AsyncHttpClient(), key='081732bb2dfde2b6',
    #              thread=12)
    # a.download()
