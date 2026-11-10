# -*- coding: utf-8 -*-
"""生成脱敏的 Postman 集合（7kid 家长端接口）。所有真实 ID/令牌都用占位符。"""
import json

BASE = "{{baseUrl}}"
CDN = "{{cdnBase}}"

COMMON_HEADERS = [
    {"key": "Authorization", "value": "Bearer {{token}}", "type": "text"},
    {"key": "sign", "value": "{{sign}}", "type": "text"},
    {"key": "req-type", "value": "web", "type": "text"},
    {"key": "web-system", "value": "7Kid_parent", "type": "text"},
    {"key": "lang", "value": "zh-CN", "type": "text"},
]


def hdr(*extra):
    return COMMON_HEADERS + list(extra)


def form(*pairs):
    return {
        "mode": "urlencoded",
        "urlencoded": [{"key": k, "value": v, "type": "text"} for k, v in pairs],
    }


def raw_json(text):
    return {"mode": "raw", "raw": text,
            "options": {"raw": {"language": "json"}}}


def req(name, method, url, body=None, headers=None, desc=""):
    item = {
        "name": name,
        "request": {
            "method": method,
            "header": headers or hdr(),
            "url": {"raw": url},
            "description": desc,
        },
        "response": [],
    }
    if body:
        item["request"]["body"] = body
    return item


def get(name, url, desc="", headers=None):
    return {"name": name,
            "request": {"method": "GET", "header": headers or [],
                        "url": {"raw": url}, "description": desc},
            "response": []}


CF_JSON = [{"key": "Content-Type", "value": "application/json", "type": "text"}]
CF_FORM = [{"key": "Content-Type", "value": "application/x-www-form-urlencoded",
            "type": "text"}]

