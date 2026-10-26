"""Account/role management. Authorization also applies to direct HTTP calls."""
from fastapi import APIRouter, Request, Response, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, insert, update, delete, func, or_
from uuid import uuid4
from .security import (Security, users, roles, user_roles, role_permissions, sessions,
                       actor, require, hasher, validate_password, digest, throttle, PERMISSIONS)
from argon2.exceptions import VerificationError

router = APIRouter(prefix='/api')


def service():
    from .main import repository
    return Security(repository)


class Login(BaseModel):
    username: str = Field(min_length=1,max_length=100)
    password: str = Field(min_length=1,max_length=200)


class Password(BaseModel):
    current_password: str = Field(max_length=200)
    new_password: str = Field(min_length=12,max_length=200)


@router.post('/auth/login')
def login(body: Login,request: Request,response: Response):
    throttle(request.client.host if request.client else '',body.username)
    current,token,csrf = service().login(body.username,body.password)
    # Production is HTTPS only. Tests and explicit local development may opt out.
    import os
    secure = os.environ.get('LEXIS_COOKIE_SECURE','1') != '0'
    response.set_cookie('lexis_session',token,httponly=True,secure=secure,samesite='strict',max_age=28800,path='/')
    response.set_cookie('lexis_csrf',csrf,httponly=False,secure=secure,samesite='strict',max_age=28800,path='/')
    response.headers['Cache-Control']='no-store'
    return current


@router.get('/auth/me')
def me():
    return actor.get()


@router.post('/auth/logout')
def logout(request: Request,response: Response):
    security = service()
    with security.engine.begin() as db:
        db.execute(delete(sessions).where(sessions.c.digest==digest(request.cookies.get('lexis_session',''))))
    response.delete_cookie('lexis_session',path='/')
    response.delete_cookie('lexis_csrf',path='/')
    return {'ok':True}


@router.post('/auth/password')
def password(body: Password,response: Response):
    validate_password(body.new_password)
    if body.current_password == body.new_password:
        raise HTTPException(422,'新密码须与原密码不同')
    security = service()
    with security.engine.begin() as db:
        user = db.execute(select(users).where(users.c.id==actor.get()['id']).with_for_update()).mappings().one()
        try:
            hasher.verify(user['password_hash'],body.current_password)
        except VerificationError:
            raise HTTPException(422,'原密码错误')
        db.execute(update(users).where(users.c.id==user['id']).values(password_hash=hasher.hash(body.new_password),must_change_password=False))
        db.execute(delete(sessions).where(sessions.c.user_id==user['id']))
        security.audit(db,'password.change',user['id'])
    response.delete_cookie('lexis_session',path='/')
    response.delete_cookie('lexis_csrf',path='/')
    return {'ok':True,'login_required':True}


class Account(BaseModel):
    username: str = Field(min_length=1,max_length=100)
    name: str = Field(min_length=1,max_length=200)
    role_ids: list[str] = Field(default_factory=list,max_length=100)
    active: bool = True
    password: str | None = Field(default=None,min_length=12,max_length=200)


@router.get('/admin/users')
def list_users(q: str = '', page: int | None = Query(default=None,ge=1), page_size: int = Query(default=10,ge=1,le=100), status: str = ''):
    require('users.manage')
    with service().engine.connect() as db:
        query=select(users.c.id,users.c.username,users.c.name,users.c.active,users.c.must_change_password)
        if q.strip():
            pattern='%'+q.strip().replace('!','!!').replace('%','!%').replace('_','!_')+'%'
            query=query.where(or_(users.c.username.ilike(pattern,escape='!'),users.c.name.ilike(pattern,escape='!')))
        if status in ('active','inactive'):
            query=query.where(users.c.active==(status=='active'))
        total=db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
        query=query.order_by(users.c.username,users.c.id)
        if page is not None:
            query=query.offset((page-1)*page_size).limit(page_size)
        result=[dict(row) for row in db.execute(query).mappings()]
        ids=[row['id'] for row in result]
        assignments=list(db.execute(select(user_roles).where(user_roles.c.user_id.in_(ids))).mappings()) if ids else []
        role_options=[dict(row) for row in db.execute(select(roles.c.id,roles.c.name).order_by(roles.c.name)).mappings()]
    return {'items':[{**user,'role_ids':[r['role_id'] for r in assignments if r['user_id']==user['id']]} for user in result], 'role_options':role_options,'total':total,'page':page or 1,'page_size':page_size}


