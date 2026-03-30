# WebSocket Patterns

> 参考文档 -- 按需使用，非模板默认功能

---

## 为什么需要

- 双向实时通信（聊天、协作编辑、实时状态同步）
- SSE 只能服务端推送，WebSocket 支持客户端也主动发消息
- 适合需要高频双向交互的场景

## Base WebSocket Handler

```python
# src/app_name/ws/base.py
import asyncio
import json
from abc import ABC, abstractmethod

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger


class BaseWSHandler(ABC):
    """WebSocket handler 基类，封装连接管理、心跳、错误处理。"""

    HEARTBEAT_INTERVAL = 30  # 秒

    async def accept(self, websocket: WebSocket) -> None:
        await websocket.accept()
        logger.info("WS connected: {}", websocket.client)

        heartbeat_task = asyncio.create_task(self._heartbeat(websocket))
        try:
            await self.on_connect(websocket)
            while True:
                raw = await websocket.receive_text()
                message = json.loads(raw)
                await self.on_message(websocket, message)
        except WebSocketDisconnect:
            logger.info("WS disconnected: {}", websocket.client)
        except json.JSONDecodeError:
            await self._send_error(websocket, "Invalid JSON")
        except Exception as e:
            logger.error("WS error: {}", e)
            await self._send_error(websocket, "Internal error")
        finally:
            heartbeat_task.cancel()
            await self.on_disconnect(websocket)

    @abstractmethod
    async def on_connect(self, websocket: WebSocket) -> None:
        """连接建立后的初始化逻辑。"""

    @abstractmethod
    async def on_message(self, websocket: WebSocket, message: dict) -> None:
        """处理收到的消息。"""

    async def on_disconnect(self, websocket: WebSocket) -> None:
        """连接断开后的清理逻辑，可选 override。"""

    async def _heartbeat(self, websocket: WebSocket) -> None:
        """定期发送 ping，检测死连接。"""
        while True:
            await asyncio.sleep(self.HEARTBEAT_INTERVAL)
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break

    async def _send_error(self, websocket: WebSocket, message: str) -> None:
        try:
            await websocket.send_json({"type": "error", "message": message})
        except Exception:
            pass
```

### 具体 Handler 示例

```python
# src/app_name/ws/notification.py
from fastapi import WebSocket

from .base import BaseWSHandler


class NotificationHandler(BaseWSHandler):
    """实时通知推送。"""

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}

    async def on_connect(self, websocket: WebSocket) -> None:
        user_id = websocket.state.user_id  # 由 auth 中间件设置
        self._connections[user_id] = websocket

    async def on_message(self, websocket: WebSocket, message: dict) -> None:
        if message.get("type") == "pong":
            return  # 心跳响应，忽略
        # 处理其他消息类型...

    async def on_disconnect(self, websocket: WebSocket) -> None:
        user_id = getattr(websocket.state, "user_id", None)
        if user_id:
            self._connections.pop(user_id, None)

    async def broadcast(self, user_id: str, payload: dict) -> None:
        ws = self._connections.get(user_id)
        if ws:
            await ws.send_json({"type": "notification", "data": payload})
```

## 认证：Query Param Token

WebSocket 不支持自定义 HTTP header（浏览器限制），通常用 query parameter 传 token：

```python
# src/app_name/api/v1/ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app_name.auth.jwt import verify_token
from app_name.ws.notification import NotificationHandler

router = APIRouter()
handler = NotificationHandler()


@router.websocket("/ws/notifications")
async def ws_notifications(
    websocket: WebSocket,
    token: str = Query(...),
):
    # 验证 token
    payload = verify_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # 将用户信息附加到 websocket state
    websocket.state.user_id = payload["sub"]

    await handler.accept(websocket)
```

**安全注意**：
- Token 应短期有效（如 5 分钟），专门为 WS 连接签发
- 不要复用长期有效的 access token 放在 URL 中（会出现在 server log）

## 前端：Vue Composable（自动重连）

```typescript
// src/frontend/src/composables/useWebSocket.ts
import { ref, onUnmounted } from 'vue'

interface UseWebSocketOptions {
  reconnectInterval?: number  // 重连间隔，毫秒
  maxRetries?: number
  onMessage?: (data: any) => void
}

export function useWebSocket(url: string, options: UseWebSocketOptions = {}) {
  const {
    reconnectInterval = 3000,
    maxRetries = 10,
    onMessage,
  } = options

  const isConnected = ref(false)
  const retryCount = ref(0)

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  function connect() {
    if (ws?.readyState === WebSocket.OPEN) return

    ws = new WebSocket(url)

    ws.onopen = () => {
      isConnected.value = true
      retryCount.value = 0
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      // 自动响应心跳
      if (data.type === 'ping') {
        ws?.send(JSON.stringify({ type: 'pong' }))
        return
      }

      onMessage?.(data)
    }

    ws.onclose = () => {
      isConnected.value = false
      scheduleReconnect()
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function scheduleReconnect() {
    if (retryCount.value >= maxRetries) return

    // 指数退避：3s, 6s, 12s, 24s...（上限 30s）
    const delay = Math.min(
      reconnectInterval * Math.pow(2, retryCount.value),
      30000,
    )
    reconnectTimer = setTimeout(() => {
      retryCount.value++
      connect()
    }, delay)
  }

  function send(data: Record<string, unknown>) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data))
    }
  }

  function disconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    retryCount.value = maxRetries  // 阻止自动重连
    ws?.close()
    ws = null
    isConnected.value = false
  }

  // 自动连接
  connect()

  onUnmounted(disconnect)

  return { isConnected, retryCount, send, disconnect, connect }
}
```

### 组件使用

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'

const notifications = ref<any[]>([])
const token = 'short-lived-ws-token'

const { isConnected } = useWebSocket(
  `ws://localhost:8000/ws/notifications?token=${token}`,
  {
    onMessage(data) {
      if (data.type === 'notification') {
        notifications.value.unshift(data.data)
      }
    },
  },
)
</script>
```

## Middleware 中处理 WebSocket

模板的 Pure ASGI middleware 天然支持 WebSocket，只需注意区分 scope type：

```python
class MyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            # WS 特有逻辑（如连接计数、rate limiting）
            await self.app(scope, receive, send)
        elif scope["type"] == "http":
            # HTTP 逻辑
            await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)
```

**关键点**：WebSocket 的 `receive` 和 `send` 与 HTTP 不同：
- `receive` 返回 `websocket.connect`、`websocket.receive`、`websocket.disconnect`
- `send` 接受 `websocket.accept`、`websocket.send`、`websocket.close`
- 不要在 WS scope 中使用 HTTP 的 response 逻辑
