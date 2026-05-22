# enhance-mode（阿尔丹项目定制版）

基于 [astrbot_plugin_astrbot_enhance_mode](https://github.com/Soulter/astrbot_plugin_astrbot_enhance_mode)（作者：阿汐）的修改版本，
针对角色扮演 QQ 机器人的防骚扰场景增加了审核层和渐进式封禁体系。

---

## 本版本的改动

### 1. 骚扰审核层（`main.py`）

在消息进入角色 LLM 之前新增两个方法：

**`_moderate_message(text, provider)`**

独立调用 LLM（脱离角色设定）对消息做意图分类，返回：
- `安全` — 放行
- `性骚扰` — 含谐音、隐晦措辞、双关语
- `辱骂` — 含人身攻击、脏话

**`guard_harassment`（事件钩子，priority=9998）**

仅针对群聊中 @ 机器人的消息，管理员消息豁免。

```
安全        → 放行，正常交给角色 LLM
辱骂 + 首次 → 记录警告（offense+1，1 秒失效），放行；角色按 prompt 给冷回应
辱骂 + 再犯 → 自动封禁（offense 升档），停止消息传递
性骚扰      → 直接封禁（无论第几次），停止消息传递
```

调用顺序：`guard_banned_user (9999) → guard_harassment (9998) → 正常 LLM 处理`

---

### 2. 渐进式封禁体系（`ban_control.py`，新增文件）

新字段：
- `offense_count`：前科次数，跨会话 SQLite 持久化
- `last_offense_at`：最近一次违规时间戳

**14 天衰减规则**：距上次违规超过 14 天，下次封禁从第 1 次重新计算。

**自动升档逻辑：**

| offense_count | 封禁时长 |
|---|---|
| 1 | 30 分钟 |
| 2 | 1 小时 |
| 3 及以上 | 1 天 |

新增：
- `offense_to_duration(count)` — 根据前科次数返回封禁秒数
- `BanResult` dataclass — 携带 `expires_at`、`offense_count`、`duration_seconds`
- `get_offense_record(scope_id, user_id)` — 查询前科（含衰减判断）

---

### 3. `enhance_ban_user` 工具改造（`main.py`）

- **移除 `duration` 参数**，时长完全由 `offense_count` 自动决定
- LLM 调用时无需判断时长，系统自动升档
- 返回值包含前科次数和实际时长，供角色在回复中说明

### 4. 新增 `enhance_get_offense_count` 工具（`main.py`）

LLM 可主动查询某用户的前科记录，便于在对话中给出准确说明。

### 5. 管理员手动封禁命令（`main.py`）

```
enhance ban @用户     # 手动封禁，自动按前科升档，返回封禁详情
enhance unban @用户   # 手动解封
```

---

## 设计决策

**为什么不用概率式触发封禁**
计数器 + 固定升档对攻击者和管理员都透明，可预测，便于申诉。

**为什么政治敏感话题不触发封禁**
单次提问不等于恶意骚扰，角色拒绝回答即可；扩展审核分类会显著提高误判率。

**审核层的局限**
- 依赖 LLM 判断，极度隐晦的谐音仍可能漏判
- 增加约 0.5–1 秒 latency；调用失败时 fail-open（自动放行）

---

## 原插件

- 原始仓库：[astrbot_plugin_astrbot_enhance_mode](https://github.com/Soulter/astrbot_plugin_astrbot_enhance_mode)
- 原作者：阿汐
- 本版本新增 `ban_control.py`，并修改 `main.py` 中的封禁工具和消息处理钩子，其余文件与原版相同
