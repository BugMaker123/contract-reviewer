"""Contract template catalogue; source originals remain immutable."""
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from fastapi.responses import FileResponse
from . import workspace_api

router = APIRouter()


class GroupInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default='', max_length=2000)
    revision: int | None = Field(default=None, ge=1)

    @field_validator('name')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('名称不能为空')
        return value.strip()


class TemplateInput(GroupInput):
    group_id: str
    source_id: str


@router.get('/api/template-groups')
def groups():
    repo = workspace_api.repo
    templates = repo.list('contract_template')
    return [{**g, 'template_count': sum(t['group_id'] == g['id'] for t in templates)}
            for g in repo.list('template_group')]


@router.post('/api/template-groups')
def create_group(body: GroupInput):
    return workspace_api.repo.create('template_group', body.model_dump(exclude={'revision'}))


@router.put('/api/template-groups/{identifier}')
def update_group(identifier: str, body: GroupInput):
    workspace_api.repo.get(identifier, 'template_group')
    if body.revision is None:
        raise HTTPException(422, '缺少记录版本，请刷新后重试')
    return workspace_api.repo.update(identifier, body.model_dump(exclude={'revision'}), body.revision)


@router.delete('/api/template-groups/{identifier}')
def delete_group(identifier: str, revision: int = Query(ge=1)):
    return workspace_api.repo.delete_catalog(identifier, 'template_group', revision)


@router.get('/api/contract-templates')
def templates(q: str = Query('', max_length=200), group_id: str = '',
              page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    rows = workspace_api.repo.list('contract_template')
    rows = [r for r in rows if (not group_id or r['group_id'] == group_id)
            and q.strip().casefold() in (r['name'] + ' ' + r['description'] + ' ' + r['filename']).casefold()]
    return {'items': rows[(page-1)*page_size:page*page_size], 'total': len(rows)}


def template_data(body):
    repo = workspace_api.repo
    repo.get(body.group_id, 'template_group')
    source = repo.get(body.source_id, 'source')
    if source['extension'] not in ('.docx', '.pdf', '.txt'):
        raise HTTPException(422, '不支持的模板格式')
    from .word_export import SOURCES
    if not (SOURCES / (source['id'] + source['extension'])).is_file():
        raise HTTPException(422, '原件缺失，请重新上传')
    return {**body.model_dump(exclude={'revision'}), 'filename': source['name'], 'extension': source['extension']}


@router.post('/api/contract-templates')
def create_template(body: TemplateInput):
    return workspace_api.repo.create('contract_template', template_data(body))


@router.get('/api/contract-templates/{identifier}')
def template_detail(identifier: str):
    return workspace_api.repo.get(identifier, 'contract_template')


@router.put('/api/contract-templates/{identifier}')
def update_template(identifier: str, body: TemplateInput):
    existing = workspace_api.repo.get(identifier, 'contract_template')
    if body.revision is None:
        raise HTTPException(422, '缺少记录版本，请刷新后重试')
    data = template_data(body)
    if existing['source_id'] != body.source_id:
        data.update(review_draft=None, review_status='draft', release_id=None)
    return workspace_api.repo.update(identifier, data, body.revision)


@router.delete('/api/contract-templates/{identifier}')
def delete_template(identifier: str, revision: int = Query(ge=1)):
    return workspace_api.repo.delete_catalog(identifier, 'contract_template', revision)


@router.get('/api/contract-templates/{identifier}/download')
def download_template(identifier: str):
    from .word_export import SOURCES
    record = workspace_api.repo.get(identifier, 'contract_template')
    source = workspace_api.repo.get(record['source_id'], 'source')
    path = SOURCES / (source['id'] + source['extension'])
    if not path.is_file():
        raise HTTPException(404, '原件缺失，请重新上传')
    return FileResponse(path, filename=Path(source['name']).name,
                        headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
