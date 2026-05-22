# 自动测试运行记录

这里用于归档 WebUI 自动测试生成的运行结果。

推荐结构：

```text
runs/
  2026-05-15T18-30-00/
    webui_results.jsonl
    webui_results.csv
    summary.md
```

当前 `run_webui_batch.js` 在浏览器内运行时会先下载结果文件，并把本次结果临时放在页面变量 `window.__UMAMUSUME_LAST_TEST_RUN__`。如果由 Codex 接管已登录 WebUI 执行测试，可以把该变量导出的结果保存到这个目录。

不要把 WebUI token、cookie、`.env`、QQ 号、群号或完整真实聊天记录放进这里。
