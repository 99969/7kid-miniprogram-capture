#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第一步：从 ProxyPin 导出的抓包 JSON 里抽出班级圈动态与媒体清单。

用法:
    python extract.py capture.json --api-host parent.example.com --authors "老师A,老师B" -o media.json
"""

import argparse
import json
import os
import sys

import kidmedia


def main():
    ap = argparse.ArgumentParser(description="从抓包 JSON 提取班级圈动态与图片/视频清单")
    ap.add_argument("capture", help="ProxyPin 导出的 JSON（或 HAR）文件")
    ap.add_argument("--api-host", default="parent.7kid.com",
                    help="业务接口域名，默认 parent.7kid.com")
    ap.add_argument("--authors", default="",
                    help="只看这些发布人，逗号分隔；留空=全部")
    ap.add_argument("-o", "--out", default="media.json", help="输出清单路径")
    ap.add_argument("--show", action="store_true", help="同时打印每条动态摘要")
    args = ap.parse_args()

    if not os.path.isfile(args.capture):
        sys.exit(f"找不到抓包文件: {args.capture}")

    records, meta = kidmedia.load_capture(args.capture)
    authors = [a for a in (args.authors or "").replace("，", ",").split(",") if a.strip()]
    moments = kidmedia.iter_moments(records, args.api_host, authors)

    n_img = sum(len(m["images"]) for m in moments)
    n_vid = sum(len(m["videos"]) for m in moments)
    payload = {
        "source": {
            "capture": os.path.basename(args.capture),
            "day": meta.get("day"),
            "records": len(records),
            "api_host": args.api_host,
        },
        "stats": {
            "moments": len(moments),
            "authors": sorted({m["author"] for m in moments if m["author"]}),
            "images": n_img,
            "videos": n_vid,
        },
        "moments": moments,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print(f"抓包记录 {len(records)} 条 → 动态 {len(moments)} 条，"
          f"图片 {n_img}，视频 {n_vid}")
    print(f"发布人: {', '.join(payload['stats']['authors']) or '(无)'}")
    print(f"清单已写入 {args.out}")

    if args.show:
        print()
        for m in moments:
            print(f"  {kidmedia.fmt_time(m['publishTime'])}  {m['author']}  "
                  f"图{len(m['images']):>3} 视频{len(m['videos'])}  {m['content'][:30]}")

    if not moments:
        print("\n提示：没有解析到动态。请确认 --api-host 与抓包里的接口域名一致，"
              "或该抓包未包含列表接口。")


if __name__ == "__main__":
    main()
