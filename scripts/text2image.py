#!/usr/bin/env python
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

from common import (
    ApiError,
    api_request,
    download_file,
    ensure_dir,
    fail,
    image_files,
    print_result,
    read_json,
    task_hash,
    write_json,
)

DEFAULT_MODEL = "doubao-seedream-5-0-260128"
DEFAULT_OUTPUT = Path("./output")
RATIO_TO_SIZE = {
    "1:1": "2048x2048",
    "3:4": "1728x2304",
    "4:3": "2304x1728",
    "16:9": "2848x1600",
    "9:16": "1600x2848",
    "3:2": "2496x1664",
    "2:3": "1664x2496",
    "21:9": "3136x1344",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="即梦 Seedream 5.0 文生图")
    parser.add_argument("prompt", help="图片生成提示词")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="模型 ID")
    parser.add_argument("--ratio", default="16:9", choices=sorted(RATIO_TO_SIZE), help="宽高比")
    parser.add_argument("--count", type=int, default=1, help="输出图片数量，1 表示单图，>1 使用组图模式")
    parser.add_argument("--size", help="输出尺寸，支持 2K/3K 或 2048x2048；兼容旧版面积整数")
    parser.add_argument("--width", type=int, help="自定义宽度，需和 --height 一起使用")
    parser.add_argument("--height", type=int, help="自定义高度，需和 --width 一起使用")
    parser.add_argument("--seed", type=int, help="随机种子")
    parser.add_argument("--output-format", default="png", choices=["png", "jpeg"], help="输出图片格式")
    parser.add_argument("--watermark", action="store_true", help="输出图片添加水印")
    parser.add_argument("--web-search", action="store_true", help="启用联网搜索能力")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="输出目录")
    parser.add_argument("--no-download", action="store_true", help="不下载图片，只返回 URL")
    parser.add_argument("--debug", action="store_true", help="输出调试信息")
    return parser.parse_args()


def resolve_size(args: argparse.Namespace) -> str:
    if (args.width is None) ^ (args.height is None):
        fail("INVALID_ARGUMENT", "--width 和 --height 需要同时提供")

    if args.width is not None and args.height is not None:
        return f"{args.width}x{args.height}"

    if args.size:
        if args.size.isdigit():
            area = int(args.size)
            side = int(math.isqrt(area))
            if side * side != area:
                fail("INVALID_ARGUMENT", "--size 为纯数字时，需要是完全平方数面积，例如 4194304")
            return f"{side}x{side}"
        return args.size

    return RATIO_TO_SIZE[args.ratio]


def cache_key(args: argparse.Namespace, size: str) -> str:
    return task_hash(
        {
            "prompt": args.prompt,
            "model": args.model,
            "size": size,
            "count": args.count,
            "seed": args.seed,
            "output_format": args.output_format,
            "watermark": args.watermark,
            "web_search": args.web_search,
        }
    )


def response_urls(data: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for item in data.get("data", []):
        url = item.get("url")
        if url:
            urls.append(url)
    return urls


def main() -> None:
    args = parse_args()
    size = resolve_size(args)

    if args.count < 1 or args.count > 15:
        fail("INVALID_ARGUMENT", "count 必须在 1 到 15 之间")

    output_root = Path(args.output).expanduser().resolve()
    folder = ensure_dir(output_root / cache_key(args, size))
    response_path = folder / "response.json"
    param_path = folder / "param.json"

    existing_images = image_files(folder)
    if existing_images and not args.no_download:
        print_result(
            {
                "success": True,
                "cached": True,
                "prompt": args.prompt,
                "model": args.model,
                "size": size,
                "count": args.count,
                "images": [str(path) for path in existing_images],
                "outputDir": str(folder),
            }
        )
        return

    response_data: dict[str, Any]
    if response_path.exists():
        response_data = read_json(response_path)
    else:
        payload: dict[str, Any] = {
            "model": args.model,
            "prompt": args.prompt,
            "size": size,
            "output_format": args.output_format,
            "response_format": "url",
            "watermark": args.watermark,
        }
        if args.seed is not None:
            payload["seed"] = args.seed
        if args.web_search:
            payload["tools"] = [{"type": "web_search"}]
        if args.count > 1:
            payload["sequential_image_generation"] = "auto"
            payload["sequential_image_generation_options"] = {"max_images": args.count}

        write_json(param_path, payload)
        try:
            response = api_request(
                "POST",
                "/images/generations",
                body=payload,
                timeout=300,
                debug=args.debug,
            )
        except ApiError as exc:
            fail(exc.code, str(exc), status=exc.status)
        response_data = response or {}
        write_json(response_path, response_data)

    urls = response_urls(response_data)
    if not urls:
        fail("INVALID_RESPONSE", "接口返回中未包含图片 URL")

    if args.no_download:
        print_result(
            {
                "success": True,
                "prompt": args.prompt,
                "model": args.model,
                "size": size,
                "count": args.count,
                "imageUrls": urls,
                "outputDir": str(folder),
                "usage": response_data.get("usage"),
            }
        )
        return

    saved_paths: list[str] = []
    ext = ".png" if args.output_format == "png" else ".jpg"
    for index, url in enumerate(urls, start=1):
        target = folder / f"{index}{ext}"
        if not target.exists():
            download_file(url, target)
        saved_paths.append(str(target))

    print_result(
        {
            "success": True,
            "prompt": args.prompt,
            "model": args.model,
            "size": size,
            "count": args.count,
            "images": saved_paths,
            "imageUrls": urls,
            "outputDir": str(folder),
            "usage": response_data.get("usage"),
        }
    )


if __name__ == "__main__":
    main()
