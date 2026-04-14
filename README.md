# 中大鸭鸭

中山大学校园 AI 陪伴「鸭鸭」：本地 SQLite 档案、抽卡人格、会话记忆与 CLI。

## 依赖

| 项 | 说明 |
|----|------|
| **Python** | **>= 3.9**（见根目录 [`pyproject.toml`](pyproject.toml) 中 `requires-python`，与 [`requirements.txt`](requirements.txt) 说明一致） |
| **PyPI 包** | 无；仅标准库（`sqlite3`、`urllib`、`json`、`difflib` 等） |

安装第三方包：**不需要**。若用 `uv` / `pip` 管理环境，可先 `pip install -r requirements.txt`（当前无包，仅锁定「无第三方依赖」的约定）。

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

`db.py` 中数据库访问通过 `db_execute()` 上下文管理：写入路径自动 `commit` / 异常 `rollback`，避免漏关连接或半提交。

## Skill 包（仓库根目录）

本仓库根目录按 Skill 包组织（未使用 `.cursor/skills/`）：

| 路径 | 说明 |
|------|------|
| `SKILL.md` | 主说明（触发条件、规则、调用方式） |
| `reference.md` | 语气速查、校区、数据库与核心文件 |
| `examples.md` | 示例对话 |
| `scripts/` | 可选辅助脚本（与 `duck.py` 编排配合时可放此处） |

将本目录作为技能源导入工具时，指向 **`SKILL.md`** 即可；需要细节时再读 `reference.md` / `examples.md`。

**作者**: Mars · **日期**: 2026-04-14
