"""Single-instance durable review jobs; browser connections only subscribe."""
import asyncio
import json
import logging
from dataclasses import dataclass, field
from .store import now
from .graph import ModelCallError
from .review_queue import get_review_queue, credential_group
from .review_policy import AdmissionError
from .review_progress import observable_events

logger = logging.getLogger(__name__)
_jobs = {}


@dataclass
class ReviewJob:
    events: list = field(default_factory=list)
    changed: asyncio.Event = field(default_factory=asyncio.Event)
    done: bool = False
    task: object = None
    ticket: object = None
    queue: object = None

    def publish(self, kind, data):
        self.events.append((kind, data))
        self.changed.set()


def key(repo, run_id):
    return (repo.path, run_id)


def launch(repo, run, config, review_events):
    # Keep only live jobs and recent completed subscriptions in memory.
    if len(_jobs) > 128:
        for identifier, previous in list(_jobs.items()):
            if previous.done:
                _jobs.pop(identifier, None)
    job = ReviewJob()
    _jobs[key(repo, run['id'])] = job
    job.publish('init', {'run_id': run['id'], 'number': run['number'], 'baseline_kind': run.get('baseline_kind', 'task'),
                         'document': {'text': run['input']['text'], 'source_id': run['input'].get('source_id')}})
    submitted_at = now()
    queue_state = {}
    def queue_changed(state):
        nonlocal queue_state
        changed = {**state, 'submitted_at': submitted_at}
        if state['status'] == 'running':
            changed['started_at'] = now()
        if changed == queue_state:
            return
        queue_state = changed
        repo.update(run['id'], {'status':state['status'], 'queue':changed})
        repo.update(run['task_id'], {'status':state['status']})
        job.publish('queue', changed)
    # Only the fingerprint enters the scheduler; credentials stay in the job closure.
    group = credential_group(config)
    job.queue = get_review_queue()
    job.ticket = job.queue.enqueue(group, key(repo, run['id']), queue_changed)

    async def execute():
        progress, trace = [], []
        completed = False
        try:
            await job.ticket.ready
            async for kind, data in observable_events(review_events, run['input'], config):
                if kind == 'progress':
                    trace.append(data)
                    repo.update(run['id'], {'audit_trace': trace})
                if kind == 'node_update':
                    progress.append(data['log'])
                    trace.append({'stage': data['node'], 'detail': data['log']['detail'], 'time': now()})
                    repo.update(run['id'], {'progress_log': progress, 'last_node': data['node'], 'audit_trace': trace})
                if kind == 'complete':
                    completed = True
                    data['audit_trace'] = trace
                    repo.update(run['id'], {'status': 'completed', 'result': data, 'completed_at': now(), 'queue':{**queue_state,'status':'completed','position':0,'finished_at':now()}})
                    repo.update(run['task_id'], {'status': 'pending_review', 'active_run': run['id'], 'error': None})
                    data = {'success': True, 'data': data, 'run_id': run['id'], 'number': run['number']}
                job.publish(kind, data)
            if not completed:
                raise ValueError('未收到完整审查结果')
        except asyncio.CancelledError:
            repo.update(run['id'], {'status': 'interrupted', 'error': '审查已取消或服务已停止', 'queue':{**queue_state,'status':'interrupted','position':0,'finished_at':now()}})
            repo.update(run['task_id'], {'status': 'interrupted', 'error': '审查已中断，上次结果已保留'})
            job.publish('error', {'error': '审查已中断，上次结果已保留'})
            raise
        except Exception as error:
            logger.exception('Review failed: run=%s', run['id'])
            message = str(error) if isinstance(error, (ModelCallError, TimeoutError)) else '审查执行失败，请检查模型连接后重试'
            trace.append({'stage': 'failed', 'detail': message, 'time': now()})
            repo.update(run['id'], {'status': 'failed', 'error': message, 'audit_trace': trace, 'queue':{**queue_state,'status':'failed','position':0,'finished_at':now()},
                                   **({'admission': error.decision} if isinstance(error, AdmissionError) else {})})
            repo.update(run['task_id'], {'status': 'failed', 'error': '审查执行失败，上次完成的结果已保留'})
            job.publish('error', {'error': message + '；上次完成的结果已保留'})
        finally:
            job.queue.release(job.ticket)
            job.done = True
            job.changed.set()

    job.task = asyncio.create_task(execute())
    return job


def event(kind, data):
    return 'event: ' + kind + '\ndata: ' + json.dumps(data, ensure_ascii=False) + '\n\n'


async def subscribe(repo, run_id):
    job = _jobs.get(key(repo, run_id))
    if job is None:
        run = repo.get(run_id, 'run')
        if run['status'] == 'completed':
            yield event('complete', {'success': True, 'data': run['result'], 'run_id': run_id, 'number': run['number']})
        else:
            yield event('error', {'error': run.get('error') or '任务无法在当前服务连接，请重新打开任务检查状态'})
        return
    cursor = 0
    while True:
        while cursor < len(job.events):
            kind, data = job.events[cursor]
            cursor += 1
            yield event(kind, data)
        if job.done:
            return
        job.changed.clear()
        if cursor < len(job.events):
            continue
        try:
            await asyncio.wait_for(job.changed.wait(), timeout=10)
        except asyncio.TimeoutError:
            yield ': keep-alive\n\n'


async def cancel(repo, run_id):
    if repo.get(run_id, 'run')['status'] not in ('running', 'queued'):
        return
    job = _jobs.get(key(repo, run_id))
    if job and not job.done:
        if job.ticket.status == 'queued':
            job.queue.cancel(job.ticket)
        job.task.cancel()
        await asyncio.gather(job.task, return_exceptions=True)
        if not job.done:  # Cancellation before execute() gets its first turn.
            state = repo.get(run_id, 'run').get('queue') or {}
            repo.update(run_id, {'status': 'interrupted', 'error': '审查已取消', 'queue':{**state,'status':'interrupted','position':0,'finished_at':now()}})
            run = repo.get(run_id, 'run')
            repo.update(run['task_id'], {'status': 'interrupted', 'error': '审查已取消，上次结果已保留'})
            job.publish('error', {'error': '审查已取消，上次结果已保留'})
            job.done = True
            job.queue.cancel(job.ticket)


async def shutdown(repo):
    running = [run_id for (path, run_id), job in list(_jobs.items()) if path == repo.path and not job.done]
    queued = [run_id for run_id in running if _jobs[key(repo, run_id)].ticket.status == 'queued']
    for run_id in queued:
        await cancel(repo, run_id)
    await asyncio.gather(*(cancel(repo, run_id) for run_id in running if run_id not in queued))
    for identifier in [identifier for identifier in _jobs if identifier[0] == repo.path]:
        _jobs.pop(identifier, None)
