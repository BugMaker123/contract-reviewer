"""Session authentication and fixed permission catalog for the single team."""
import hashlib
import os
import secrets
import time
import weakref
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import HTTPException
from sqlalchemy import (MetaData, Table, Column, String, Integer, Text, Boolean,
                        select, delete, insert, update, text)

actor = ContextVar('actor', default=None)
hasher = PasswordHasher()
PERMISSIONS = {
    **{f'review.{action}': f'合同审查：{label}' for action, label in
       [('view','查看'),('create','新建'),('edit','编辑'),('execute','执行'),('export','导出'),('archive','归档')]},
    **{f'drafting.{action}': f'合同起草：{label}' for action, label in
       [('view','查看'),('create','新建'),('edit','编辑'),('generate','生成'),('export','导出')]},
    **{f'{kind}.{action}': f'{label}：{operation}' for kind, label in [('templates','模板'),('checklists','清单')]
       for action, operation in [('view','查看'),('maintain','维护'),('publish','发布')]},
    'catalog.view': '分类与分组：查看', 'catalog.maintain': '分类与分组：维护',
    'validation.view': '模板核验：查看', 'validation.execute': '模板核验：执行',
    'users.manage': '系统管理：账号', 'roles.manage': '系统管理：角色权限',
    'models.manage': '系统管理：模型配置', 'records.all': '查看全部业务记录',
}
LEGAL_PERMISSIONS = {p for p in PERMISSIONS if p.split('.')[0] not in ('users','roles','models','records')
                     and not p.endswith(('.maintain','.publish'))}
PUBLIC_KINDS = {'category','checklist','checklist_version','template_group','contract_template','template_release'}

metadata = MetaData()
users = Table('users', metadata, Column('id',String(64),primary_key=True),
    Column('username',String(100),unique=True,nullable=False), Column('name',String(200),nullable=False),
    Column('password_hash',Text,nullable=False), Column('active',Boolean,nullable=False),
    Column('must_change_password',Boolean,nullable=False))
roles = Table('roles', metadata, Column('id',String(64),primary_key=True),
    Column('name',String(100),unique=True,nullable=False), Column('description',Text,nullable=False))
user_roles = Table('user_roles',metadata,Column('user_id',String(64),primary_key=True),Column('role_id',String(64),primary_key=True))
role_permissions = Table('role_permissions',metadata,Column('role_id',String(64),primary_key=True),Column('permission',String(100),primary_key=True))
sessions = Table('sessions',metadata,Column('digest',String(64),primary_key=True),Column('user_id',String(64),index=True,nullable=False),
    Column('csrf_digest',String(64),nullable=False),Column('expires',String(40),nullable=False))
logs = Table('operation_logs',metadata,Column('id',String(64),primary_key=True),Column('user_id',String(64)),
    Column('action',String(100),nullable=False),Column('target',String(200)),Column('created',String(40),nullable=False))
settings = Table('model_settings',metadata,Column('id',Integer,primary_key=True),Column('data',Text,nullable=False))

model_history = Table('model_settings_history',metadata,
    Column('id',String(64),primary_key=True),Column('data',Text,nullable=False),
    Column('created',String(40),nullable=False),Column('operator',String(200),nullable=False),
    Column('action',String(30),nullable=False))


def enabled():
    return os.environ.get('LEXIS_WEB_MODE') == '1' or bool(os.environ.get('LEXIS_DATABASE_URL'))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def require(permission):
    current = actor.get()
    if enabled() and (not current or permission not in current['permissions']):
        raise HTTPException(403, '没有此操作权限')


