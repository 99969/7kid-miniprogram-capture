# -*- coding: utf-8 -*-
"""共用工具：抓包记录解析、动态归一化、文件名清洗。"""

import datetime
import json
import os
import re

# 表情符号与非法文件名字符
_EMOJI = re.compile("[\U00010000-\U0010ffff]")
_ILLEGAL = re.compile(r'[\\/:*?"<>|\r\n\t]')

MEDIA_IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic")
MEDIA_VIDEO_EXT = (".mp4", ".mov", ".m4v", ".3gp", ".avi", ".mkv")


def clean_name(text, limit=16, fallback="untitled"):
    """把动态正文变成安全的目录名：去表情、去非法字符、限长、去尾部空格与点。"""
    s = _EMOJI.sub("", text or "")
    s = _ILLEGAL.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip(" .")
    s = s[:limit].strip(" .")
    return s or fallback


def moment_folder_name(publish_ms, content, limit=16):
    """目录名：YYYY-MM-DD_HHMM_标题（带时分，避免同一天多条动态撞名）。"""
    if publish_ms:
        t = datetime.datetime.fromtimestamp(publish_ms / 1000)
        stamp = t.strftime("%Y-%m-%d_%H%M")
    else:
        stamp = "unknown-date"
    return f"{stamp}_{clean_name(content, limit)}"


def fmt_time(publish_ms):
    if not publish_ms:
        return "-"
    return datetime.datetime.fromtimestamp(publish_ms / 1000).strftime("%Y-%m-%d %H:%M")


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def load_capture(path):
    """读取 ProxyPin 导出的 JSON，返回 (records, meta)。"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        records = data.get("records") or data.get("entries") or []
        meta = {"day": data.get("day")}
    else:
        records = data
        meta = {}
    return records, meta


def entry_of(record):
    """兼容 ProxyPin 的 {entry:{...}} 与原生 HAR 两种结构。"""
    return record.get("entry", record)


def response_text(entry):
    content = (entry.get("response") or {}).get("content") or {}
    return content.get("text") or "", content.get("mimeType") or ""


def url_of(entry):
    return (entry.get("request") or {}).get("url") or ""


def host_of(url):
    m = re.match(r"https?://([^/]+)", url)
    return m.group(1) if m else ""


def classify_media(url, file_type=""):
    """返回 'image' / 'video' / None。"""
    ft = (file_type or "").lower()
    path = url.split("?")[0].lower()
    if ft in ("mp4", "video", "mov"):
        return "video"
    if ft in ("img", "image", "jpg", "jpeg", "png"):
        return "image"
    if path.endswith(MEDIA_VIDEO_EXT):
        return "video"
    if path.endswith(MEDIA_IMAGE_EXT):
        return "image"
    return None


def iter_moments(records, api_host, authors=None):
    """从抓包记录中抽出班级圈动态（同一 id 合并去重）。

    api_host: 业务 API 域名，例如 parent.example.com
    authors:  发布人白名单（集合/列表），None 表示全部
    """
    moments = {}
    wanted = {a.strip() for a in authors} if authors else None

    for record in records:
        entry = entry_of(record)
        url = url_of(entry)
        if api_host not in host_of(url):
            continue
        # 只解析动态接口，菜单/图标配置接口也返回列表，必须排除
        path = re.sub(r"https?://[^/]+", "", url.split("?")[0])
        if not re.search(r"/moment/(get-list|get-by-id)$", path):
            continue

        text, mime = response_text(entry)
        if "json" not in mime and not text.lstrip().startswith("{"):
            continue
        try:
            payload = json.loads(text)
        except ValueError:
            continue

        items = payload.get("data")
        if not isinstance(items, list):
            continue

        for item in items:
            if not isinstance(item, dict):
                continue
            mid = item.get("clazzMomentId") or item.get("momentId") or ""
            if not mid:
                continue
            author = (item.get("publisherName") or "").strip()
            if wanted is not None and author not in wanted:
                continue

            rec = moments.setdefault(mid, {
                "id": mid,
                "publishTime": item.get("publishTime") or 0,
                "author": author,
                "content": (item.get("content") or "").strip(),
                "type": item.get("momentType"),
                "icon": item.get("iconTitle") or "",
                "images": [],
                "videos": [],
            })
            _seen = {m["url"] for m in rec["images"]} | {m["url"] for m in rec["videos"]}
            for vo in item.get("resourceVOs") or []:
                info = (vo or {}).get("fileInfoVO") or {}
                url = (info.get("url") or "").split("?")[0]
                if not url or url in _seen:
                    continue
                kind = classify_media(url, info.get("fileType"))
                if not kind:
                    continue
                thumb = (info.get("thumbnailUrl") or "").split("?")[0]
                rec["images" if kind == "image" else "videos"].append(
                    {"url": url, "thumb": thumb}
                )
                _seen.add(url)

    return sorted(moments.values(), key=lambda m: m.get("publishTime") or 0)


def media_plan(moments, out_root):
    """把动态展开成下载任务：[(url, 目标路径, 类型)]。"""
    jobs = []
    for m in moments:
        folder = os.path.join(out_root, clean_name(m["author"], 20, "unknown"),
                              moment_folder_name(m["publishTime"], m["content"]))
        for kind, key, sub in (("image", "images", "images"), ("video", "videos", "videos")):
            for i, item in enumerate(m[key], 1):
                name = f"{i:02d}_{os.path.basename(item['url'])}"
                jobs.append((item["url"], os.path.join(folder, sub, name), kind))
    return jobs
