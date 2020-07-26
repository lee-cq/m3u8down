#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
@File Name  : m3u8_5.py
@Author     : LeeCQ
@Date-Time  : 2020/1/23 0:46

测试URI： https://d3c7rimkq79yfu.cloudfront.net/10000/1/v2/360/10000-eps-1_360p.m3u8

v1: 未成形 -- 下载一个单一的给定格式的M3U8
v2: V1的简单优化。
v3: 受到m3u8Download.exe的影响，想到启用json文件作为缓存数据，但是结构复杂，没有完成。

v4: 一定意义上完成了m3u8Down的所有基本功能。
    采用了本地的SQLite数据库作为数据的保存结构。
    使用的全新的模块 - m3u8 来解析m3u8文件。
    使用了copy二进制文件的方式合并文件
    加入了AES-128的解码器，并在下载文件时解码。

v5: [F]优化解码位置，下载文件时，把KEY文件也下载到源文件夹，方便本地直接使用m3u8播放(重命名).
        直接保存解码后的ts文件.
    [T]文件含有多个Key时解析key.
    [T]下载块重命名, 最好直接在解析的时候就规划好重命名的规则并写入sql(很多的ts文件使用参数寻址,文件名完全一样,重命名)
    [T]优化文件合并的方式
    [T]详细注释                             -- ok 2020/3/7
    [T]可以指定其他的合并输出目录             -- ok 2020/3/7
    [T]可以指定m3u8文件夹的目录
    [T]在下载未完成前合并的问题。

