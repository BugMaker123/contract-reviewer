"""Replaceable FIFO admission queue for review jobs; local adapter is process-local."""
import asyncio
import hashlib
from contextlib import asynccontextmanager
from uuid import uuid4
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Protocol
from weakref import WeakKeyDictionary


@dataclass(eq=False)
class QueueTicket:
    group: str
    job_id: object
    notify: Callable
    ready: asyncio.Future
    status: str = 'queued'


class ReviewQueue(Protocol):
    def enqueue(self, group: str, job_id: object, notify: Callable) -> QueueTicket: ...
    def release(self, ticket: QueueTicket) -> None: ...
    def cancel(self, ticket: QueueTicket) -> None: ...


@dataclass
class _Group:
    running: set = field(default_factory=set)
    waiting: deque = field(default_factory=deque)


class LocalReviewQueue:
    """All mutations run atomically on one asyncio loop. FIFO is per credential."""
    def __init__(self, limit=5):
        if limit < 1:
            raise ValueError('Concurrency limit must be positive')
        self.limit = limit
        self.groups = {}

    def enqueue(self, group, job_id, notify):
        ticket = QueueTicket(group, job_id, notify, asyncio.get_running_loop().create_future())
        state = self.groups.setdefault(group, _Group())
        state.waiting.append(ticket)
        self._dispatch(group, state)
        return ticket

    def _dispatch(self, group, state):
        while len(state.running) < self.limit and state.waiting:
            ticket = state.waiting.popleft()
            if ticket.ready.cancelled():
                ticket.status = 'cancelled'
                continue
            ticket.status = 'running'
            state.running.add(ticket)
            ticket.notify({'status':'running', 'position':0, 'limit':self.limit})
            ticket.ready.set_result(None)
        for position, ticket in enumerate(state.waiting, 1):
            ticket.notify({'status':'queued', 'position':position, 'limit':self.limit})
        if not state.running and not state.waiting:
            self.groups.pop(group, None)

    def _remove(self, ticket, status):
        if ticket.status in ('done', 'cancelled'):
            return
        state = self.groups.get(ticket.group)
        ticket.status = status
        if not ticket.ready.done():
            ticket.ready.cancel()
        if state is None:
            return
        state.running.discard(ticket)
        try:
            state.waiting.remove(ticket)
        except ValueError:
            pass
        self._dispatch(ticket.group, state)

    def release(self, ticket):
        self._remove(ticket, 'done')

    def cancel(self, ticket):
        self._remove(ticket, 'cancelled')


_queues = WeakKeyDictionary()


def get_review_queue() -> ReviewQueue:
    loop = asyncio.get_running_loop()
    if loop not in _queues:
        _queues[loop] = LocalReviewQueue(limit=5)
    return _queues[loop]


def credential_group(config):
    from .graph import resolved_api_key
    credential = resolved_api_key(config)
    value = 'credential:' + credential if credential else 'local:no-model'
    return hashlib.sha256(value.encode()).hexdigest()


@asynccontextmanager
async def review_slot(config):
    """Legacy review requests share capacity with persisted background jobs."""
    queue = get_review_queue()
    ticket = queue.enqueue(credential_group(config), uuid4().hex, lambda state: None)
    try:
        await ticket.ready
        yield
    finally:
        queue.release(ticket)
