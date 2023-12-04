# M3U8Down 一个高效的M3U8下载工具

```bash
ffmpeg -allowed_extensions ALL -protocol_whitelist "file,http,https,tls,tcp,crypto" \
  -i https://vod2.kczybf.com/20230630/nCw2IWbg/1500kb/hls/index.m3u8 -c copy 庆余年-01.mp4


ffmpeg -i index.m3u8 -c copy xxx.mp4

ffmpeg -i "1.ts|2.ts|3.ts|" -c copy xxx.mp4
```



