import time
from pathlib import Path
from typing import Any

import aiohttp

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.event.filter import EventMessageType
from astrbot.api.star import Context, Star, StarTools, register

from .capture import (
    DEFAULT_AUTO_STOP_SECONDS,
    CaptureState,
    append_jsonl,
    build_download_jobs,
    collect_records,
    count_jsonl_lines,
    normalize_auto_stop_seconds,
)


@register(
    "astrbot_plugin_mface_capture",
    "local",
    "本地 QQ 表情采集辅助，记录 mface/image 元数据并可保存图片",
    "0.2.2",
)
class MFaceCapturePlugin(Star):
    def __init__(self, context: Context, config: dict[str, Any] | None = None):
        super().__init__(context)
        self.config = config or {}
        self.auto_stop_seconds = normalize_auto_stop_seconds(
            self.config.get("auto_stop_seconds", DEFAULT_AUTO_STOP_SECONDS)
        )
        self.state = CaptureState(
            enabled=bool(self.config.get("enabled", False)),
            auto_stop_seconds=self.auto_stop_seconds,
            now=time.time(),
        )
        self.capture_mface = bool(self.config.get("capture_mface", True))
        self.capture_image = bool(self.config.get("capture_image", True))
        self.silence_during_capture = bool(
            self.config.get("silence_during_capture", True)
        )
        self.save_images = bool(self.config.get("save_images", True))
        self.download_timeout_seconds = max(
            1, int(self.config.get("download_timeout_seconds", 15) or 15)
        )

        output_filename = Path(
            str(
                self.config.get("output_filename") or "mface_captures.jsonl"
            ).strip()
        ).name
        if not output_filename.endswith(".jsonl"):
            output_filename = "mface_captures.jsonl"

        self.data_dir = Path(StarTools.get_data_dir())
        self.output_path = self.data_dir / output_filename
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @filter.event_message_type(EventMessageType.ALL, priority=10000)
    async def capture_message(self, event: AstrMessageEvent):
        now = time.time()
        source_origin = self._get_source_origin(event)
        if not self.state.is_active_for(now, source_origin):
            return

        raw_message = self._get_raw_message(event)
        message_type = self._get_message_type(event)
        records = collect_records(
            raw_message,
            message_type=message_type,
            capture_mface=self.capture_mface,
            capture_image=self.capture_image,
            label=self.state.label,
        )
        if not records:
            return

        if self.save_images:
            await self._save_images(raw_message, records, self.state.label)

        written = append_jsonl(self.output_path, records)
        logger.info(
            f"[mface_capture] captured {written} segment(s) to {self.output_path}"
        )
        if self.silence_during_capture:
            logger.info("[mface_capture] stopped event propagation during capture")
            event.stop_event()

    @filter.command("表情采集", priority=10000)
    async def mface_capture(self, event: AstrMessageEvent, action: str = ""):
        action = str(action or "").strip()
        if action in ("", "状态", "status"):
            async for result in self._status_result(event):
                yield result
            event.stop_event()
            return
        if action in ("开启", "开", "enable"):
            async for result in self._enable_result(event, label=None):
                yield result
            event.stop_event()
            return
        if action in ("关闭", "关", "disable"):
            async for result in self._disable_result(event):
                yield result
            event.stop_event()
            return

        async for result in self._enable_result(event, label=action):
            yield result
        event.stop_event()

    async def _status_result(self, event: AstrMessageEvent):
        now = time.time()
        count = count_jsonl_lines(self.output_path)
        active = self.state.is_active(now)
        state = "开启" if active else "关闭"
        remaining = self.state.remaining_seconds(now)
        current_source_origin = self._get_source_origin(event)
        if not active:
            scope = "未绑定"
        elif not self.state.source_origin:
            scope = "全部会话"
        elif self.state.source_origin == current_source_origin:
            scope = "当前会话"
        else:
            scope = "其它会话"
        yield event.plain_result(
            "表情采集状态：{}\n"
            "当前标签：{}\n"
            "采集作用域：{}\n"
            "静默拦截：{}\n"
            "自动关闭：{} 秒{}\n"
                "采集类型：mface={}，image={}\n"
                "保存图片：{}\n"
                "本地文件：{}\n"
            "已记录：{} 条".format(
                state,
                self.state.label or "未设置",
                scope,
                "开" if self.silence_during_capture else "关",
                self.auto_stop_seconds,
                f"，剩余约 {remaining} 秒" if active and remaining else "",
                "开" if self.capture_mface else "关",
                "开" if self.capture_image else "关",
                "开" if self.save_images else "关",
                self.output_path,
                count,
            )
        )

    async def _enable_result(self, event: AstrMessageEvent, label: str | None):
        self.state.activate(
            time.time(),
            label=label,
            source_origin=self._get_source_origin(event),
        )
        suffix = (
            f"本轮将在约 {self.auto_stop_seconds} 秒后自动关闭。"
            if self.auto_stop_seconds
            else "本轮不会自动关闭，请手动发送 /表情采集 关闭。"
        )
        if label:
            yield event.plain_result(
                f"已开启「{label}」表情采集，采集期间会静默拦截表情消息。{suffix}"
            )
            return
        yield event.plain_result(
            f"已开启本地表情采集，采集期间会静默拦截表情消息。{suffix}"
        )

    async def _disable_result(self, event: AstrMessageEvent):
        self.state.deactivate()
        yield event.plain_result("已关闭本地表情采集，阿尔丹已恢复正常回复。")

    def _get_raw_message(self, event: AstrMessageEvent):
        message_obj = getattr(event, "message_obj", None)
        return getattr(message_obj, "raw_message", None)

    def _get_message_type(self, event: AstrMessageEvent) -> str:
        try:
            message_type = event.get_message_type()
        except Exception:
            return ""
        return str(getattr(message_type, "value", message_type) or "")

    def _get_source_origin(self, event: AstrMessageEvent) -> str:
        return str(getattr(event, "unified_msg_origin", "") or "")

    async def _save_images(
        self,
        raw_message,
        records: list[dict[str, Any]],
        label: str,
    ) -> None:
        jobs = build_download_jobs(raw_message, records, label=label)
        if not jobs:
            return

        timeout = aiohttp.ClientTimeout(total=self.download_timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for job in jobs:
                target = self.data_dir / job["relative_path"]
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    async with session.get(job["url"]) as resp:
                        if resp.status != 200:
                            logger.warning(
                                f"[mface_capture] image download failed: status={resp.status}"
                            )
                            continue
                        content = await resp.read()
                    target.write_bytes(content)
                    self._attach_local_file(records, job["fingerprint"], target)
                    logger.info(f"[mface_capture] saved image to {target}")
                except Exception as exc:
                    logger.warning(f"[mface_capture] image save failed: {exc}")

    def _attach_local_file(
        self,
        records: list[dict[str, Any]],
        fingerprint: str,
        target: Path,
    ) -> None:
        for record in records:
            if record.get("fingerprint") == fingerprint:
                record["local_file"] = str(target.relative_to(self.data_dir)).replace(
                    "\\", "/"
                )
                return
