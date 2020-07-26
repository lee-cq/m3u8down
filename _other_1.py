#!/usr/bin/python3 
# -*- coding: utf-8 -*-
"""
@File Name  : _other_1.py
@Author     : LeeCQ
@Date-Time  : 2020/1/5 12:26

"""
import requests
import os, sys
import re
from bs4 import BeautifulSoup
from Crypto.Cipher import AES  # 解决Key的问题
import time


def progressbar(tot, pre):
    '''
    max_bar means the total number of tasks.
    i means the number of finished tasks.
    '''
    max_bar = 20
    finish = int(pre * max_bar / tot)
    unfinish = (max_bar - finish)
    bar = "[{}{}]".format(finish * "-", unfinish * " ")
    percent = str(int(pre / tot * 100)) + "%"
    if pre < tot:
        sys.stdout.write(bar + percent + "\r")
    else:
        sys.stdout.write(bar + percent + "\n")
    sys.stdout.flush()


def cal_time(fun):
    def inner_wrapper(*args):
        start = time.time()
        fun(*args)
        end = time.time()
        print('Time spent is ' + str(round(end - start, 1)))

    return inner_wrapper


@cal_time
def video_downlowner(url):
    download_file = "./other/"
    headers = {'user-agent': 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50'}
    result = requests.get(url, headers=headers)
    soup = BeautifulSoup(result.text, 'html.parser')
    filename = soup.find('div', class_='tit')
    filename = filename.find_all('a')[-1].string
    filename = re.sub(" ", "", filename)  # remove the blank in the string.
    # filename = "111"
    folder = os.path.exists(download_file + '/' + filename)
    if not folder:
        os.makedirs(download_file + '/' + filename)
    folder = download_file + '/' + filename

    pattern = re.compile(r'var vHLSurl = "(.*)";')
    script = soup.find_all('script', type="text/javascript")
    s = script[3].text
    s_after = re.sub(" +", " ", s)
    res = pattern.findall(s_after)[0]
    new_result = requests.get(res, headers)

    res = re.sub('index.m3u8', '1000kb/hls/index.m3u8', res)
    nn_result = requests.get(res, headers)
    # print(nn_result.text)

    pattern1 = re.compile(r",(.*?)#")
    lis = pattern1.findall(re.sub('\n', '', nn_result.text))

    res = re.sub('index.m3u8', 'key.key', res)
    nnn_result = requests.get(res, headers)
    key = nnn_result.text
    print('key is ' + key)

    i = 0
    for item in lis[1:]:

        download_url = re.sub('key.key', item, res)
        r = requests.get(download_url, headers=headers).content
        cryptor = AES.new(key.encode('utf-8'), AES.MODE_CBC)
        i += 1
        # print(i)
        progressbar(len(lis[1:]), i)

        if os.path.exists(folder + '/' + item):
            continue
        with open(folder + '/' + item, 'ab+') as file:
            r = requests.get(download_url, headers=headers).content

            file.write(cryptor.decrypt(r))
    '''
    Merge ts files.
    '''
    if not os.path.exists(os.path.join(download_file, filename + ".ts")):
        os.system("copy /b {} {}".format(os.path.join(download_file, filename, "*.ts"),
                                         os.path.join(download_file, filename + ".ts")))
    '''
    Start to delete ts files.
    '''
    for i in os.listdir(os.path.join(download_file, filename)):
        os.remove(os.path.join(download_file, filename, i))
    os.removedirs(os.path.join(os.path.join(download_file, filename)))


if __name__ == "__main__":
    url_ = 'https://videocdn.hndtl.com:8091/20190522//XRW-655/index.m3u8'
    video_downlowner(url_)
