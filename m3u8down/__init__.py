#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : __init__.py
@Author     : LeeCQ
@Date-Time  : 2020/7/30 11:40
"""
__version__ = '0.5.4'

from .m3u8_5 import M3U8

__all__ = ['m3u8_download', 'M3U8', 'M3U8Down']

m3u8_download = M3U8
M3U8Down = M3U8
