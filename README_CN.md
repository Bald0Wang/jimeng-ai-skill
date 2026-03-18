# 即梦 AI Skill

这个仓库已经从旧的 TypeScript + OpenAPI 签名实现，切换为基于火山方舟官方 Ark API 的 Python 实现。

当前接口：

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

## 脚本入口

- 文生图：`python scripts/text2image.py`
- 文生视频：`python scripts/text2video.py`

## 文生图

默认模型：`doubao-seedream-5-0-260128`

```bash
python scripts/text2image.py "一只戴墨镜的柯基，在海边，胶片感"
```

常用参数：

- `--model`：模型 ID
- `--ratio`：宽高比
- `--size`：`2K`、`3K` 或 `2048x2048`
- `--width --height`：自定义像素尺寸
- `--count`：输出图片数量；大于 1 时使用组图模式
- `--seed`：随机种子
- `--output-format`：`png` 或 `jpeg`
- `--watermark`：添加水印
- `--web-search`：启用联网搜索
- `--no-download`：只返回 URL

示例：

```bash
python scripts/text2image.py "制作一张上海未来5日天气预报图" --web-search --size 2048x2048
python scripts/text2image.py "同一庭院四季变迁插画" --count 4 --size 2K
```

结果会缓存到 `output/<hash>/`。

## 文生视频

默认模型：`doubao-seedance-1-5-pro-251215`

```bash
python scripts/text2video.py "一只猫在窗边打哈欠，晨光，电影感"
```

常用参数：

- `--ratio`
- `--resolution`
- `--duration`
- `--frames`
- `--seed`
- `--camera-fixed`
- `--watermark`
- `--return-last-frame`
- `--draft`
- `--mute`
- `--service-tier`
- `--wait`
- `--cancel`
- `--task-id`
- `--no-download`

示例：

```bash
python scripts/text2video.py "赛博朋克城市俯瞰镜头" --ratio 16:9 --resolution 720p
python scripts/text2video.py "雨夜霓虹街道，镜头缓慢推进" --wait --return-last-frame
python scripts/text2video.py "雨夜霓虹街道，镜头缓慢推进" --cancel
```

视频任务状态会缓存在 `output/video/<hash>/`。

## 官方文档

- 视频生成 API：<https://www.volcengine.com/docs/82379/1520757?lang=zh>
- 查询视频任务：<https://www.volcengine.com/docs/82379/1521309?lang=zh>
- 查询视频任务列表：<https://www.volcengine.com/docs/82379/1521675?lang=zh>
- 取消/删除视频任务：<https://www.volcengine.com/docs/82379/1521720?lang=zh>
- 图片生成 API：<https://www.volcengine.com/docs/82379/1541523>
