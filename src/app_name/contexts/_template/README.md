# Context Template

Copy this directory to create a new bounded context:

```bash
cp -r contexts/_template contexts/my_context
```

## Directory Structure

```
my_context/
├── domain/              # Domain layer (innermost)
│   ├── entities.py      # Core domain objects (@dataclass, frozen)
│   ├── value_objects.py  # Immutable value types
│   └── events.py        # Domain events
│
├── application/         # Application layer
│   ├── ports/           # Abstract interfaces (Protocol classes)
│   │   └── my_port.py   # Define what the context NEEDS
│   └── services/        # Use cases / application services
│       └── my_service.py # Orchestrate domain logic
│
├── infrastructure/      # Infrastructure layer (outermost)
│   ├── repositories/    # Data persistence implementations
│   ├── gateways/        # External service integrations
│   └── adapters/        # Port implementations
│
└── interface/           # Interface layer
    └── api/             # FastAPI routers and schemas
        └── router.py    # HTTP endpoints
```

## Rules

1. **Domain** has ZERO external dependencies (no FastAPI, no Motor, no third-party libs).
2. **Application** depends only on Domain. Uses Protocols (ports) for infrastructure.
3. **Infrastructure** implements the ports defined in Application.
4. **Interface** wires everything together and exposes HTTP endpoints.
5. Contexts NEVER import from each other directly. Use the event bus for cross-context communication.

External I/O belongs behind a port:

```python
# application/ports/chat_model.py
from collections.abc import AsyncIterator
from typing import Protocol


class ChatModelPort(Protocol):
    async def stream_reply(self, messages: list[dict[str, str]]) -> AsyncIterator[str]: ...


# application/services/chat_service.py
class ChatService:
    def __init__(self, model: ChatModelPort) -> None:
        self._model = model
```

Put provider SDK code in `infrastructure/gateways/` or `infrastructure/adapters/`, then inject it through a dependency provider or registry wiring. Do not import HTTP clients, LLM SDKs, payment SDKs, email SDKs, or search SDKs from application services.
