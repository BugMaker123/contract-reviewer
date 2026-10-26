"""Authentication, CSRF and default-deny API permissions for web deployments."""
import hmac
import os
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from .security import actor, digest, enabled, Security


def permission_for(path,method):
    read=method in ('GET','HEAD')
    if path.startswith('/api/admin/'):
        return {'users':'users.manage','roles':'roles.manage','model':'models.manage'}.get(path.split('/')[3])
    if path.startswith('/api/auth/'):
        return 'authenticated'
    if path=='/api/model/check':
        return 'models.manage'
    if path.startswith('/api/work-copies'):
        return 'authenticated'
    if path.startswith('/api/categories') or path.startswith('/api/template-groups'):
        return 'catalog.view' if read else 'catalog.maintain'
    if path.startswith('/api/checklists'):
        return 'checklists.view' if read else 'checklists.maintain'
    if path.startswith('/api/template-validations'):
        return 'validation.view'
    if path.startswith('/api/contract-templates'):
        if path.endswith('/validate'):
            return 'validation.execute'
        if path.endswith('/publish'):
            return 'templates.publish'
        return 'templates.view' if read else 'templates.maintain'
    if path.startswith('/api/contract-drafts'):
        return ('drafting.export' if path.endswith('/word') else 'drafting.view') if read else (
            'drafting.generate' if path.endswith('/generate') else 'drafting.edit' if method=='PUT' else 'drafting.create')
    if path.startswith(('/api/tasks','/api/runs','/api/reports')):
        if read:
            return 'review.export' if path.endswith(('/export','/document','/review-document','/preview-file')) or path.startswith('/api/reports') else 'review.view'
        if path.endswith('/archive'):
            return 'review.archive'
        if path.endswith(('/review/stream','/retry','/cancel','/verify-current','/regenerate','/followup')):
            return 'review.execute'
        return 'review.create' if path=='/api/tasks' else 'review.edit'
    if path.startswith('/api/sources'):
        return 'source.view' if read else 'review.edit'
    if path.startswith('/api/contracts/'):
        return 'upload'
    if path in ('/api/samples','/api/graph/info'):
        return 'review.view'
    if path in ('/api/requirements/extract','/api/documents/compare'):
        return 'review.edit'
    # Old transient review APIs cannot satisfy the persisted-job contract.
    return None


async def authenticate_request(request,call_next,repository):
    if not enabled() or not request.url.path.startswith('/api/') or request.method=='OPTIONS':
        return await call_next(request)
    path=request.url.path
    if path in ('/api/health','/api/client-config','/api/auth/login'):
        return await call_next(request)
    security=Security(repository)
    # Hash/database work runs outside the event loop.
    import asyncio
    identity=await asyncio.to_thread(security.authenticate,request.cookies.get('lexis_session'))
    if not identity:
        return JSONResponse({'detail':'请先登录'},401)
    current,csrf_digest=identity
    context=actor.set(current)
    try:
        if request.method not in ('GET','HEAD','OPTIONS'):
            csrf=request.headers.get('x-csrf-token','')
            if not csrf or not hmac.compare_digest(digest(csrf),csrf_digest):
                raise HTTPException(403,'页面安全凭据无效，请刷新后重试')
        if current['must_change_password'] and path not in ('/api/auth/me','/api/auth/password','/api/auth/logout'):
            raise HTTPException(403,'首次登录或重置密码后须先修改密码')
        permission=permission_for(path,request.method)
        allowed=permission=='authenticated' or permission in current['permissions']
        if permission=='upload':
            allowed=bool(set(current['permissions']) & {'review.create','review.edit','drafting.create','templates.maintain','validation.execute'})
        if permission=='source.view':
            allowed=bool(set(current['permissions']) & {'review.view','templates.view','validation.view'})
        if not allowed:
            raise HTTPException(403,'没有此操作权限')
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        if response.status_code<400 and ('export' in path or path.endswith(('/publish','/download','/word'))):
            def audit():
                with security.engine.begin() as db:
                    security.audit(db,'export' if 'publish' not in path else 'publish',path)
            await asyncio.to_thread(audit)
        return response
    except HTTPException as error:
        return JSONResponse({'detail':error.detail},error.status_code)
    finally:
        actor.reset(context)
