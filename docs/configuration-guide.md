# 配置与日志管理指南

## 配置体系概览

项目使用 **Pydantic Settings V2** 管理配置，支持多源合并：

```
优先级 (高 → 低):
  环境变量  >  .env 文件  >  config.yaml  >  代码默认值
```

### 两个文件的分工

| 文件 | 用途 | 是否提交到 git |
|---|---|---|
| `config.yaml` | 非敏感默认值 (端口、日志、CORS) | **是** |
| `.env` | 敏感配置 (密钥、连接串、API key) | **否** (.gitignore) |

### 嵌套分隔符

环境变量用 `__` (双下划线) 表示嵌套层级：

```bash
# config.yaml 中:
logging:
  level: "INFO"

# 等价的环境变量:
LOGGING__LEVEL=DEBUG

# .env 文件中:
LOGGING__LEVEL=DEBUG
```

环境变量优先级最高，可以覆盖 config.yaml 中的任何值。

## config.yaml 完整字段说明

```yaml
# ---- 服务器 ----
server:
  host: "0.0.0.0"       # 监听地址
  port: 8665             # 监听端口
  reload: true           # 热重载 (开发环境 true, 生产环境 false)

# ---- CORS ----
cors:
  allow_origins:         # 允许的前端域名
    - "http://localhost:5173"
    - "http://localhost:8006"
  allow_credentials: true
  allow_methods: ["*"]
  allow_headers: ["*"]

# ---- 前端 ----
frontend:
  base_url: "http://localhost:5173"

# ---- 日志 ----
logging:
  level: "INFO"                # 控制台 + 通用日志级别
  log_dir: "logs"              # 日志目录
  retention_days: 30           # app.log 保留天数
  error_retention_days: 90     # error.log 保留天数
  rotation: "00:00"            # 轮转时间 (每天午夜)
  compression: "gz"            # 归档压缩格式

# ---- OpenAI (可选) ----
# openai:
#   api_key: ""                # 建议放 .env: OPENAI__API_KEY=sk-xxx
#   model: "gpt-4o-mini"
#   temperature: 0.0
```

## .env 文件说明

```bash
# 从 .env.example 复制:
cp .env.example .env

# 典型内容:
OPENAI__API_KEY=sk-xxxxxxxx

# 覆盖 config.yaml 中的值:
SERVER__PORT=9000
LOGGING__LEVEL=DEBUG

# 布尔值:
DEBUG=true
```

### 如何添加新配置

1. 在 `config.py` 中添加嵌套 BaseModel:

```python
class RedisConfig(BaseModel):
    url: str = "redis://localhost:6379"
    max_connections: int = 10
```

2. 在 `Settings` 类中注册:

```python
class Settings(BaseSettings):
    redis: RedisConfig = RedisConfig()
```

3. 在 `config.yaml` 中添加默认值:

```yaml
redis:
  url: "redis://localhost:6379"
  max_connections: 10
```

4. 敏感值放 `.env`:

```bash
REDIS__URL=redis://:password@prod-redis:6379
```

5. 代码中使用:

```python
from app_name.config import get_settings
settings = get_settings()
print(settings.redis.url)
```

## 日志管理

### 日志文件结构

```
logs/
├── app.log                  # 当天的通用日志 (DEBUG+)
├── app.log.2026-03-29.gz    # 昨天的归档
├── app.log.2026-03-28.gz
├── error.log                # 当天的错误日志 (ERROR+)
├── error.log.2026-03-29.gz
└── ...
```

### 在代码中打日志

```python
from loguru import logger

# 基本用法 — 直接 import 即可，无需任何配置
logger.debug("Processing item {}", item_id)
logger.info("User {} logged in", user_id)
logger.warning("Rate limit approaching: {}/100", count)
logger.error("Failed to connect: {}", err)

# 带结构化上下文
logger.bind(user_id=user_id, action="login").info("Auth event")

# 带异常堆栈
try:
    risky_operation()
except Exception:
    logger.exception("Operation failed")  # 自动附带 traceback
```

### 关联 request_id

结合 RequestContextMiddleware，可以在日志中追踪请求链路：

```python
from loguru import logger
from app_name.shared.middleware.request_context import get_request_id

logger.bind(request_id=get_request_id()).info("Processing order")
```

### 调整日志级别

**开发环境** — 在 config.yaml 中设为 DEBUG:

```yaml
logging:
  level: "DEBUG"
```

**生产环境** — 通过环境变量覆盖:

```bash
LOGGING__LEVEL=WARNING
```

**临时调试** — 不改文件，直接设环境变量:

```bash
LOGGING__LEVEL=DEBUG uv run poe api
```

### 生产环境建议

| 配置项 | 开发 | 生产 |
|---|---|---|
| `level` | DEBUG | INFO 或 WARNING |
| `retention_days` | 7 | 30 |
| `error_retention_days` | 30 | 90 |
| `rotation` | "00:00" | "00:00" 或 "500 MB" |
| `compression` | gz | gz |
| `server.reload` | true | **false** |

### 磁盘空间管理

Loguru 的 `retention` 参数自动清理过期日志。但仍建议:

1. **监控 logs/ 目录大小** — 添加磁盘告警 (参考 `docs/extra/observability.md`)
2. **按大小轮转** — 高流量场景改用 `rotation: "500 MB"` 替代按天轮转
3. **外部归档** — 如需长期保留，配合 logrotate 或 S3 上传脚本

### 自定义日志 handler

如需添加额外输出 (如 JSON 格式、发送到 Sentry 等)，在 `core/logging.py` 的 `setup_logging()` 中添加:

```python
# JSON 格式输出 (生产环境适用)
logger.add(
    log_path / "app.json.log",
    level="INFO",
    rotation=config.rotation,
    retention=f"{config.retention_days} days",
    serialize=True,  # Loguru 内置 JSON 序列化
)

# 发送到 Sentry
# import sentry_sdk
# sentry_sdk.init(dsn="...")
# logger.add(sentry_handler, level="ERROR")
```
