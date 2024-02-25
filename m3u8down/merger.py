#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : merge.py
@Author     : LeeCQ
@Date-Time  : 2023/12/3 03:07

M3U8 合并器

"""
from pathlib import Path
import subprocess
from m3u8 import loads


class TsMerger:
    exec_ffmpeg = Path(__file__).parent.joinpath('ffmpeg')

    def __init__(self, m3u8: Path | str, target: Path | str):
        self.m3u8 = Path(m3u8)
        self.target = Path(target)

        self.base_path = self.m3u8.parent
        self.loaded_m3u8 = loads(self.m3u8.read_text())

        if self.target.exists():
            # self.target.unlink()
            raise FileExistsError(f"目标文件已存在: {target}")

    def to_mp4(self):
        """将合并后的ts文件转换为mp4文件"""
        if not self.exec_ffmpeg.exists():
            raise FileNotFoundError(f"ffmpeg 未找到: {self.exec_ffmpeg}")
        subprocess.run(
            [str(self.exec_ffmpeg),
             '-i', self.m3u8.as_posix(), '-c', 'copy',
             self.target.with_suffix('.mp4').as_posix()
             ],
            cwd=self.base_path,
            check=True
        )
