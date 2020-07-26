#!/usr/bin/python3 
# -*- coding: utf-8 -*-
"""
@File Name  : m3u8_4.py
@Author     : LeeCQ
@Date-Time  : 2020/1/8 20:40

测试URI： https://d3c7rimkq79yfu.cloudfront.net/10000/1/v2/360/10000-eps-1_360p.m3u8

"""
import logging
import sys

logger = logging.getLogger("logger")  # 创建实例
formatter = logging.Formatter("[%(asctime)s] < %(funcName)s: %(thread)d > [%(levelname)s] %(message)s")
# 终端日志
consle_handler = logging.StreamHandler(sys.stdout)
consle_handler.setFormatter(formatter)  # 日志文件的格式
logger.setLevel(logging.DEBUG)  # 设置日志文件等级

sys.path.append('C:/code/Py')

import requests, urllib3, m3u8  # 网络相关组件
import os, time, threading  # 系统相关组件
from SQL.SQLite import SQLiteAPI  # SQLite数据库操作 -- 自定义
from Crypto.Cipher import AES  # 解码器AES

__all__ = ['M3U8', 'M3U8Error', 'M3U8KeyError', 'PlayListError', 'HTTPGetError']


class M3U8Error(Exception): pass


class HTTPGetError(M3U8Error): pass


class PlayListError(M3U8Error): pass


class M3U8KeyError(PlayListError): pass


_media_format = {'mp4': ['MPEG', 'MPG'],
                 '3gp': None,
                 }


