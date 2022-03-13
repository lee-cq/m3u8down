#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : error.py
@Author     : LeeCQ
@Date-Time  : 2019/12/11 13:42

"""


class M3U8Error(Exception):
    """M3U8基础错误"""


class M3U8IOError(M3U8Error):
    """M3U8网络错误"""


class RetryError(M3U8Error):
    """重试异常"""


class DirNotFind(M3U8Error):
    """目录没找到"""


class EncryptMethodNotImplemented(NotImplementedError, M3U8Error):
    """解码方法未实现"""


class M3U8KeyError(M3U8Error):
    """未能正确获取到 Key"""