"""
import logging
import os  # 系统相关组件
import sys
import threading
import time
import pathlib
import m3u8  # 网络相关组件
import requests
import urllib3
from Crypto.Cipher import AES  # 解码器AES
from sqlite3 import OperationalError, Binary
from SQL import SQLiteAPI  # SQLite数据库操作 -- 自定义

logger = logging.getLogger("logger")  # 创建实例
formatter = logging.Formatter("[%(asctime)s] < %(funcName)s: %(lineno)d > [%(levelname)s] %(message)s")
# 终端日志
consle_handler = logging.StreamHandler(sys.stdout)
consle_handler.setFormatter(formatter)  # 日志文件的格式
logger.setLevel(logging.INFO)  # 设置日志文件等级

__all__ = ['M3U8', 'M3U8Error', 'M3U8KeyError', 'PlayListError', 'HTTPGetError']


class M3U8Error(Exception):
    """基础错误"""


class HTTPGetError(M3U8Error):
    """HTTP请求错误"""


class PlayListError(M3U8Error):
    """播放列表错误"""


class M3U8KeyError(PlayListError):
    """Key错误"""


_media_format = {'mp4': ['MPEG', 'MPG'],
                 '3gp': None,
                 }


class RequestsSession:
    """模拟浏览器会话"""


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
    """
    header = {}
    cookie = {}

    def __init__(self, url_m3u8: str, verify=False, retry=5, timeout=90, threads=5,
                 local_root='./down/', save_path='', save_name='', debug_level=3,
                 strict_mode=True, is_out_json=True, key=''
                 ):
        """
        :param url_m3u8: str - 需要下载的M3U8地址。
        :param verify: bool - HTTP安全验证
        :param retry: int - HTTP请求失败重试
        :param timeout: int - HTTP请求超时
        :param threads: int - 下载ts的线城数
        :param local_root: str - 保存的本地路径 - 及工作路径
        :param save_name: str - 保存的文件名
        :param debug_level: int -日志输出等级
        :param strict_mode: bool - 严格模式，出现异常直接抛出错误
        :param is_out_json: bool - 导出json格式的文件
        """
        self.save_name = save_name if save_name else url_m3u8.split('/')[-1].split('.')[0] + time.strftime(
            '-%Y%m%d%H%M')
        #
        self.input_url = url_m3u8
        self.retry, self.timeout, self.threads = retry, timeout, threads
        self.debug_level, self.strictMode = debug_level, strict_mode
        self.is_out_json = is_out_json

        # 构建本地文件
        self.out_path = os.path.abspath(save_path or local_root)
        self.m3u8_root_dir = local_root + save_name if local_root.endswith('/') else local_root + '/' + save_name
        os.makedirs(self.m3u8_root_dir, exist_ok=True)
        self.fileName = save_name
        self.key = pathlib.Path(key).read_bytes() if key else None

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

    def set_key(self, path):
        """设置Key - AES-128"""
        with open(path, 'rb') as f:
            return f.read()

    def SQL_create_master(self):
        """创建表: master"""
        _c = ("abs_uri      varchar(150) not null unique, "
              "resolution   int, "  # 长 * 宽
              "audio        varchar(100) "
              )
        return self.sql.create_table(table_name='master', keys=_c, ignore_exists=True)

    def SQL_create_segments(self, table_name):
        """创建表: segments"""
        _c = ("idd      INTEGER PRIMARY KEY AUTOINCREMENT, "
              "abs_uri  varchar(160) not null UNIQUE, "
              "segment_name varchar(50) , "
              "duration float, "
              "key      blob, "
              "key_uri   varchar(160), "
              "key_name varchar(50), "
              "method   varchar(10), "
              "iv       varchar(50)"
              )
        self.sql.create_table(table_name=table_name, keys=_c, ignore_exists=True)
        # self.sql.write_db(f"UPDATE sqlite_sequence SET seq=0 WHERE name=`{table_name}`")

    def SQL_create_config(self):
        """创建表 - 配置文件"""
        _c = "key_ varchar(50) not null unique, value_ VARCHAR(100)"
        return self.sql.create_table(table_name='config', keys=_c, ignore_exists=True)

    def config_init(self):
        """ 配置文件初始化 """
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
        """设值请求头"""
        if header is None: header = dict()
        header.setdefault("User-Agent",
                          "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.25 Safari/537.36 Core/1.70.3741.400 QQBrowser/10.5.3863.400", )
        header.setdefault("Accept", "*/*")
        header.setdefault("Connection", "keep-alive")
        self.header = header
        self.client.headers.update(header)

    # 如果可能 设置cookie
    def client_setCookie(self, name, value, **kwargs):
        """设置cookies"""
        # self.cookie = _cookies
        self.client.cookies.set(name, value, **kwargs)

    # http请求入口
    def __requests_get(self, url: str, header: dict):
        """http请求入口"""
        n, _e = self.retry, ''
        while n:
            n -= 1
            try:
                _data = self.client.get(url=url, headers=header, timeout=self.timeout)
                if _data.status_code == 200:
                    if self.debug_level > 2:
                        logger.debug(f'HTTP正常返回 [200]: {url}')
                    return _data
                else:
                    _e += f'[STATUS_CODE: {_data.status_code}]'
                    if self.debug_level > 2:
                        logger.warning(f'HTTP异常返回 [{_data.status_code}]: {url}')
            except Exception as e:
                _e += f'[Exception: {e}]'
                logger.warning(f'HTTP请求异常: {sys.exc_info()}')
        time.sleep(2)
        logger.error(f'经过{self.retry}次尝试依旧失败。{_e}: {url}')
        if self.strictMode:
            raise HTTPGetError(f'')
        return -1

    def requests_get(self, url: str):
        """对外接口"""
        return self.__requests_get(url, header=self.header)

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
        """下载并构建KEY"""
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
        __segments = _m3u8.segments
        for _ in __segments:
            key = keys.get(_.key.absolute_uri) if _.key else None
            method = _.key.method if _.key else None
            iv = _.key.iv if _.key else None
            _is_m3u8 = _.absolute_uri.split('?')[0].split('.')[-1].upper()
            self.sql.insert(table_name=table_name,
                            ignore_repeat=True,
                            abs_uri=_.absolute_uri,
                            segment_name=None if _is_m3u8 == "M3U8" else 'ts' + f'{__segments.index(_)}'.rjust(4,
                                                                                                               '0') + '.ts',
                            duration=_.duration,
                            key=Binary(self.key) if self.key is not None else Binary(key),
                            key_name=None if _is_m3u8 == "M3U8" else 'key' + f'{__segments.index(_)}'.rjust(4,
                                                                                                            '0') + '.key',
                            key_uri=None if _is_m3u8 == "M3U8" else _.key.absolute_uri,
                            method=method,
                            iv=iv
                            )
            # print(_.absolute_uri, _.duration, _.key.absolute_uri,)

    # 解析初始化，调度解析状态
    def m3u8_index(self, _uri):
        """解析初始化，调度解析方式"""
        # ==========================================================
        # loads通过添加URI的方式可能会造成目录错误的
        # ==========================================================
        # _m3u8 = self.__requests_get(_uri, self.header)
        # if _m3u8 is -1:
        #     logger.error(f"M3U8文件获取失败: {self.input_url}")
        #     raise M3U8Error(f"M3U8文件获取失败: {self.input_url}")
        # _m3u8 = m3u8.loads(_m3u8.text, uri=self.input_url)
        # ==========================================================
        logger.info(f"尝试解析m3u8文件：{_uri}")
        _m3u8 = m3u8.load(_uri, timeout=60, headers=self.header)
        if _m3u8.playlists:  # 构建master列表
            self.SQL_create_master()
            self.m3u8_master(_m3u8)
        if _m3u8.segments:  # 构建segments列表
            for index in range(9):
                table_name = f'segment_{index}'
                if table_name not in self.sql.show_tables(name_only=True):
                    self.SQL_create_segments(table_name)
                    self.sql.insert(table_name, idd=0, abs_uri=_uri, segment_name='index.m3u8')
                    self.sql.insert('config', key_=table_name + '_uri', value_=_uri)
                    self.m3u8_segments(_m3u8, table_name)
                    break

    def m3u8_outJson(self):
        """把m3u8信息导出为JSON"""
        pass

    def segment_totalDuration(self, table_name=None):
        """计算总持续时间"""

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
    def decode_AES128(data: bytes, key, iv='') -> bytes:
        """AES128解密"""
        if iv:
            ASE128 = AES.new(key if isinstance(key, bytes) else bytes(key, encoding='utf8'), AES.MODE_CBC,
                             bytes(iv[-16:], encoding='utf8'))
        else:
            ASE128 = AES.new(bytes(key, encoding='utf8'), AES.MODE_CBC)
        return ASE128.decrypt(data)

    def ts_down(self, seg: dict, dir):
        """下载ts文件

        :argument seg: 一个包含块信息的字典
        :argument dir:
        """
        try:
            _ts = self.__requests_get(seg['abs_uri'], self.header).content
            # _key = self.__requests_get(seg['key_uri'], header=self.header).content
            _key = 'USpF5ukvXYobhrEoHpzDtw=='
        except:
            return -1
        if seg.get('method') == 'AES-128':
            print(seg['iv'][2:])
            _ts = self.decode_AES128(_ts, seg['key'], seg['iv'][2:])
        elif seg.get('method') is None:
            pass
        # 在这里可以添加解密函数 添加的函数需要decode_开始<<<
        fileName = seg['segment_name']
        filePath = os.path.join(dir, fileName) if not seg['abs_uri'].endswith('m3u8') else os.path.join(dir,
                                                                                                        'index.m3u8')
        with open(filePath, 'wb') as f:
            f.write(_ts)
            self.tmp_down_count += 1

    def ts_index(self):
        """启用多线程下载"""
        print('\n')
        logger.info('尝试下载视频块文件...')
        if not [_ for _ in self.sql.show_tables() if _.startswith('segment')]:
            raise M3U8Error
        for _name in [_ for _ in self.sql.show_tables() if _.startswith('segment')]:
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
        """通过moviePy合并文件"""
        # ========================================================
        # 此方法合并大视频内容的时候会造成内存溢出，而导致系统崩溃。
        # ========================================================
        # from moviepy.video.io.VideoFileClip import VideoFileClip
        # from moviepy.video.compositing.concatenate import concatenate_videoclips
        # video_list = [VideoFileClip(_) for _ in segments]
        # final_clip = concatenate_videoclips(video_list)  # 进行视频合并
        # final_clip.to_videofile(out_file, fps=24, remove_temp=True)  # 将合并后的视频输出
        # ========================================================

    def combine_ffmpeg(self, segments, out_file):
        """使用ffmpeg合并文件"""

    def combine_index(self):
        """合并下载的内容"""
        print('\n')
        logger.info(f'尝试合并 ...')
        segments_name = [i[0] for i in self.sql.select('segment_0', 'segment_name', ORDER='idd')
                         if i[0] is not None and i[0].endswith('ts')
                         ]
        dir_root = os.path.abspath(self.out_path)
        # print(segments_name, len(segments_name))

        files = [os.path.join(dir_root, self.save_name, "segment_0", _.split('/')[-1])
                 for _ in segments_name
                 ]  # 构建文件列表的绝对路径
        if len(files) != len(segments_name):
            print(f'(文件: {len(files)} 数据库{len(segments_name)})')
            raise FileNotFoundError(f"ts文件下载不完全  ... ")
        newFile = os.path.join(dir_root, self.fileName + ".mp4")  # 构建输出文件的绝对路径
        self.combine_winCopy(segments=files, out_file=newFile)

    def clear_index(self):
        """清理零时文件

        db, json, ts, m3u8
        """
        import shutil
        self.sql.close_db()
        shutil.rmtree(os.path.join(self.out_path, self.save_name), ignore_errors=True)
        # os.rmdir(os.path.join(self.out_path, self.save_name))

    def run(self, clear=False):
        """运行"""
        # self.m3u8_index(self.input_url)   # 解析
        # if self.is_out_json: self.m3u8_outJson()
        # self.ts_index()                   # 下载
        # self.combine_index()  # 合并
        _n = 5
        while _n:
            _n -= 1
            try:
                self.combine_index()
                break
            except (M3U8Error, FileNotFoundError, OperationalError) as e:
                logger.info(f'合并文件失败,{e}...')
                try:
                    self.ts_index()
                except (M3U8Error, OperationalError, FileNotFoundError):
                    logger.info('文件下载失败, 可能解析有问题 ...')
                    self.m3u8_index(self.input_url)
                except Exception as e:
                    raise e
        if clear:
            self.clear_index()


