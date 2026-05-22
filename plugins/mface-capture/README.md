# QQ 表情本地采集辅助

> 插件本体维护在独立仓库：[Junliang-Lyu/astrbot_plugin_mface_capture](https://github.com/Junliang-Lyu/astrbot_plugin_mface_capture)
> 本目录为该仓库的快照，附带配套管理脚本。

这个插件用于在 AstrBot 中临时采集 QQ/NapCat 收到的 `mface` / `image` 表情消息段，并可把图片或 GIF 保存到本地。它适合作为 `meme_manager` 的采集辅助：本插件负责采集和落盘，`meme_manager` 负责后续管理与发送。

当前版本是初版辅助工具，主要面向 QQ/NapCat；其它 AstrBot 平台如果能在原始消息里提供 `image.url` 或 `file_url`，也可能保存普通图片。

## 保存位置

采集结果保存在插件自己的本地数据目录：

```text
data/plugin_data/astrbot_plugin_mface_capture/mface_captures.jsonl
```

实际路径也可以在 QQ 里发送：

```text
/表情采集 状态
```

## 采集内容

插件记录 `mface` 和 `image` 消息段的脱敏元数据，例如：

- `emoji_id`
- `emoji_package_id`
- `key`
- `summary`
- 图片文件名
- URL 域名和路径尾部

插件不会保存聊天正文、群号、QQ 号、昵称或完整消息。图片 URL 的查询参数会被丢弃，避免保存临时鉴权参数。

开启 `save_images` 后，插件会在采集时把图片/GIF 保存到：

```text
data/plugin_data/astrbot_plugin_mface_capture/images/<标签>/
```

JSONL 记录里只写入 `local_file` 本地相对路径，不写入完整 URL。

## 命令

```text
/表情采集 状态
/表情采集 开启
/表情采集 生气
/表情采集 关闭
```

`开启` 会启动一轮临时采集，默认 120 秒后自动关闭。采集会绑定到发送命令的当前会话，其它聊天里的图片不会被写入本轮标签目录。采集期间如果当前会话收到可记录的 `mface/image` 消息段，插件会调用 `event.stop_event()` 阻止后续 LLM 回复，避免机器人逐个评价正在采集的表情。

`/表情采集 生气` 这类写法会把 `生气` 当作本轮采集备注并直接开启采集，避免被当普通聊天交给 LLM。

`关闭` 会立即结束本轮采集并恢复正常回复。

如果需要调整自动关闭时间，可以修改配置项 `auto_stop_seconds`。设为 `0` 表示不自动关闭。

## 和 meme_manager 配合

采集完成后，可以把本插件保存的图片复制到 `meme_manager` 的本地分类目录：

```text
data/plugin_data/meme_manager/memes/<category>/
```

推荐标签映射：

```text
开心 -> happy
生气 -> angry
害羞 -> shy
疑惑 -> confused
伤心 -> sad
赞同 -> like
感谢 -> thanks
```

## 配套脚本

`generate_mface_label_manifest.py` — 把 `mface_captures.jsonl` 转换为带标签的 CSV，
用于批量核查采集结果和手动补标签。

```sh
python generate_mface_label_manifest.py
# 输出：data/plugin_data/astrbot_plugin_mface_capture/mface_label_manifest.csv
```

`test_mface_capture.py` — `capture.py` 的单元测试，覆盖脱敏逻辑、标签绑定、
下载路径生成、JSONL 写入和 `CaptureState` 的自动过期与 source_origin 绑定。

```sh
python -m pytest test_mface_capture.py -v
```

---

## 隐私和发布说明

- 插件代码不会上传或同步图片，图片只保存在本地 AstrBot 数据目录。
- 不建议把采集到的商城表情、个人表情、聊天日志或 `plugin_data` 一起提交到 GitHub。
- JSONL 记录会脱敏：不保存聊天正文、群号、QQ 号、昵称，也不保存完整图片 URL 查询参数。
- 如果要开源插件，请只提交插件代码、README、配置 schema 和测试文件。
