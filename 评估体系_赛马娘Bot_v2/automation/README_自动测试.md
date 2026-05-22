# 赛马娘 Bot 自动测试 v2.2

这个目录用于跑 AstrBot WebUI 批量测试。第一版只测试 WebUI 对话接口，不自动给真实 QQ 发消息。

## 文件

- `test_cases_v2.json`：30 条基础回归题，加 7 条表情回归题和评分规则。
- `run_webui_batch.js`：在已登录 AstrBot WebUI 页面内运行的批量测试脚本。
- `../04_QQ最小烟测清单_v2.md`：真实 QQ 链路的少量人工烟测题。

## 运行方式

1. 打开并登录 AstrBot WebUI。
2. 确认存在人格配置 `阿尔丹v2.2`。脚本找不到该人格会停止，不会自动换人格。
3. 在浏览器控制台执行 `run_webui_batch.js` 的全部内容。
4. 先运行：

```js
await window.runUmamusumeBotRegression({ mode: "smoke" })
```

5. smoke 正常后运行：

```js
await window.runUmamusumeBotRegression({ mode: "full" })
```

如果要只测某几题，可以运行：

```js
await window.runUmamusumeBotRegression({
  caseIds: ["ARD-01", "ARD-02"],
  download: false,
  sendTimeoutMs: 120000
})
```

脚本会在浏览器中下载：

- `webui_results_<timestamp>.jsonl`
- `summary_<timestamp>.md`
- `webui_results_<timestamp>.csv`

同时结果会保存在页面内存 `window.__UMAMUSUME_LAST_TEST_RUN__`。这只用于当前页面，刷新后消失。

## Codex 接管说明

如果由 Codex 接管已登录 WebUI，理想流程是把 `run_webui_batch.js` 注入页面后读取 `window.__UMAMUSUME_LAST_TEST_RUN__`，再把结果保存到 `runs/<时间戳>/`。当前 Codex Browser 自动化可能会拦截 `javascript:` 页内注入；如果遇到这种限制，就先手动在浏览器控制台运行脚本，或后续改成带临时测试 token 的受控接口测试方案。

## 安全边界

- 不读取 `.env`。
- 不读取 NapCat token、API key、cookie。
- 不保存 WebUI token。脚本只在已登录页面内发同源请求。
- 不读取真实 QQ 聊天记录。
- 不修改 AstrBot 配置、人格、知识库或 Docker 配置。

## 结果怎么看

自动评分只是建议分，不是最终裁判：

- `2`：事实和语气大体可用。
- `1`：事实大体对，但语气、长度、边界或自我代入有问题。
- `0`：事实错、编造、客服腔、暴露规则、严重出戏。

优先看 `summary.md` 里的失败样例。常见归因：

- 事实缺失：优先改知识库。
- 像客服或规则泄露：优先改人格 prompt。
- 搜索类问题不稳定：检查搜索工具调用策略。
- 表情图没有出现但文字正常：优先用 `04_QQ最小烟测清单_v2.md` 在真实 QQ 链路确认，WebUI 批量测试只能稳定检查提示词是否愿意触发表情语义。
- QQ 里才出现的问题：用 `04_QQ最小烟测清单_v2.md` 单独确认，通常和 @、分段、表情、主动回复触发有关。
