#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : sqlite-test-blob.py
@Author     : LeeCQ
@Date-Time  : 2020/7/26 18:23
"""
import sqlite3

db = sqlite3.connect('test.db')
cur = db.cursor()

cur.execute("CREATE TABLE if not exists t (b BLOB);")

with open('../sup/GetKey', 'rb') as f:
    cur.execute("insert into t values(?)", (sqlite3.Binary(f.read()), ))
    db.commit()

cur.execute('select b from t limit 1')
b = cur.fetchone()[0]

with open('../sup/key', 'wb') as f:
    f.write(b)

db.close()