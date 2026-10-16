"""Revision proposals, safe previews and Word track-changes documents."""
from copy import deepcopy
from fastapi import HTTPException

from .word_export import contract_document


def revised_text(run, ids=None):
    text = run['input']['text']
    issues = {issue['id']: issue for issue in run['result']['issues']}
    for identifier in run['applied'] if ids is None else ids:
        redline = issues[identifier].get('redline')
        if not redline:
            raise HTTPException(422, '此项没有可采纳的修订文本')
        if redline.get('change_type') == 'insert':
            text += '\n' + redline['suggested_text']
        else:
            original = redline.get('original_text')
            if not original or text.count(original) != 1:
                raise HTTPException(409, '修订与原文匹配不唯一或存在冲突，请人工核对')
            text = text.replace(original, '' if redline.get('change_type') == 'delete' else redline['suggested_text'], 1)
    return text


def revision_plan(run):
    ids, warnings = list(run['applied']), []
    for issue in run['result']['issues']:
        if issue['id'] in ids or run.get('decisions', {}).get(issue['id']) == 'rejected':
            continue
        if not issue.get('redline'):
            continue
        try:
            revised_text(run, ids + [issue['id']])
        except HTTPException:
            warnings.append({'id': issue['id'], 'message': '与已接受修订冲突或无法唯一定位原文，尚未放入正文'})
        else:
            ids.append(issue['id'])
    return ids, warnings


def review_document(run, repo, builder, display='markup'):
    if display not in ('markup', 'current', 'original'):
        raise HTTPException(422, '无效修订显示方式')
    accepted = revised_text(run)
    base_text = run['input']['text'] if display == 'original' else accepted
    document, layout = contract_document(run, base_text, repo, builder)
    ids, warnings = revision_plan(run)
    if display == 'markup':
        proposal = revised_text(run, ids)
        snapshot = {**run, 'input': {**run['input'], 'text': accepted, 'source_id': None}}
        document, layout = contract_document(snapshot, proposal, repo, builder, tracked=True,
                                             base_document=document, base_layout=layout)
    return document, layout, warnings


def editable_run(repo, run_id, revision):
    run = repo.get(run_id, 'run')
    task = repo.get(run['task_id'], 'task')
    if run['status'] != 'completed' or task.get('active_run') != run_id or task['status'] == 'running':
        raise HTTPException(409, '只能修改当前已完成的审查版本')
    if run['revision'] != revision:
        raise HTTPException(409, '修订已在其他页面变更，请刷新后重试')
    if any(task.get(key) != run['input'].get(key) for key in ('title', 'text', 'role', 'type', 'mode', 'scale', 'background', 'focus', 'reference_text', 'references', 'checklist', 'source_id')):
        raise HTTPException(409, '合同或审查条件已改变，请重新审查后再生成修订')
    return run


def revision_anchor(run, issue):
    redline = issue.get('redline')
    if redline and redline.get('change_type') == 'insert':
        return '', 'insert'
    original = (redline or {}).get('original_text') or issue.get('evidence')
    if not original:
        segment = next((s for s in run['result'].get('segments', []) if s['id'] == issue.get('segment_id')), {})
        original = segment.get('content')
    if not original or run['input']['text'].count(original) != 1:
        raise HTTPException(409, '此意见无法唯一定位原文，请先人工核对条款')
    return original, 'replace'


def save_candidate(repo, run, issue_id, redline, explanation, instruction, source, stamp):
    editable_run(repo, run['id'], run['revision'])
    result = deepcopy(run['result'])
    issue = next(item for item in result['issues'] if item['id'] == issue_id)
    history = deepcopy(run.get('revision_history', {}))
    versions = history.setdefault(issue_id, [])
    if not versions and issue.get('redline'):
        versions.append({'version': 1, 'redline': deepcopy(issue['redline']), 'explanation': '首次审查生成的建议',
                         'instruction': '', 'source': 'initial', 'created_at': run.get('completed_at', run['created_at'])})
    versions.append({'version': len(versions) + 1, 'redline': deepcopy(redline), 'explanation': explanation,
                     'instruction': instruction, 'source': source, 'created_at': stamp})
    issue['redline'] = redline
    issue.pop('rewrite_warning', None)
    issue['revision_explanation'] = explanation
    applied = [identifier for identifier in run['applied'] if identifier != issue_id]
    candidate = {**run, 'result': result, 'applied': applied}
    revised_text(candidate, applied + [issue_id])
    decisions = {**run.get('decisions', {}), issue_id: 'pending'}
    saved = repo.update(run['id'], {'result': result, 'applied': applied, 'decisions': decisions,
                                   'revision_history': history}, run['revision'])
    task = repo.get(run['task_id'], 'task')
    if task.get('active_run') == run['id'] and task['status'] == 'completed':
        repo.update(task['id'], {'status': 'pending_review'})
    return saved
