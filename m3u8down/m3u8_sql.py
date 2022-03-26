#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : m3u8_sql.py
@Author     : LeeCQ
@Date-Time  : 2022/2/26 18:12
"""
import time
from pathlib import Path
from sqllib import SQLiteAPI

from small_tools import sum_prefix_md5, logger


class M3U8SQL(SQLiteAPI):
    """SQL相关操作

    :param db - 数据库位置
    :param m3u8_uri - 需要下载的M3U8的网络路径
    :param m3u8_name - 希望保存在本地的名字
    :param prefix - 计算好的前缀
    :param save_path - M3U8的保存位置
    """
    _db_name = '.m3u8DownInfo.db'
    prefix_map_name = 'prefix_map'

    def __init__(self, base_path='.', db=None, m3u8_uri=None, m3u8_name=None, prefix=None, **kwargs):

        if db:
            db = Path(db)
            self._db = db.joinpath(self._db_name) if db.is_dir() else db
        else:
            self._db = Path(base_path).joinpath(self._db_name)
        logger.debug(f'开始准备数据库对象, 位于: {self._db}, base_path= {base_path}')

        self.m3u8_name = m3u8_name
        self.m3u8_uri = m3u8_uri
        self.base_path = Path(base_path) if base_path else self._db.parent

        self._kwargs = kwargs

        self.no_prefix_api = SQLiteAPI(self._db, **kwargs)
        self.prefix = prefix or self.make_prefix()
        self._create_prefix_table()
        super().__init__(self._db, prefix=self.prefix, **kwargs)

        if prefix and prefix not in self.prefixes_list:
            raise NotImplementedError("指定的前缀在库中不存在！")

        elif self.prefix and self.prefix not in self.prefixes_list:
            self.is_new = True
            self._insert_prefix()

        else:
            self.is_new = False

    @property
    def save_path(self):
        try:
            return Path(self.prefix_map_select('save_path', WHERE=f'`prefix_md5`="{self.prefix}"')[0][0])
        except Exception as _e:
            logger.error(
                f'预期失败：{_e}' + '\t查询内容' + str(self.prefix_map_select('save_path', WHERE=f'`prefix_md5`="{self.prefix}"')),
            )
            return self.base_path.joinpath(self.m3u8_name)

    def make_prefix(self):
        """创建并插入前缀"""
        if (self.m3u8_name and not self.m3u8_uri) or (not self.m3u8_name and self.m3u8_uri):
            raise ValueError('m3u8_name & m3u8_uri 必须同时存在或不存在')
        if not self.m3u8_name:
            return ''  # 全部参数为空的时候返回一个空前缀的对象

        return sum_prefix_md5(self.m3u8_uri, self.base_path.joinpath(self.m3u8_name))

    @property
    def prefixes_list(self) -> list:
        """返回已有的前缀列表"""
        return [i[0] for i in self.prefix_map_select('prefix_md5')]

    def _insert_prefix(self):
        """FIXME"""
        _s = self.prefix_map_install(
            prefix_md5=self.prefix,
            m3u8_uri=self.m3u8_uri,
            m3u8_name=self.m3u8_name,
            save_path=self.save_path.absolute().__str__(),
            create_time=int(time.time())

        )

    def tables_name(self) -> list:
        """如果指定了表前缀，则仅返回符合前缀的表"""
        return [i.removeprefix(self.prefix) for i in super(M3U8SQL, self).tables_name() if i.startswith(self.prefix)]

    def prefix_map_update(self, **kwargs):
        return self.no_prefix_api.update(self.prefix_map_name, 'prefix_md5', self.prefix, **kwargs)

    def prefix_map_install(self, ignore_repeat=True, **kwargs):
        return self.no_prefix_api.insert(self.prefix_map_name, ignore_repeat=ignore_repeat, **kwargs)

    def prefix_map_select(self, cols, *args, result_type=None, **kwargs):
        return self.no_prefix_api.select(self.prefix_map_name, cols, *args, result_type=result_type, **kwargs)

    def _create_prefix_table(self):
        """前缀映射表"""
        _c = (
            "prefix_md5   varchar(32) not null unique , -- MD5表前缀(uri的Md5)\n "  # 
            "m3u8_name  varchar(256) not null ,         -- 下载视频的名字\n"
            "m3u8_uri VARCHAR(512) not null,            -- 下载视频的原始URI地址\n"
            "m3u8_base VARCHAR(256),                    -- M3U8 相对路径\n "
            "m3u8_text  TEXT ,                          -- 下载的m3u8文档原文\n"
            "m3u8_parse  TEXT,                          -- M3U8解析结果 JSON\n"  # TODO 目前只考虑1层播放列表的情况
            "save_path VARCHAR(128) not null,           -- 下载位置 \n"
            "create_time INT ,                          -- 此条记录的创建时间\n"
            "need_combine bool ,                        -- 是否需要合并单一文件\n"
            "combined_md5 varchar(32),                  -- 已经合并单一文件MD5值\n"
            "need_transcode bool,                       -- 是否需要转码文件 \n"
            "transcode_args TEXT,                       -- 转码参数 JSON \n"
            "transcode_md5 varchar(32) ,                -- 转码后的文件的MD5值\n "
            "need_clean    BOOL  ,                      -- 是否需要清理中间产物 \n "
            "completed_time int                         \n"
            ""
        )
        return self.no_prefix_api.create_table(table_name=self.prefix_map_name, cmd=_c, exists_ok=True)

    def create_master(self):
        """创建表: master"""
        _c = ("abs_uri      varchar(150) not null unique, "
              "resolution   int, "  # 长 * 宽
              "audio        varchar(100) "
              )
        return self.create_table(table_name='master', cmd=_c, exists_ok=True)

    def create_segments(self, table_name):
        """创建表: segments"""
        _c = (" idd      INTEGER PRIMARY KEY AUTOINCREMENT, "
              " uri  varchar(160) not null UNIQUE, "
              " segment_name varchar(50) , "
              " duration float, "
              " key_uri    varchar(160) ,  "
              " key_value  blob, "
              " key_method  varchar(10), "
              " key_iv      varchar(50) "
              )
        self.create_table(table_name=table_name, cmd=_c, exists_ok=True)
        # self.sql.write_db(f"UPDATE sqlite_sequence SET seq=0 WHERE name=`{table_name}`")

    def create_config(self):
        """创建表 - 配置文件"""
        _c = "key_ varchar(50) not null unique, value_ VARCHAR(100)"
        return self.create_table(table_name='config', cmd=_c, exists_ok=True)
