#!/usr/bin/python3 
# -*- coding: utf-8 -*-
"""
@File Name  : test_moviepy.py
@Author     : LeeCQ
@Date-Time  : 2020/1/20 12:37

"""
import sys, os
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.video.compositing.concatenate import concatenate_videoclips
from natsort import natsorted



final_clip = concatenate_videoclips(video_list)  # 进行视频合并
final_clip.to_videofile(target, fps=24, remove_temp=True)  # 将合并后的视频输出

