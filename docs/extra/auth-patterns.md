# 认证系统参考实现

> 参考文档 -- 按需使用，非模板默认功能

---

本文档提供完整的 JWT 认证实现，可直接复制到项目中使用。
前置条件: 已完成 [数据库集成](../database-patterns.md)（需要 MongoDB 或其他持久层存储用户数据）。

---

## 后端实现

### 1. 安装依赖

```bash
uv add pyjwt
```

### 2. 领域实体

```python
# src/app_name/contexts/auth/domain/entities.py
"""Authentication domain entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuthPrincipal:
    """Represents an authenticated identity."""

    user_id: str
    username: str
    roles: tuple[str, ...] = ("user",)
    created_at: datetime | None = None

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles
```

### 3. 端口定义

```python
# src/app_name/contexts/auth/application/ports/auth_port.py
"""Authentication port -- defines the contract for auth operations."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app_name.contexts.auth.domain.entities import AuthPrincipal


@runtime_checkable
class AuthPort(Protocol):
    """Port for authentication operations."""

    async def authenticate(self, username: str, password: str) -> AuthPrincipal | None:
        """Verify credentials and return the principal, or None if invalid."""
        ...

    async def find_by_id(self, user_id: str) -> AuthPrincipal | None:
        """Look up a principal by user ID."""
        ...
```

### 4. AuthService（完整业务逻辑）

```python
# src/app_name/contexts/auth/application/services/auth_service.py
"""JWT-based authentication service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from loguru import logger

from app_name.contexts.auth.domain.entities import AuthPrincipal


class AuthService:
    """Handles login, token issuance, refresh, and logout."""

    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_minutes: int = 30,
        refresh_token_days: int = 7,
        user_collection: Any = None,  # AsyncIOMotorCollection
    ) -> None:
        self._secret = secret_key
        self._algo = algorithm
        self._access_ttl = timedelta(minutes=access_token_minutes)
        self._refresh_ttl = timedelta(days=refresh_token_days)
        self._users = user_collection
        # In-memory revocation set (use Redis in production)
        self._revoked_tokens: set[str] = set()

    # -- public API -------------------------------------------------------

    async def login(self, username: str, password: str) -> dict[str, str] | None:
        """Authenticate and return access + refresh tokens, or None."""
        principal = await self._authenticate(username, password)
        if principal is None:
            return None
        return {
            "access_token": self._create_token(principal, self._access_ttl, "access"),
            "refresh_token": self._create_token(principal, self._refresh_ttl, "refresh"),
            "token_type": "bearer",
        }

    def resolve_access_token(self, token: str) -> AuthPrincipal | None:
        """Decode and validate an access token. Returns principal or None."""
        payload = self._decode_token(token)
        if payload is None or payload.get("type") != "access":
            return None
        if token in self._revoked_tokens:
            return None
        return AuthPrincipal(
            user_id=payload["sub"],
            username=payload["username"],
            roles=tuple(payload.get("roles", ["user"])),
        )

    def refresh_token(self, token: str) -> dict[str, str] | None:
        """Issue a new access token from a valid refresh token."""
        payload = self._decode_token(token)
        if payload is None or payload.get("type") != "refresh":
            return None
        if token in self._revoked_tokens:
            return None
        principal = AuthPrincipal(
            user_id=payload["sub"],
            username=payload["username"],
            roles=tuple(payload.get("roles", ["user"])),
        )
        return {
            "access_token": self._create_token(principal, self._access_ttl, "access"),
            "token_type": "bearer",
        }

    def logout(self, token: str) -> None:
        """Revoke a token (add to blacklist)."""
        self._revoked_tokens.add(token)
        logger.debug("Token revoked")

    # -- private ----------------------------------------------------------

    async def _authenticate(self, username: str, password: str) -> AuthPrincipal | None:
        """Look up user in DB and verify password.

        Replace this with your actual authentication logic (e.g., bcrypt).
        """
        if self._users is None:
            # Demo mode: accept any non-empty credentials
            logger.warning("No user collection configured -- using demo auth")
            return AuthPrincipal(user_id="demo", username=username)

        doc = await self._users.find_one({"username": username})
        if doc is None:
            return None

        # TODO: replace plain-text comparison with bcrypt / argon2
        if doc.get("password") != password:
            return None

        return AuthPrincipal(
            user_id=str(doc["_id"]),
            username=doc["username"],
            roles=tuple(doc.get("roles", ["user"])),
        )

    def _create_token(
        self, principal: AuthPrincipal, ttl: timedelta, token_type: str,
    ) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": principal.user_id,
            "username": principal.username,
            "roles": list(principal.roles),
            "type": token_type,
            "iat": now,
            "exp": now + ttl,
        }
        return jwt.encode(payload, self._secret, algorithm=self._algo)

    def _decode_token(self, token: str) -> dict | None:
        try:
            return jwt.decode(token, self._secret, algorithms=[self._algo])
        except jwt.PyJWTError:
            return None
```

