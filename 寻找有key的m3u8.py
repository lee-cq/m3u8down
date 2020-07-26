#!/usr/bin/python3 
# -*- coding: utf-8 -*-
"""
@File Name  : 寻找有key的m3u8.py
@Author     : LeeCQ
@Date-Time  : 2020/1/18 0:09

"d_playurl"
"""
import sys, logging

logger = logging.getLogger("logger")  # 创建实例
formatter = logging.Formatter("[%(asctime)s] < %(funcName)s: %(thread)d > [%(levelname)s] %(message)s")
# 终端日志
consle_handler = logging.StreamHandler(sys.stdout)
consle_handler.setFormatter(formatter)  # 日志文件的格式
logger.setLevel(logging.DEBUG)  # 设置日志文件等级
logger.addHandler(consle_handler)  #
import json
import os, m3u8
from SQL.MySQL import TencentMySQL


class FindKey(TencentMySQL):
    def __init__(self, user='test', passwd='test123456', db='test', **kwargs):
        super().__init__(user, passwd, db, warning=False, **kwargs)
        self.create_table_()

    def create_table_(self):
        _c = "Uri varchar(150) UNIQUE, text MEDIUMTEXT"
        return self.create_table(_c, table_name='m3u8Uri')


filePath = '../Download_9C/data/'


from HTTP.Download_9C.c2_root import sort_relation
from HTTP.common import request_class

requests = request_class.HTTPRequests(timeout=40)

m3u8List = []
fileList = [f'{os.path.abspath(filePath)}\\{sort["id"]}.txt' for sort in sort_relation if sort['type'] == "video"]
[m3u8List.append(_["d_playurl"]) for _list in [json.load(open(file)) for file in
                                               [f'{os.path.abspath(filePath)}\\{sort["id"]}.txt'
                                                for sort in sort_relation if sort['type'] == "video"
                                                ]
                                               ]
 for _ in _list
 ]
m3u8Uri = FindKey()


def parse_m3u8(_uri):
    _ = requests.get(_uri)[1].text
    _m3u8 = m3u8.loads(_, uri=_uri)
    if _m3u8.playlists:
        for playlist in _m3u8.playlists:
            parse_m3u8(playlist.absolute_uri)
    if _m3u8.segments:
        for s in _m3u8.segments:
            if s.key is not None:
                m3u8Uri.insert('m3u8Uri', ignore=True, Uri=_uri, text=_)
    if _m3u8.keys:
        m3u8Uri.insert('m3u8Uri', ignore=True, Uri=_uri, text=_)
    return 0


n = 0
for u in m3u8List:
    try:
        n += 1
        parse_m3u8(u)
        print(f'已完成第{n}个: {u}')
        logger.info(f'已完成第{n}个: {u}')
    except Exception as e:
        logger.error(e)
