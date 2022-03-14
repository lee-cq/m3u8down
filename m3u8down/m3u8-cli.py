#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : m3u8-cli.py
@Author     : LeeCQ
@Date-Time  : 2022/2/23 12:35
"""
import logging
from argparse import ArgumentParser
from pathlib import Path

from m3u8_5 import *
from m3u8down.m3u8_5 import logger, console_handler

_args = ArgumentParser("M3U8Down 命令行工具")
_args.add_argument('-u', '--uri', dest='uri', help='必要参数：需要下载的M3U8-URI')
_args.add_argument('-n', '--name', dest='name', default=None, help='保存的名字')
_args.add_argument('-c', '--config', dest='config_file', default=None, help='指定配置文件')
_args.add_argument('-o', '--out-path', dest='out_path', default='.', help='本地保存路径')
_args.add_argument('-k', '--key', dest='key', default='', help='手动指定m3u8加密秘钥')
_args.add_argument('-nc', '--no-combine', dest='is_combine', action='store_false', default=True, help='禁止合并单一ts文件(会删除文件分片)')
_args.add_argument('-nt', '--no-transcode', dest='is_transcode', action='store_false', default=True,
                   help='禁止转码(会删除合并的文件和分片文件, 当-nc指定时，-nt自动指定)')
_args.add_argument('-t', '--threads', default=5, type=int, help='同时下载线程数')
_args.add_argument('-v', '--version', action='version', version='0.5.5')

_a0 = ['-h']
_a1 = ['-u', 'https://v.baoshiyun.com/resource/media-861644078907392/lud/188ed3dfd07a44a7bf53bed61a13d841.m3u8',
       '-n', '【申论】基础精讲-1',
       '-o', r'D:/Temp',
       '-k', '165cb2bc1c699e26',
       '-t', '20', ]

if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)  # 设置日志文件等级
    logger.addHandler(console_handler)
    args = _args.parse_args(_a1)

    out_path = Path(args.out_path).absolute()
    logger.info(f'下载：{args.uri}')
    logger.info(f'保存至：{out_path}')
    logger.debug(f'{args=}')

    M3U8(url_m3u8=args.uri,
         save_name=args.name,
         save_path=args.out_path,
         key=args.key,
         is_combine=args.is_combine,
         is_transcode=args.is_transcode,
         threads=args.threads,
         ).run()
