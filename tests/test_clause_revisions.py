import asyncio
from copy import deepcopy

from backend import workspace_review as review
from backend.workspace_api import revised_text


def result_fixture():
    original = '4.3 乙方提供发票。'
    base = dict(segment_id='s1', clause_title='4.3 发票', severity='warning', category='财税',
                legal_basis='依据', negotiation_strategy='完善开票约定', evidence=original)
    issues = [{**base, 'id': 'rate', 'issue_title': '税率不明确', 'risk_analysis': '需确认税率',
               'redline': {'original_text': original, 'suggested_text': '4.3 明确税率后提供发票。', 'change_type': 'replace'}},
              {**base, 'id': 'type', 'severity': 'critical', 'issue_title': '发票类型不明确',
               'risk_analysis': '需确认发票类型', 'redline': None}]
    return {'issues': issues, 'segments': [{'id': 's1', 'content': original}], 'summary': {}}, original


def test_same_clause_gets_one_comprehensive_rewrite_and_preview(monkeypatch):
    result, original = result_fixture()
    monkeypatch.setattr(review.graph, 'get_llm_client', lambda config: object())
    rewritten = '4.3 乙方按【待确认】税率开具【待确认类型】发票。'

    async def generate(config, prompt):
        assert '税率不明确' in prompt and '发票类型不明确' in prompt
        return {'revisions': [{'id': 'rate', 'suggested_text': rewritten}]}

    monkeypatch.setattr(review, 'model_json', generate)
    asyncio.run(review.consolidate_revisions(result, {'text': original}, {}))
    assert len(result['issues']) == 1
    issue = result['issues'][0]
    assert len(issue['risk_points']) == 2 and issue['severity'] == 'critical'
    assert result['summary']['critical_count'] == 1
    run = {'input': {'text': original}, 'result': result, 'applied': []}
    assert revised_text(run, [issue['id']]) == rewritten
    assert run['applied'] == []  # Suggestion preview does not decide for the user.


def test_unavailable_model_keeps_verified_partial_edit_and_explains_gap(monkeypatch):
    result, original = result_fixture()
    monkeypatch.setattr(review.graph, 'get_llm_client', lambda config: None)
    asyncio.run(review.consolidate_revisions(result, {'text': original}, {}))
    assert len(result['issues']) == 1
    assert result['issues'][0]['redline']['suggested_text'] == '4.3 明确税率后提供发票。'
    assert result['issues'][0]['rewrite_warning']


def test_failed_model_without_valid_edits_does_not_fabricate_rewrite(monkeypatch):
    result, original = result_fixture()
    for issue in result['issues']:
        issue['redline'] = None
    monkeypatch.setattr(review.graph, 'get_llm_client', lambda config: object())

    async def unavailable(config, prompt):
        raise ConnectionError('offline')

    monkeypatch.setattr(review, 'model_json', unavailable)
    asyncio.run(review.consolidate_revisions(result, {'text': original}, {}))
    assert result['issues'][0]['redline'] is None
    assert '保留原文' in result['issues'][0]['rewrite_warning']


def test_distinct_clauses_keep_independent_decisions_and_valid_edits(monkeypatch):
    result, original = result_fixture()
    result['issues'] = result['issues'][:1]
    second = deepcopy(result['issues'][0])
    second.update(id='payment', segment_id='s2', evidence='5.1 验收后付款。')
    second['redline'] = {'original_text': second['evidence'], 'suggested_text': '5.1 验收后30日付款。', 'change_type': 'replace'}
    result['issues'].append(second)
    result['segments'].append({'id': 's2', 'content': second['evidence']})
    monkeypatch.setattr(review.graph, 'get_llm_client', lambda config: None)
    text = original + '\n' + second['evidence']
    asyncio.run(review.consolidate_revisions(result, {'text': text}, {}))
    assert len(result['issues']) == 2
    output = revised_text({'input': {'text': text}, 'result': result}, ['rate', 'payment'])
    assert '明确税率' in output and '30日' in output
