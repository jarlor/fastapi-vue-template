# CLAUDE.md — Project Instructions for Claude Code

## What This Is

FastAPI + Vue 3 / Arco Design / Vite 全栈项目模板。
使用 `app_name` 作为占位符包名，运行 `uv run poe init` 自动从目录名推导项目名并完成初始化。

## Tech Stack

- **Backend**: FastAPI, Pydantic Settings V2, Loguru
- **Frontend**: Vue 3 (Composition API), Arco Design Web Vue, Vite, Pinia
- **Python**: >=3.13, managed by `uv`, tasks via `poethepoet`
- **Database**: 按需集成 (见 [docs/database-patterns.md](docs/database-patterns.md))

## Key File Locations

| File / Dir | Purpose |
|---|---|
| `src/app_name/main.py` | FastAPI app factory + lifespan (启动入口) |
| `src/app_name/run_api.py` | Uvicorn runner (`factory=True`) |
| `src/app_name/config.py` | Pydantic Settings V2 + YAML 多源配置 + 延迟单例 |
| `src/app_name/core/registry.py` | AppRegistry — DI 容器 (dataclass) |
| `src/app_name/core/service_factory.py` | build_registry() + partial() 工厂 |
| `src/app_name/core/logging.py` | Loguru 日志初始化 (startup 时调用一次) |
| `src/app_name/api/deps.py` | FastAPI Depends 依赖提供者 (registry) |
| `src/app_name/api/v1/` | 版本化 API 路由 |
| `src/app_name/contexts/` | 限界上下文 (业务模块) |
| `src/app_name/contexts/_template/` | 空白上下文模板 (四层目录 + README) |
| `src/app_name/shared/events/bus.py` | 进程内异步事件总线 |
| `src/app_name/models/` | 共享领域模型 |
| `src/frontend/` | Vue 3 SPA (Vite + Arco Design) |
| `config.yaml` | 非敏感默认配置 |
| `.env` / `.env.example` | 敏感配置 (永不提交) |

## Architecture — DI Wiring Flow (核心脉络)

这是整个架构的核心链路，新增功能时必须理解这条线：

```
main.py lifespan
  │
  ├─ 1. get_settings()          ← config.py (延迟单例, 合并 env + yaml)
  ├─ 2. setup_logging()         ← core/logging.py
  ├─ 3. build_registry()        ← core/service_factory.py
  │     ├─ 创建 InProcessEventBus
  │     ├─ 用 partial() 包装其他服务工厂
  │     └─ 返回 AppRegistry (存入 app.state.registry)
  ├─ 4. 事件订阅注册
  └─ 5. yield → 应用运行 → 清理

请求时:
  router handler
    → Depends(get_xxx_service)      ← api/deps.py
      → _get_registry(request)      ← 从 app.state.registry 取
        → registry.xxx_factory()    ← 返回服务实例
```

当前模板还额外约束两点：

- `create_app()` 可接收显式 `Settings`，测试和脚本优先用这个方式注入配置，不要依赖 import 副作用。
- 模板默认只保留一个 `/api/v1` 前缀；是否需要公开/内部拆分，由具体项目自行决定。

## Module Decoupling Rules

- 限界上下文在 `src/app_name/contexts/<name>/` 下
- 每个上下文四层: `domain/` → `application/` → `infrastructure/` → `interface/`
- **上下文之间禁止互相 import**
- 跨上下文通信: Events (fire-and-forget) 或 Ports (同步查询)
- 只有 `application/` 层编排 domain 和 infrastructure

## Commands

```bash
uv run poe api        # 启动后端 (port 8665)
uv run poe frontend   # 启动前端 (port 8006)
uv run poe lint       # Ruff 检查
uv run poe fmt        # Ruff 格式化
uv run poe test       # pytest + coverage
```

## Config

- `.env` — 敏感配置 (数据库连接串、API 密钥等)
- `config.yaml` — 非敏感默认值 (端口, CORS, 日志目录)
- 嵌套分隔符: `__` (如 `MONGODB__URL` 对应 `mongodb.url`)
- Pydantic Settings 合并: env > .env > config.yaml

## Development Standards (docs/)

开发前**必读**以下文档，按顺序：

| 顺序 | 文档 | 核心内容 |
|---|---|---|
| 1 | [architecture.md](docs/architecture.md) | 四层架构、DI、事件总线 — **先理解全局** |
| 2 | [coding-standards.md](docs/coding-standards.md) | 命名规范、文件约束、不可变性 |
| 3 | [module-development.md](docs/module-development.md) | 新建上下文完整流程 + checklist |
| 4 | [context-contracts.md](docs/context-contracts.md) | 上下文间通信契约 |
| 5 | [api-conventions.md](docs/api-conventions.md) | REST API 设计约定 |
| 6 | [frontend-standards.md](docs/frontend-standards.md) | Vue3 组件/状态/API 规范 |
| 7 | [security-standards.md](docs/security-standards.md) | 11 条安全规则 + pre-commit checklist |
| 8 | [testing-guide.md](docs/testing-guide.md) | TDD 流程、pytest 模式 |
| 9 | [configuration-guide.md](docs/configuration-guide.md) | 配置体系 + 日志管理 (.env / yaml / 日志轮转) |
| 10 | [database-patterns.md](docs/database-patterns.md) | 数据库集成指南 (MongoDB / PostgreSQL) |

## How to Add a New Feature (端到端流程)

详见 [docs/walkthrough.md](docs/walkthrough.md) — 以创建一个完整的 `catalog` 上下文为例，
演示从领域模型到 API 到前端页面的完整流程。

## Reference Implementations

参考文档在 `docs/extra/` 目录下，按需复制到项目中:

- [docs/extra/auth-patterns.md](docs/extra/auth-patterns.md) — JWT 认证完整实现 (后端 + 前端)
- [docs/extra/sse-streaming.md](docs/extra/sse-streaming.md) — SSE 流式推送
- [docs/extra/websocket-patterns.md](docs/extra/websocket-patterns.md) — WebSocket 双向通信
- [docs/extra/llm-provider-router.md](docs/extra/llm-provider-router.md) — LLM 提供商路由
- [docs/extra/observability.md](docs/extra/observability.md) — 可观测性

## Critical Rules

1. **不要在模块顶层产生副作用** — 不要在 import 时创建 Settings()、DB 连接、文件 I/O
2. **不要跨上下文 import** — 用事件总线或 Ports
3. **不要在路由中写业务逻辑** — 路由只负责 HTTP 协议转换，逻辑在 Service 中
4. **不要硬编码密钥** — 走 .env 或环境变量
5. **不要跳过类型标注** — 所有公开函数必须有 type hints
6. **不要直接在组件中调 axios** — 走 `src/api/index.ts` 封装层
7. **不要恢复模块级 app 单例** — 保持 app factory 形式，避免 import 时读取配置 / 文件
