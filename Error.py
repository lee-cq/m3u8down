#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : Error.py
@Author     : LeeCQ
@Date-Time  : 2019/12/11 13:42

"""


class M3U8Error(Exception):
    pass


class RetryError(M3U8Error):
    pass


class NotFindDir(M3U8Error):
    pass