class M3U8:
    """下载m3u8一个视频

    m3u8文件格式的详解：https://www.jianshu.com/p/e97f6555a070

    组织结构：
        1. 构建config.json配置文件    -> {}

        2. 读取配置文件并下载。

    类属性的组织方式：
        1. 得到一个m3u8的URL         < URL
        2. 下载m3u8文件
        3. 解析m3u8文件             --> 生成配置文件
            3.1. 判断选择清晰度页面  --> 生成playlist.json文件。
            3.2. 判断ts内容页       --> 生成tsList.json文件。
                3.2.1 判断是否有Key --> 下载并解析key文件。

    config.json 数据结构：   <<-- 4中使用m3u8模块解析 - 不再创建config文件 意义不大

    SQLite 储存数据?
        master 表
        playlist 表（可能有多个）


    文件组织结构：
        /root/saveName/fragment_`int`/*.ts + playlist.m3u8
        /root/saveName/config.json
        /root/saveName/`saveName.*`  <- output video files

    兼容性怎么办？如何解决？
        可能的情况————
            1. 输入的是一个master列表（里面包含了一个或者多个子列表）
            2. 解析了一个带Key的列表。（列表中的key可能有一个或者多个）
            3. 解析了一个普通列表。
                            v|----------------------------------+
            所有的输入URL走master函数 --> 是 > master解析 playlist |  # 可能递归
                                    |-> 否 > 交给 m3u8_segments 解析segments列表

                key: 做key的字典 -->  {key_uri: key.key}  https://video1.jianzhuluntan.com:8091/20191215/EBOD668/1000kb/hls/index.m3u8
                    如果没有找到键则请求键

    :param url_m3u8:
    :param verify:
    :param retry:
    :param timeout:
    :param threads:
    :param local_root:
    :param save_name:
    :param debug_level:
    :param strict_mode:
    :param is_out_json:
    """
    header = {}
    cookie = {}

    def __init__(self, url_m3u8: str, verify=False, retry=5, timeout=90, threads=5,
                 local_root='./down/', save_name='', debug_level=3, strict_mode=True,
                 is_out_json=True,
                 ):
        save_name = url_m3u8.split('/')[-1].split('.')[0] + time.strftime('-%Y%m%d%H%M') if not save_name else save_name
        #
        self.input_url = url_m3u8
        self.retry, self.timeout, self.threads = retry, timeout, threads
        self.debug_level, self.strictMode = debug_level, strict_mode
        self.is_out_json = is_out_json
        # 构建本地文件
        self.out_path = os.path.abspath(local_root)
        self.m3u8_root_dir = local_root + save_name if local_root.endswith('/') else local_root + '/' + save_name
        os.makedirs(self.m3u8_root_dir, exist_ok=True)
        self.fileName = save_name
        # 构建SQLite
        self.sql = SQLiteAPI(os.path.join(self.m3u8_root_dir, 'm3u8Info.db'))
        # 模拟HTTP客户端
        self.client = requests.Session()
        self.client.verify = verify
        self.client_setHeader()
        urllib3.disable_warnings()
        #
        self.root_m3u8 = url_m3u8[:url_m3u8.rfind('/') + 1]
        self.configuration = dict()
        self.config_init()
        self.tmp_down_count = 0

    def SQL_create_master(self):
        _c = ("abs_uri      varchar(150) not null unique, "
              "resolution   int, "  # 长 * 宽
              "audio        varchar(100) "
              )
        return self.sql.create_table(table_name='master', keys=_c, ignore_exists=True)

    def SQL_create_segments(self, table_name):
        _c = ("idd      INTEGER PRIMARY KEY AUTOINCREMENT, "
              "abs_uri  varchar(160) not null UNIQUE, "
              "duration float, "
              "key      varchar(50), "
              "method   varchar(10), "
              "iv       varchar(50)"
              )
        self.sql.create_table(table_name, _c, ignore_exists=True)
        # self.sql.write_db(f"UPDATE sqlite_sequence SET seq=0 WHERE name=`{table_name}`")

    def SQL_create_config(self):
        _c = "key_ varchar(50) not null unique, value_ VARCHAR(100)"
        return self.sql.create_table('config', _c)

    def config_init(self):
        """配置文件初始化"""
        self.configuration.setdefault('inputURL', self.input_url)
        self.configuration.setdefault('m3u8Root', self.root_m3u8)
        self.configuration.setdefault('fileName', self.fileName)
        self.configuration.setdefault('updateTime', int(time.time()))
        self.SQL_create_config()
        self.sql.insert('config', ignore_repeat=True,
                        key_=list(self.configuration.keys()),
                        value_=list(self.configuration.values())
                        )

    # 客户端头
    def client_setHeader(self, header=None):
        if header is None: header = dict()
        header.setdefault("User-Agent",
                          "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.25 Safari/537.36 Core/1.70.3741.400 QQBrowser/10.5.3863.400", )
        header.setdefault("Accept", "*/*")
        header.setdefault("Connection", "keep-alive")
        self.header = header
        self.client.headers.update(header)

    # 如果可能 设置cookie
    def client_setCookie(self, cookie=None):
        self.cookie = cookie
        self.client.cookies = cookie

    def __requests_get(self, url: str, header: dict):
        """"""
        n = self.retry
        while n:
            n -= 1
            try:
                _data = self.client.get(url=url, headers=header, timeout=self.timeout)
                if _data.status_code == 200:
                    if self.debug_level > 2:
                        logger.info(f'HTTP正常返回 [200]: {url}')
                    return _data
                else:
                    if self.debug_level > 2:
                        logger.warning(f'HTTP异常返回 [{_data.status_code}]: {url}')
            except:
                logger.warning(f'HTTP请求异常: {sys.exc_info()}')
        logger.error(f'经过{self.retry}次尝试依旧失败。')
        if self.strictMode:
            raise HTTPGetError(f'')
        return -1

    def m3u8_master(self, _m3u8: m3u8.M3U8, down_max=True):
        """构建master列表，调用 m3u8_index()

        :param down_max:
        :param _m3u8: 一个m3u8.M3U8对象的事例
        :return: 0
        """
        logger.info("识别到Master列表，开始解析...")
        max_resolute, uri = 0, ''
        for _ in _m3u8.playlists:
            self.sql.insert("master", ignore_repeat=True,
                            abs_uri=_.absolute_uri,
                            resolution=_.stream_info.resolution[0] * _.stream_info.resolution[1],
                            audio=_.stream_info.audio
                            )
            _r = _.stream_info.resolution[0] * _.stream_info.resolution[1]
            max_resolute, uri = (max_resolute, uri) if max_resolute > _r else (_r, _.absolute_uri)
            # print(max_resolute, uri)  #
            if not down_max:
                self.m3u8_index(_.absolute_uri)
        if down_max:
            self.m3u8_index(uri)

    def segments_keys(self, keys: list) -> dict:
        if not keys:
            return dict()
        logger.info(f"m3u8视频已加密，正在下载并构建Key ...")
        _dic = dict()
        for k in keys:
            if k is not None:
                _dic.setdefault(k.absolute_uri, self.__requests_get(k.absolute_uri, self.header).text)
        return _dic

    def m3u8_segments(self, _m3u8: m3u8.M3U8, table_name):
        """构建segments列表

        包含 absolute_uri, key
        for i, _ in enumerate(a.segments):
            print(_.absolute_uri)
            print(f'key:{_.key}, duration={_.duration}')

        M3U8.key是一个对象，包含[absolute_uri, iv, method, keyformat, [base_uri, keyformatversions, tag, uri]]

        写数据库SQLite ： segments
        :param table_name:
        :param _m3u8: 一个m3u8.M3U8对象的事例
        :return: 0
        """
        logger.info("正在解析Segments ...")
        keys = self.segments_keys(_m3u8.keys)
        for _ in _m3u8.segments:
            key = keys.get(_.key.absolute_uri) if _.key else None
            method = _.key.method if _.key else None
            iv = _.key.iv if _.key else None
            self.sql.insert(table_name=table_name,
                            ignore_repeat=True,
                            abs_uri=_.absolute_uri,
                            duration=_.duration,
                            key=key,
                            method=method,
                            iv=iv
                            )
            # print(_.absolute_uri, _.duration, _.key.absolute_uri,)

    # 解析初始化，调度解析状态
    def m3u8_index(self, _uri):
        # ==========================================================
        # loads通过添加URI的方式可能会造成目录错误的
        # ==========================================================
        # _m3u8 = self.__requests_get(_uri, self.header)
        # if _m3u8 is -1:
        #     logger.error(f"M3U8文件获取失败: {self.input_url}")
        #     raise M3U8Error(f"M3U8文件获取失败: {self.input_url}")
        # _m3u8 = m3u8.loads(_m3u8.text, uri=self.input_url)
        # ==========================================================
        logger.info(f"m3u8解析初始化：{_uri}")
        _m3u8 = m3u8.load(_uri, timeout=60, headers=self.header)
        if _m3u8.playlists:  # 构建master列表
            self.SQL_create_master()
            self.m3u8_master(_m3u8)
        if _m3u8.segments:  # 构建segments列表
            for index in range(9):
                table_name = f'segment_{index}'
                if table_name not in self.sql.show_tables(name_only=True):
                    self.SQL_create_segments(table_name)
                    self.sql.insert(table_name, idd=0, abs_uri=_uri)
                    self.sql.insert('config', key_=table_name + '_uri', value_=_uri)
                    self.m3u8_segments(_m3u8, table_name)
                    break

    def m3u8_outJson(self):
        pass

    def segment_totalDuration(self, table_name=None):
        """"""
        def __count(_name):
            _total = 0
            for _ in self.sql.select(_name, 'duration'):
                if not isinstance(_[0], type(None)):
                    _total += _[0]
            return _total

        if not table_name:
            for _ in [_ for _ in self.sql.show_tables() if _.startswith('seg')]:
                _dur = __count(_)
                self.sql.insert('config', key_=f'Duration_{_}', value_=_dur, ignore_repeat=True)
        else:
            _dur = __count(table_name)
            self.sql.insert('config', key_=f'Duration_{table_name}', value_=_dur)

    @staticmethod
    def decode_AES128(data, key, iv=''):
        if iv:
            ASE128 = AES.new(bytes(key, encoding='utf8'), AES.MODE_CBC, bytes(iv, encoding='utf8'))
        else:
            ASE128 = AES.new(bytes(key, encoding='utf8'), AES.MODE_CBC)
        return ASE128.decrypt(data)

    def ts_down(self, seg: dict, dir):
        try:
            _ts = self.__requests_get(seg['abs_uri'], self.header).content
        except:
            return -1
        if seg.get('method') == 'AES-128':
            _ts = self.decode_AES128(_ts, seg['key'], seg['iv'])
        elif seg.get('method') is None:
            pass
        # 在这里可以添加解密函数 添加的函数需要decode_开始<<<
        fileName = seg['abs_uri'].split('/')[-1]
        filePath = os.path.join(dir, fileName) if not seg['abs_uri'].endswith('m3u8') else os.path.join(dir,
                                                                                                        'index.m3u8')
        with open(filePath, 'wb') as f:
            f.write(_ts)
            self.tmp_down_count += 1

    def ts_index(self):
        """启用多线程下载"""
        logger.info('准备启用多线程下载...')
        _names = [_ for _ in self.sql.show_tables() if _.startswith('segment')]
        if not _names: raise PlayListError('没有发现可用的playlist')
        for _name in _names:
            _part_dir = os.path.join(self.m3u8_root_dir, _name)
            os.makedirs(_part_dir, exist_ok=True)
            down_list = self.sql.select(_name, '*', result_type=dict, ORDER='idd')
            self.tmp_down_count, total = len(os.listdir(_part_dir)), len(down_list)
            logger.info(f'查询到{total}个元素, 即将下载...')  #
            for segInfo in down_list:
                if os.path.exists(os.path.join(_part_dir, segInfo['abs_uri'][segInfo['abs_uri'].rfind('/') + 1:])):
                    continue
                # self.ts_down(segInfo, _part_dir)  # 单线程测试
                threading.Thread(target=self.ts_down, args=(segInfo, _part_dir)).start()  # 启用多线程
                while threading.active_count() > self.threads: time.sleep(1)  # 线程大于预定时等待继续添加
                print('\r已下载: ', self.tmp_down_count, '/', total, f'线程数：{threading.active_count()}', end='')
            while threading.active_count() > 1: time.sleep(1)  # 等待子线程IO结束

    @staticmethod
    def combine_winCopy(segments, out_file):
        """使用Windows的cmd命令 copy /b 进行合并"""
        len_files = len(segments)
        with open(out_file, 'wb') as nf:
            for i, file in enumerate(segments):
                print(f'\r已合并{i + 1}/{len_files}', end='')
                with open(file, 'rb') as of:
                    nf.write(of.read())
        # =====================================================
        # 下面的方法存在问题文件排序的问题，不好解决, 而且不具有跨平台的兼容性
        # =====================================================
        #     os.popen(f'copy /b {newFile}+{os.path.join(dir_root, "segment_0", file)} '
        #              f'{newFile}').read()
        # =====================================================

    def combine_moviePy(self, segments, out_file):
        """"""
        # ========================================================
        # 此方法合并大视频内容的时候会造成内存溢出，而导致系统崩溃。
        # ========================================================
        # from moviepy.video.io.VideoFileClip import VideoFileClip
        # from moviepy.video.compositing.concatenate import concatenate_videoclips
        # video_list = [VideoFileClip(_) for _ in segments]
        # final_clip = concatenate_videoclips(video_list)  # 进行视频合并
        # final_clip.to_videofile(out_file, fps=24, remove_temp=True)  # 将合并后的视频输出
        # ========================================================

    def combine_index(self):
        """合并下载的内容"""
        logger.info(f'开始合并 ...')
        dir_root = os.path.abspath(self.m3u8_root_dir)
        files = [os.path.join(dir_root, "segment_0", _[0].split('/')[-1])
                 for _ in self.sql.select('segment_0', 'abs_uri', ORDER='idd')
                 if _[0].endswith('ts')]  # 构建文件列表的绝对路径
        newFile = os.path.join(dir_root, self.fileName + ".mp4")  # 构建输出文件的绝对路径吗
        self.combine_winCopy(segments=files, out_file=newFile)

    def expected_duration(self):
        """"""
        self.sql.select('segment_0', '')

    def clear_index(self):
        """清理零时文件

        db, json, ts, m3u8
        """

    def run(self):
        """运行环境的RUN方法。"""
        # self.ts_index()
        print(f"正在下载：{self.input_url}")
        __n = 3
        while __n:
            try:
                self.ts_index()
                break
            except:
                self.m3u8_index(self.input_url)   # 解析
                __n -= 1
        # if self.out_json: self.m3u8_outJson()
        self.ts_index()       # 下载
        self.combine_index()  # 合并


if __name__ == '__main__':
    logger.addHandler(consle_handler)  # 添加控制台
    # db_ = r'C:\code\Py\HTTP\Download_m3u8\down\test\m3u8Info.db'
    # if os.path.exists(db_): os.remove(db_)
    m = M3U8(r"https://1400200613.vod2.myqcloud.com/d3af585bvodtranscq1400200613/0d4478295285890805508448302/drm/v.f230.m3u8?t=5f1c2b5b&us=q97k1b37&sign=6a2e020efae35bf14daec46916bdd656",
             local_root=r'C:\Users\LCQ\Desktop\m3u8',
             save_name='WEB测试1',
             debug_level=3,
             threads=5
             )
    m.run()