if __name__ == '__main__':
    logger.addHandler(consle_handler)  # 添加控制台
    db_ = r'C:\code\Py\HTTP\Download_m3u8\down\test\m3u8Info.db'
    cookie = {
        'Hm_lpvt_7640497445529879f7be1821661cc9e3': '1595665133',
        'Hm_lvt_7640497445529879f7be1821661cc9e3': '1595474328, 1595492345, 1595590328, 1595605143',
        'access_token': 'eyJhbGciOiJSUzI1NiIsImtpZCI6IjhFNDhBQ0UwNjcwNkVDQkZCNjc1M0NDM0NCMDNEMjk2ODUzMTY2QUEiLCJ0eXAiOiJKV1QiLCJ4NXQiOiJqa2lzNEdjRzdMLTJkVHpEeXdQU2xvVXhacW8ifQ',
        'ckCsrfToken': 'N98PG8hyFhMoMW4f60qwuiWZ6KzElQ0iAijt7h3P'
    }

    # if os.path.exists(db_): os.remove(db_)
    m = M3U8(
        'https://1400200613.vod2.myqcloud.com/d3af585bvodtranscq1400200613/cde3cdb15285890804973367404/drm/v.f230.m3u8?t=5f1e9f49&us=dhmm1ff8&sign=df7ab4b9206851fe57974ee354c6f511',
        local_root=r'C:\Users\LCQ\Desktop\m3u8',
        save_name='WEB测试1',
        debug_level=5,
        key='./sup/GetKey',
        threads=5
    )
    # m.client_setCookie('Hm_lpvt_7640497445529879f7be1821661cc9e3', str(int(time.time())))
    # m.client_setCookie('Hm_lvt_7640497445529879f7be1821661cc9e3', '1595474328, 1595492345, 1595590328, 1595605143')
    # m.client_setCookie('access_token',
    #                    'eyJhbGciOiJSUzI1NiIsImtpZCI6IjhFNDhBQ0UwNjcwNkVDQkZCNjc1M0NDM0NCMDNEMjk2ODUzMTY2QUEiLCJ0eXAiOiJKV1QiLCJ4NXQiOiJqa2lzNEdjRzdMLTJkVHpEeXdQU2xvVXhacW8ifQ')
    # m.client_setCookie('ckCsrfToken', 'N98PG8hyFhMoMW4f60qwuiWZ6KzElQ0iAijt7h3P'
    #                    )

    m.run()
    # m.clear_index()
    # a = m.requests_get(
    #     'https://www.atstudy.com/api/courseMedia/GetKey?edk=CiCDZvMRFr2%2BecDRB9d%2Bzli%2BZhrnF%2BRu5zQ5oAWTnqYFiRCO08TAChiaoOvUBCokZGVkZmJkYjQtNDdhYy00NDQxLTkxYzMtYWY3NTQ3ZTgzZTZm&fileId=5285890804973367404&keySource=VodBuildInKMS')
    # with open('./sup/key', 'wb') as f:
    #     f.write(a.content)
