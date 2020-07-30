#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : sqlite.py
@Author     : LeeCQ
@Date-Time  : 2020/1/13 12:30

SQLite

2020.01.28 -- _select OFFSET 添加str()
"""

import sqlite3
from .SQLCommon import sql_join
import logging
import sys
logger = logging.getLogger("logger")  # 创建实例
formatter = logging.Formatter("[%(asctime)s] < %(funcName)s: %(thread)d > [%(levelname)s] %(message)s")
# 终端日志
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)  # 日志文件的格式
logger.setLevel(logging.DEBUG)  # 设置日志文件等级


class SQLiteError(Exception):
    """基础错误"""


class SQLiteWriteError(SQLiteError):
    """写数据库错误"""


class SQLiteReadError(SQLiteError):
    """都数据库错误"""


class SQLiteInsertZipError(SQLiteError):
    """数据打包错误"""


class SQLiteNameError(SQLiteError):
    """数据库名称错误"""


class SQLiteModuleError(SQLiteError):
    """数据库模块错误"""


# 以字典形式返回游标的sqlite实现
def dict_factory(cursor, row) -> dict:
    """用来替换sqlite.connect().row_factory

    :return: dict
    """
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class MySQLite:
    """SQLite实现的基类

    """

    def __init__(self, db, **kwargs):
        self._sql = sqlite3.connect(db, **kwargs)
        self.TABLE_PREFIX = '' if 'prefix' not in kwargs.keys() else kwargs['prefix']

    def close_db(self):
        """关闭数据库链接，并退出"""
        self._sql.close()

    @property
    def get_connect(self):
        """返回数据库链接句柄"""
        return self._sql

    # 写数据库操作
    def __write_db(self, command, args=None):
        __sql = self._sql
        cur = __sql.cursor()  # 使用cursor()方法获取操作游标
        try:
            if not args:
                cur.execute(command)
            else:
                cur.execute(command, args)
            __sql.commit()  # 提交数据库
            return 0
        except sqlite3.IntegrityError as e:
            __sql.rollback()
            raise sqlite3.IntegrityError(e)
        except Exception as e:
            __sql.rollback()
            raise SQLiteError(f'操作数据库时出现问题，数据库已回滚至操作前：{e}')
        finally:
            cur.close()

    def __write_no_except(self, command, args=None):
        """未收集错误的"""
        __sql = self._sql
        cur = __sql.cursor()  # 使用cursor()方法获取操作游标
        if not args:
            cur.execute(command)
        else:
            cur.execute(command, args)
        __sql.commit()  # 提交数据库
        cur.close()
        return 0

    def __write_many(self, command, args):
        """数据库事务写入。"""
        __sql = self._sql
        cur = __sql.cursor()
        try:
            cur.executemany(command, args)
            __sql.commit()
            return cur.rowcount
        except Exception as e:
            __sql.rollback()
            sys.exc_info()
            raise SQLiteWriteError(f"执行写事物时出错，已回滚：{e}")
        finally:
            cur.close()

    def __read_db(self, command, result_type=None):
        """数据库读取的具体实现。主要涉及数据库查询"""
        __sql = self._sql
        if result_type is dict:
            __sql.row_factory = dict_factory
        else:
            __sql.row_factory = sqlite3.connect('').row_factory
        cur = __sql.cursor()
        cur.execute(command)
        results = cur.fetchall()
        cur.close()
        return results

    def read_db(self, cmd, result_type=None):
        """是菊科操作的对外接口。"""
        return self.__read_db(cmd, result_type=result_type)

    def write_db(self, cmd, args=None):
        """数据库操作的对外接口。"""
        # logger.warning("使用此函数时注意表前缀! ")
        return self.__write_db(cmd, args)

    def write_no_except(self, cmd, args=None):
        """数据库写入对外接口，它没有收集任何错误! """
        logger.warning("使用此函数时注意表前缀! ")
        return self.__write_no_except(cmd, args)

    # 判断表、键值的存在性
    def _key_and_table_is_exists(self, table, *args, **kwargs):
        """ 判断 key & table 是否存在

        :param table: 前缀 + 表单名
        :param key, args: 键名
        :param kwargs: 键名=键值；
        :return: 0 存在
        """
        if table not in self.show_tables():
            raise SQLiteNameError(f"{table} NOT in The Database. (ALL Tables {self.show_tables()}")
        cols = self.show_columns(table)

        not_in_table_keys = [k for k, v in kwargs.items() if k not in cols]
        not_in_table_keys += [k for k in args if k not in cols]
        if not_in_table_keys:
            raise SQLiteNameError(f'The key {not_in_table_keys} NOT in this Table: {table};'
                                  f'(ALL Columns {cols})'
                                  )
        return 0

    # 创建数据库
    def create_table(self, table_name, keys, ignore_exists=True):
        """创建数据表

           CREATE TABLE IF NOT EXISTS COMPANY(
           ID INT PRIMARY KEY     NOT NULL,
           NAME           TEXT    NOT NULL,
           AGE            INT     NOT NULL,
           ADDRESS        CHAR(50),
           SALARY         REAL
            );
        """
        if isinstance(keys, tuple):
            keys = sql_join(keys)[1]  #
        keys = keys.rstrip().rstrip(',')
        _ignore = ' IF NOT EXISTS ' if ignore_exists else ''

        _c = f"CREATE TABLE {_ignore} {self.TABLE_PREFIX}{table_name} ( "
        _c += keys + ");"
        logger.debug(_c)
        # print(_c)
        return self.__write_db(_c)

    @staticmethod  # 插入或更新多条数据时，数据格式转换
    def _insert_zip(values):
        """一次向插入数据库多条数据时，打包相应的数据。"""
        for x in values:
            if not isinstance(x, (tuple, list)):
                raise SQLiteInsertZipError(f"INSERT多条数据时，出现非列表列！确保数据都是list或者tuple。\n错误的值是：{x}")
            if not len(values[0]) == len(x):
                raise SQLiteInsertZipError(f'INSERT多条数据时，元组长度不整齐！请确保所有列的长度一致！\n'
                                           f'[0号]{len(values[0])}-[{values.index(x)}号]{len(x)}')
        return tuple([v for v in zip(*values)])  # important *

    # 插入表数据
    def _insert(self, table_name, ignore_repeat=False, **kwargs):
        """ 向数据库插入内容。

        :param table_name: 表名；
        :param kwargs: 字段名 = 值；
        :return:
        """
        _ignore = 'OR IGNORE' if ignore_repeat else ''
        _c = f"INSERT {_ignore} INTO {self.TABLE_PREFIX}{table_name} ( "
        _c += ", ".join([_ for _ in kwargs.keys()]) + " ) "
        _c += "VALUES ( "
        _c += ", ".join([f"?" for _ in kwargs.values()]) + ");"

        if isinstance(list(kwargs.values())[0], (tuple, list)):  # kwargs第一个键是不是字符串
            arg = self._insert_zip(tuple(kwargs.values()))
            return self.__write_many(_c, arg)
        else:
            for x in kwargs.values():
                if isinstance(x, (list, tuple, set)):
                    raise SQLiteInsertZipError(f"INSERT一条数据时，出现列表列或元组！确保数据统一: VALUE({x})")
            return self.__write_db(_c, list(kwargs.values()))  # 提交

    def _insert_rows(self, table_name, args, k=None, ignore_repeat=False):
        """插入

        :param table_name:
        :param args:
        :param ignore_repeat:
        :return:
        """
        _a = [_.values() for _ in args]
        if k is None:
            if not isinstance(args[0], dict):
                raise ValueError(f'既没有k, 也不是dict')
            k = args[0].keys()
        _ignore = 'OR IGNORE' if ignore_repeat else ''
        _c = f"INSERT {_ignore} INTO {self.TABLE_PREFIX}{table_name} ( "
        _c += ", ".join([_ for _ in k]) + " ) "
        _c += "VALUES ( "
        _c += ", ".join([f"?" for _ in args[0].values()]) + ");"
        return self.__write_many(_c, _a)

    # 检索表
    def _select(self, table, cols: list and tuple, result_type=None, **kwargs):
        """ select的应用。

            ·· `就不再支持 * `
            ·· column_name, table, key 可以用 ` ` 包裹， value 一定不能用， value 用 ' ' 。
        :param result_type: {dict, other}
        :param table:
        :param cols: 传参时自行使用 `` , 尤其是数字开头的参数
        :param kwargs: {'WHERE', 'LIMIT', 'OFFSET', ORDER} 全大写
        :return 结果集
        """
        command = f'SELECT  ' + ' , '.join(cols) + ' ' + f'FROM `{self.TABLE_PREFIX}{table}` '
        # ===========================================
        # 下面是更好的解决方案
        # ===========================================
        # for key, value in kwargs.items():
        #     key = key.upper()
        #     if key in ['WHERE', 'LIMIT', 'OFFSET']:
        #         command += f' {key}  {value}'
        #     if key == 'ORDER':
        #         command += f' {key} BY {value}'
        # ===========================================
        command += ' '.join([' '.join((key.upper(), str(value))) for key, value in kwargs.items()
                             if key.upper() in ['WHERE', 'LIMIT', 'OFFSET']]) + '  '
        command += ' '.join([f'ORDER BY {value}' for key, value in kwargs.items()
                             if key.upper() == 'ORDER']) + ' '
        # print(command)
        return self.__read_db(command, result_type=result_type)

    # 更新表
    def _update(self, table, where_key, where_value, **kwargs):
        """ 更新数据库

        :param table: 数据表名字
        :param where_key: where的键
        :param where_value: where的值
        :param kwargs: 更新的键 = 更新的值， 注意大小写，数字键要加 - ``
        :return: 0 成功。
        """
        self._key_and_table_is_exists(self.TABLE_PREFIX + table, where_key, **kwargs)  # 判断 表 & 键 的存在性！

        command = f"UPDATE `{self.TABLE_PREFIX}{table}` SET  " + \
                  ' , '.join([f" {k}=? " for k, v in kwargs.items()]) + \
                  f" WHERE `{where_key}`='{where_value}' ;"  # 构造WHERE语句

        return self.__write_db(command, [_ for _ in kwargs.values()])  # 执行SQL语句

    # 删除表数据 一行
    def _delete(self, table, **kwargs):
        """删除数据表中的某一行数据，
        :param table:
        :param kwargs: 键名=键值；最好是数据库的主键或唯一的键。如果数据库没有，则最好组合where，以保证删除 - 唯一行。
        """
        self._key_and_table_is_exists(self.TABLE_PREFIX + table, **kwargs)  # 判断键的存在性

        command = f"DELETE FROM `{self.TABLE_PREFIX}{table}` WHERE  "
        for k, v in kwargs.items():
            command += f"{k}='{v}'"
        return self.__write_db(command)

    # 删除表或者数据库
    def _drop(self, option, name):
        """ 删除数据库内容：

        :param option: (TABLE or INDEX)
        :param name:
        :return: 0 成功
        """
        if option.upper() == 'TABLE':
            command = f'DROP  {option}  `{self.TABLE_PREFIX}{name}`'
        else:
            command = f'DROP  {option}  `{name}`'
        return self.__write_db(command)

    def show_tables(self, name_only: bool = True):
        """

        :param name_only:
        :return: {'type': 类型(table), 'name': 名称, 'tbl_name': 所属表明, 'rootpage': 表编号, 'sql':创建表时执行的SQL语句
        """
        if name_only:
            return [_[0] for _ in self.read_db('SELECT name FROM sqlite_master where type="table";')]
        else:
            return [_ for _ in self.read_db('SELECT * FROM sqlite_master where type="table";', result_type=dict)]

    def show_columns(self, table_name, name_only=True) -> list:
        """显示列信息

        :return: {'cid': 0, 'name': 'id', 'type': 'int', 'notnull': 0, 'dflt_value': None, 'pk': 0}
                  字段编号     字段名        字段类型        不允许null      默认值
        """
        table_name = self.TABLE_PREFIX + table_name
        if name_only:
            return [_['name'] for _ in self.read_db(f'PRAGMA table_info({table_name});', result_type=dict)]
        else:
            return [_ for _ in self.read_db(f'PRAGMA table_info({table_name});', result_type=dict)]

    # 修改表结构
    def _alter(self, table, command):
        """ 目前sqlite只支持RENAME，ADD COLUMN """
        table = self.TABLE_PREFIX + table
        _c = f'ALTER TABLE {table}  {command}'
        return self.__write_db(_c)


class SQLiteAPI(MySQLite):
    """接口类"""

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_db()

    def __enter__(self):
        return self

    def insert(self, table_name, ignore_repeat=False, **kwargs):
        """插入数据到数据库，支持插入多条数据。

        :param table_name:
        :param ignore_repeat:
        :param kwargs: 需要插入的 字段名=值 （当值为list or tuple时，开启事物插入多条数据）
                        当多个字段的list长度不一致时，抛出ZIPError。
        :return:
        """
        return self._insert(table_name, ignore_repeat=ignore_repeat, **kwargs)

    # 更好的解决方案：insert(ignore_repeat=True, ...)
    def insert_line2line(self, table_name, **kwargs):
        """已单条的形式插入大量数据 - 不推荐"""
        logger.warning('这个函数的性能极低！谨慎使用！')
        if not isinstance(list(kwargs.values())[0], str):  # kwargs第一个键是不是字符串
            arg = self._insert_zip(tuple(kwargs.values()))
            for _a in arg:  # 关键逻辑
                try:
                    self._insert(table_name, **{_k: _a[index] for index, _k in enumerate(kwargs.keys())})
                except Exception as e:
                    logger.warning(f'Except: {e}')
            return 0
        else:
            raise SQLiteModuleError('插入单条数据请使用 insert()方法。')

    def select(self, table, cols, *args, result_type=None, **kwargs):
        """

        :param table:
        :param cols:
        :param result_type:
        :param kwargs: {'WHERE', 'LIMIT', 'OFFSET', ORDER} 全大写
        :return:
        """
        _cols = []
        if isinstance(cols, str):
            _cols.append(cols)
        if isinstance(cols, (list, tuple)):
            [_cols.append(_) for _ in cols]
        if not args:
            [_cols.append(_) for _ in args]
        return self._select(table, _cols, result_type=result_type, **kwargs)

    def update(self, table, where_key, where_value, **kwargs):
        """更新数据库数据 -

        :param table:
        :param where_key:
        :param where_value:
        :param kwargs:
        :return:
        """
        return self._update(table, where_key, where_value, **kwargs)

    def delete(self, table, **kwargs):
        """删除数据表中的某一行数据，
        :param table:
        :param kwargs: 键名=键值；最好是数据库的主键或唯一的键。如果数据库没有，则最好组合where，以保证删除 - 唯一行。
        :return
        """
        return self._delete(table, **kwargs)

    def drop_table(self, table_name):
        """删除一个数据库"""
        return self._drop('TABLE', table_name)

    def drop_index(self, index_name):
        """删除一个索引"""
        return self._drop('INDEX', index_name)

    def alter_rename(self, old_name, new_name):
        """重命名表"""
        new_name = self.TABLE_PREFIX + new_name
        cmd = f'RENAME TO `{new_name}`'
        return self._alter(old_name, cmd)

    def alter_all_column(self, table_name, columns_info):
        """怎加表的列"""
        cmd = f'ADD COLUMN {columns_info}'
        return self._alter(table_name, cmd)


if __name__ == '__main__':
    logger.addHandler(console_handler)  #

    a = SQLiteAPI('./sup/test.db')
    a.create_table('test2', 'id int unique, name varchar(100)', ignore_exists=True)
    _ = a.insert('test2', ignore_repeat=True, id=[7, 8, 19], name=['ww', 'qq', 'ee'])
    # _ = a.insert_line2line('test2', id=[7,8,9], name=['ww', 'qq', 'ee'])
    # a.write_no_except(f"insert or IGNORE into test2 (id, name) VALUES ('1', 'name1');")
    # a.update('test2', 'id', 1, name='NEW')
    # a.delete('test2', id='2')
    _ = a.select('test2', '*', result_type=dict)
    # _ = a.read_db('PRAGMA table_info(test1);', result_type=dict)
    print(_)
