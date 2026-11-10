#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二步：按清单并发下载图片与视频。

用法:
    python download.py media.json --out ./downloads --referer https://parent.example.com/
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import kidmedia

UA = ("Mozilla/5.0 (Linux; Android 12; wv) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Version/4.0 Chrome/120.0 Mobile Safari/537.36 MicroMessenger/8.0")


def fetch(url, path, headers, retries):
    err = ""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=180) as resp, open(path, "wb") as f:
                while True:
                    chunk = resp.read(262144)
                    if not chunk:
                        break
                    f.write(chunk)
            return True, os.path.getsize(path), ""
        except Exception as exc:                     # noqa: BLE001
            err = f"{type(exc).__name__}: {exc}"
            time.sleep(1.5 * (attempt + 1))
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
    return False, 0, err


def main():
    ap = argparse.ArgumentParser(description="按清单下载班级圈图片与视频")
    ap.add_argument("manifest", help="extract.py 生成的 media.json")
    ap.add_argument("--out", default="downloads", help="下载根目录，默认 ./downloads")
    ap.add_argument("--referer", default="", help="请求 Referer；部分 CDN 校验它，建议填业务站点根地址")
    ap.add_argument("--workers", type=int, default=12, help="并发数，默认 12")
    ap.add_argument("--retries", type=int, default=3, help="单个文件重试次数，默认 3")
    ap.add_argument("--images-only", action="store_true", help="只下载图片")
    ap.add_argument("--videos-only", action="store_true", help="只下载视频")
    args = ap.parse_args()

    with open(args.manifest, encoding="utf-8") as f:
        data = json.load(f)
    moments = data.get("moments") or []
    if not moments:
        sys.exit("清单里没有动态，先运行 extract.py")

    if args.images_only:
        moments = [{**m, "videos": []} for m in moments]
    if args.videos_only:
        moments = [{**m, "images": []} for m in moments]

    jobs = kidmedia.media_plan(moments, args.out)
    for _, path, _kind in jobs:
        os.makedirs(os.path.dirname(path), exist_ok=True)

    headers = {"User-Agent": UA, "Accept": "*/*"}
    if args.referer:
        headers["Referer"] = args.referer

    print(f"待下载 {len(jobs)} 个文件"
          f"（图片 {sum(1 for j in jobs if j[2] == 'image')} / "
          f"视频 {sum(1 for j in jobs if j[2] == 'video')}），并发 {args.workers}")
    if not args.referer:
        print("提示：未设置 --referer，若出现 403/404 请补上业务站点地址")

    # 视频通常更大，先下，避免长尾等待
    jobs.sort(key=lambda j: 0 if j[2] == "video" else 1)

    results = []

    def run(job):
        ok, size, err = fetch(job[0], job[1], headers, args.retries)
        return {"url": job[0], "path": job[1], "kind": job[2],
                "ok": ok, "size": size, "err": err}

    with ThreadPoolExecutor(args.workers) as pool:
        for i, res in enumerate(pool.map(run, jobs), 1):
            results.append(res)
            if i % 25 == 0 or not res["ok"]:
                print(f"  {i}/{len(jobs)}  失败 {sum(1 for r in results if not r['ok'])}")

    ok = [r for r in results if r["ok"]]
    bad = [r for r in results if not r["ok"]]
    img = [r for r in ok if r["kind"] == "image"]
    vid = [r for r in ok if r["kind"] == "video"]

    index = {}
    for m in moments:
        for item in m["images"] + m["videos"]:
            index[item["url"]] = m

    csv_path = os.path.join(args.out, "manifest.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["发布人", "发布时间", "动态内容", "类型", "资源URL", "本地路径", "大小", "状态"])
        for r in results:
            m = index.get(r["url"], {})
            w.writerow([m.get("author", ""), kidmedia.fmt_time(m.get("publishTime")),
                        m.get("content", ""), r["kind"], r["url"], r["path"],
                        r["size"], "OK" if r["ok"] else r["err"]])

    print()
    print(f"完成：成功 {len(ok)}（图片 {len(img)}，视频 {len(vid)}），失败 {len(bad)}")
    print(f"图片 {sum(r['size'] for r in img) / 1048576:.1f} MB，"
          f"视频 {sum(r['size'] for r in vid) / 1048576:.1f} MB")
    print(f"逐文件清单: {csv_path}")
    for r in bad[:10]:
        print(f"  失败: {r['url']}  {r['err']}")
    if len(bad) > 10:
        print(f"  ... 另有 {len(bad) - 10} 个失败")


if __name__ == "__main__":
    main()
