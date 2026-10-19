"""Public execution trace, containing observable actions and outcomes only."""
import asyncio
import threading
import time
from contextvars import ContextVar
from datetime import datetime, timezone


_observer = ContextVar('review_progress_observer', default=None)
_cancelled = ContextVar('review_cancelled', default=None)


def review_cancelled():
    flag = _cancelled.get()
    return bool(flag and flag.is_set())


def emit_progress(stage, detail, **fields):
    observer = _observer.get()
    if observer:
        observer({'stage': stage, 'detail': detail,
                  'time': datetime.now(timezone.utc).isoformat(), **fields})


async def observable_events(events, snapshot, config):
    """Forward progress emitted by graph worker threads before a node completes."""
    loop = asyncio.get_running_loop()
    queue = asyncio.Queue()
    owner = threading.get_ident()
    stopped = threading.Event()
    started = time.monotonic()

    def observe(data):
        if stopped.is_set():
            return
        if threading.get_ident() == owner:
            queue.put_nowait(('progress', data))
        elif not loop.is_closed():
            loop.call_soon_threadsafe(queue.put_nowait, ('progress', data))

    async def produce():
        token = _observer.set(observe)
        cancel_token = _cancelled.set(stopped)
        try:
            emit_progress('prepare', f"已接收合同，共 {len(snapshot.get('text', ''))} 字；正在解析原文与审查条件。",
                          contract_chars=len(snapshot.get('text', '')), reference_count=len(snapshot.get('references') or []),
                          priority_count=len(snapshot.get('requirements') or []) + len([line for line in (snapshot.get('focus') or '').splitlines() if line.strip()]) + len((snapshot.get('checklist') or {}).get('items', [])))
            async for item in events(snapshot, config):
                await queue.put(item)
        except Exception as error:
            await queue.put(('exception', error))
        finally:
            _observer.reset(token)
            _cancelled.reset(cancel_token)
            await queue.put(('done', None))

    task = asyncio.create_task(produce())
    try:
        while True:
            if time.monotonic() - started > 360:
                raise TimeoutError('审查超过 6 分钟，已停止等待；请缩短合同或检查模型服务后重试')
            try:
                kind, data = await asyncio.wait_for(queue.get(), timeout=10)
            except asyncio.TimeoutError:
                yield 'progress', {'stage':'waiting', 'detail':f'模型仍在处理，已等待 {int(time.monotonic()-started)} 秒；可随时取消。',
                                   'time':datetime.now(timezone.utc).isoformat()}
                continue
            if kind == 'done':
                break
            if kind == 'exception':
                raise data
            yield kind, data
    finally:
        stopped.set()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
