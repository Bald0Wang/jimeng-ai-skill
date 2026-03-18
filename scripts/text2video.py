#!/usr/bin/env python
from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

from common import (
    ApiError,
    api_request,
    download_file,
    ensure_dir,
    fail,
    first_existing,
    print_result,
    read_text,
    task_hash,
    write_json,
    write_text,
)

DEFAULT_MODEL = "doubao-seedance-1-5-pro-251215"
DEFAULT_OUTPUT = Path("./output")
PENDING_STATUSES = {"queued", "running"}
FINAL_STATUSES = {"succeeded", "failed", "expired", "cancelled"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="即梦 Seedance 视频生成任务")
    parser.add_argument("prompt", nargs="?", help="视频生成提示词")
    parser.add_argument("--task-id", help="直接查询或取消指定任务 ID")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="模型 ID")
    parser.add_argument(
        "--ratio",
        default="9:16",
        choices=["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"],
        help="视频宽高比",
    )
    parser.add_argument(
        "--resolution",
        default="720p",
        choices=["480p", "720p", "1080p"],
        help="视频分辨率",
    )
    parser.add_argument("--duration", type=int, default=5, help="视频时长，单位秒")
    parser.add_argument("--frames", type=int, help="视频帧数；设置后优先于 duration")
    parser.add_argument("--seed", type=int, help="随机种子")
    parser.add_argument("--camera-fixed", action="store_true", help="固定摄像头")
    parser.add_argument("--watermark", action="store_true", help="输出视频添加水印")
    parser.add_argument("--return-last-frame", action="store_true", help="返回尾帧")
    parser.add_argument("--draft", action="store_true", help="开启 Draft 样片模式")
    parser.add_argument("--mute", action="store_true", help="关闭音频生成")
    parser.add_argument("--service-tier", choices=["default", "flex"], default="default", help="服务等级")
    parser.add_argument("--execution-expires-after", type=int, help="任务过期时间，单位秒")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="输出目录")
    parser.add_argument("--wait", action="store_true", help="等待任务完成")
    parser.add_argument("--max-attempts", type=int, default=120, help="轮询最大次数")
    parser.add_argument("--poll-interval", type=int, default=5, help="轮询间隔秒数")
    parser.add_argument("--no-download", action="store_true", help="不下载视频，只返回 URL")
    parser.add_argument("--cancel", action="store_true", help="取消排队中的任务，或删除已结束任务记录")
    parser.add_argument("--debug", action="store_true", help="输出调试信息")
    args = parser.parse_args()

    if not args.prompt and not args.task_id:
        parser.error("需要提供 prompt，或者通过 --task-id 指定已存在任务")
    if args.frames is not None and args.frames <= 0:
        parser.error("--frames 必须大于 0")
    if args.duration <= 0:
        parser.error("--duration 必须大于 0")
    return args


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    if not args.prompt:
        fail("INVALID_ARGUMENT", "缺少 prompt，无法提交视频任务")

    payload: dict[str, Any] = {
        "model": args.model,
        "content": [{"type": "text", "text": args.prompt}],
        "resolution": args.resolution,
        "ratio": args.ratio,
        "camera_fixed": args.camera_fixed,
        "watermark": args.watermark,
        "service_tier": args.service_tier,
        "return_last_frame": args.return_last_frame,
        "draft": args.draft,
    }
    if args.frames is not None:
        payload["frames"] = args.frames
    else:
        payload["duration"] = args.duration
    if args.seed is not None:
        payload["seed"] = args.seed
    if args.execution_expires_after is not None:
        payload["execution_expires_after"] = args.execution_expires_after
    if args.mute:
        payload["generate_audio"] = False
    return payload


def cache_key(args: argparse.Namespace) -> str:
    return task_hash(
        {
            "prompt": args.prompt,
            "model": args.model,
            "ratio": args.ratio,
            "resolution": args.resolution,
            "duration": None if args.frames is not None else args.duration,
            "frames": args.frames,
            "seed": args.seed,
            "camera_fixed": args.camera_fixed,
            "watermark": args.watermark,
            "return_last_frame": args.return_last_frame,
            "draft": args.draft,
            "mute": args.mute,
            "service_tier": args.service_tier,
            "execution_expires_after": args.execution_expires_after,
        }
    )


def task_folder(args: argparse.Namespace) -> Path:
    output_root = Path(args.output).expanduser().resolve()
    return ensure_dir(output_root / "video" / cache_key(args))


def direct_task_folder(output: str, task_id: str) -> Path:
    output_root = Path(output).expanduser().resolve()
    return ensure_dir(output_root / "video" / f"task-{task_id}")


def load_saved_task_id(folder: Path) -> str | None:
    task_path = folder / "taskId.txt"
    if task_path.exists():
        return read_text(task_path)
    return None


