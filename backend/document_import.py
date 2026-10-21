"""Four isolated parsers at most, each terminated after 45 seconds."""
import json
import os
import subprocess
import sys
from pathlib import Path
from threading import BoundedSemaphore
from fastapi import HTTPException

_slots = BoundedSemaphore(4)


def parse_document(content, extension):
    if not _slots.acquire(timeout=0.1):
        raise HTTPException(503, '文件解析繁忙，请稍后重试')
    try:
        try:
            command = ([sys.executable, '--parse-document', extension] if getattr(sys, 'frozen', False)
                       else [sys.executable, '-m', 'backend.document_parse', extension])
            result = subprocess.run(command, input=content,
                                    capture_output=True, timeout=45, cwd=Path(__file__).parent.parent, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            data = json.loads(result.stdout.decode('utf-8'))
        except subprocess.TimeoutExpired:
            raise HTTPException(413, '文档解析超过 45 秒，请拆分文档或粘贴正文')
        except (ValueError, OSError):
            raise HTTPException(422, '文件无法解析，请检查是否损坏或加密，或改用粘贴文本')
        if 'error' in data:
            raise HTTPException(data['status'], data['error'])
        return data['text']
    finally:
        _slots.release()


class ImportBodyLimit:
    """Reject oversized multipart bodies before the multipart parser spools them."""
    def __init__(self, app, limit=11 * 1024 * 1024):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope.get('path') != '/api/contracts/import' or scope.get('method') != 'POST':
            return await self.app(scope, receive, send)
        from fastapi.responses import JSONResponse
        messages, size = [], 0
        length = dict(scope.get('headers', [])).get(b'content-length', b'0')
        try:
            size = int(length)
        except ValueError:
            pass
        if size > self.limit:
            return await JSONResponse({'detail': '上传请求超过 11 MB（文件上限 10 MB）'}, status_code=413)(scope, receive, send)
        size = 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            size += len(message.get('body', b''))
            if size > self.limit:
                return await JSONResponse({'detail': '上传请求超过 11 MB（文件上限 10 MB）'}, status_code=413)(scope, receive, send)
            messages.append(message)
            if not message.get('more_body', False):
                break
        iterator = iter(messages)
        async def replay():
            try:
                return next(iterator)
            except StopIteration:
                return await receive()
        await self.app(scope, replay, send)
