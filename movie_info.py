#!/usr/bin/python3 
# -*- coding: utf-8 -*-
"""
@File Name  : movie_info.py
@Author     : LeeCQ
@Date-Time  : 2020/1/20 11:19

"""
import json, subprocess

videoFile = './down/test/01.ts'


# 定义个方法，获取单个media文件的元数据，返回为字典数据
# 此程序核心是调用了mediainfo工具来提取视频信息的
def get_media_info(file):
    pname = r'.\sup\mediaInfo_CLI\MediaInfo.exe "%s" --Output=JSON' % file
    result = subprocess.Popen(pname, shell=False, stdout=subprocess.PIPE).stdout
    list_std = result.read()
    str_tmp = list_std
    open('./sup/test_mediaInfo.json', 'w', encoding='utf8').write(str_tmp.decode('utf8'))
    json_data = json.loads(str_tmp)
    return json_data


# 定义个方法传递字典数据,返回自己想要的字段数据,返回值列表
def get_dict_data(json_data):
    # 获取文件大小
    filesize = json_data['media']['track'][0]['FileSize']
    # 获取码率
    malv = json_data['media']['track'][0]['OverallBitRate'][0:4]
    # 获取播放时长
    duration = json_data['media']['track'][0]['Duration'].split('.')[0]
    # 获取文件类型
    file_format = json_data['media']['track'][0]['Format']
    # 获取帧宽
    samp_width = json_data['media']['track'][1]['Sampled_Width']
    # 获取帧高
    samp_height = json_data['media']['track'][1]['Sampled_Height']
    return [filesize, malv, duration, file_format, samp_width, samp_height]


print(get_dict_data(get_media_info(videoFile)))

