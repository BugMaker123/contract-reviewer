"""Durable, revision-protected forms before they become business records."""
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from .security import require, actor

router=APIRouter(prefix='/api/work-copies')


def repo():
    from .main import repository
    return repository


class WorkCopy(BaseModel):
    key: str = Field(min_length=1,max_length=200)
    payload: dict
    revision: int | None = Field(default=None,ge=1)

    def validate_size(self):
        if len(json.dumps(self.payload,ensure_ascii=False).encode())>4_000_000:
            raise HTTPException(413,'草稿过大，请拆分内容')
        if self.key.startswith('drafting'):
            require('drafting.edit')
        else:
            require('review.edit')


@router.get('')
def recent(key: str):
    require('drafting.view' if key.startswith('drafting') else 'review.view')
    # Even administrators' working forms are personal.
    rows=[r for r in repo().list('work_copy') if r['key']==key and r.get('user_id')==(actor.get() or {}).get('id')]
    return {'items':rows[:1]}


@router.post('')
def create(body: WorkCopy):
    require('drafting.create' if body.key.startswith('drafting') else 'review.create')
    body.validate_size()
    return repo().create('work_copy',{'key':body.key,'payload':body.payload,'user_id':(actor.get() or {}).get('id')})


@router.get('/{identifier}')
def detail(identifier: str):
    row=repo().get(identifier,'work_copy')
    if row.get('user_id')!=(actor.get() or {}).get('id'):
        raise HTTPException(404,'草稿不存在')
    require('drafting.view' if row['key'].startswith('drafting') else 'review.view')
    return row


@router.put('/{identifier}')
def save(identifier: str,body: WorkCopy):
    body.validate_size()
    row=detail(identifier)
    if body.key!=row['key'] or body.revision is None:
        raise HTTPException(422,'草稿类型或版本无效')
    return repo().update(identifier,{'payload':body.payload},body.revision)