class Security:
    initialized = weakref.WeakSet()

    def __init__(self, repository):
        self.engine = repository.database.engine
        if self.engine not in self.initialized:
            metadata.create_all(self.engine)
            self.initialized.add(self.engine)

    def audit(self, db, action, target='', user_id=None):
        db.execute(insert(logs).values(id=uuid4().hex,user_id=user_id or (actor.get() or {}).get('id'),
                   action=action,target=target,created=stamp()))

    def write_lock(self,db):
        if self.engine.dialect.name=='mysql':
            db.execute(text('SELECT id FROM repository_lock WHERE id=1 FOR UPDATE'))
        else:
            db.exec_driver_sql('BEGIN IMMEDIATE')

    def bootstrap(self, username, name, password):
        validate_password(password)
        with self.engine.begin() as db:
            self.write_lock(db)
            if db.execute(select(users.c.id).limit(1)).first():
                raise ValueError('Accounts already initialized')
            identifier = uuid4().hex
            db.execute(insert(users).values(id=identifier,username=username.strip().casefold(),name=name,
                       password_hash=hasher.hash(password),active=True,must_change_password=True))
            for role_id, role_name, permissions in [('administrator','管理员',PERMISSIONS),('legal','法务用户',LEGAL_PERMISSIONS)]:
                db.execute(insert(roles).values(id=role_id,name=role_name,description=role_name))
                db.execute(insert(role_permissions),[{'role_id':role_id,'permission':p} for p in permissions])
            db.execute(insert(user_roles).values(user_id=identifier,role_id='administrator'))
            self.audit(db,'bootstrap',identifier,identifier)
        return identifier

    def identity(self, db, user_id):
        user = db.execute(select(users).where(users.c.id==user_id,users.c.active==True)).mappings().first()
        if not user:
            return None
        permissions = list(db.execute(select(role_permissions.c.permission).join(user_roles,
            user_roles.c.role_id==role_permissions.c.role_id).where(user_roles.c.user_id==user_id)).scalars())
        return {k:user[k] for k in ('id','username','name','must_change_password')} | {'permissions':sorted(set(permissions))}

    def authenticate(self, token):
        if not token:
            return None
        with self.engine.begin() as db:
            session = db.execute(select(sessions).where(sessions.c.digest==digest(token),sessions.c.expires>stamp())).mappings().first()
            if not session:
                return None
            current = self.identity(db,session['user_id'])
            return (current,session['csrf_digest']) if current else None

    def login(self, username, password):
        with self.engine.begin() as db:
            user = db.execute(select(users).where(users.c.username==username.strip().casefold()).with_for_update()).mappings().first()
            valid = False
            try:
                # The same expensive hash runs for unknown/disabled users.
                valid = hasher.verify(user['password_hash'] if user else _dummy_hash, password)
            except (VerificationError,InvalidHashError):
                pass
            if not valid or not user or not user['active']:
                raise HTTPException(401,'账号或密码错误')
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            db.execute(delete(sessions).where(sessions.c.expires<=stamp()))
            db.execute(insert(sessions).values(digest=digest(token),user_id=user['id'],csrf_digest=digest(csrf),
                expires=(datetime.now(timezone.utc)+timedelta(hours=8)).isoformat()))
            self.audit(db,'login',user['id'],user['id'])
            return self.identity(db,user['id']),token,csrf

    def revoke(self,user_id):
        with self.engine.begin() as db:
            db.execute(delete(sessions).where(sessions.c.user_id==user_id))


def validate_password(password):
    if not 12 <= len(password) <= 200:
        raise HTTPException(422,'密码长度须为 12–200 个字符')


_dummy_hash = hasher.hash(secrets.token_urlsafe(32))
# Single-process, bounded login throttle. Both source IP and account are limited.
_attempts = {}


def throttle(ip, username):
    now = time.monotonic()
    for key in list(_attempts):
        _attempts[key] = [t for t in _attempts[key] if now-t<300]
        if not _attempts[key]:
            del _attempts[key]
    keys = [('ip',ip),('account',username.strip().casefold())]
    if any(len(_attempts.get(key,[])) >= (30 if key[0]=='ip' else 10) for key in keys):
        raise HTTPException(429,'登录尝试过多，请 5 分钟后重试')
    for key in keys:
        _attempts.setdefault(key,[]).append(now)
