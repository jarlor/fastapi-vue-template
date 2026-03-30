# Observability：Metrics + Alerting

> 参考文档 -- 按需使用，非模板默认功能

---

## 为什么需要

- 了解 API 真实性能表现（P50/P95/P99 延迟）
- LLM 调用的 token 消耗追踪与预算控制
- 异常情况自动告警（错误率飙升、响应超时）
- 排查问题时有 request/response 日志可查

## Metrics 采集：Background Thread 批量写入

避免在请求路径中同步写数据库，使用后台线程批量刷写：

```python
# src/app_name/observability/metrics.py
import asyncio
import time
from collections import deque
from dataclasses import dataclass, field

from motor.motor_asyncio import AsyncIOMotorCollection


@dataclass(frozen=True)
class RequestMetric:
    route: str
    method: str
    status_code: int
    duration_ms: float
    timestamp: float
    token_usage: dict[str, int] = field(default_factory=dict)
    error: str | None = None


class MetricsCollector:
    """非阻塞 metrics 采集器，后台批量写入 MongoDB。"""

    def __init__(self, collection: AsyncIOMotorCollection, flush_interval: float = 5.0, batch_size: int = 100):
        self._collection = collection
        self._flush_interval = flush_interval
        self._batch_size = batch_size
        self._buffer: deque[RequestMetric] = deque(maxlen=10000)
        self._task: asyncio.Task | None = None

    def record(self, metric: RequestMetric) -> None:
        """非阻塞记录，O(1) 操作。"""
        self._buffer.append(metric)

    async def start(self) -> None:
        self._task = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            await self._flush_remaining()

    async def _flush_loop(self) -> None:
        while True:
            await asyncio.sleep(self._flush_interval)
            await self._flush_remaining()

    async def _flush_remaining(self) -> None:
        if not self._buffer:
            return
        batch = []
        while self._buffer and len(batch) < self._batch_size:
            metric = self._buffer.popleft()
            batch.append({
                "route": metric.route,
                "method": metric.method,
                "status_code": metric.status_code,
                "duration_ms": metric.duration_ms,
                "timestamp": metric.timestamp,
                "token_usage": metric.token_usage,
                "error": metric.error,
            })
        if batch:
            await self._collection.insert_many(batch)
```

### 在 Middleware 中使用

```python
# src/app_name/middleware/metrics.py
import time

from app_name.observability.metrics import MetricsCollector, RequestMetric


class MetricsMiddleware:
    """Pure ASGI middleware，记录每个请求的性能指标。"""

    def __init__(self, app, collector: MetricsCollector):
        self.app = app
        self.collector = collector

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_code = 500  # default if send never called

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = (time.perf_counter() - start) * 1000
            self.collector.record(RequestMetric(
                route=scope.get("path", ""),
                method=scope.get("method", ""),
                status_code=status_code,
                duration_ms=round(duration, 2),
                timestamp=time.time(),
            ))
```

## Alerting：Webhook 通知

### 告警器（支持去重 + 限频）

```python
# src/app_name/observability/alerting.py
import time

import httpx


class WebhookAlerter:
    """Webhook 告警，内置去重和限频。"""

    def __init__(
        self,
        webhook_url: str,
        *,
        min_interval: float = 300.0,  # 同类告警最小间隔（秒）
        platform: str = "feishu",     # feishu | dingtalk | slack
    ):
        self._webhook_url = webhook_url
        self._min_interval = min_interval
        self._platform = platform
        self._last_sent: dict[str, float] = {}

    async def alert(self, key: str, title: str, content: str) -> bool:
        """发送告警。key 用于去重，相同 key 在 min_interval 内只发一次。"""
        now = time.time()
        if key in self._last_sent and (now - self._last_sent[key]) < self._min_interval:
            return False  # 限频，跳过

        payload = self._build_payload(title, content)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self._webhook_url, json=payload)
            resp.raise_for_status()

        self._last_sent[key] = now
        return True

    def _build_payload(self, title: str, content: str) -> dict:
        if self._platform == "feishu":
            return {
                "msg_type": "interactive",
                "card": {
                    "header": {"title": {"tag": "plain_text", "content": title}},
                    "elements": [{"tag": "markdown", "content": content}],
                },
            }
        if self._platform == "dingtalk":
            return {
                "msgtype": "markdown",
                "markdown": {"title": title, "text": f"## {title}\n{content}"},
            }
        # slack
        return {
            "text": f"*{title}*\n{content}",
        }
```

## Request/Response Logging（敏感字段脱敏）

```python
# src/app_name/observability/sanitize.py
import re

SENSITIVE_PATTERNS = re.compile(
    r"(password|token|secret|api_key|authorization|cookie)",
    re.IGNORECASE,
)

MASK = "***"


def sanitize_dict(data: dict, depth: int = 0) -> dict:
    """递归脱敏字典中的敏感字段。"""
    if depth > 5:
        return {"_truncated": True}

    result = {}
    for key, value in data.items():
        if SENSITIVE_PATTERNS.search(key):
            result[key] = MASK
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value, depth + 1)
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            result[key] = [sanitize_dict(item, depth + 1) for item in value]
        else:
            result[key] = value
    return result
```

使用示例：

```python
from loguru import logger
from app_name.observability.sanitize import sanitize_dict

# 记录请求时自动脱敏
logger.info("Request body: {}", sanitize_dict(request_body))
# {"username": "alice", "password": "***", "token": "***"}
```

## 集成到模板的方式

1. 在 `lifespan` 中初始化 `MetricsCollector`，传入 `metrics` collection
2. 将 `MetricsMiddleware` 添加到 app（Pure ASGI，不影响 SSE）
3. 在需要告警的地方注入 `WebhookAlerter`（如 pipeline 失败、错误率阈值）
4. Request logging 在现有 logging middleware 中添加 `sanitize_dict` 调用

```python
# main.py lifespan 示例片段
async def lifespan(app):
    collector = MetricsCollector(db["metrics"])
    await collector.start()
    app.state.metrics = collector

    yield

    await collector.stop()
```
