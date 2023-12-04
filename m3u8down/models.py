#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : models.py
@Author     : LeeCQ
@Date-Time  : 2023/12/3 00:20

"""
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class MetaInfo(BaseModel):
    """一个下载任务到源信息"""
    uri: str
    base_uri: Optional[str] = None  # Base URI
    m3u8_name: Optional[str] = None  # M3U8 文件名
    m3u8_rewrites: bool = False  # M3U8 重写列表
    keys: dict[str, bytes] = {}  # Key 列表


class DownloadList(BaseModel):
    name: str
    base_path: Path
    count: int  # 下载数量
    max_workers: int = 2  # 最大并发数
    max_threads: int = 16  # 最大线程数
    proxy: Optional[str | dict] = None  # 代理

    items: dict[str, str] = dict()