def query_task(task_id: str, *, debug: bool = False) -> dict[str, Any]:
    response = api_request(
        "GET",
        f"/contents/generations/tasks/{task_id}",
        debug=debug,
        timeout=120,
    )
    return response or {}


def cancel_task(task_id: str, *, debug: bool = False) -> None:
    api_request(
        "DELETE",
        f"/contents/generations/tasks/{task_id}",
        debug=debug,
        timeout=120,
    )


def wait_for_task(task_id: str, args: argparse.Namespace) -> dict[str, Any]:
    last_response: dict[str, Any] | None = None
    for _ in range(args.max_attempts):
        response = query_task(task_id, debug=args.debug)
        last_response = response
        status = response.get("status")
        if status in FINAL_STATUSES:
            return response
        time.sleep(args.poll_interval)
    if last_response:
        return last_response
    fail("TIMEOUT", f"任务 {task_id} 轮询超时")
    raise AssertionError("unreachable")


def existing_video(folder: Path) -> Path | None:
    return first_existing([folder / "video.mp4", folder / "video.mov"])


def materialize_result(
    task_id: str,
    response: dict[str, Any],
    folder: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    write_json(folder / "response.latest.json", response)
    status = response.get("status")
    content = response.get("content") or {}
    result: dict[str, Any] = {
        "success": True,
        "taskId": task_id,
        "status": status,
        "model": response.get("model", args.model),
        "ratio": response.get("ratio"),
        "resolution": response.get("resolution"),
        "duration": response.get("duration"),
        "frames": response.get("frames"),
        "usage": response.get("usage"),
        "outputDir": str(folder),
    }

    if status in {"failed", "expired", "cancelled"}:
        result["error"] = response.get("error")
        return result

    video_url = content.get("video_url")
    last_frame_url = content.get("last_frame_url")
    if video_url:
        result["videoUrl"] = video_url
    if last_frame_url:
        result["lastFrameUrl"] = last_frame_url

    if args.no_download or status != "succeeded":
        return result

    local_video = existing_video(folder)
    if not local_video and video_url:
        local_video = download_file(video_url, folder / "video.mp4")
    if local_video:
        result["videoPath"] = str(local_video)

    if last_frame_url:
        last_frame_path = folder / "last_frame.png"
        if not last_frame_path.exists():
            download_file(last_frame_url, last_frame_path)
        result["lastFramePath"] = str(last_frame_path)

    return result


def submit_task(args: argparse.Namespace, folder: Path) -> str:
    payload = build_payload(args)
    write_json(folder / "param.json", payload)
    response = api_request(
        "POST",
        "/contents/generations/tasks",
        body=payload,
        debug=args.debug,
        timeout=180,
    )
    response = response or {}
    write_json(folder / "response.submit.json", response)

    task_id = response.get("id")
    if not task_id:
        fail("INVALID_RESPONSE", "提交任务成功但响应中没有返回任务 ID")

    write_text(folder / "taskId.txt", task_id)
    return task_id


def main() -> None:
    args = parse_args()

    try:
        if args.task_id:
            folder = direct_task_folder(args.output, args.task_id)
            if args.cancel:
                cancel_task(args.task_id, debug=args.debug)
                print_result(
                    {
                        "success": True,
                        "taskId": args.task_id,
                        "cancelled": True,
                        "message": "已发送取消/删除请求",
                    }
                )
                return

            response = query_task(args.task_id, debug=args.debug)
            print_result(materialize_result(args.task_id, response, folder, args))
            return

        folder = task_folder(args)
        task_id = load_saved_task_id(folder)

        if args.cancel:
            if not task_id:
                fail("TASK_NOT_FOUND", "未找到与当前参数对应的历史任务")
            cancel_task(task_id, debug=args.debug)
            print_result(
                {
                    "success": True,
                    "taskId": task_id,
                    "cancelled": True,
                    "message": "已发送取消/删除请求",
                    "outputDir": str(folder),
                }
            )
            return

        if task_id:
            response = query_task(task_id, debug=args.debug)
            status = response.get("status")
            if status in PENDING_STATUSES and args.wait:
                response = wait_for_task(task_id, args)
            print_result(materialize_result(task_id, response, folder, args))
            return

        task_id = submit_task(args, folder)
        if not args.wait:
            print_result(
                {
                    "success": True,
                    "submitted": True,
                    "taskId": task_id,
                    "prompt": args.prompt,
                    "model": args.model,
                    "outputDir": str(folder),
                    "message": "任务已提交，请稍后重试相同命令查询结果",
                }
            )
            return

        response = wait_for_task(task_id, args)
        print_result(materialize_result(task_id, response, folder, args))

    except ApiError as exc:
        fail(exc.code, str(exc), status=exc.status)


if __name__ == "__main__":
    main()
