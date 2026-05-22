# Smoke 尝试记录

时间：2026-05-15

## 结果

API runner 已生成并通过本地语法检查，但本次没有完成正式 WebUI API smoke。

原因：Codex Browser 自动化拒绝 `javascript:` 页内注入，无法把 `run_webui_batch.js` 注入到已登录 AstrBot 页面执行。直接 shell 调用 AstrBot API 又会返回 401，因为本轮不读取或保存 WebUI token。

## 已做的最低限度检查

- `test_cases_v2.json` 可解析，包含 30 条测试题。
- `run_webui_batch.js` 通过 `node --check`。
- 常见密钥形态扫描未命中。
- 通过 WebUI ChatUI 做了 1 条非正式 UI smoke：`目白阿尔丹是谁？`

该 UI smoke 不是正式评分结果，因为无法在 UI 层确认它一定使用 `阿尔丹v2.2` 并按计划每题新建独立 session。

## 边界

- 未读取 `.env`、token、cookie、API key。
- 未触碰真实 QQ 群聊或私聊。
- 未修改 AstrBot 配置、人格、知识库或 Docker 配置。
