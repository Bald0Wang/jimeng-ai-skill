---
name: jimeng-ai
description: 基于火山方舟官方 Ark API 的即梦文生图 / 文生视频 Skill，使用 Python 实现。
---

# 即梦 AI Skill

当前版本已从旧的 OpenAPI 签名版 TypeScript 实现切换为 Python 实现，直接调用火山方舟官方接口：

- 图片生成：`POST /api/v3/images/generations`
- 视频任务创建：`POST /api/v3/contents/generations/tasks`
- 视频任务查询：`GET /api/v3/contents/generations/tasks/{id}`
- 视频任务取消/删除：`DELETE /api/v3/contents/generations/tasks/{id}`

## 环境要求

- Python 3.10+
- 环境变量：`ARK_API_KEY`

```bash
export ARK_API_KEY="your-api-key"
```

获取方式见火山方舟控制台 API Key 页面。

## 核心脚本

- 文生图：`python scripts/text2image.py`
- 文生视频：`python scripts/text2video.py`

## 文生图

默认模型：`doubao-seedream-5-0-260128`

```bash
python scripts/text2image.py "一只戴墨镜的柯基，海边，胶片感"
```

常用参数：

- `--model`：指定模型 ID
- `--ratio`：宽高比，默认 `16:9`
- `--size`：支持 `2K`、`3K` 或像素值如 `2048x2048`
- `--width --height`：自定义像素尺寸
- `--count`：输出张数；大于 1 时启用组图模式
- `--seed`：随机种子
- `--output-format`：`png` 或 `jpeg`
- `--watermark`：添加水印
- `--web-search`：启用 Seedream 5.0 联网搜索
- `--no-download`：只返回 URL，不下载图片

结果会缓存在 `output/<hash>/` 目录下。相同参数再次执行时，优先复用本地结果。

## 文生视频

默认模型：`doubao-seedance-1-5-pro-251215`

```bash
python scripts/text2video.py "一只猫在窗边打哈欠，晨光，电影感"
```

常用参数：

- `--ratio`：默认 `9:16`
- `--resolution`：`480p` / `720p` / `1080p`
- `--duration`：视频时长
- `--frames`：指定帧数，优先于 `--duration`
- `--seed`：随机种子
- `--camera-fixed`：固定镜头
- `--watermark`：添加水印
- `--return-last-frame`：返回尾帧图片
- `--draft`：开启 Draft 样片模式
- `--mute`：关闭音频生成
- `--service-tier`：`default` 或 `flex`
- `--wait`：提交后轮询直到任务结束
- `--cancel`：取消排队中的任务，或删除已结束任务记录
- `--task-id`：直接查询或取消指定任务
- `--no-download`：只返回 URL，不下载视频

视频任务信息会缓存在 `output/video/<hash>/` 下，包括：

- `param.json`
- `response.submit.json`
- `response.latest.json`
- `taskId.txt`
- `video.mp4`
- `last_frame.png`

## 示例

```bash
# 单图输出，启用联网搜索
python scripts/text2image.py "制作一张上海未来5日天气预报图" --web-search --size 2048x2048

# 4 张组图
python scripts/text2image.py "同一庭院四季变迁插画" --count 4 --size 2K

# 提交视频任务
python scripts/text2video.py "赛博朋克城市俯瞰镜头" --ratio 16:9 --resolution 720p

# 提交并等待完成，同时保存尾帧
python scripts/text2video.py "雨夜霓虹街道，镜头缓慢推进" --wait --return-last-frame

# 取消或删除历史任务
python scripts/text2video.py "雨夜霓虹街道，镜头缓慢推进" --cancel
```

## 参考

- 视频生成 API：<https://www.volcengine.com/docs/82379/1520757?lang=zh>
- 查询视频任务：<https://www.volcengine.com/docs/82379/1521309?lang=zh>
- 查询视频任务列表：<https://www.volcengine.com/docs/82379/1521675?lang=zh>
- 取消/删除视频任务：<https://www.volcengine.com/docs/82379/1521720?lang=zh>
- 图片生成 API：<https://www.volcengine.com/docs/82379/1541523>
