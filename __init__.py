#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : __init__.py
@Author     : LeeCQ
@Date-Time  : 2019/12/11 12:37

"""
import logging
import sys

logger = logging.getLogger("logger")  # 创建实例
formatter = logging.Formatter("[%(asctime)s] < %(funcName)s: %(thread)d > [%(levelname)s] %(message)s")
# 终端日志
consle_handler = logging.StreamHandler(sys.stdout)
consle_handler.setFormatter(formatter)  # 日志文件的格式
logger.setLevel(logging.DEBUG)  # 设置日志文件等级

from .m3u8_4 import M3U8 as M3U8_4

M3U8 = M3U8_4
__all__ = ['M3U8']

if __name__ == '__main__':
    logger.addHandler(consle_handler)  # 添加控制台
    # db_ = r'C:\code\Py\HTTP\Download_m3u8\down\test\m3u8Info.db'
    # if os.path.exists(db_): os.remove(db_)
    m = M3U8(
        "https://cdn-ali-dest.dushu.io/media/video/1577439434d300eba4fd17caf4675f90bb0bdd9f4dfmpzv2/2/playlist.m3u8",
        local_root='D:/H1/FDReader/m3u8/',
        save_name='论大传略',
        debug_level=3,
        threads=5
    )
    m.run()
