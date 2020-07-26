# -*- coding: utf-8 -*-
"""
@Time   : 2019/11/25 13:15
@Author : LeeCQ

[MySQL(pymysql, 需要服务器),  MongoDB(pyMongoDB，需要服务器),
 SQLite(关系型数据库, Python原生支持),
 bsddb(NoSQL Bsddb3),
 UnQLite(NoSQL),
 LiteDB(.NET开发轻量级,文件数据库, For Python v1.0.0),  # https://pypi.org/project/litedb/
 CodernityDB(纯Python开发, 功能不足),  #
 Redis(需要安装软件),


]

MySQL:

SQLite:

MongoDB:

bsddb: ??

UnQLite:
    描述：嵌入式NoSQL - 体积小，无服务器， 源码付费
    官网：https://unqlite.org/
    简介：https://blog.csdn.net/robinL2005/article/details/40182699

LiteDB:
    官网：http://www.litedb.org/
"""

from .sqlite import SQLiteAPI
# from .MySQL import MyMySqlAPI, TencentMySQL
from .SQLCommon import sql_join

# from . import SQLCommon

# 直接访问会出错，但是，其他模块可以正常导入这些API

__all__ = ['SQLCommon',
           'SQLiteAPI', 'MyMySqlAPI', 'TencentMySQL', 'sql_join']
