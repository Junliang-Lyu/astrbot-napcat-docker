# Changelog

## v0.2.2

- Bind capture sessions to the chat where `/表情采集` was started.
- Save captured images/GIFs into `images/<label>/` under the plugin data directory.
- Record only sanitized metadata in JSONL.
- Stop event propagation for captured image messages during active capture.
- Add labeled capture commands such as `/表情采集 开心`.
