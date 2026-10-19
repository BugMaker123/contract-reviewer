from copy import deepcopy
from backend.stance_policy import changes_identity, guard_generated_issues, internal_identity_conflict, perspective, STANCE_INSTRUCTIONS
from backend import graph, workspace_api, workspace_review
from backend.review_policy import review_context
from test_tracked_revisions import revision_client, seed_review

TEXT = '甲方（供方）：甲公司\n乙方（需方）：乙公司\n乙方向甲方采购产品。甲方向乙方开具发票。'
BAD = {'id': 'bad', 'issue_title': '首部将乙方写成需方，与乙方卖方/服务方审查立场冲突，且开票义务落在甲方',
       'risk_analysis': '若我方实际为乙方卖方，则开票、收款、质量责任主体全部错位，应校正角色。',
       'redline': {'original_text': TEXT, 'suggested_text': TEXT.replace('供方', '需方').replace('乙方（需方）', '乙方（供方）'), 'change_type': 'replace'}}


def test_perspective_is_not_a_party_identity_or_transaction_fact():
    assert perspective('乙方(卖方/开发方/服务方)') == '乙方'
    assert review_context({'role': '甲方(买方/采购方/委托方)'})['role'] == '甲方'
    assert not internal_identity_conflict(TEXT)
    genuine = {'id': 'good', 'issue_title': '付款期限不明确', 'risk_analysis': '从乙方立场建议明确付款期限。', 'redline': None}
    assert guard_generated_issues([deepcopy(BAD), genuine], TEXT) == [genuine]


def test_auto_revision_cannot_swap_supply_roles_or_reverse_purchase():
    assert changes_identity(TEXT, BAD['redline']['suggested_text'])
    assert changes_identity('乙方向甲方采购产品。', '甲方向乙方采购产品。')
    assert not changes_identity('乙方向甲方采购产品。', '乙方向甲方采购产品，并在验收后付款。')
    assert not changes_identity('甲方（供方）', '甲方（供应商）')
    issue = {'id': 'real', 'issue_title': '缺少开票时间', 'risk_analysis': '请明确时点。', 'redline': BAD['redline']}
    guarded = guard_generated_issues([issue], TEXT)[0]
    assert guarded['redline'] is None
    assert '供需身份' in guarded['rewrite_warning']


def test_real_contract_identity_contradiction_is_still_reported():
    inconsistent = TEXT + '\n后文约定乙方（供方）负责供货。'
    assert internal_identity_conflict(inconsistent)
    result = guard_generated_issues([deepcopy(BAD)], inconsistent)
    assert len(result) == 1
    assert result[0]['redline'] is None


def test_deep_review_prompt_and_output_guard(monkeypatch):
    captured = []
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: object())
    def invoke(client, messages, config):
        captured.extend(messages)
        return {'tax_settlement': {}, 'issues': [deepcopy(BAD)]}
    monkeypatch.setattr(graph, 'invoke_review_with_retry', invoke)
    result = graph.node_balance_review({'contract_text': TEXT, 'segments': [], 'party_role': '乙方(卖方/开发方/服务方)', 'review_mode': 'deep'})
    assert result['balance_issues'] == []
    prompt = captured[-1].content
    assert '站在【乙方】立场' in prompt
    assert STANCE_INSTRUCTIONS in prompt


def test_previous_bad_advice_cannot_be_accepted(revision_client):
    task, run = seed_review(revision_client)
    result = deepcopy(run['result'])
    issue = result['issues'][0]
    issue.update(issue_title=BAD['issue_title'], risk_analysis=BAD['risk_analysis'])
    run = workspace_api.repo.update(run['id'], {'result': result})
    response = revision_client.put('/api/runs/' + run['id'] + '/handling', json={'revision': run['revision'], 'applied': [issue['id']]})
    assert response.status_code == 409
    assert '审查立场' in response.text
    assert revision_client.get('/api/runs/' + run['id']).json()['applied'] == []


def test_perspective_can_still_support_real_commercial_advice():
    advice = {'issue_title': '供应商应合理分担验收成本', 'risk_analysis': '与乙方审查立场不符，供应商仍需承担合理验收义务。', 'redline': None}
    assert guard_generated_issues([advice], TEXT) == [advice]


def test_ai_regeneration_cannot_swap_existing_party_facts(revision_client, monkeypatch):
    task, run = seed_review(revision_client)
    workspace_api.repo.update(task['id'], {'text': TEXT})
    result = deepcopy(run['result'])
    result['issues'][0].update(evidence=TEXT, redline={'original_text': TEXT, 'suggested_text': TEXT + '\n保留原有身份。', 'change_type': 'replace'})
    run = workspace_api.repo.update(run['id'], {'input': {**run['input'], 'text': TEXT}, 'result': result})
    async def generate(config, prompt):
        assert STANCE_INSTRUCTIONS in prompt
        return {'suggested_text': BAD['redline']['suggested_text'], 'explanation': '错误交换主体'}
    monkeypatch.setattr(workspace_review, 'model_json', generate)
    response = revision_client.post('/api/runs/' + run['id'] + '/issues/payment/regenerate', json={'revision': run['revision']})
    assert response.status_code == 422
    assert '供需身份' in response.text
    assert revision_client.get('/api/runs/' + run['id']).json()['result'] == result


def test_consolidated_rewrite_retains_issue_but_blocks_identity_swap(monkeypatch):
    import asyncio
    monkeypatch.setattr(graph, 'get_llm_client', lambda config: object())
    async def generate(config, prompt):
        assert '"role": "乙方"' in prompt
        return {'revisions': [{'id': 'invoice', 'suggested_text': BAD['redline']['suggested_text']}]}
    monkeypatch.setattr(workspace_review, 'model_json', generate)
    issue = {'id': 'invoice', 'segment_id': 's', 'clause_title': '开票安排', 'severity': 'warning', 'category': '发票',
             'issue_title': '开票时间不明确', 'risk_analysis': '未明确时间。', 'legal_basis': '', 'negotiation_strategy': '明确开票时间。',
             'evidence': TEXT, 'redline': None}
    result = {'issues': [issue], 'segments': [{'id': 's', 'content': TEXT}], 'summary': {}}
    asyncio.run(workspace_review.consolidate_revisions(result, {'text': TEXT, 'role': '乙方(卖方/开发方/服务方)'}, {}))
    assert len(result['issues']) == 1
    assert result['issues'][0]['redline'] is None
    assert '供需身份' in result['issues'][0]['rewrite_warning']
