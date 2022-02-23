#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : Error.py
@Author     : LeeCQ
@Date-Time  : 2019/12/11 13:42

"""


class M3U8Error(Exception):
    """M3U8基础错误"""


class M3U8IOError(M3U8Error):
    """M3U8网络错误"""


class RetryError(M3U8Error):
    """重试异常"""


class NotFindDir(M3U8Error):
    """目录没找到"""
