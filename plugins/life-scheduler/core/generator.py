import asyncio
import datetime
import json
import random
import re
from dataclasses import asdict, dataclass

from astrbot.api import logger
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.star.context import Context

from .data import ScheduleData, ScheduleDataManager

_STYLE_PREFIX_RE = re.compile(
    r"^\s*(?:【?风格】?|\[?风格\]?)\s*[:：]\s*(?P<style>.+?)(?:\n|$)"
)


@dataclass(slots=True)
class ScheduleContext:
    date_str: str
    weekday: str
    holiday: str
    persona_desc: str
    history_schedules: str
    recent_chats: str
    day_frame: str
    mood_color: str
    special_event: str


class SchedulerGenerator:
    _STYLE_ENFORCE_RETRIES = 2
    _EMPTY_COMPLETION_RETRIES = 1

    def __init__(
        self,
        context: Context,
        config: AstrBotConfig,
        data_mgr: ScheduleDataManager,
    ):
        self.context = context
        self.config = config
        self.data_mgr = data_mgr

        self._gen_lock = asyncio.Lock()
        self._generating = False

    async def generate_schedule(
        self, date: datetime.datetime | None = None, umo: str | None = None, extra: str | None = None
    ) -> ScheduleData:
        async with self._gen_lock:
            if self._generating:
                raise RuntimeError("schedule_generating")
            self._generating = True

        data: ScheduleData | None = None
        date = date or datetime.datetime.now()
        date_str = date.strftime("%Y-%m-%d")
        try:
            logger.info(f"正在生成 {date_str} 的日程...")
            ctx = await self._collect_context(date, umo)
            prompt = self._build_prompt(ctx, extra)
            sid_base = f"life_scheduler_gen_{date_str}"
            content = await self._call_llm(prompt, sid=f"{sid_base}_0")

            payload = self._extract_json_obj(content)
            ok, reason = self._validate_payload(payload, ctx)
            for attempt in range(1, self._STYLE_ENFORCE_RETRIES + 1):
                if ok:
                    break
                repair_prompt = self._build_style_repair_prompt(ctx, content, reason)
                content = await self._call_llm(repair_prompt, sid=f"{sid_base}_{attempt}")
                payload = self._extract_json_obj(content)
                ok, reason = self._validate_payload(payload, ctx)

            if not ok or not payload:
                raise ValueError(f"模型未遵循穿搭风格约束：{reason}")

            data = self._to_schedule_data(payload, date_str, ctx)
            self.data_mgr.set(data)
            logger.info(
                f"日程生成成功: {json.dumps(asdict(data), ensure_ascii=False, indent=2)}"
            )
            return data
        except Exception as e:
            logger.error(f"日程生成失败: {e}")
            return ScheduleData(
                date=date_str, outfit="生成失败", schedule="生成失败", status="failed"
            )
        finally:
            async with self._gen_lock:
                self._generating = False
            if data:
                self.data_mgr.set(data)

    # ---------- context ----------

    async def _collect_context(
        self, data: datetime.datetime, umo: str | None
    ) -> ScheduleContext:
        return ScheduleContext(
            date_str=data.strftime("%Y年%m月%d日"),
            weekday=self._weekday(data),
            holiday=self._get_holiday_info(data.date()),
            persona_desc=await self._get_persona(),
            history_schedules=self._get_history(data),
            recent_chats=await self._get_recent_chats(umo),
            day_frame=self._build_day_frame(data),
            mood_color=self._pick_mood(),
            special_event=self._roll_special_event(),
        )

    def _weekday(self, data):
        return ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][
            data.weekday()
        ]

    def _get_holiday_info(self, date: datetime.date) -> str:
        """获取节日信息（中国）"""
        try:
            import holidays

            cn_holidays = holidays.CN()
            holiday_name = cn_holidays.get(date)
            if holiday_name:
                return f"今天是 {holiday_name}"
        except Exception:
            return ""
        return ""

    def _pick_mood(self) -> str:
        moods = self.config.get("pool", {}).get("mood_colors") or []
        return random.choice(moods) if moods else "平和"

    def _build_day_frame(self, date: datetime.datetime) -> str:
        """根据星期几给出确定性的作息骨架"""
        wd = date.weekday()
        if wd <= 4:
            return (
                "今天是工作日，作息大致如下：\n"
                "- 清晨：起床、晨间准备，做点简单热身\n"
                "- 上午：在特雷森学园上课\n"
                "- 中午：和伙伴一起午餐、稍作休息\n"
                "- 下午：训练（跑步、体能、技术打磨）\n"
                "- 傍晚：自习、整理，放松一下\n"
                "- 晚上：独处休息，早些就寝"
            )
        if wd == 5:
            return (
                "今天是周六，作息大致如下：\n"
                "- 上午：训练，强度比平日略轻\n"
                "- 下午：比较自由——社团活动、和伙伴外出，或自己安排\n"
                "- 晚上：放松休息"
            )
        return (
            "今天是周日，作息大致如下：\n"
            "- 全天以休息和调整为主，训练明显减量\n"
            "- 做些自己喜欢的事，或安静地待着\n"
            "- 傍晚为下周做点准备"
        )

    _NO_SPECIAL_EVENT = "今天没有特别的事，按平常的节奏过就好。"

    def _roll_special_event(self) -> str:
        """按概率掷骰，决定今天是否有特殊事件（含角色事件）"""
        try:
            chance = int(self.config.get("special_event_chance", 30))
        except (TypeError, ValueError):
            chance = 30
        if not (random.random() < chance / 100):
            return self._NO_SPECIAL_EVENT

        char_event = self._roll_character_event()
        if char_event:
            return char_event

        events = self.config.get("special_events") or []
        if events:
            return random.choice(events)
        return self._NO_SPECIAL_EVENT

    def _roll_character_event(self) -> str:
        """特殊事件命中后，按比例决定是否为角色事件，并按权重抽角色填模板"""
        try:
            chance = int(self.config.get("character_event_chance", 50))
        except (TypeError, ValueError):
            chance = 50
        if not (random.random() < chance / 100):
            return ""

        templates = self.config.get("character_event_templates") or []
        names, weights = self._parse_roster()
        if not names or not templates:
            return ""

        name = random.choices(names, weights=weights, k=1)[0]
        tmpl = random.choice(templates)
        try:
            return tmpl.format(name=name)
        except Exception:
            return tmpl

    def _parse_roster(self) -> tuple[list[str], list[float]]:
        """解析「角色名:权重」名册，返回 (名字列表, 权重列表)"""
        names: list[str] = []
        weights: list[float] = []
        for entry in self.config.get("character_roster") or []:
            text = str(entry).strip()
            if not text:
                continue
            name, sep, raw_weight = text.replace("：", ":").rpartition(":")
            if sep:
                name = name.strip()
                try:
                    weight = float(raw_weight.strip())
                except (TypeError, ValueError):
                    weight = 1.0
            else:
                name, weight = text, 1.0
            if name and weight > 0:
                names.append(name)
                weights.append(weight)
        return names, weights

    def _extract_style_from_outfit(self, outfit: str) -> str:
        if not outfit:
            return ""
        m = _STYLE_PREFIX_RE.match(outfit.strip())
        if not m:
            return ""
        return (m.group("style") or "").strip()

    def _get_history(self, today: datetime.date) -> str:
        items: list[str] = []

        days = self.config.get("reference_history_days", 0)
        if days <= 0:
            return "（无历史记录）"

        for i in range(1, days + 1):
            date = today - datetime.timedelta(days=i)
            data = self.data_mgr.get(date)
            if not data or data.status != "ok":
                continue

            outfit = data.outfit[:40]
            schedule = data.schedule[:60]
            style = (getattr(data, "outfit_style", "") or "").strip() or self._extract_style_from_outfit(data.outfit)

            if style:
                items.append(f"[{date.strftime('%Y-%m-%d')}] 风格：{style} 穿搭：{outfit} 日程：{schedule}")
            else:
                items.append(f"[{date.strftime('%Y-%m-%d')}] 穿搭：{outfit} 日程：{schedule}")

        return "\n".join(items) if items else "（无历史记录）"

    async def _get_recent_chats(
        self, umo: str | None = None, count: int | None = None
    ) -> str:
        """获取指定会话的最近聊天记录"""
        count = count or self.config["reference_recent_count"]

        if not umo or not count:
            return "无近期对话"

        try:
            cid = await self.context.conversation_manager.get_curr_conversation_id(umo)
            if not cid:
                return "无最近对话记录"

            conv = await self.context.conversation_manager.get_conversation(umo, cid)
            if not conv or not conv.history:
                return "无最近对话记录"

            history = json.loads(conv.history)

            recent = history[-count:] if count > 0 else []

            formatted = []
            for msg in recent:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if role == "user":
                    formatted.append(f"用户: {content}")
                elif role == "assistant":
                    formatted.append(f"我: {content}")

            return "\n".join(formatted)

        except Exception as e:
            logger.error(f"Failed to get recent chats for {umo}: {e}")
            return "获取对话记录失败"

    async def _get_persona(self) -> str:
        try:
            p = await self.context.persona_manager.get_default_persona_v3()
            return p.get("prompt") if isinstance(p, dict) else getattr(p, "prompt", "")
        except Exception:
            return "你是一个热爱生活、情感细腻的AI伙伴。"

    # ---------- llm ----------
    def _build_prompt(self, ctx: ScheduleContext, extra: str | None = None) -> str:
        ctx_dict = asdict(ctx)  # 实际有的字段
        tmpl_vars = set(re.findall(r"\{(\w+)\}", self.config["prompt_template"]))
        missing = tmpl_vars - ctx_dict.keys()
        if missing:
            logger.warning(
                f"prompt 模板存在 ScheduleContext 未提供的字段：{missing}| 已自动替换成空串"
            )

        # 统一补空值，避免 KeyError
        for k in missing:
            ctx_dict[k] = ""
        prompt = self.config["prompt_template"].format(**ctx_dict)

        # 如果有用户补充要求，追加到 prompt 末尾
        if extra:
            prompt += f"\n\n【用户补充要求】\n请在生成日程时特别注意以下要求：{extra}"

        return prompt

    async def _call_llm(self, prompt: str, *, sid: str = "life_scheduler_gen") -> str:
        provider = self.context.get_using_provider()
        if not provider:
            raise RuntimeError("No provider")

        try:
            for attempt in range(self._EMPTY_COMPLETION_RETRIES + 1):
                resp = await provider.text_chat(prompt, session_id=sid)
                text = self._extract_completion_text(resp)
                if text:
                    return text
                if attempt < self._EMPTY_COMPLETION_RETRIES:
                    logger.warning("LLM completion 为空，准备重试一次")
            raise RuntimeError("API返回的completion为空")
        finally:
            await self._cleanup_session(sid)

    @staticmethod
    def _extract_completion_text(resp: object) -> str:
        if resp is None:
            return ""
        for key in ("completion_text", "completion", "text", "content"):
            value = getattr(resp, key, None)
            if isinstance(value, str):
                text = value.strip()
                if text:
                    return text
        return ""

    async def _cleanup_session(self, sid: str):
        try:
            cid = await self.context.conversation_manager.get_curr_conversation_id(sid)
            if cid:
                await self.context.conversation_manager.delete_conversation(sid, cid)
        except Exception:
            pass

    # ---------- parse ----------
    def _extract_json_obj(self, text: str) -> dict | None:
        text = text.strip()
        text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^```\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)

        start = text.find("{")
        if start == -1:
            return None

        brace = 0
        in_string = False
        escape = False

        for i, ch in enumerate(text[start:], start=start):
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
            else:
                if ch == '"':
                    in_string = True
                elif ch == "{":
                    brace += 1
                elif ch == "}":
                    brace -= 1
                    if brace == 0:
                        json_str = text[start : i + 1]
                        try:
                            data = json.loads(json_str)
                            return data if isinstance(data, dict) else None
                        except Exception:
                            return None

        return None

    def _validate_payload(self, payload: dict | None, ctx: ScheduleContext) -> tuple[bool, str]:
        if not payload:
            return False, "未能解析出 JSON 对象"

        outfit = str(payload.get("outfit", "")).strip()
        schedule = str(payload.get("schedule", "")).strip()
        if not outfit:
            return False, "outfit 不能为空"
        if not schedule:
            return False, "schedule 不能为空"

        return True, ""

    def _build_style_repair_prompt(self, ctx: ScheduleContext, bad_text: str, reason: str) -> str:
        return (
            "你之前的输出未通过校验，需要重写。\n"
            f"校验原因：{reason}\n\n"
            "请只输出 JSON 对象本体，不要 Markdown，不要解释。\n"
            "输出 JSON 必须包含字段：outfit_style、outfit、schedule，且 outfit、schedule 都不能为空。\n\n"
            "你之前的输出（供参考，可能不合规）：\n"
            f"{bad_text}\n"
        )

    def _to_schedule_data(self, payload: dict, date_str: str, ctx: ScheduleContext) -> ScheduleData:
        outfit = str(payload.get("outfit", "")).strip() or "日常休闲装"
        schedule = str(payload.get("schedule", "")).strip() or "无"
        outfit_style = str(payload.get("outfit_style", "")).strip()
        return ScheduleData(
            date=date_str,
            outfit_style=outfit_style,
            outfit=outfit,
            schedule=schedule,
        )
