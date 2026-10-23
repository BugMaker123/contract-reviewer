import asyncio
import json
from types import SimpleNamespace

import pytest

from backend import graph, workspace_review
from backend.models import ModelConfig
from langchain_core.messages import HumanMessage


def test_review_retries_with_validation_feedback_and_recovers():
    class Client:
        calls = 0

        def invoke(self, messages):
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(content='说明文字，没有结果')
            assert 'JSON' in messages[-1].content
            assert '说明文字，没有结果' == messages[-2].content
            return SimpleNamespace(content='{"issues":[]}')

    client = Client()
    assert graph.invoke_review_with_retry(client, [HumanMessage(content='审查合同')], {})['issues'] == []
    assert client.calls == 2


def test_default_three_retries_means_four_total_requests():
    class Client:
        calls = 0

        def invoke(self, messages):
            self.calls += 1
            return SimpleNamespace(content='invalid')

    client = Client()
    assert ModelConfig().max_retries == 3
    with pytest.raises(graph.ModelCallError, match='已尝试 4 次'):
        graph.invoke_review_with_retry(client, [], {})
    assert client.calls == 4


def test_transient_network_failure_uses_backoff(monkeypatch):
    delays = []
    monkeypatch.setattr(graph.time, 'sleep', delays.append)

    class Client:
        calls = 0

        def invoke(self, messages):
            self.calls += 1
            if self.calls < 3:
                raise ConnectionError('offline')
            return SimpleNamespace(content='{"issues":[]}')

    graph.invoke_review_with_retry(Client(), [], {})
    assert delays == [1, 2]


def test_authentication_error_does_not_retry():
    class Unauthorized(Exception):
        status_code = 401

    class Client:
        calls = 0

        def invoke(self, messages):
            self.calls += 1
            raise Unauthorized()

    client = Client()
    with pytest.raises(graph.ModelCallError, match='鉴权失败'):
        graph.invoke_review_with_retry(client, [], {})
    assert client.calls == 1


def test_rewrite_missing_clause_retries_and_recovers(monkeypatch):
    class Client:
        calls = 0

        async def ainvoke(self, messages):
            self.calls += 1
            if self.calls == 1:
                return SimpleNamespace(content='{"revisions":[]}')
            assert 'revisions' in messages[-1].content
            return SimpleNamespace(content=json.dumps({'revisions':[{'id':'a','suggested_text':'修订后条款'}]}))

    client = Client()
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: client)
    config = {'_required_json_arrays':['revisions'], '_revision_originals':{'a':'原文'}}
    result = asyncio.run(workspace_review.model_json(config, '改写'))
    assert result['revisions'][0]['suggested_text'] == '修订后条款'
    assert client.calls == 2


def test_rewrite_keeps_valid_clauses_when_batch_is_incomplete(monkeypatch):
    class Client:
        calls = 0

        async def ainvoke(self, messages):
            self.calls += 1
            return SimpleNamespace(content=json.dumps({'revisions': [
                {'id': 'a', 'suggested_text': '修订后的第一条'},
                {'id': 'b', 'suggested_text': '原文第二条'},
            ]}))

    client = Client()
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: client)
    result = asyncio.run(workspace_review.model_json({
        '_required_json_arrays': ['revisions'],
        '_revision_originals': {'a': '原文第一条', 'b': '原文第二条', 'c': '原文第三条'},
    }, '改写'))
    assert result['revisions'] == [{'id': 'a', 'suggested_text': '修订后的第一条'}]
    assert client.calls == 1


def test_zero_retries_stops_after_first_response(monkeypatch):
    class Client:
        calls = 0

        async def ainvoke(self, messages):
            self.calls += 1
            return SimpleNamespace(content='not JSON')

    client = Client()
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: client)
    with pytest.raises(graph.ModelCallError, match='已尝试 1 次'):
        asyncio.run(workspace_review.model_json({'max_retries':0}, '改写'))
    assert client.calls == 1


def test_placeholder_expansion_gets_feedback_instead_of_applied(monkeypatch):
    class Client:
        calls = 0

        async def ainvoke(self, messages):
            self.calls += 1
            text = '银行账号：【待确认】。' if self.calls == 1 else '银行账号：____。双方应核验收款账户。'
            if self.calls == 2:
                assert '占位符' in messages[-1].content
            return SimpleNamespace(content=json.dumps({'revisions':[{'id':'a','suggested_text':text}]}))

    client = Client()
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: client)
    result = asyncio.run(workspace_review.model_json({'_required_json_arrays':['revisions'],
                        '_revision_originals':{'a':'银行账号：____。'}}, '最小改写'))
    assert '待确认' not in result['revisions'][0]['suggested_text']
    assert client.calls == 2


def test_stream_cannot_continue_indefinitely(monkeypatch):
    ticks = iter([0,121])
    monkeypatch.setattr(graph.time, 'monotonic', lambda:next(ticks))

    class Client:
        def stream(self, messages):
            yield SimpleNamespace(content='still generating')

    with pytest.raises(TimeoutError, match='120 秒'):
        graph.stream_public_review(Client(), [], 0)


def test_cancelled_review_does_not_retry(monkeypatch):
    monkeypatch.setattr(graph, 'review_cancelled', lambda:True)
    with pytest.raises(graph.ModelCallError, match='已取消'):
        graph.prepare_model_retry([], ConnectionError(), 0, 3)
