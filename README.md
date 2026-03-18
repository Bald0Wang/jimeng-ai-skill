# Jimeng AI Skill

Python-based CLI wrappers for Volcengine Ark image and video generation APIs.

This repository no longer uses the legacy OpenAPI signature flow. It now follows the official Ark API style:

- Images: `POST /api/v3/images/generations`
- Video create: `POST /api/v3/contents/generations/tasks`
- Video get: `GET /api/v3/contents/generations/tasks/{id}`
- Video delete/cancel: `DELETE /api/v3/contents/generations/tasks/{id}`

## Requirements

- Python 3.10+
- `ARK_API_KEY`

```bash
export ARK_API_KEY="your-api-key"
```

## Scripts

- `python scripts/text2image.py`
- `python scripts/text2video.py`

## Text to Image

Default model: `doubao-seedream-5-0-260128`

```bash
python scripts/text2image.py "a corgi wearing sunglasses on the beach"
```

Common options:

- `--model`
- `--ratio`
- `--size`
- `--width --height`
- `--count`
- `--seed`
- `--output-format`
- `--watermark`
- `--web-search`
- `--no-download`

Examples:

```bash
python scripts/text2image.py "future Shanghai weather poster" --web-search --size 2048x2048
python scripts/text2image.py "four-panel seasonal courtyard illustration" --count 4 --size 2K
```

Cached outputs are stored under `output/<hash>/`.

## Text to Video

Default model: `doubao-seedance-1-5-pro-251215`

```bash
python scripts/text2video.py "a cat yawning by the window, morning light"
```

Common options:

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

Examples:

```bash
python scripts/text2video.py "cyberpunk city aerial shot" --ratio 16:9 --resolution 720p
python scripts/text2video.py "rainy neon street, slow push-in" --wait --return-last-frame
python scripts/text2video.py "rainy neon street, slow push-in" --cancel
```

Video task state is cached under `output/video/<hash>/`.

## References

- Video generation API: <https://www.volcengine.com/docs/82379/1520757?lang=zh>
- Get video task: <https://www.volcengine.com/docs/82379/1521309?lang=zh>
- List video tasks: <https://www.volcengine.com/docs/82379/1521675?lang=zh>
- Cancel/delete video task: <https://www.volcengine.com/docs/82379/1521720?lang=zh>
- Image generation API: <https://www.volcengine.com/docs/82379/1541523>
