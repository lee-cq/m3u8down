#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : install_ffmpeg.py
@Author     : LeeCQ
@Date-Time  : 2023/12/3 15:42

"""
import platform
import tarfile
import tempfile

import rich.progress

from httpx import get, stream

from zipfile import ZipFile
from tarfile import TarFile

download_url = {

    ("Darwin", "arm64"): "https://evermeet.cx/ffmpeg/ffmpeg-6.1.zip",
    ("Darwin", "x86_64"): "https://evermeet.cx/ffmpeg/ffmpeg-6.1.zip",
    ("Linux", "x86_64"): "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
    ("Linux", "aarch64"): "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz",
    ("Windows", "AMD64"): "https://ffmpeg.zeranoe.com/builds/win64/static/ffmpeg-latest-win64-static.zip",
    ("Windows", "x86"): "https://ffmpeg.zeranoe.com/builds/win32/static/ffmpeg-latest-win32-static.zip",
}


class Install:
    def __init__(self, url=None):
        self.file = tempfile.NamedTemporaryFile()
        self.url = url or self.get_url()
        self.name = self.url.split('/')[-1].split('?')[0]
        self.download(self.url)
        self.unpackage()

    def __del__(self):
        self.file.close()

    @staticmethod
    def get_url():
        version = platform.system(), platform.machine()
        if version not in download_url:
            raise Exception(f"不支持的平台: {version}")
        return download_url.get(version)

    def download(self, url):
        print(f"正在下载: {self.url}")

        with stream("GET", url) as response:
            total = int(response.headers["Content-Length"])
            print("大小：", total)
            with rich.progress.Progress(
                    "[progress.percentage]{task.percentage:>3.0f}%",
                    rich.progress.BarColumn(bar_width=None),
                    rich.progress.DownloadColumn(),
                    rich.progress.TransferSpeedColumn(),
            ) as progress:
                download_task = progress.add_task("Download", total=total)
                for chunk in response.iter_bytes():
                    self.file.write(chunk)
                    progress.update(download_task, completed=response.num_bytes_downloaded)

    def unpackage(self):
        name = self.url.split('/')[-1].split('?')[0]
        if name.endswith(".zip"):
            with ZipFile(self.file, 'r') as _f:
                _f.extractall()

        if tarfile.is_tarfile(self.file):
            with TarFile.open(self.file) as _f:
                _f.extractall()
        print("解压完成")


if __name__ == '__main__':
    Install(
        # 'https://alist.leecq.cn/d/local/Another%20Redis%20Desktop%20Manager.zip?sign=lctaqsRz3g2QU_IK71TNUQvXWFcrRLMe-keeiHsI5EQ=:0'
    )
