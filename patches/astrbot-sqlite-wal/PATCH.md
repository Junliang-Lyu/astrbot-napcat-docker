# AstrBot SQLite WAL 模式优化补丁

## 背景

AstrBot 默认使用 SQLite，在消息并发处理时，默认的 DELETE journal 模式偶发
`database is locked` 错误，导致对话响应失败。

## 变更内容

在 `astrbot/core/db/sqlite.py` 的 `initialize()` 方法中，建表完成后追加以下 PRAGMA：

```diff
  async with self.engine.begin() as conn:
      await conn.run_sync(SQLModel.metadata.create_all)
+     await conn.execute(text("PRAGMA journal_mode=WAL"))
+     await conn.execute(text("PRAGMA synchronous=NORMAL"))
+     await conn.execute(text("PRAGMA cache_size=20000"))
+     await conn.execute(text("PRAGMA temp_store=MEMORY"))
+     await conn.execute(text("PRAGMA mmap_size=134217728"))
+     await conn.execute(text("PRAGMA optimize"))
      await self._ensure_persona_folder_columns(conn)
```

| PRAGMA | 说明 |
|--------|------|
| `journal_mode=WAL` | WAL 模式：读写并发，互不阻塞 |
| `synchronous=NORMAL` | 降低 fsync 频率，提升写入性能 |
| `cache_size=20000` | 约 20 MB 页缓存（默认 ~2 MB） |
| `temp_store=MEMORY` | 临时表放内存，避免磁盘 I/O |
| `mmap_size=134217728` | 128 MB mmap，大表扫描更快 |
| `optimize` | 收集统计信息，优化查询计划 |

## 适用版本

- AstrBot 镜像：`soulter/astrbot:latest`（2026-05-15 快照）
- 文件路径（容器内）：`/AstrBot/astrbot/core/db/sqlite.py`

## 如何应用

将本目录下的 `sqlite.py` 挂载覆盖容器内的原始文件：

```yaml
# 在 docker-compose.yml 的 astrbot 服务 volumes 下追加
volumes:
  - ./data:/AstrBot/data
  - ./patches/astrbot-sqlite-wal/sqlite.py:/AstrBot/astrbot/core/db/sqlite.py
```

修改后重启：

```sh
docker compose restart astrbot
```

## 说明

`sqlite.py` 基于 [AstrBot](https://github.com/Soulter/AstrBot)（MIT License）修改，
原始版权归 AstrBot 项目贡献者所有。本补丁仅追加 PRAGMA 初始化配置，不修改业务逻辑。
