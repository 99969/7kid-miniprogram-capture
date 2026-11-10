# 7kid 微信小程序 · 抓包参考

本文记录 7kid 家长端小程序的入口、域名分工、关键接口与媒体 URL 规则，供用 `extract.py` 之前定位抓包用。

> 所有示例中的 `<accountId>`、`<token>`、`<userId>`、`<momentId>` 均为占位符。这些值因人而异，请用你自己抓到的替换，**不要**把带 token 的 URL 发到任何公开地方。

---

## 1. 小程序概况

| 项 | 值 |
|---|---|
| 名称 | 7kid（家长端） |
| AppID | `wxb8e4ed6a71d9c2a9` |
| 宿主 | 微信 8.0.x（XWEB 内核，Android/iOS 通用） |
| UA 特征 | `MicroMessenger/8.0.78 ... miniProgram/wxb8e4ed6a71d9c2a9 XWEB/1500205 MMWEBSDK/20260901` |
| 家长端容器页 | `https://parent.7kid.com/miniprogram/index?accountId=<accountId>&appId=wxb8e4ed6a71d9c2a9&expire=<ts>&token=<token>` |

抓包时按 `wxb8e4ed6a71d9c2a9` 或 UA 里的 `miniProgram/` 过滤，就能把它的请求单独拎出来。

## 2. 域名分工

| 域名 | 用途 | 是否需要鉴权 |
|---|---|---|
| `parent.7kid.com` | 业务 API（H5 容器 + 接口），所有 `/api/**` | 需要，`Authorization: Bearer` + `sign` 请求头 + `sl-session` Cookie |
| `kidapi.7kid.com` | IAM 令牌服务，如 `POST /iam/v1/web-oauth/common/token` | 需要 |
| `resource-pro.7kid.com` | 媒体 CDN（阿里云 OSS），图片/视频直链 | **不需要**，直接 GET 即可 |

这就是为什么本工具只需要抓包、不需要复刻登录态：**媒体在 CDN 上是裸链**，拿到的 URL 就能下载。

## 3. 要抓什么

只需要 **列表接口的响应体**：

```
POST https://parent.7kid.com/api/moment/v1/parent/moment/get-list
Content-Type: application/json

{"isAllClazz":true,"lastMomentId":0,"pageSize":20,"viewType":1}
```

返回 `data[]`，每条是一条动态，媒体在 `resourceVOs[]`：

```json
{
  "clazzMomentId": "<momentId>",
  "publisherName": "张老师",
  "content": "今天的户外活动",
  "publishTime": 1793793768000,
  "resourceVOs": [
    {
      "fileInfoVO": {
        "url": "https://resource-pro.7kid.com/7kid/cloud/resouce/<YYYYMM>/<userId>/<ts>-<ts>.jpg",
        "thumbnailUrl": "...?x-oss-process=image/resize,w_200,h_200/format,src/quality,Q_50",
        "compressUrl": "...?x-oss-process=image/resize,l_800,m_lfit",
        "fileType": "img"
      },
      "sort": "0"
    }
  ]
}
```

分页靠 `lastMomentId`（传上一条动态的 `clazzMomentId`，`0` 表示第一页）。想抓全量历史，就多下拉几次，或手工把请求重放几轮。

## 4. 其他相关接口

抓包时顺带会看到这些，媒体导出用不上，但了解结构有助于判断：

| 接口 | 作用 |
|---|---|
| `POST /api/moment/v1/parent/moment/get-by-id` | 单条动态详情（也会带 `resourceVOs`） |
| `POST /api/moment/v1/parent/get-icon-list` | **菜单图标配置**，`data` 也是数组，内容不是动态 —— 解析时必须排除，否则会误判出几十条空动态 |
| `POST /api/moment/v1/parent/notify/get-count` | 未读通知数 |
| `POST /api/album/v1/parent/clazz_album/list-by-page` | 班级相册列表（返回相册元信息，不含媒体直链） |
| `POST /api/album/v1/parent/album/parent-get-album` | 相册详情（`childName`/`childImgUrl`/`totalNum` 等） |
| `POST /api/album/v1/parent/album/album-detail` | 相册内页分页 |
| `POST /api/kid-arch/v1/parent/student/info` | 孩子与班级信息 |
| `POST /api/iam/v1/web-oauth/kid-login/parent-login` | 家长登录（换 Bearer token） |
| `POST /api/file/v1/aliyun/oss/get-config-and-callback-info` | 上传用 OSS 配置（家长发动态时用） |

## 5. 媒体 URL 规则

```
https://resource-pro.7kid.com/7kid/cloud/resouce/<YYYYMM>/<userId>/<ts1>-<ts2>.jpg
                                     ^^^^^^^ 注意官方就是拼错的 resouce
```

- 目录 `<YYYYMM>` 是**上传月份**，不是拍摄月份。
- `<userId>` 是发布者的用户 ID。
- 图片是 jpg 或 png；视频 `fileType` 标成 `mp4`，但实际扩展名可能是 **`.mov`**（iPhone 直传）。

### 阿里云 OSS 图片处理参数

| 参数 | 用途 |
|---|---|
| `image/resize,w_200,h_200/format,src/quality,Q_50` | 列表缩略图 |
| `image/resize,w_300,h_300/format,src/quality,Q_80` | 中等缩略图 |
| `image/resize,l_800,m_lfit` | 压缩大图（长边 800） |
| `video/snapshot,t_200,f_jpg,m_fast,ar_auto` | 视频封面（第 200ms 截帧） |

**下载原图就把 `?` 后面整段 query 去掉** —— 本工具的 `kidmedia.py` 已经这么处理了（`("?")[0]`）。

## 6. 已知坑

1. **视频要带 Referer**
   `resource-pro.7kid.com` 上的图片可以直接 GET，但视频直链不带 `Referer: https://parent.7kid.com/` 时可能返回 404。`download.py` 的 `--referer` 就是为这个准备的。

2. **`get-icon-list` 会污染解析**
   它的 `data` 同样是数组、每项也有 `url` 字段，但内容是 `/childLeave/list`、`/babyVideo/index` 这类菜单路径。`kidmedia.py` 里按接口路径 `/(get-list|get-by-id)$` 严格过滤，就是为了挡掉它。

3. **微信的请求走微信进程**
   小程序流量挂在 `com.tencent.mm` 下，ProxyPin 里按 App 过滤时选微信；同时会混进大量 `mmtls`、`wxs.qq.com` 的帖子视频流量，与本工具无关。

4. **一次刷新只返回 20 条**
   `pageSize` 默认 20，想拿全就多次下拉，或改 body 里的 `pageSize` 重放。

5. **同一天多条无文字动态**
   目录名必须带 `HHMM`，否则会全部落进同一个文件夹。工具已处理。

## 7. 边界

这份文档只描述「如何从自己账号的抓包里定位媒体」，不涉及绕过鉴权：媒体 CDN 本身就是公开直链，登录态部分（Bearer/token）完全没有被用到。

导出的照片涉及未成年人肖像，请仅作个人留档。
