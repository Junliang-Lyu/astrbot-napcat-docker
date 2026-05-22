# life-scheduler（阿尔丹项目定制版）

基于 astrbot_plugin_life_scheduler（原作者 QQ 群 215532038）的修改版本，
针对目白阿尔丹角色扮演场景重写了日程生成逻辑。

---

## 原插件功能

- 每日定时用 LLM 生成角色日程和穿搭描述
- 将当日状态注入 system prompt，让角色"记得"自己今天在做什么
- `查看日程` / `重写日程` / `日程时间` 指令

---

## 本版本的改动

### 1. 人设改造（`_conf_schema.json` · `core/generator.py`）

将 prompt 模板和创意池全部改写为目白阿尔丹版本：

- `prompt_template`：以特雷森学园为背景，穿着按"上课日制服 / 训练时训练服 / 休息日便服"规则描述，明确禁止出现玩家视角词汇
- `mood_colors` 池：替换为符合阿尔丹性格的情绪词（温柔、轻快、优雅、踏实等）
- `special_events` 池：内容围绕目白家拜访、比赛备战、学园活动等场景
- `character_roster`：Uma Musume 角色名册，含权重（樱花千代王×5、八重无敌×5、目白拉茉奴×4 等）

### 2. 作息骨架（`core/generator.py` · `_build_day_frame`）

原插件从创意池随机抽取 `daily_themes` / `schedule_types`。
本版本改为按**星期几**生成固定的作息骨架，注入 prompt 约束日程结构：

| 日期 | 骨架内容 |
|---|---|
| 周一至周五 | 晨间准备 → 特雷森学园上课 → 午餐 → 训练（跑步/体能/技术）→ 自习/放松 → 早睡 |
| 周六 | 轻量训练 → 下午自由安排（社团/外出）→ 晚间放松 |
| 周日 | 全天以休息为主，训练明显减量，傍晚为下周做准备 |

这样保证日程结构与角色设定一致，不会出现"上班""会议"等不适内容。

### 3. 角色事件系统（`core/generator.py` · `_roll_special_event` · `_roll_character_event`）

新增两级概率掷骰，让每天偶尔发生特别事件：

```
special_event_chance（默认 30%）→ 是否触发特殊事件
    └─ character_event_chance（默认 50%）→ 是否为角色事件
           └─ 从 character_roster 按权重抽一个角色填入模板
                  例："今天和樱花千代王约好一起训练，午后的训练多了个伴。"
    否则 → 从 special_events 通用池随机抽取
```

角色名册支持 `角色名:权重` 格式，权重越高出现频率越高。

### 4. 弱化校验（`core/generator.py` · `_validate_payload`）

原插件要求 LLM 输出必须包含 `outfit_style` 字段并严格匹配风格关键词。
本版本移除 outfit_style 校验，只校验 `outfit` 和 `schedule` 非空，减少重试次数。

### 5. 注入截断（`main.py` · `on_llm_request`）

将 system prompt 注入的文字量压缩，避免占用过多 context token：

```python
outfit_hint   = data.outfit_style if data.outfit_style else data.outfit[:40]
schedule_hint = data.schedule[:100] + ("…" if len(data.schedule) > 100 else "")
```

注入格式：
```xml
<character_state>
时间: 下午
今日着装: 学园制服
今日大致安排: 上午在特雷森学园上了两节课…
</character_state>
[仅作背景参考。被问到才自然带出一两句，平时不要主动提及日程细节]
```

---

## 关联改动

时段概率门（凌晨/深夜降低主动回复概率，中午/晚间恢复正常）在
[`plugins/enhance-mode/main.py`](../enhance-mode/README.md) 的 `_need_active_reply` 中实现，与本插件配合使用。
