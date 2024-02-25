#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : down_list.py
@Author     : LeeCQ
@Date-Time  : 2023/12/3 18:08

从列表批量下载
======文件模型======
{
    "name": "系列名称",
    "base_path": "/Movies/",
    "count": 48
}

URI 编号或子名称  # 一行一个，不支持注释
https://vod2.kcs/index.m3u8 01
https://vod2.kczybf.com/20230630/WbLVqG9A/1500kb/hls/index.m3u8 02
https://vod2.kczybf.com/20230630/ofMpuIjr/1500kb/hls/index.m3u8 03

"""
import asyncio
import json
import logging
from pathlib import Path

from models import DownloadList
from downloader import Downloader

logger = logging.getLogger('m3u8down.down_list')


async def create(se, *args, **keywords):
    async with se:
        return await Downloader(*args, **keywords).async_run()


async def down_list(list_file):
    """从列表批量下载"""
    list_file = Path(list_file).absolute()
    if not list_file.exists():
        raise FileNotFoundError(f"列表文件不存在: {list_file}")

    meta, list_ = list_file.read_text().split('\n\n', maxsplit=1)
    down_info: DownloadList = DownloadList(**json.loads(meta))
    for line in list_.split('\n'):
        if not line.strip():
            continue
        uri, index = line.split()
        down_info.items.setdefault(f"{down_info.name}-{index}", uri)

    if down_info.base_path.name != down_info.name:
        down_info.base_path = down_info.base_path.joinpath(down_info.name)

    down_info.base_path.mkdir(parents=True, exist_ok=True)
    down_info.base_path.joinpath('down_list.json').write_text(down_info.model_dump_json(indent=2), encoding='utf-8')
    logger.info("下载信息：\n%s", down_info.model_dump_json(indent=2))

    tasks = []
    se = asyncio.Semaphore(down_info.max_workers)
    for name, uri in down_info.items.items():
        if down_info.base_path.joinpath(name + '.mp4').exists():
            logger.info("已经下载%s， 跳过。。。", name)
            continue
        print(f"下载 {name} {uri}")
        tasks.append(asyncio.create_task(
            create(
                se,
                uri,
                down_info.base_path.joinpath(name),
                max_thread=down_info.max_threads,
            )
        ))
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    logging.basicConfig(level='INFO')
    asyncio.run(down_list('../test/down.list'))
