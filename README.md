# 中大鸭鸭

中山大学校园 AI 陪伴「鸭鸭」：本地 SQLite 档案、抽卡人格、会话记忆与 CLI。

## 依赖

仅使用 Python 3 标准库（`sqlite3`、`urllib`、`json`、`difflib` 等），无需 `pip install`。

## 运行

```bash
export DUCK_USER_ID=你的用户ID
python3 duck.py help
```

可选环境变量：

- `DUCK_DB_PATH`：数据库文件路径（默认 `data/duck.db`）
- `DUCK_YAYAID_URL`：全校编号云函数地址
- `DUCK_YAYAID_TIMEOUT`：单次请求超时秒数（默认 `5`）
- `DUCK_YAYAID_RETRIES`：失败或返回无效编号时的重试次数（默认 `3`）
- `DUCK_YAYAID_BACKOFF`：重试间隔基数秒，线性递增（默认 `0.35`）

## 测试

```bash
python3 -m unittest discover -s tests -v
```

## 说明文档

智能体编排规范见仓库内 `SKILL.md`。

**作者**: Mars · **日期**: 2026-04-14