### 5. API 路由

```python
# src/app_name/contexts/auth/interface/api/auth_router.py
"""Authentication API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app_name.contexts.auth.application.services.auth_service import AuthService
from app_name.contexts.auth.domain.entities import AuthPrincipal

router = APIRouter(prefix="/auth", tags=["auth"])


# --- Schemas ---


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    user_id: str
    username: str
    roles: list[str]


# --- Dependency ---


def _get_auth_service(request: Request) -> AuthService:
    return request.app.state.registry.auth_service


# --- Endpoints ---


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    auth: Annotated[AuthService, Depends(_get_auth_service)],
) -> TokenResponse:
    result = await auth.login(body.username, body.password)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return TokenResponse(**result)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    auth: Annotated[AuthService, Depends(_get_auth_service)],
) -> TokenResponse:
    result = auth.refresh_token(body.refresh_token)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return TokenResponse(**result)


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    principal: Annotated[AuthPrincipal, Depends(require_auth)],
) -> UserResponse:
    return UserResponse(
        user_id=principal.user_id,
        username=principal.username,
        roles=list(principal.roles),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    auth: Annotated[AuthService, Depends(_get_auth_service)],
) -> None:
    token = get_bearer_token(request)
    if token:
        auth.logout(token)
```

### 6. FastAPI 依赖（认证守卫）

```python
# 添加到 src/app_name/api/deps.py

from fastapi import Request, HTTPException, status
from app_name.contexts.auth.domain.entities import AuthPrincipal


def get_bearer_token(request: Request) -> str | None:
    """Extract Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


def require_auth(request: Request) -> AuthPrincipal:
    """FastAPI dependency: require a valid access token."""
    token = get_bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    registry = request.app.state.registry
    principal = registry.auth_service.resolve_access_token(token)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal
```

### 7. ErrorCode 扩展

```python
# 在 src/app_name/shared/exceptions/error_codes.py 添加:

class ErrorCode(IntEnum):
    # Common:  10000-10999
    VALIDATION_ERROR = 10000
    UNKNOWN_ERROR = 10099

    # Auth:    11000-11999
    AUTH_INVALID_CREDENTIALS = 11000
    AUTH_TOKEN_EXPIRED = 11001
    AUTH_TOKEN_INVALID = 11002
    AUTH_INSUFFICIENT_PERMISSIONS = 11003
    AUTH_USER_NOT_FOUND = 11004
```

### 8. config.yaml 添加 auth 段

```yaml
auth:
  secret_key: "app-name-change-me"      # 生产环境走 .env
  access_token_minutes: 720
  refresh_token_days: 30
```

`.env` 中覆盖:

```dotenv
AUTH__SECRET_KEY=your-production-secret-here
```

### 9. 注册到 v1 router

```python
# src/app_name/api/v1/router.py
from app_name.contexts.auth.interface.api.auth_router import router as auth_router

router.include_router(auth_router)
```

### 10. 注册到 service_factory + registry

**registry.py** -- 添加 `auth_service` 字段:

```python
@dataclass(slots=True)
class AppRegistry:
    settings: Settings
    event_bus: InProcessEventBus
    db: MongoDBManager
    auth_service: AuthService       # <-- 新增
```