def save_account(body,identifier=None):
    require('users.manage')
    if not body.username.strip() or not body.name.strip():
        raise HTTPException(422,'账号和姓名不能为空')
    security = service()
    with security.engine.begin() as db:
        security.write_lock(db)
        role_ids = set(db.execute(select(roles.c.id)).scalars())
        if not set(body.role_ids).issubset(role_ids):
            raise HTTPException(422,'角色不存在')
        username = body.username.strip().casefold()
        duplicate = db.execute(select(users.c.id).where(users.c.username==username)).scalar()
        if duplicate and duplicate != identifier:
            raise HTTPException(409,'账号已存在')
        values = {'username':username,'name':body.name.strip(),'active':body.active}
        if body.password:
            validate_password(body.password)
            values.update(password_hash=hasher.hash(body.password),must_change_password=True)
        if identifier:
            if not db.execute(select(users.c.id).where(users.c.id==identifier)).first():
                raise HTTPException(404,'账号不存在')
            # Keep the initial administrator available for recovery.
            original_roles = set(db.execute(select(user_roles.c.role_id).where(user_roles.c.user_id==identifier)).scalars())
            if 'administrator' in original_roles and (not body.active or 'administrator' not in body.role_ids):
                other = db.execute(select(users.c.id).join(user_roles,user_roles.c.user_id==users.c.id).where(
                    users.c.id!=identifier,users.c.active==True,user_roles.c.role_id=='administrator')).first()
                if not other:
                    raise HTTPException(409,'须保留至少一个启用的管理员')
            db.execute(update(users).where(users.c.id==identifier).values(**values))
            db.execute(delete(user_roles).where(user_roles.c.user_id==identifier))
            db.execute(delete(sessions).where(sessions.c.user_id==identifier))
        else:
            if not body.password:
                raise HTTPException(422,'须设置独立的初始密码')
            identifier=uuid4().hex
            db.execute(insert(users).values(id=identifier,**values))
        if body.role_ids:
            db.execute(insert(user_roles),[{'user_id':identifier,'role_id':r} for r in set(body.role_ids)])
        security.audit(db,'account.save',identifier)
    return {'id':identifier}


@router.post('/admin/users')
def create_user(body: Account):
    return save_account(body)


@router.put('/admin/users/{identifier}')
def edit_user(identifier: str,body: Account):
    return save_account(body,identifier)


class Role(BaseModel):
    name: str = Field(min_length=1,max_length=100)
    description: str = Field(default='',max_length=1000)
    permissions: list[str] = Field(default_factory=list,max_length=100)


@router.get('/admin/roles')
def list_roles(q: str = '', page: int | None = Query(default=None,ge=1), page_size: int = Query(default=10,ge=1,le=100)):
    require('roles.manage')
    with service().engine.connect() as db:
        query=select(roles)
        if q.strip():
            pattern='%'+q.strip().replace('!','!!').replace('%','!%').replace('_','!_')+'%'
            query=query.where(or_(roles.c.name.ilike(pattern,escape='!'),roles.c.description.ilike(pattern,escape='!')))
        total=db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
        query=query.order_by(roles.c.name,roles.c.id)
        if page is not None:
            query=query.offset((page-1)*page_size).limit(page_size)
        result=list(db.execute(query).mappings())
        ids=[row['id'] for row in result]
        permissions=list(db.execute(select(role_permissions).where(role_permissions.c.role_id.in_(ids))).mappings()) if ids else []
        counts=dict(db.execute(select(user_roles.c.role_id,func.count()).group_by(user_roles.c.role_id)).all())
    return {'catalog':PERMISSIONS,'items':[{**r,'member_count':counts.get(r['id'],0),'permissions':[p['permission'] for p in permissions if p['role_id']==r['id']]} for r in result],'total':total,'page':page or 1,'page_size':page_size}


