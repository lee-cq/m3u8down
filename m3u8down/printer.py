#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : printer.py
@Author     : LeeCQ
@Date-Time  : 2023/12/11 21:14

"""
import time
from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn, ProgressColumn, SpinnerColumn
from rich import get_console

from rich.logging import RichHandler

with Progress(
        auto_refresh=True,

) as progress:
    progress.columns = [
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeRemainingColumn(),
    ]
    task1 = progress.add_task("[red]Downloading...", total=100)
    task2 = progress.add_task("[green]Processing...", total=100)
    task3 = progress.add_task("[cyan]Cooking...", total=100)

    while not progress.finished:
        get_console().print("Hello, World!")

        progress.update(task1, advance=0.5)
        progress.update(task2, advance=0.3)
        progress.update(task3, advance=0.8)
        progress.refresh()
        time.sleep(0.02)