**service_factory.py** -- 创建 AuthService:

```python
from app_name.contexts.auth.application.services.auth_service import AuthService
from app_name.database.mongo import get_manager

def build_registry(*, settings: Settings) -> AppRegistry:
    event_bus = InProcessEventBus()
    db = get_manager()

    auth_service = AuthService(
        secret_key=settings.auth.secret_key,
        algorithm=settings.auth.jwt_algorithm,
        access_token_minutes=settings.auth.access_token_minutes,
        refresh_token_days=settings.auth.refresh_token_days,
        user_collection=db.get_collection("users"),
    )

    return AppRegistry(
        settings=settings,
        event_bus=event_bus,
        db=db,
        auth_service=auth_service,
    )
```

---

## 前端集成

### 1. Token 管理工具

```typescript
// src/frontend/src/utils/auth.ts

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function isLoggedIn(): boolean {
  return getAccessToken() !== null;
}
```

### 2. Pinia Auth Store

```typescript
// src/frontend/src/stores/auth.ts

import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { loginApi, refreshApi, logoutApi, getMeApi } from "@/api/index";
import {
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
  isLoggedIn as checkLoggedIn,
} from "@/utils/auth";

interface UserInfo {
  user_id: string;
  username: string;
  roles: string[];
}

export const useAuthStore = defineStore("auth", () => {
  const user = ref<UserInfo | null>(null);
  const loggedIn = ref(checkLoggedIn());

  const isAdmin = computed(() => user.value?.roles.includes("admin") ?? false);

  async function login(username: string, password: string): Promise<void> {
    const { data } = await loginApi({ username, password });
    setTokens(data.access_token, data.refresh_token!);
    loggedIn.value = true;
    await fetchUser();
  }

  async function fetchUser(): Promise<void> {
    try {
      const { data } = await getMeApi();
      user.value = data;
    } catch {
      clearTokens();
      loggedIn.value = false;
      user.value = null;
    }
  }

  async function refresh(): Promise<boolean> {
    const token = getRefreshToken();
    if (!token) return false;
    try {
      const { data } = await refreshApi({ refresh_token: token });
      setTokens(data.access_token, getRefreshToken()!);
      return true;
    } catch {
      clearTokens();
      loggedIn.value = false;
      user.value = null;
      return false;
    }
  }

  async function logout(): Promise<void> {
    try {
      await logoutApi();
    } finally {
      clearTokens();
      loggedIn.value = false;
      user.value = null;
    }
  }

  return { user, loggedIn, isAdmin, login, fetchUser, refresh, logout };
});
```

### 3. API 拦截器（Bearer Token + 401 自动刷新）

```typescript
// src/frontend/src/api/index.ts -- 在 axios 实例创建后添加:

import { getAccessToken, getRefreshToken, setTokens, clearTokens } from "@/utils/auth";

// Request interceptor: attach Bearer token
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: auto-refresh on 401
let isRefreshing = false;
let pendingRequests: Array<(token: string) => void> = [];

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // Queue the request until refresh completes
        return new Promise((resolve) => {
          pendingRequests.push((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(api(originalRequest));
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        clearTokens();
        window.location.href = "/login";
        return Promise.reject(error);
      }

      try {
        const { data } = await api.post("/auth/refresh", {
          refresh_token: refreshToken,
        });
        setTokens(data.access_token, refreshToken);

        // Replay pending requests
        pendingRequests.forEach((cb) => cb(data.access_token));
        pendingRequests = [];

        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch {
        clearTokens();
        window.location.href = "/login";
        return Promise.reject(error);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  },
);

// --- Auth API functions ---

export function loginApi(data: { username: string; password: string }) {
  return api.post<{ access_token: string; refresh_token: string; token_type: string }>(
    "/auth/login",
    data,
  );
}

export function refreshApi(data: { refresh_token: string }) {
  return api.post<{ access_token: string; token_type: string }>("/auth/refresh", data);
}

export function getMeApi() {
  return api.get<{ user_id: string; username: string; roles: string[] }>("/auth/me");
}

export function logoutApi() {
  return api.post("/auth/logout");
}
```

