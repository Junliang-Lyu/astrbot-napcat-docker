# custome_segment_reply 图片兼容补丁

## 背景

`astrbot_plugin_custome_segment_reply` 会对 LLM 回复做智能分段，
把长文本拆成多条消息逐条发送。

但 `meme_manager` 的回复链中包含图片组件（非 `Plain` 类型），
原始插件在处理时会清空 `result.chain`，导致图片被吞——只发出文字，图片丢失。

## 变更内容

在 `handle_segment_reply` 方法入口处，新增非文本组件检测：

```diff
  @event_filter.on_decorating_result()
  async def handle_segment_reply(self, event: AstrMessageEvent):
      result = event.get_result()
      if not result or not result.chain:
          return

+     if any(not isinstance(comp, Plain) for comp in result.chain):
+         logger.info("检测到图片或其他非文本组件，跳过自定义规则分段")
+         return
```

回复链中只要有任意一个非 `Plain` 组件（图片、表情等），直接跳过分段逻辑，
保持原始 chain 不变，图片正常发出。

## 适用版本

- `astrbot_plugin_custome_segment_reply` v1.0.0（LinJohn8）
- 文件路径（容器内）：`/AstrBot/data/plugins/astrbot_plugin_custome_segment_reply/main.py`

## 如何应用

将本补丁中的两行代码插入 `handle_segment_reply` 方法中
`if not result or not result.chain: return` 之后即可。
