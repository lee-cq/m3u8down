#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : SQLCommon
@Author     : LeeCQ
@Date-Time  : 2020/2/23 16:43

"""
import logging
import sys
import json

logger = logging.getLogger("SQL")  # 创建实例
formatter = logging.Formatter("[%(asctime)s] < %(funcName)s: %(lineno)d > [%(levelname)s] %(message)s")
# 终端日志
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)  # 日志文件的格式
logger.setLevel(logging.DEBUG)  # 设置日志文件等级


def _get(_l: list or tuple, n: int) -> str:
    """列表中取值，"""
    try:
        return _l[n]
    except:
        return ''


def sql_join(data: (tuple, list)) -> tuple:
    """在创建表的时候，通过给定的元组生成SQL语句

    给定的元组形式：
        (字段名，共有属性，MySql属性，Sqlite属性)  -- 4 元素

    :param data: 这是嵌套元组 (( ), ...)
    :return (mysql, sqlite)
    """
    return (
        ', '.join(
            [_ for _ in [' '.join(
                [_i for _i in [m[0], m[1], _get(m, 2)] if _i.strip() != '']
            ) for m in data] if _.strip() != '']
        ),
        ', '.join(
            [_ for _ in [' '.join(
                [_i for _i in [m[0], m[1], _get(m, 3)] if _i.strip() != '']
            ) for m in data] if _.strip() != '']
        )
    )


class SQLiteJson:
    """SQLite的JSON数据类型支持"""


if __name__ == '__main__':
    _c = (('No', ' ', 'INT(4) PRIMARY KEY AUTO_INCREMENT', 'INTEGER PRIMARY KEY AUTOINCREMENT'),
          ('orderId', 'BIGINT UNIQUE'),
          ('orderNumber', 'BIGINT UNIQUE'),
          ('user', 'VARCHAR(20)'),
          ('passwd', 'VARCHAR(36)'),
          ('albumId', 'INT(5)'),
          ('albumName', 'VARCHAR(50)'),
          ('officePrice', 'FLOAT')
          )
    print(sql_join(_c)[0])
