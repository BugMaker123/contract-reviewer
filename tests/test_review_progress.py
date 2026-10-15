import asyncio
import json
import threading
from types import SimpleNamespace

from fastapi.testclient import TestClient
from backend.main import app
from backend import graph
from backend.review_progress import observable_events, emit_progress


def test_thread_progress_arrives_before_node_finishes():
    async def run():
        release = asyncio.Event()

        async def events(snapshot, config):
            await asyncio.to_thread(emit_progress, 'retry', '格式校验失败，正在重试')
            await release.wait()
            yield 'complete', {'issues':[]}

        stream = observable_events(events, {'text':'合同'}, {})
        assert (await anext(stream))[1]['stage'] == 'prepare'
        kind, data = await asyncio.wait_for(anext(stream), timeout=2)
        assert kind == 'progress' and data['stage'] == 'retry'
        release.set()
        assert (await anext(stream))[0] == 'complete'
        await stream.aclose()

    asyncio.run(run())


def test_public_trace_is_saved_with_completed_review(isolated_workspace, monkeypatch):
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: None)
    with TestClient(app) as client:
        task = client.post('/api/tasks', json={'title':'过程记录', 'text':'第一条 标的\n交付设备。', 'mode':'quick'}).json()
        response = client.post('/api/tasks/'+task['id']+'/review/stream', json={})
        blocks = response.text.strip().split('\n\n')
        complete = next(b for b in blocks if b.startswith('event: complete'))
        completed = json.loads(complete.split('data: ', 1)[1])
        run = client.get('/api/runs/'+completed['run_id']).json()
        assert 'event: progress' in response.text
        assert any(item['stage'] == 'segment' for item in run['audit_trace'])
        assert run['result']['audit_trace'] == run['audit_trace']
        assert all(set(item) >= {'stage','detail','time'} for item in run['audit_trace'])


def test_public_model_summary_streams_before_review_is_finished():
    issue = {'id':'a','clause_title':'付款条款','severity':'warning','category':'付款',
             'issue_title':'付款期限不明确','legal_basis':'按合同约定',
             'risk_analysis':'未约定付款日期，履约时间容易发生争议。',
             'negotiation_strategy':'补充双方约定的付款期限。','redline':None}
    release = threading.Event()

    class Client:
        def stream(self, messages):
            yield SimpleNamespace(content='{"issues":['+json.dumps(issue),
                                  additional_kwargs={'reasoning_content':'INTERNAL_REASONING_MUST_NOT_APPEAR'})
            assert release.wait(3)
            yield SimpleNamespace(content='],"tax_settlement":{}}')

    async def run():
        async def events(snapshot, config):
            result = await asyncio.to_thread(graph.invoke_review_with_retry, Client(), [], {})
            yield 'complete', result

        stream = observable_events(events, {'text':'合同'}, {})
        observed=[]
        try:
            for _ in range(5):
                kind,data=await asyncio.wait_for(anext(stream),2)
                observed.append(data)
                if data.get('stage')=='analysis_summary':
                    assert data['analysis']==issue['risk_analysis']
                    assert data['provisional'] is True
                    assert 'INTERNAL_REASONING' not in json.dumps(observed)
                    break
            else:
                raise AssertionError('No streamed public analysis')
            release.set()
            remaining=[item async for item in stream]
            assert remaining[-1][0]=='complete'
        finally:
            release.set()
            await stream.aclose()

    asyncio.run(run())
