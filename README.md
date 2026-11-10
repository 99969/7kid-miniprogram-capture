# 7kid 小程序抓包 · 班级圈图片视频导出工具

把自己孩子在幼儿园/学校班级圈里的**图片和视频**从手机抓包里导出来，按动态分目录保存，并生成一个可以网页浏览的相册。

全程本地运行，不登录任何服务、不上传任何数据。

---

## 使用方法

### 0. 准备

- Python 3.8+（无需任何第三方库）
- 手机装 [ProxyPin](https://github.com/wanghongenpin/network_proxy_flutter)（或任意能导出 JSON/HAR 的抓包工具）
- 手机上装好 Root 证书或用 ProxyPin 内置的 HTTPS 解密，确保能抓到 HTTPS 明文

### 1. 抓包并导出

1. 手机连上 ProxyPin 代理，打开班级圈 App 或小程序，**下拉刷新一次动态列表，并点开几个带图/带视频的动态**（列表接口返回媒体 URL，点开才会加载大图，但导出只需要列表接口）。
2. 在 ProxyPin 里 `⋯ → 导出`，选 **JSON** 格式，把文件传到电脑，比如叫 `capture.json`。

> 关键：导出必须包含列表接口的**响应体**。如果导出时勾了"不保存响应体"，后面解析会得到 0 条动态。

### 2. 提取媒体清单

```bash
python extract.py capture.json --api-host parent.7kid.com --authors "张老师,李老师" -o media.json
```

输出示例：

```
抓包记录 313 条 → 动态 19 条，图片 542，视频 5
发布人: 张老师, 李老师
清单已写入 media.json
```

- `--api-host`：业务接口域名。不填默认是 `parent.7kid.com`；不确定就先不填，看步骤 3 是否拿到数据。
- `--authors`：只看这些发布人的动态，逗号分隔；**留空 = 全部人**。
- `--show`：额外打印每条动态的时间、作者、图数/视频数，方便先核对。

### 3. 下载图片和视频

```bash
python download.py media.json --out ./downloads --referer https://parent.7kid.com/
```

- `--referer`：**强烈建议填**。不少 CDN 校验 Referer，不填会 403/404。填业务站点的根地址即可。
- `--workers 12`：并发数，默认 12；学校网络差可降到 4。
- `--images-only` / `--videos-only`：只要其中一种。

下载目录结构：

```
downloads/
├── 张老师/
│   ├── 2026-09-01_1054_开学第一天/
│   │   ├── images/01_xxx.jpg
│   │   └── videos/
│   └── 2026-09-05_0748_小鱼快跑/videos/01_xxx.mp4
├── 李老师/...
└── manifest.csv          ← 逐文件 URL、本地路径、大小、成功/失败
```

### 4. 生成相册并浏览

```bash
python album.py media.json --root ./downloads
python serve.py 8899 ./downloads
```

打开 <http://127.0.0.1:8899/album.html> 即可看图、播视频（支持拖动进度条）。

想让手机/平板也能看：

```bash
python serve.py 8899 ./downloads --lan
```

然后在同一网段的设备上访问 `http://<电脑内网IP>:8899/album.html`。

> `--lan` 会把相册暴露给整个网段，看完记得 `Ctrl+C`。小朋友的照片，别随手开着。

---

## 参数速查

| 文件 | 作用 | 常用参数 |
|---|---|---|
| `extract.py` | 抓包 JSON → 媒体清单 | `--api-host` `--authors` `-o` `--show` |
| `download.py` | 按清单下载 | `--out` `--referer` `--workers` `--images-only` `--videos-only` |
| `album.py` | 生成 album.html + summary.md | `--root`（必须与 download 的 `--out` 一致） `--out` |
| `serve.py` | 本地浏览（支持 Range） | `<端口>` `<目录>` `--lan` |

`media.json` 是中间产物，结构如下，也可以自己改或手工构造：

```json
{
  "moments": [
    {
      "id": "动态ID",
      "publishTime": 1793947732000,
      "author": "张老师",
      "content": "今天的户外活动",
      "images": [{"url": "https://cdn.example.com/a.jpg", "thumb": ""}],
      "videos": []
    }
  ]
}
```

---

## 7kid 小程序参考

已针对 7kid 家长端（AppID `wxb8e4ed6a71d9c2a9`）实测通过，完整信息见 **[docs/7kid.md](docs/7kid.md)**。抓包时记住三点：

| 环节 | 要点 |
|---|---|
| 定位 | 微信进程（`com.tencent.mm`）下 host 含 `7kid.com` 的请求，UA 带 `miniProgram/wxb8e4ed6a71d9c2a9` |
| 必抓 | `POST /api/moment/v1/parent/moment/get-list` 的**响应体** —— 媒体 URL 全在这里 |
| 下载 | 图片直链无需鉴权；**视频必须带 `--referer https://parent.7kid.com/`**，否则 404 |

媒体直链形如：

```
https://resource-pro.7kid.com/7kid/cloud/resouce/<YYYYMM>/<userId>/<ts>-<ts>.jpg
                                      ^^^^^^^ 官方就是这么拼的，不是笔误
```

去掉 `?x-oss-process=...` 整段 query 就是原图；视频 `fileType` 标成 `mp4`，实际可能是 `.mov`。

各域名分工：`parent.7kid.com` 业务接口（需 Bearer）、`kidapi.7kid.com` 换 token、`resource-pro.7kid.com` 媒体 CDN（**无需鉴权**）。所以本工具只吃抓包、不复刻登录态。

接口集合（Postman v2.1）：**[`api/7kid.postman_collection.json`](api/7kid.postman_collection.json)** —— 6 个分组 26 个请求，导入后把 `{{token}}`、`{{sign}}` 填上就能逐个调试。注意 POST 编码不统一：`get-list`、`msg/unread` 是 JSON，`parent-login`、`album-detail`、`get-by-id` 是 form-urlencoded。

---

## 常见问题

**解析到 0 条动态**
1. 抓包里没有列表接口的响应体 → 重新导出，确认勾选保存 body。
2. 域名不对 → 用 `--api-host` 换成抓包里实际的接口域名。
3. 接口路径不是 `/moment/get-list` → 改 `kidmedia.py` 里 `iter_moments` 的正则，把新路径加进去。

**下载大量 403 / 404**
- 先补 `--referer`（最常见原因）。
- 视频比图片更容易被拦；如果只有视频失败，说明 CDN 对视频有额外校验，通常带上 Referer 即可。

**视频下下来了但拖不动进度条**
- 别用 `python -m http.server`，用本项目的 `serve.py`，它实现了 Range（206 分段响应）。

**目录名带乱码或空目录**
- 已内置处理：去表情符号、去 `\ / : * ? " < > |`、截断到 16 字、去尾部空格（Windows 上尾随空格的目录用起来很坑）。
- 同一天多条无文字动态不会撞名——目录名带 `HHMM` 时分。

**清单里的"解析到图标配置"**
- `/moment/get-icon-list` 这类接口也返回数组，但内容是菜单图标，不是动态。工具已按接口路径过滤，若换 App 版本后出现误判，改 `iter_moments` 的正则即可。

---

## 说明

- 本工具只做一件事：把你**自己账号有权查看**的内容，从抓包里导出成本地文件。
- 抓包文件（`capture*.json`）、导出的照片视频（`downloads/`）、以及 `media.json` 都已写进 `.gitignore`，不会被误提交。
- 导出的内容涉及未成年人肖像，请仅作个人留档，不要二次传播、不要公开发布。

## License

MIT