### 4. Router Guard（路由认证守卫）

```typescript
// src/frontend/src/router/index.ts -- 添加 beforeEach guard:

import { isLoggedIn } from "@/utils/auth";

router.beforeEach((to, _from, next) => {
  if (to.meta.requiresAuth && !isLoggedIn()) {
    next({ name: "login", query: { redirect: to.fullPath } });
  } else if (to.name === "login" && isLoggedIn()) {
    next({ name: "home" });
  } else {
    next();
  }
});
```

### 5. Login.vue 登录页面

```vue
<!-- src/frontend/src/pages/Login.vue -->
<template>
  <div class="login-container">
    <a-card :style="{ width: '400px' }" title="登录">
      <a-form :model="form" @submit="handleLogin" layout="vertical">
        <a-form-item field="username" label="用户名" :rules="[{ required: true }]">
          <a-input v-model="form.username" placeholder="请输入用户名" />
        </a-form-item>
        <a-form-item field="password" label="密码" :rules="[{ required: true }]">
          <a-input-password v-model="form.password" placeholder="请输入密码" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" long :loading="loading">
            登录
          </a-button>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { Message } from "@arco-design/web-vue";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const loading = ref(false);

const form = reactive({
  username: "",
  password: "",
});

async function handleLogin() {
  loading.value = true;
  try {
    await authStore.login(form.username, form.password);
    Message.success("登录成功");
    const redirect = (route.query.redirect as string) || "/";
    router.push(redirect);
  } catch {
    Message.error("登录失败，请检查用户名和密码");
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: var(--color-bg-1);
}
</style>
```

---

## OAuth2 / 第三方登录（简要思路）

如需集成 Google、GitHub 等第三方登录:

1. **安装**: `uv add httpx` (用于后端 OAuth 回调中请求 token)
2. **流程**:
   - 前端重定向到 OAuth provider authorize URL
   - 用户授权后回调到后端 `/auth/callback/<provider>`
   - 后端用 authorization code 换取 access token
   - 后端查找或创建用户，签发本地 JWT
   - 重定向回前端并附带 JWT
3. **建议**: 使用 `authlib` 库简化 OAuth 流程 (`uv add authlib`)
4. **数据模型**: 在 `AuthPrincipal` 中添加 `provider: str` 和 `provider_id: str` 字段

---

## 集成步骤 Checklist

### 后端

- [ ] `uv add pyjwt`
- [ ] 创建 `contexts/auth/` 四层目录
- [ ] 实现 `domain/entities.py` -- AuthPrincipal
- [ ] 实现 `application/ports/auth_port.py` -- AuthPort Protocol
- [ ] 实现 `application/services/auth_service.py` -- 完整 JWT 逻辑
- [ ] 实现 `interface/api/auth_router.py` -- 4 个端点
- [ ] 在 `api/deps.py` 添加 `require_auth` 和 `get_bearer_token`
- [ ] 在 `error_codes.py` 添加 auth 范围 (11000-11999)
- [ ] 在 `config.yaml` 添加 auth 段
- [ ] 在 `.env` 添加 `AUTH__SECRET_KEY`
- [ ] 在 `AppRegistry` 添加 `auth_service` 字段
- [ ] 在 `service_factory.py` 创建并注入 AuthService
- [ ] 在 `api/v1/router.py` 注册 auth_router
- [ ] 需要认证的路由添加 `Depends(require_auth)`

### 前端

- [ ] 创建 `utils/auth.ts` -- token 管理
- [ ] 创建 `stores/auth.ts` -- Pinia store
- [ ] 在 `api/index.ts` 添加 Bearer 拦截器 + 401 刷新逻辑
- [ ] 在 router 添加 `beforeEach` 认证守卫
- [ ] 创建 `Login.vue` 页面
- [ ] 在 router 注册 `/login` 路由
- [ ] `uv run poe lint` 通过
- [ ] `uv run poe test` 通过
