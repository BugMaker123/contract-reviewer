"""AI revisions and native Word review previews for the current review run."""
import json
from io import BytesIO

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from . import workspace_review
from .store import now
from .stance_policy import STANCE_INSTRUCTIONS, changes_identity, model_input
from .rewrite_policy import REWRITE_INSTRUCTIONS, REWRITE_WARNING, adds_signing_reminder
from .export_policy import exportable_run
from .word_export import paragraphs, visible_paragraph_text
from .workspace_models import RevisionGenerate, RevisionEdit, RevisionRestore
from .revisions import editable_run, revision_anchor, save_candidate, review_document, revision_plan
from .review_policy import requirements_for, verify_requirements


def create_revision_router(repository, builder):
    router = APIRouter()

    def issue_for(run, issue_id):
        issue = next((item for item in run['result']['issues'] if item['id'] == issue_id), None)
        if not issue:
            raise HTTPException(404, '修订条目不存在')
        return issue

    def completed(run_id):
        run = repository().get(run_id, 'run')
        if run['status'] != 'completed':
            raise HTTPException(409, '审查尚未完成')
        return run

    @router.post('/api/runs/{run_id}/issues/{issue_id}/regenerate')
    async def regenerate(run_id: str, issue_id: str, request: RevisionGenerate):
        repo = repository()
        run = editable_run(repo, run_id, request.revision)
        issue = issue_for(run, issue_id)
        if any(item.get('conflict_with') for item in run['result'].get('requirement_findings', [])):
            raise HTTPException(409, '审查要求存在冲突，请明确要求并重新审查后再生成修订。')
        original, kind = revision_anchor(run, issue)
        prompt = f'''{STANCE_INSTRUCTIONS}{REWRITE_INSTRUCTIONS}
为合同中选定的一处条款重新生成可直接替换的完整修订文本。
仅返回 JSON {{"suggested_text":"完整替代条款","explanation":"本次调整说明"}}。
保留原有条款编号和未涉及的内容；不得编造金额、日期、主体、税率等交易事实，不新增待确认占位符。
所选条款：{original or '需补充的缺失条款'}
原审查意见：{json.dumps(issue, ensure_ascii=False)}
此前建议：{json.dumps(run.get('revision_history', {}).get(issue_id, [])[-3:], ensure_ascii=False)}
审查立场与交易背景：{json.dumps(model_input(run['input']), ensure_ascii=False)}
本次调整要求：{request.instruction or '保留风险防控目标，换一种更清晰且可执行的表述。'}'''
        try:
            data = await workspace_review.model_json(request.model_config_data.model_dump(), prompt)
            suggested = data.get('suggested_text')
            explanation = data.get('explanation', '')
            if (not isinstance(suggested, str) or not suggested.strip() or len(suggested) > 20000 or
                    not isinstance(explanation, str) or len(explanation) > 5000 or
                    suggested.strip() == original.strip() or
                    suggested.count('待确认') > original.count('待确认') or
                    suggested.strip() == (issue.get('redline') or {}).get('suggested_text', '').strip()):
                raise ValueError('模型未返回有效的新修订')
        except Exception:
            raise HTTPException(502, 'AI 未能生成有效的新修订，请检查模型配置或调整要求后重试。上一版建议已保留。')
        if changes_identity(original, suggested):
            raise HTTPException(422, 'AI 修订改变了合同主体的供需身份或交易方向，已保留原建议；请依据正文人工核对。')
        if adds_signing_reminder(original, suggested):
            raise HTTPException(422, REWRITE_WARNING + '原建议已保留。')
        requirements = requirements_for(run['input'])
        proposed = run['input']['text'].replace(original, suggested, 1) if original else run['input']['text'] + '\n' + suggested
        verification = await verify_requirements(run['input'], requirements, request.model_config_data.model_dump(), workspace_review.model_json, text=proposed)
        return save_candidate(repo, run, issue_id, {'original_text': original, 'suggested_text': suggested, 'change_type': kind},
                              explanation, request.instruction, 'ai', now(), verification=verification)

    @router.put('/api/runs/{run_id}/issues/{issue_id}/revision')
    def edit_revision(run_id: str, issue_id: str, request: RevisionEdit):
        repo = repository()
        run = editable_run(repo, run_id, request.revision)
        original, kind = revision_anchor(run, issue_for(run, issue_id))
        if not request.suggested_text.strip() or request.suggested_text.strip() == original.strip():
            raise HTTPException(422, '修订内容不能为空或与原文相同')
        return save_candidate(repo, run, issue_id, {'original_text': original, 'suggested_text': request.suggested_text, 'change_type': kind},
                              '人工调整了修订建议', '', 'manual', now())

    @router.post('/api/runs/{run_id}/issues/{issue_id}/revision/restore')
    def restore_revision(run_id: str, issue_id: str, request: RevisionRestore):
        repo = repository()
        run = editable_run(repo, run_id, request.revision)
        issue_for(run, issue_id)
        version = next((item for item in run.get('revision_history', {}).get(issue_id, []) if item['version'] == request.version), None)
        if not version:
            raise HTTPException(404, '修订历史版本不存在')
        return save_candidate(repo, run, issue_id, version['redline'], f'恢复第 {request.version} 版建议', '', 'restore', now())

    @router.get('/api/runs/{run_id}/review-document/info')
    def document_info(run_id: str, display: str = 'markup'):
        run = completed(run_id)
        document, layout, warnings = review_document(run, repository(), builder, display)
        content = [visible_paragraph_text(p._p) for p in paragraphs(document)]
        ids, _ = revision_plan(run)
        items = [{**issue, 'state': 'applied' if issue['id'] in run['applied'] else run.get('decisions', {}).get(issue['id'], 'pending'),
                  'in_document': issue['id'] in ids} for issue in run['result']['issues']]
        suffix = '-修订稿' if display == 'markup' else '-当前稿' if display == 'current' else '-原始稿'
        return {'id': run['input'].get('source_id'), 'name': run['input']['title'] + suffix + '.docx', 'extension': '.docx',
                'text': '\n'.join(content), 'paragraphs': content, 'layout': layout, 'review_items': items,
                'revision_warnings': warnings, 'revision': run['revision']}

    @router.get('/api/runs/{run_id}/review-document')
    def document_file(run_id: str, display: str = 'markup'):
        return document_response(run_id, display, False)

    @router.get('/api/runs/{run_id}/review-document/preview')
    def document_preview(run_id: str, display: str = 'markup'):
        return document_response(run_id, display, True)

    def document_response(run_id, display, preview):
        run = completed(run_id) if preview else exportable_run(repository(), run_id)
        document, layout, _ = review_document(run, repository(), builder, display)
        buffer = BytesIO()
        document.save(buffer)
        buffer.seek(0)
        from urllib.parse import quote
        name = run['input']['title'] + ('-修订稿' if display == 'markup' else '-当前稿' if display == 'current' else '-原始稿') + '.docx'
        return StreamingResponse(buffer, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                 headers={'Content-Disposition': ("inline" if preview else "attachment") + "; filename*=UTF-8''" + quote(name),
                                          'Cache-Control': 'no-store', 'X-Word-Layout': layout})

    return router
