#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Setup module for core.

@File Name  : setup.py
@Author     : LeeCQ
@Date-Time  : 2020/7/30 11:42
"""
import logging
import os
import platform
from setuptools import setup, find_packages

PACKAGE = "m3u8Download"
DESCRIPTION = "Download a m3u8 video."
AUTHOR = "Lee CQ"
AUTHOR_EMAIL = "lee-cq@qq.com"
# URL = "null"

TOPDIR = os.path.dirname(__file__) or "."
VERSION = __import__(PACKAGE).__version__

with open("requirements.txt") as fp:
    requires = fp.read().split('\n')


setup_args = {
    'version': VERSION,
    'description': DESCRIPTION,
    # 'long_description': LONG_DESCRIPTION,
    'author': AUTHOR,
    'author_email': AUTHOR_EMAIL,
    'license': "Apache License 2.0",
    # 'url': URL,
    'keywords': ["m3u8", "download", "video"],
    'packages': find_packages(exclude=["tests*"]),
    # 'package_data': {'aliyunsdkcore': ['data/*.json', '*.pem', "vendored/*.pem"],
    #                  'aliyunsdkcore.vendored.requests.packages.certifi': ['cacert.pem']},
    'platforms': 'any',
    'install_requires': requires,
    'classifiers': [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development',
    ]
}

setup(name='m3u8-down', **setup_args)
