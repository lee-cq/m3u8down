# m3u8_6 全新架构，单文件完成全部的需求，一站式解决方案。

## 1. 存储文件结构：

/\<Root>/.allInfo.sqlite  
/\<Root>/<movie>/\*.m3u8  
/\<Root>/<movie>/\*.ts  
/\<Root>/<movie>.mp4

## 2. SQLite数据结构：

_main: moviesHeaders  
_id | name | m3u8Url | Description | is_parse | is_down | is_combine

```
    names: everyMovie - > 表名 = <name>  
              "idd      INTEGER PRIMARY KEY AUTOINCREMENT, "  
              "abs_uri  varchar(160) not null UNIQUE, "    
              "segment_name varchar(50) , "  
              "duration float, "  
              "key      blob, "  
              "key_uri   varchar(160), "  
              "key_name varchar(50), "  
              "method   varchar(10), "  
              "iv       varchar(50)"  
```

## 3. 接口函数： m3u8down: 接一个m3u8的连接下载一个视频

m3u8downs: 接受一个m3u8down的配置文件（包含下载的Root | m3u8列表 | Key如果有）

## 4. 实现方法接口：

```python
from m3u8 import M3U8
from requests import Session


def load(uri, timeout=None, headers={}, custom_tags_parser=None, verify_ssl=True) -> M3U8:
    """
    Retrieves the content from a given URI and returns a M3U8 object.  
    Raises ValueError if invalid content or IOError if request fails.  
    从给定的URI中检索内容并返回M3U8对象；  
    内容无效ValueError，请求失败返回IOError。  
    :return M3U8  
    """
    pass


class HttpClient(retry=3, timeout=30, *args, **kwargs) -> Session:
    """创建一个HTTP客户端用于同一的调度下载文件。  
    :return requests.Session  
    """


class SQL():
    """负责运行过程中的SQL操作。
     :return sql操作句柄
    """


class M3U8Down():
    """负责下载m3u8和ts文件。"""


class M3U8Combine():
    """负责合并ts文件。"""


class M3U8Reload:
    """重载M3U8文件  """

```

## 5. 其他辅助方法实现：

5.1. 打印输出接口 - 实现在不同位置有不同的输出。  
5.2. 配置文件解析接口 -  
5.3. 配置文件模板输出接口 -  
5.4. 命令行启动 -  
5.5. 命令行配置文件校验 -

## 6. 实现的功能：

6.1. 下载并解析m3u8文件。  
6.2. 根据解析得到的m3u8对象，下载ts文件。  
6.3. 合并ts文件得到mp4文件。  
6.4. 根据配置文件批量得到下载列表。

* 操作日志  
  2020-8-28：完成m3u8down模块的主体架构，详细需求文档、完成大概的搭建架构。  

