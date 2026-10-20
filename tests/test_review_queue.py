"""Concurrency, FIFO, credentials, cancellation and restart behavior for local review jobs."""
import asyncio
import json
from pathlib import Path
from fastapi import HTTPException
import pytest
from backend import review_jobs
from backend.store import Repository


def make_run(repo, name):
    task = repo.create('task', {'title':name,'text':'第一条 交付设备。第二条 验收后付款。','type':'商务合同','role':'中立审慎','mode':'quick','scale':'中立','background':'','focus':'','requirements':[],'references':[],'checklist':None,'source_id':None,'execution':'plan','status':'draft','archived':False,'active_run':None})
    return repo.start_run(task['id'])


async def until(predicate):
    async with asyncio.timeout(3):
        while not predicate():
            await asyncio.sleep(.01)


def test_five_per_effective_key_fifo_and_cancelled_waiter_never_executes(tmp_path, monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY','private-key-A')
    repo = Repository(tmp_path/'queue.db')
    async def scenario():
        runs=[make_run(repo,f'A{i}') for i in range(8)]+[make_run(repo,'B0')]
        gates={run['input']['title']:asyncio.Event() for run in runs}
        entered=[];active={'A':0,'B':0};peak={'A':0,'B':0}
        async def events(snapshot,config):
            name=snapshot['title'];group=name[0];entered.append(name);active[group]+=1;peak[group]=max(peak[group],active[group])
            try:
                await gates[name].wait()
                yield 'complete',{'issues':[],'summary':{'verdict':'已完成'}}
            finally:
                active[group]-=1
        jobs=[]
        try:
            for i,run in enumerate(runs):
                config={} if i==5 else {'api_key':' private-key-A ' if i<8 else 'private-key-B','base_url':f'https://endpoint-{i}.invalid'}
                jobs.append(review_jobs.launch(repo,run,config,events))
            await until(lambda:len(entered)==6)
            assert set(entered)=={'A0','A1','A2','A3','A4','B0'}
            assert peak=={'A':5,'B':1}
            assert [repo.get(run['id'])['queue']['position'] for run in runs[5:8]]==[1,2,3]
            assert all(repo.get(run['task_id'])['status']=='queued' for run in runs[5:8])
            with pytest.raises(HTTPException) as error:
                repo.start_run(runs[5]['task_id'])
            assert error.value.status_code==409
            await review_jobs.cancel(repo,runs[6]['id'])
            assert repo.get(runs[6]['id'])['status']=='interrupted'
            assert repo.get(runs[7]['id'])['queue']['position']==2
            gates['A0'].set()
            await until(lambda:'A5' in entered)
            assert 'A7' not in entered
            await review_jobs.cancel(repo,runs[1]['id'])
            await until(lambda:'A7' in entered)
            assert 'A6' not in entered
            assert peak['A']==5
            for gate in gates.values():gate.set()
            await asyncio.gather(*(job.task for job in jobs),return_exceptions=True)
            assert repo.get(runs[0]['task_id'])['status']=='pending_review'
            assert repo.get(runs[0]['task_id'])['active_run']==runs[0]['id']
            assert all(job.done for job in jobs)
            assert not jobs[0].queue.groups
            assert b'private-key' not in Path(repo.path).read_bytes()
            assert 'private-key' not in json.dumps([job.events for job in jobs])
        finally:
            for gate in gates.values():gate.set()
            await review_jobs.shutdown(repo)
    asyncio.run(scenario())


def test_cancel_before_execution_and_failure_release_capacity(tmp_path):
    repo=Repository(tmp_path/'cancel.db')
    async def scenario():
        runs=[make_run(repo,str(i)) for i in range(7)]
        gate=asyncio.Event();entered=[]
        async def events(snapshot,config):
            entered.append(snapshot['title'])
            if snapshot['title']=='1':raise ValueError('simulated failure')
            await gate.wait()
            yield 'complete',{'issues':[],'summary':{'verdict':'完成'}}
        jobs=[review_jobs.launch(repo,run,{'api_key':'key'},events) for run in runs]
        try:
            await review_jobs.cancel(repo,runs[0]['id'])
            await until(lambda:'6' in entered)
            assert '0' not in entered
            assert repo.get(runs[0]['id'])['status']=='interrupted'
            assert repo.get(runs[1]['id'])['status']=='failed'
            gate.set()
            await asyncio.gather(*(job.task for job in jobs),return_exceptions=True)
            assert not jobs[0].queue.groups
        finally:
            gate.set();await review_jobs.shutdown(repo)
    asyncio.run(scenario())


def test_local_queue_restart_marks_waiters_interrupted_without_losing_previous_result(tmp_path):
    repo=Repository(tmp_path/'restart.db')
    run=make_run(repo,'queued')
    repo.update(run['task_id'],{'status':'queued','active_run':'previous'})
    repo.update(run['id'],{'status':'queued','queue':{'position':1}})
    repo.interrupt_running()
    assert repo.get(run['id'])['status']=='interrupted'
    assert repo.get(run['task_id'])['status']=='interrupted'
    assert repo.get(run['task_id'])['active_run']=='previous'


def test_legacy_slot_and_background_jobs_share_the_same_limit(tmp_path):
    from backend.review_queue import review_slot
    repo=Repository(tmp_path/'shared.db')
    async def scenario():
        gate=asyncio.Event();inside=[]
        async def events(snapshot,config):
            await gate.wait()
            yield 'complete',{'issues':[],'summary':{'verdict':'完成'}}
        jobs=[review_jobs.launch(repo,make_run(repo,str(i)),{'api_key':'shared'},events) for i in range(5)]
        async def legacy(key):
            async with review_slot({'api_key':key}):
                inside.append(key)
        waiting=asyncio.create_task(legacy('shared'))
        try:
            await legacy('other')
            await asyncio.sleep(.02)
            assert inside==['other']
            gate.set()
            await waiting
            assert inside==['other','shared']
            await asyncio.gather(*(job.task for job in jobs))
            assert not jobs[0].queue.groups
        finally:
            gate.set();waiting.cancel();await asyncio.gather(waiting,return_exceptions=True)
            await review_jobs.shutdown(repo)
    asyncio.run(scenario())
