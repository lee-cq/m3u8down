#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : __main__.py
@Author     : LeeCQ
@Date-Time  : 2023/12/10 12:35
"""
import logging
from argparse import ArgumentParser
from pathlib import Path

from .downloader import Downloader

_args = ArgumentParser("M3U8Down 命令行工具")
_args.add_argument('-u', '--uri', dest='uri', help='必要参数：需要下载的M3U8-URI')
_args.add_argument('-n', '--name', dest='name', default=None, help='保存的名字')
_args.add_argument('-c', '--config', dest='config_file', default=None,
                   help='指定配置文件')
_args.add_argument('-o', '--out-path', dest='out_path', default='.',
                   help='本地保存路径')
_args.add_argument('-k', '--key', dest='key', default='', help='手动指定m3u8加密秘钥')
_args.add_argument('-nc', '--no-combine', dest='is_combine', action='store_false',
                   default=True,
                   help='禁止合并单一ts文件(会删除文件分片)')
_args.add_argument('-nt', '--no-transcode', dest='is_transcode', action='store_false',
                   default=True,
                   help='禁止转码(会删除合并的文件和分片文件, 当-nc指定时，-nt自动指定)')
_args.add_argument('-t', '--threads', default=5, type=int, help='同时下载线程数')
_args.add_argument('-v', '--version', action='version', version='0.5.5')

if __name__ == '__main__':
    args = _args.parse_args()
    Downloader(
        uri=args.uri,
        name=args.name,
    ).run()
