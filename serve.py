#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第四步：本地起个静态服务，用手机/电脑浏览相册。

比 python -m http.server 多两件事：
  1. 支持 Range 分段请求 —— 视频才能拖动进度条；
  2. 正确处理中文路径。

用法:
    python serve.py 8899 ./downloads          # 本机访问
    python serve.py 8899 ./downloads --lan    # 局域网/内网可访问（注意隐私）
"""

import argparse
import mimetypes
import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

ROOT = os.getcwd()
mimetypes.add_type("video/quicktime", ".mov")


class RangeHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def translate_path(self, path):
        path = unquote(urlparse(path).path)
        parts = [p for p in path.split("/") if p not in ("", ".", "..")]
        return os.path.join(ROOT, *parts)

    def send_head(self):
        self._range_len = None
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        if not os.path.isfile(path):
            self.send_error(404, "File not found")
            return None

        size = os.path.getsize(path)
        ctype = self.guess_type(path) or "application/octet-stream"
        header = (self.headers.get("Range") or "").strip()
        match = re.match(r"bytes=(\d*)-(\d*)$", header)

        if not match or (match.group(1) == "" and match.group(2) == ""):
            f = open(path, "rb")
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            return f

        start_s, end_s = match.group(1), match.group(2)
        if start_s == "":                       # bytes=-N → 末尾 N 字节
            start = max(0, size - int(end_s))
            end = size - 1
        else:
            start = int(start_s)
            end = int(end_s) if end_s else size - 1
            end = min(end, size - 1)

        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None

        length = end - start + 1
        f = open(path, "rb")
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        self._range_len = length
        return f

    def copyfile(self, source, outputfile):
        if not self._range_len:
            return super().copyfile(source, outputfile)
        remaining = self._range_len
        while remaining > 0:
            buf = source.read(min(262144, remaining))
            if not buf:
                break
            outputfile.write(buf)
            remaining -= len(buf)
        self._range_len = None


def main():
    global ROOT
    ap = argparse.ArgumentParser(description="本地相册静态服务（支持视频拖动）")
    ap.add_argument("port", nargs="?", type=int, default=8899, help="端口，默认 8899")
    ap.add_argument("dir", nargs="?", default=".", help="要服务的目录，默认当前目录")
    ap.add_argument("--lan", action="store_true",
                    help="监听 0.0.0.0，局域网/内网可访问（默认只监听 127.0.0.1）")
    args = ap.parse_args()

    ROOT = os.path.abspath(args.dir)
    if not os.path.isdir(ROOT):
        raise SystemExit(f"目录不存在: {ROOT}")

    bind = "0.0.0.0" if args.lan else "127.0.0.1"
    srv = ThreadingHTTPServer((bind, args.port), RangeHandler)
    shown = args.port
    print(f"服务目录: {ROOT}")
    print(f"本机访问: http://127.0.0.1:{shown}/")
    if args.lan:
        print(f"已监听 {bind}:{shown}，同网段的其它设备可用本机内网 IP 访问")
        print("提醒：这会把相册暴露给整个网段，用完请 Ctrl+C")
    print("Ctrl+C 停止")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
