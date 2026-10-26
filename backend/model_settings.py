"""Server-only encrypted model credentials. Never expose decrypted settings."""
import json
import os
from urllib.parse import urlsplit
from cryptography.fernet import Fernet
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, insert, update, func
from .security import settings, model_history, require, Security, actor, stamp
from uuid import uuid4
import time
import httpx

router=APIRouter(prefix='/api/admin/model')


def security():
    from .main import repository
    return Security(repository)


def cipher():
    key=os.environ.get('LEXIS_MODEL_ENCRYPTION_KEY')
    if not key:
        raise HTTPException(503,'服务器尚未配置模型加密主密钥')
    return Fernet(key.encode())


def load_model(secret=False):
    with security().engine.connect() as db:
        raw=db.execute(select(settings.c.data).where(settings.c.id==1)).scalar()
    data=json.loads(raw) if raw else {'model_name':'deepseek-v4-flash','base_url':'https://api.deepseek.com/v1','max_retries':3}
    encrypted=data.pop('encrypted_key',None)
    data['has_api_key']=bool(encrypted or os.environ.get('DEEPSEEK_API_KEY') or os.environ.get('OPENAI_API_KEY'))
    if secret:
        data['api_key']=cipher().decrypt(encrypted.encode()).decode() if encrypted else os.environ.get('DEEPSEEK_API_KEY') or os.environ.get('OPENAI_API_KEY','')
    return data


class Settings(BaseModel):
    model_name: str = Field(min_length=1,max_length=200)
    base_url: str = Field(min_length=1,max_length=1000)
    api_key: str | None = Field(default=None,max_length=2000)
    max_retries: int = Field(default=3,ge=0,le=10)


@router.get('')
def read():
    require('models.manage')
    return load_model()


def validate_address(address):
    parsed=urlsplit(address)
    approved=os.environ.get('LEXIS_MODEL_ALLOWED_ORIGINS','https://api.deepseek.com').split(',')
    if parsed.scheme not in ('http','https') or parsed.username or parsed.password or parsed.query or parsed.fragment or f'{parsed.scheme}://{parsed.netloc}' not in approved:
        raise HTTPException(422,'模型地址须在服务器批准的地址列表内')


def add_history(db,data,action='save'):
    db.execute(insert(model_history).values(id=uuid4().hex,data=json.dumps(data,ensure_ascii=False),created=stamp(),operator=(actor.get() or {}).get('name','管理员'),action=action))


@router.put('')
def save(body: Settings):
    require('models.manage')
    validate_address(body.base_url)
    service=security()
    with service.engine.begin() as db:
        service.write_lock(db)
        old=db.execute(select(settings.c.data).where(settings.c.id==1)).scalar()
        old_data=json.loads(old) if old else {}
        if old and not db.execute(select(model_history.c.id).limit(1)).first():
            add_history(db,old_data,'baseline')
        data=body.model_dump(exclude={'api_key'})
        if body.api_key:
            data['encrypted_key']=cipher().encrypt(body.api_key.encode()).decode()
        elif old_data.get('encrypted_key'):
            data['encrypted_key']=old_data['encrypted_key']
        values={'data':json.dumps(data,ensure_ascii=False)}
        db.execute(update(settings).where(settings.c.id==1).values(**values) if old else insert(settings).values(id=1,**values))
        add_history(db,data)
        service.audit(db,'model.save','1')
    return load_model()


@router.post('/test')
async def test_connection(body: Settings):
    require('models.manage')
    validate_address(body.base_url)
    key=body.api_key or load_model(secret=True).get('api_key','')
    if not key:
        raise HTTPException(422,'请先填写 API 密钥，或保存有效的密钥配置')
    started=time.perf_counter()
    success=False
    try:
        async with httpx.AsyncClient(timeout=15.0,follow_redirects=False) as client:
            response=await client.post(body.base_url.rstrip('/')+'/chat/completions',headers={'Authorization':'Bearer '+key},json={'model':body.model_name,'messages':[{'role':'user','content':'Reply with OK.'}],'max_tokens':16,'stream':False})
        if response.status_code==200:
            payload=response.json()
            choices=payload.get('choices')
            if isinstance(choices,list) and choices and isinstance(choices[0],dict) and isinstance(choices[0].get('message'),dict) and (choices[0]['message'].get('content') or choices[0]['message'].get('reasoning_content')):
                success=True
                message='连接成功，模型响应正常'
            else:
                message='服务已连接，但未返回有效的模型回复，请检查模型名称和接口协议'
        elif response.status_code in (401,403):
            message='认证失败，请检查 API 密钥和服务访问权限'
        elif response.status_code==404:
            message='未找到模型或接口，请检查服务地址和模型名称'
        elif response.status_code==429:
            message='服务请求受限，请检查额度或稍后重试'
        else:
            message=f'模型服务返回异常（HTTP {response.status_code}）'
    except httpx.TimeoutException:
        message='连接超时（15 秒），请检查服务地址和网络'
    except httpx.RequestError:
        message='无法连接模型服务，请检查服务地址和网络'
    except (ValueError,TypeError,AttributeError,IndexError):
        message='服务返回的数据格式无效，请检查接口是否兼容'
    return {'success':success,'message':message,'latency_ms':round((time.perf_counter()-started)*1000)}


@router.get('/history')
def history(page: int=Query(default=1,ge=1),page_size: int=Query(default=5,ge=1,le=50)):
    require('models.manage')
    with security().engine.connect() as db:
        total=db.execute(select(func.count()).select_from(model_history)).scalar_one()
        rows=db.execute(select(model_history).order_by(model_history.c.created.desc(),model_history.c.id.desc()).offset((page-1)*page_size).limit(page_size)).mappings().all()
    items=[]
    for row in rows:
        data=json.loads(row['data'])
        items.append({'id':row['id'],'created':row['created'],'operator':row['operator'],'action':row['action'],'model_name':data['model_name'],'base_url':data['base_url'],'max_retries':data.get('max_retries',3),'has_api_key':bool(data.get('encrypted_key'))})
    return {'items':items,'total':total,'page':page,'page_size':page_size}


@router.post('/history/{identifier}/restore')
def restore(identifier: str):
    require('models.manage')
    service=security()
    with service.engine.begin() as db:
        service.write_lock(db)
        raw=db.execute(select(model_history.c.data).where(model_history.c.id==identifier)).scalar()
        if not raw:
            raise HTTPException(404,'历史配置不存在')
        data=json.loads(raw)
        validate_address(data['base_url'])
        if data.get('encrypted_key'):
            cipher().decrypt(data['encrypted_key'].encode())
        old=db.execute(select(settings.c.data).where(settings.c.id==1)).scalar()
        values={'data':json.dumps(data,ensure_ascii=False)}
        db.execute(update(settings).where(settings.c.id==1).values(**values) if old else insert(settings).values(id=1,**values))
        add_history(db,data,'restore')
        service.audit(db,'model.restore',identifier)
    return load_model()