def save_role(body,identifier=None):
    require('roles.manage')
    if not body.name.strip() or not set(body.permissions).issubset(PERMISSIONS):
        raise HTTPException(422,'角色名称或权限无效')
    security=service()
    with security.engine.begin() as db:
        security.write_lock(db)
        if db.execute(select(roles.c.id).where(roles.c.name==body.name.strip(),roles.c.id!=(identifier or ''))).first():
            raise HTTPException(409,'角色名称已存在')
        if identifier:
            if identifier=='administrator' and set(body.permissions)!=set(PERMISSIONS):
                raise HTTPException(409,'内置管理员须保留全部权限，请新增角色分配其他权限')
            if not db.execute(select(roles.c.id).where(roles.c.id==identifier)).first():
                raise HTTPException(404,'角色不存在')
            db.execute(update(roles).where(roles.c.id==identifier).values(name=body.name.strip(),description=body.description))
            db.execute(delete(role_permissions).where(role_permissions.c.role_id==identifier))
            affected=select(user_roles.c.user_id).where(user_roles.c.role_id==identifier)
            db.execute(delete(sessions).where(sessions.c.user_id.in_(affected)))
        else:
            identifier=uuid4().hex
            db.execute(insert(roles).values(id=identifier,name=body.name.strip(),description=body.description))
        if body.permissions:
            db.execute(insert(role_permissions),[{'role_id':identifier,'permission':p} for p in set(body.permissions)])
        security.audit(db,'role.save',identifier)
    return {'id':identifier}


@router.post('/admin/roles')
def create_role(body: Role):
    return save_role(body)


@router.put('/admin/roles/{identifier}')
def edit_role(identifier: str,body: Role):
    return save_role(body,identifier)


@router.delete('/admin/users/{identifier}')
def delete_user(identifier: str):
    require('users.manage')
    security=service()
    with security.engine.begin() as db:
        security.write_lock(db)
        user=db.execute(select(users).where(users.c.id==identifier)).mappings().first()
        if not user:
            raise HTTPException(404,'账号不存在')
        if identifier==actor.get()['id']:
            raise HTTPException(409,'不能删除当前登录账号')
        assigned=set(db.execute(select(user_roles.c.role_id).where(user_roles.c.user_id==identifier)).scalars())
        if user['active'] and 'administrator' in assigned:
            other=db.execute(select(users.c.id).join(user_roles,user_roles.c.user_id==users.c.id).where(users.c.id!=identifier,users.c.active==True,user_roles.c.role_id=='administrator')).first()
            if not other:
                raise HTTPException(409,'须保留至少一个启用的管理员')
        db.execute(delete(sessions).where(sessions.c.user_id==identifier))
        db.execute(delete(user_roles).where(user_roles.c.user_id==identifier))
        db.execute(delete(users).where(users.c.id==identifier))
        security.audit(db,'account.delete',identifier)
    return {'ok':True}


@router.delete('/admin/roles/{identifier}')
def delete_role(identifier: str):
    require('roles.manage')
    security=service()
    with security.engine.begin() as db:
        security.write_lock(db)
        if not db.execute(select(roles.c.id).where(roles.c.id==identifier)).first():
            raise HTTPException(404,'角色不存在')
        if identifier=='administrator':
            raise HTTPException(409,'不能删除内置管理员角色')
        if db.execute(select(user_roles.c.user_id).where(user_roles.c.role_id==identifier)).first():
            raise HTTPException(409,'该角色仍有成员使用，请先调整成员角色')
        db.execute(delete(role_permissions).where(role_permissions.c.role_id==identifier))
        db.execute(delete(roles).where(roles.c.id==identifier))
        security.audit(db,'role.delete',identifier)
    return {'ok':True}
