# Multi-LLM Provider 路由模式

> 参考文档 -- 按需使用，非模板默认功能

---

## 为什么需要

- 不同任务适合不同模型（GPT-4o 擅长推理，Gemini Flash 便宜快速，本地模型保隐私）
- 供应商故障时自动 fallback
- 无需改代码即可切换 provider

## 设计模式：Config-Driven Provider Factory

### 配置结构

```yaml
# config.yaml
llm:
  default_provider: openai
  providers:
    openai:
      model: gpt-4o
      api_key_env: OPENAI_API_KEY
      base_url: https://api.openai.com/v1
      timeout: 30
    gemini:
      model: gemini-2.0-flash
      api_key_env: GEMINI_API_KEY
      base_url: https://generativelanguage.googleapis.com/v1beta/openai
      timeout: 30
    local:
      model: qwen2.5:7b
      base_url: http://localhost:11434/v1
      api_key_env: ""
      timeout: 60
```

### Provider 基础接口

```python
# src/app_name/llm/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    usage: dict[str, int]


class BaseLLMProvider(ABC):
    """所有 LLM Provider 的统一接口。"""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse: ...
```

### OpenAI-Compatible Provider

大多数 provider（OpenAI、Gemini、Ollama）都兼容 OpenAI API 格式：

```python
# src/app_name/llm/openai_compat.py
import os

import httpx

from .base import BaseLLMProvider, LLMResponse


class OpenAICompatProvider(BaseLLMProvider):
    def __init__(self, model: str, base_url: str, api_key_env: str, timeout: int = 30):
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._api_key = os.getenv(api_key_env, "")
        self._timeout = timeout

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]["message"]
        usage = data.get("usage", {})

        return LLMResponse(
            content=choice["content"],
            model=data.get("model", self._model),
            usage={
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            },
        )
```

### Provider Registry & Factory

```python
# src/app_name/llm/registry.py
from .base import BaseLLMProvider
from .openai_compat import OpenAICompatProvider

_providers: dict[str, BaseLLMProvider] = {}


def init_providers(config: dict) -> None:
    """从配置初始化所有 provider，应用启动时调用一次。"""
    llm_config = config.get("llm", {})
    for name, provider_cfg in llm_config.get("providers", {}).items():
        _providers[name] = OpenAICompatProvider(
            model=provider_cfg["model"],
            base_url=provider_cfg["base_url"],
            api_key_env=provider_cfg.get("api_key_env", ""),
            timeout=provider_cfg.get("timeout", 30),
        )


def get_provider(name: str | None = None) -> BaseLLMProvider:
    """获取指定 provider，None 则返回 default。"""
    if name is None:
        # 取第一个注册的作为默认
        name = next(iter(_providers))
    if name not in _providers:
        raise KeyError(f"LLM provider '{name}' not registered. Available: {list(_providers)}")
    return _providers[name]
```

### 在模板 Context 中集成

模板使用 `context/` 目录管理请求级依赖。添加 LLM provider 的方式：

```python
# src/app_name/context/llm.py
from contextvars import ContextVar

from app_name.llm.base import BaseLLMProvider
from app_name.llm.registry import get_provider

_current_provider: ContextVar[BaseLLMProvider | None] = ContextVar(
    "current_llm_provider", default=None
)


def set_llm_provider(name: str | None = None) -> None:
    _current_provider.set(get_provider(name))


def get_llm() -> BaseLLMProvider:
    provider = _current_provider.get()
    if provider is None:
        return get_provider()  # fallback to default
    return provider
```

在 service 层使用：

```python
from app_name.context.llm import get_llm


async def summarize_article(content: str) -> str:
    llm = get_llm()
    response = await llm.chat([
        {"role": "system", "content": "Summarize the following article in 2-3 sentences."},
        {"role": "user", "content": content},
    ])
    return response.content
```

## 扩展思路

- **Fallback 链**：在 `get_provider` 中加 try/except，失败时尝试下一个 provider
- **按任务路由**：配置中为不同任务指定不同 provider（如 extraction 用 GPT-4o，summary 用 Flash）
- **Token 计费追踪**：`LLMResponse.usage` 已包含 token 数据，写入 metrics collection 即可
