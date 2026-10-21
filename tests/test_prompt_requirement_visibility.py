from copy import deepcopy
from backend import workspace_api
from backend.revisions import revision_plan
from test_tracked_revisions import revision_client, seed_review


def test_new_custom_prompt_stays_in_requirement_verification(revision_client):
    client=revision_client
    task=client.post('/api/tasks',json={'title':'Prompt范围','text':'第一条 合同双方验收后付款。第二条 违约责任另行协商。','mode':'quick','focus':'知识产权'}).json()
    client.post('/api/tasks/'+task['id']+'/review/stream',json={})
    run=client.get('/api/tasks/'+task['id']).json()['run']
    assert any(f['id']=='focus-1' for f in run['result']['requirement_findings'])
    assert not any(i.get('requirement_id','').startswith('focus-') or i.get('clause_title')=='自定义要求' for i in run['result']['issues'])


def test_legacy_prompt_card_hidden_without_losing_verification_or_history(revision_client):
    client=revision_client
    task,run=seed_review(client)
    workspace_api.repo.update(task['id'],{'focus':'知识产权'})
    snapshot={**run['input'],'focus':'知识产权'}
    result=deepcopy(run['result'])
    legacy={**result['issues'][0],'id':'req-focus-1','requirement_id':'focus-1','clause_title':'自定义要求',
            'category':'要求核验','redline':None,'evidence':'','segment_id':None}
    result['issues'].append(legacy)
    result['requirement_findings']=[{'id':'focus-1','status':'needs_review','text':'知识产权'}]
    run=workspace_api.repo.update(run['id'],{'input':snapshot,'result':result})
    view=client.get('/api/runs/'+run['id']).json()
    assert len(view['result']['issues'])==2
    assert view['result']['requirement_findings']==result['requirement_findings']
    assert len(workspace_api.repo.get(run['id'])['result']['issues'])==3
    response=client.put('/api/runs/'+run['id']+'/handling',json={'revision':run['revision'],'applied':[],
        'decisions':{'payment':'rejected','liability':'rejected'}})
    assert response.status_code==200,response.text
    run=response.json()
    verified=client.post('/api/runs/'+run['id']+'/verify-current',json={'revision':run['revision']})
    assert verified.status_code==200,verified.text
    task=client.get('/api/tasks/'+task['id']).json()
    response=client.post('/api/tasks/'+task['id']+'/complete',json={'revision':task['revision'],'archived':False,
        'confirmations':{'focus-1':'已人工核对并接受此项风险'}})
    assert response.status_code==200,response.text


def test_hidden_legacy_prompt_proposal_is_not_automatically_added(revision_client):
    _,run=seed_review(revision_client)
    legacy={**run['result']['issues'][0], 'id':'req-focus-1','requirement_id':'focus-1','clause_title':'自定义要求',
        'redline':{'change_type':'insert','original_text':'','suggested_text':'历史自定义汇总条款'}}
    run['result']['issues'].append(legacy)
    ids,_=revision_plan(run)
    assert 'req-focus-1' not in ids
    run['applied']=['req-focus-1']
    ids,_=revision_plan(run)
    assert 'req-focus-1' in ids
