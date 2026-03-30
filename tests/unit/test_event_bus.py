"""Tests for the in-process event bus."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from app_name.shared.events.bus import InProcessEventBus


@dataclass(frozen=True)
class SampleEvent:
    value: str


class TestInProcessEventBus:
    @pytest.fixture()
    def bus(self) -> InProcessEventBus:
        return InProcessEventBus()

    async def test_publish_calls_handler(self, bus: InProcessEventBus) -> None:
        received: list[SampleEvent] = []

        async def handler(event: SampleEvent) -> None:
            received.append(event)

        bus.subscribe(SampleEvent, handler)
        await bus.publish(SampleEvent(value="hello"))

        assert len(received) == 1
        assert received[0].value == "hello"

    async def test_multiple_handlers(self, bus: InProcessEventBus) -> None:
        call_count = 0

        async def handler_a(_: SampleEvent) -> None:
            nonlocal call_count
            call_count += 1

        async def handler_b(_: SampleEvent) -> None:
            nonlocal call_count
            call_count += 1

        bus.subscribe(SampleEvent, handler_a)
        bus.subscribe(SampleEvent, handler_b)
        await bus.publish(SampleEvent(value="test"))

        assert call_count == 2

    async def test_no_handlers(self, bus: InProcessEventBus) -> None:
        # Should not raise
        await bus.publish(SampleEvent(value="orphan"))

    async def test_handler_exception_isolated(self, bus: InProcessEventBus) -> None:
        results: list[str] = []

        async def bad_handler(_: SampleEvent) -> None:
            msg = "intentional failure"
            raise RuntimeError(msg)

        async def good_handler(event: SampleEvent) -> None:
            results.append(event.value)

        bus.subscribe(SampleEvent, bad_handler)
        bus.subscribe(SampleEvent, good_handler)
        await bus.publish(SampleEvent(value="still works"))

        assert "still works" in results

    async def test_handler_timeout(self, bus: InProcessEventBus) -> None:
        async def slow_handler(_: SampleEvent) -> None:
            await asyncio.sleep(10)

        bus.subscribe(SampleEvent, slow_handler)
        # Should not hang — timeout kicks in
        await bus.publish(SampleEvent(value="timeout test"), timeout=0.1)
