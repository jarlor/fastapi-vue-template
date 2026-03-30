# SSE Streaming（Server-Sent Events）

> 参考文档 -- 按需使用，非模板默认功能

---

## 为什么需要

- AI 模型生成（LLM chat、摘要）通常需要数秒到数十秒
- 用户等待空白页面体验极差
- SSE 提供单向服务端推送，比 WebSocket 简单，浏览器原生支持自动重连

## 依赖

```bash
uv add sse-starlette
```

## 后端实现

### 基本 SSE Endpoint

```python
# src/app_name/api/v1/stream.py
import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/stream", tags=["stream"])


async def _generate_summary(article_id: str) -> AsyncGenerator[str, None]:
    """模拟 LLM 流式输出。实际使用时替换为 provider 的 stream 接口。"""
    chunks = ["正在分析文章...", "提取关键信息...", "生成摘要：", "这是一篇关于...", "[DONE]"]
    for chunk in chunks:
        yield json.dumps({"text": chunk, "article_id": article_id}, ensure_ascii=False)
        await asyncio.sleep(0.3)


@router.get("/summary/{article_id}")
async def stream_summary(article_id: str):
    return EventSourceResponse(
        _generate_summary(article_id),
        media_type="text/event-stream",
    )
```

### 带错误处理的完整版

```python
async def _stream_with_error_handling(task_id: str) -> AsyncGenerator[str, None]:
    try:
        # 发送开始事件
        yield json.dumps({"event": "start", "task_id": task_id})

        async for chunk in some_llm_stream(task_id):
            yield json.dumps({"event": "chunk", "data": chunk})

        # 发送完成事件
        yield json.dumps({"event": "done", "task_id": task_id})

    except Exception as e:
        # 发送错误事件，前端据此关闭连接
        yield json.dumps({"event": "error", "message": str(e)})


@router.get("/task/{task_id}")
async def stream_task(task_id: str):
    return EventSourceResponse(
        _stream_with_error_handling(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        },
    )
```

## 前端实现

### Vue Composable

```typescript
// src/frontend/src/composables/useSSE.ts
import { ref, onUnmounted } from 'vue'

export function useSSE(url: string) {
  const data = ref('')
  const chunks = ref<string[]>([])
  const isStreaming = ref(false)
  const error = ref<string | null>(null)

  let eventSource: EventSource | null = null

  function start() {
    if (eventSource) return

    isStreaming.value = true
    error.value = null
    chunks.value = []
    data.value = ''

    eventSource = new EventSource(url)

    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)

        if (parsed.event === 'done') {
          stop()
          return
        }
        if (parsed.event === 'error') {
          error.value = parsed.message
          stop()
          return
        }

        const text = parsed.text || parsed.data || ''
        chunks.value.push(text)
        data.value += text
      } catch {
        // 非 JSON 数据，直接追加
        data.value += event.data
      }
    }

    eventSource.onerror = () => {
      error.value = 'Connection lost'
      stop()
    }
  }

  function stop() {
    eventSource?.close()
    eventSource = null
    isStreaming.value = false
  }

  onUnmounted(stop)

  return { data, chunks, isStreaming, error, start, stop }
}
```

### 在组件中使用

```vue
<script setup lang="ts">
import { useSSE } from '@/composables/useSSE'

const { data, isStreaming, error, start } = useSSE('/api/v1/stream/summary/abc123')
</script>

<template>
  <button @click="start" :disabled="isStreaming">
    {{ isStreaming ? '生成中...' : '生成摘要' }}
  </button>
  <pre v-if="data">{{ data }}</pre>
  <p v-if="error" class="error">{{ error }}</p>
</template>
```

## 关键陷阱：BaseHTTPMiddleware 会破坏 SSE

Starlette 的 `BaseHTTPMiddleware` 会缓冲整个响应体后再发送，这直接破坏 SSE 的流式特性。

**错误做法**：

```python
# 这会导致 SSE 响应被缓冲，客户端收不到流式数据
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)  # 缓冲了整个响应！
        return response
```

**正确做法** -- 使用 Pure ASGI Middleware：

```python
# src/app_name/middleware/base.py（模板已提供此基类）
class ASGIMiddleware:
    """Pure ASGI middleware base，不缓冲响应，SSE/WebSocket 安全。"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # 在此添加逻辑（如 logging、timing）
            await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)
```

如果需要对 SSE 路由做特殊处理（如跳过 request body 读取），可以在 middleware 中检查路径：

```python
async def __call__(self, scope, receive, send):
    if scope["type"] == "http":
        path = scope.get("path", "")
        is_stream = path.startswith("/api/v1/stream/")
        # stream 路由跳过 body 解析等操作
        if not is_stream:
            # 常规 HTTP 的额外处理...
            pass
        await self.app(scope, receive, send)
    else:
        await self.app(scope, receive, send)
```

## 生产注意事项

- **Nginx**：添加 `X-Accel-Buffering: no` header，或在 nginx.conf 中设置 `proxy_buffering off`
- **超时**：SSE 长连接需要合理的超时配置，nginx 默认 60s `proxy_read_timeout` 可能不够
- **心跳**：长时间无数据时发送 comment（`:keepalive\n\n`）防止代理层断开连接
- **并发限制**：浏览器对同一域名的 SSE 连接有限制（HTTP/1.1 为 6 个），使用 HTTP/2 可解除
