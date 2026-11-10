#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第三步：生成相册页面（album.html）与汇总报告（summary.md）。

用法:
    python album.py media.json --root ./downloads
"""

import argparse
import html
import json
import os

import kidmedia


def scan(moments, root):
    """按下载目录结构核对实际文件。"""
    rows = []
    for m in moments:
        folder = os.path.join(root, kidmedia.clean_name(m["author"], 20, "unknown"),
                              kidmedia.moment_folder_name(m["publishTime"], m["content"]))
        imgs, vids = [], []
        for sub, bucket in (("images", imgs), ("videos", vids)):
            d = os.path.join(folder, sub)
            if os.path.isdir(d):
                bucket.extend(sorted(os.listdir(d)))
        size = 0
        for sub in ("images", "videos"):
            d = os.path.join(folder, sub)
            if os.path.isdir(d):
                size += sum(os.path.getsize(os.path.join(d, f)) for f in os.listdir(d))
        rows.append({"m": m, "folder": folder, "images": imgs, "videos": vids, "size": size})
    return rows


def write_html(rows, out_path, root):
    base = os.path.dirname(os.path.abspath(out_path))
    total_i = sum(len(r["images"]) for r in rows)
    total_v = sum(len(r["videos"]) for r in rows)
    total_s = sum(r["size"] for r in rows)

    sections = []
    for r in rows:
        m = r["m"]
        rel = os.path.relpath(r["folder"], base).replace("\\", "/")
        tiles = [f'<a class="ph" href="{rel}/images/{html.escape(f)}" target="_blank">'
                 f'<img loading="lazy" src="{rel}/images/{html.escape(f)}" alt=""></a>'
                 for f in r["images"]]
        tiles += [f'<div class="vid"><video controls preload="none" '
                  f'src="{rel}/videos/{html.escape(f)}"></video>'
                  f'<span>{html.escape(f)}</span></div>' for f in r["videos"]]
        sections.append(
            f'<section><div class="hd">'
            f'<span class="d">{kidmedia.fmt_time(m["publishTime"])}</span>'
            f'<span class="a">{html.escape(m["author"])}</span>'
            f'<b>{html.escape(m["content"][:60] or "(无文字)")}</b>'
            f'<em>{len(r["images"])} 图 / {len(r["videos"])} 视频 · '
            f'{kidmedia.human_size(r["size"])}</em></div>'
            f'<div class="grid">{"".join(tiles)}</div></section>')

    doc = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>班级相册</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#f5f6f8;color:#1f2328;font:14px/1.6 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif}}
header{{padding:22px 26px;background:#fff;border-bottom:1px solid #e6e8eb}}
h1{{margin:0 0 6px;font-size:19px}}
header p{{margin:0;color:#6b7280;font-size:13px}}
.stat{{margin-top:10px;display:flex;gap:10px;flex-wrap:wrap}}
.stat span{{background:#eef2ff;color:#3b4cca;border-radius:6px;padding:3px 9px;font-size:12px}}
main{{padding:18px 26px 60px;max-width:1500px;margin:0 auto}}
section{{background:#fff;border:1px solid #e6e8eb;border-radius:10px;margin-bottom:16px;overflow:hidden}}
.hd{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:12px 14px;border-bottom:1px solid #f0f1f3;background:#fafbfc}}
.d{{font-variant-numeric:tabular-nums;color:#6b7280;font-size:12px}}
.a{{background:#e8f5ec;color:#1a7f45;border-radius:20px;padding:1px 9px;font-size:12px}}
.hd b{{font-size:13px;font-weight:600}}
.hd em{{margin-left:auto;color:#9aa1ab;font-size:12px;font-style:normal}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:6px;padding:10px}}
.ph{{display:block;aspect-ratio:1;border-radius:6px;overflow:hidden;background:#eef0f2}}
.ph img{{width:100%;height:100%;object-fit:cover;transition:transform .18s}}
.ph:hover img{{transform:scale(1.06)}}
.vid{{grid-column:span 2;display:flex;flex-direction:column;gap:4px}}
.vid video{{width:100%;border-radius:6px;background:#000}}
.vid span{{font-size:11px;color:#9aa1ab;word-break:break-all}}
</style></head><body>
<header><h1>班级相册</h1>
<p>共 {len(rows)} 条动态　|　点击图片查看原图</p>
<div class="stat"><span>{len(rows)} 条动态</span><span>{total_i} 张图片</span>
<span>{total_v} 个视频</span><span>{kidmedia.human_size(total_s)}</span></div>
</header><main>{"".join(sections)}</main></body></html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return total_i, total_v, total_s


def write_md(rows, out_path):
    total_i = sum(len(r["images"]) for r in rows)
    total_v = sum(len(r["videos"]) for r in rows)
    total_s = sum(r["size"] for r in rows)
    authors = sorted({r["m"]["author"] for r in rows if r["m"]["author"]})

    lines = ["# 班级圈媒体汇总", "",
             f"- 动态条数：{len(rows)}",
             f"- 发布人：{'、'.join(authors) or '(未知)'}",
             f"- 图片：{total_i} 张",
             f"- 视频：{total_v} 个",
             f"- 合计体积：{kidmedia.human_size(total_s)}", "",
             "## 明细", "",
             "| # | 发布时间 | 发布人 | 内容 | 图片 | 视频 | 大小 |",
             "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        m = r["m"]
        content = (m["content"] or "(无文字)").replace("|", "／").replace("\n", " ")[:38]
        lines.append(f'| {i} | {kidmedia.fmt_time(m["publishTime"])} | {m["author"]} | '
                     f'{content} | {len(r["images"])} | {len(r["videos"])} | '
                     f'{kidmedia.human_size(r["size"])} |')

    if total_v:
        lines += ["", "## 视频直链", ""]
        for r in rows:
            for f in r["videos"]:
                idx = int(f.split("_")[0]) - 1
                vids = r["m"]["videos"]
                lines.append(f'- {kidmedia.fmt_time(r["m"]["publishTime"])} '
                             f'{r["m"]["author"]}《{r["m"]["content"][:24]}》 → `{f}`')
                if idx < len(vids):
                    lines.append(f'  - {vids[idx]["url"]}')

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return total_i, total_v, total_s


def main():
    ap = argparse.ArgumentParser(description="生成相册页面与汇总报告")
    ap.add_argument("manifest", help="extract.py 生成的 media.json")
    ap.add_argument("--root", default="downloads", help="下载目录，默认 ./downloads")
    ap.add_argument("--out", default="", help="报告输出目录，默认与 root 相同")
    ap.add_argument("--title", default="", help="(预留) 自定义标题")
    args = ap.parse_args()

    with open(args.manifest, encoding="utf-8") as f:
        data = json.load(f)
    moments = data.get("moments") or []
    if not moments:
        raise SystemExit("清单里没有动态")

    out_dir = args.out or args.root
    os.makedirs(out_dir, exist_ok=True)

    rows = scan(moments, args.root)
    html_path = os.path.join(out_dir, "album.html")
    md_path = os.path.join(out_dir, "summary.md")

    n_i, n_v, n_s = write_html(rows, html_path, args.root)
    write_md(rows, md_path)

    missing = sum(1 for r in rows if not r["images"] and not r["videos"])
    print(f"动态 {len(rows)} 条 | 图片 {n_i} | 视频 {n_v} | {kidmedia.human_size(n_s)}")
    if missing:
        print(f"注意：{missing} 条动态在 --root 下没找到文件，请确认 --root 与 download.py 的 --out 一致")
    print(f"已生成: {html_path}")
    print(f"已生成: {md_path}")


if __name__ == "__main__":
    main()