collection = {
    "info": {
        "name": "7kid 家长端 (sanitized)",
        "description": (
            "7kid 家长端小程序接口集合，用于理解抓包结构与调试自己的数据导出。\n\n"
            "**所有账号相关值都是占位符**：`{{token}}` `{{sign}}` `{{studentId}}` "
            "`{{clazzId}}` `{{momentId}}` `{{albumId}}` `{{userId}}`。\n\n"
            "填法：先从自己的抓包里复制 `Authorization` 的 Bearer 值到 `{{token}}`，"
            "`sign` 头到 `{{sign}}`（这两个每次请求都会变，通常一次抓包内可复用几分钟）。\n\n"
            "注意 POST 的编码不统一：`moment/get-list`、`msg/unread` 用 JSON；"
            "`parent-login`、`album-detail`、`get-by-id` 用 form-urlencoded。\n\n"
            "媒体直链在 CDN 上无需鉴权，直接 GET 即可，详见仓库 docs/7kid.md。"
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "variable": [
        {"key": "baseUrl", "value": "https://parent.7kid.com", "type": "string"},
        {"key": "cdnBase", "value": "https://resource-pro.7kid.com", "type": "string"},
        {"key": "token", "value": "", "type": "string"},
        {"key": "sign", "value": "", "type": "string"},
        {"key": "studentId", "value": "", "type": "string"},
        {"key": "clazzId", "value": "", "type": "string"},
        {"key": "momentId", "value": "", "type": "string"},
        {"key": "albumId", "value": "", "type": "string"},
        {"key": "userId", "value": "", "type": "string"},
        {"key": "yyyyMM", "value": "202611", "type": "string"},
        {"key": "date", "value": "2026-11-06", "type": "string"},
        {"key": "appId", "value": "wxb8e4ed6a71d9c2a9", "type": "string"},
        {"key": "code", "value": "", "type": "string"},
        {"key": "signedUrl", "value": "", "type": "string"},
        {"key": "file", "value": "", "type": "string"},
    ],
    "item": [
        {
            "name": "01 登录与令牌",
            "description": "登录换 token。抓包时这几个接口的响应体里含 Bearer token，注意别外泄。",
            "item": [
                req("服务器时间", "POST", f"{BASE}/api/iam/v1/common/time",
                    hdr(*CF_FORM), desc="用于对齐本地时间，部分接口的 sign 与时间戳相关"),
                req("家长登录", "POST", f"{BASE}/api/iam/v1/web-oauth/kid-login/parent-login",
                    form(("studentId", "{{studentId}}"), ("loginType", "5")),
                    hdr(*CF_FORM), "form 编码。返回体里含 Bearer token"),
                req("家长-学生切换", "POST", f"{BASE}/api/iam/v1/web-oauth/kid-login/parent-student",
                    None, hdr(*CF_FORM), "多孩账号切换当前 studentId"),
                req("刷新登录态", "POST", f"{BASE}/api/iam/v1/web-oauth/kid-login/parent-refresh",
                    form(("loginType", "")), hdr(*CF_FORM), "token 过期前刷新"),
                req("IAM 换令牌", "POST",
                    "https://kidapi.7kid.com/iam/v1/web-oauth/common/token",
                    raw_json('{"appId":"{{appId}}","code":"{{code}}",'
                             '"loginType":"","clientType":""}'),
                    hdr(*CF_JSON), "kidapi 域名，独立于 parent 的登录流程"),
            ],
        },
        {
            "name": "02 班级圈动态（媒体来源）",
            "description": "导出图片视频只需要这一个接口的响应体：media 全在 resourceVOs[].fileInfoVO。",
            "item": [
                req("动态列表 ★", "POST",
                    f"{BASE}/api/moment/v1/parent/moment/get-list",
                    raw_json('{"isAllClazz":true,"lastMomentId":0,"pageSize":20,"viewType":1}'),
                    hdr(*CF_JSON),
                    "核心接口。lastMomentId 传上一条的 clazzMomentId 翻页，0 表示首页；"
                    "pageSize 默认 20。返回 resourceVOs[].fileInfoVO{url,thumbnailUrl,"
                    "compressUrl,fileType}，fileType 为 img 或 mp4（实际可能是 .mov）"),
                req("动态详情", "POST",
                    f"{BASE}/api/moment/v1/parent/moment/get-by-id",
                    form(("clazzMomentId", "{{momentId}}")),
                    hdr(*CF_FORM), "form 编码，注意不是 JSON"),
                req("未读计数", "POST",
                    f"{BASE}/api/moment/v1/parent/notify/get-count",
                    None, hdr(*CF_JSON)),
                req("菜单图标配置（勿当动态解析）", "POST",
                    f"{BASE}/api/moment/v1/parent/get-icon-list",
                    None, hdr(*CF_JSON),
                    "坑：data 也是数组，但内容是 /childLeave/list、/babyVideo/index 这类菜单路径，"
                    "解析动态时必须排除，否则会多出几十条空动态"),
                req("消息未读数", "POST", f"{BASE}/api/kid-arch/v1/parent/msg/unread",
                    raw_json("[0]"), hdr(*CF_JSON), "body 是数组，不是对象"),
            ],
        },
        {
            "name": "03 班级相册",
            "description": "只返回相册元信息（名称、张数、封面），不含媒体直链。",
            "item": [
                req("相册列表（分页）", "POST",
                    f"{BASE}/api/album/v1/parent/clazz_album/list-by-page",
                    form(("clazzId", "{{clazzId}}"), ("pageNum", "1"), ("pageSize", "10")),
                    hdr(*CF_FORM)),
                req("我的班级相册", "POST",
                    f"{BASE}/api/album/v1/parent/album/parent-get-album",
                    None, hdr(*CF_FORM),
                    "返回 childName/childImgUrl/totalNum 等，注意这是孩子信息"),
                req("相册详情（按年月日筛）", "POST",
                    f"{BASE}/api/album/v1/parent/album/album-detail",
                    form(("albumId", "{{albumId}}"), ("pageNum", "1"), ("pageSize", "30"),
                         ("year", ""), ("month", ""), ("day", "")),
                    hdr(*CF_FORM), "year/month/day 留空表示不筛"),
            ],
        },
        {
            "name": "04 孩子与学校",
            "item": [
                req("孩子信息", "POST", f"{BASE}/api/kid-arch/v1/parent/student/info",
                    None, hdr(*CF_FORM), "返回姓名、班级、学校等，敏感，别贴公开处"),
                req("在校状态", "POST",
                    f"{BASE}/api/kid-arch/v1/parent/student/get-stu-status"
                    "?studentId={{studentId}}",
                    None, hdr(*CF_FORM), "studentId 走 query，不在 body 里"),
                req("班级状态", "POST",
                    f"{BASE}/api/kid-arch/v1/parent/student/get-student-clazz-status",
                    None, hdr(*CF_FORM)),
                req("权限列表", "POST",
                    f"{BASE}/api/kid-arch/v1/parent/school/permission-list",
                    None, hdr(*CF_FORM), "决定前端显示哪些功能入口"),
                req("URL 签名", "POST", f"{BASE}/api/kid-arch/v1/weixinConfig/urlSign",
                    form(("url", "{{signedUrl}}")), hdr(*CF_FORM),
                    "给要分享的 URL 做签名，注意 url 需二次编码"),
            ],
        },
        {
            "name": "05 其他",
            "item": [
                req("当日食谱", "POST",
                    f"{BASE}/api/garden/v1/parent/ck/cookbook/get-by-date",
                    form(("date", "{{date}}")), hdr(*CF_FORM)),
                req("全部路由", "POST", f"{BASE}/api/boss/v1/content/getAllRoutes",
                    form(("clientType", "2")), hdr(*CF_FORM)),
                req("微信公众号订阅状态", "POST",
                    f"{BASE}/api/user/v1/account/wechat/get-subscribe-status",
                    None, hdr(*CF_JSON)),
                req("OSS 上传配置", "POST",
                    f"{BASE}/api/file/v1/aliyun/oss/get-config-and-callback-info",
                    None, hdr(*CF_FORM), "家长发动态时用，返回 OSS 临时凭证"),
            ],
        },
        {
            "name": "06 媒体直链（无需鉴权）",
            "description": "CDN 裸链，无 Authorization 也能下载。视频建议带 Referer。",
            "item": [
                get("原图", f"{CDN}/7kid/cloud/resouce/{{{{yyyyMM}}}}/{{{{userId}}}}/{{{{file}}}}.jpg",
                    "去掉全部 ?x-oss-process 参数 = 原图。注意官方把 resource 拼成了 resouce"),
                get("列表缩略图",
                    f"{CDN}/7kid/cloud/resouce/{{{{yyyyMM}}}}/{{{{userId}}}}/{{{{file}}}}.jpg"
                    "?x-oss-process=image/resize,w_300,h_300/format,src/quality,Q_80",
                    "OSS 图片处理参数，w/h 可调"),
                get("压缩大图",
                    f"{CDN}/7kid/cloud/resouce/{{{{yyyyMM}}}}/{{{{userId}}}}/{{{{file}}}}.jpg"
                    "?x-oss-process=image/resize,l_800,m_lfit",
                    "长边 800，对应响应里的 compressUrl"),
                get("视频封面",
                    f"{CDN}/7kid/cloud/resouce/{{{{yyyyMM}}}}/{{{{userId}}}}/{{{{file}}}}.mp4"
                    "?x-oss-process=video/snapshot,t_200,f_jpg,m_fast,ar_auto",
                    "t_200 取第 200ms 帧。视频直链建议加 Referer: https://parent.7kid.com/"),
            ],
        },
    ],
}

out = "api/7kid.postman_collection.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(collection, f, ensure_ascii=False, indent=2)

n = sum(len(g["item"]) for g in collection["item"])
print(f"已生成 {out}：{len(collection['item'])} 个分组，{n} 个请求")
