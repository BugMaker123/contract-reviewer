import asyncio
from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest
from fastapi import HTTPException
from backend.store import Repository
from backend.revisions import editable_run
from backend.source_storage import save_source
from backend.review_queue import LocalReviewQueue


def finished(repo):
    task = repo.create('task', {'title': 'test', 'text': 'contract', 'status': 'draft', 'active_run': None})
    run = repo.start_run(task['id'])
    run = repo.update_review(run['id'], {'status': 'completed'}, task_changes={'status': 'completed', 'active_run': run['id']})
    return task, run


def test_queued_revision_cannot_be_committed(tmp_path):
    repo = Repository(tmp_path / 'test.db')
    task, run = finished(repo)
    repo.update(task['id'], {'status': 'queued'})
    with pytest.raises(HTTPException) as error:
        editable_run(repo, run['id'], run['revision'])
    assert error.value.status_code == 409
    with pytest.raises(HTTPException):
        repo.update_review(run['id'], {'applied': ['bad']}, run['revision'], editable=True)
    assert 'applied' in repo.get(run['id']) and repo.get(run['id'])['applied'] == []


def test_second_write_failure_rolls_back_run(tmp_path):
    repo = Repository(tmp_path / 'test.db')
    task, run = finished(repo)
    with repo.connect() as db:
        db.execute("CREATE TRIGGER fail_task BEFORE UPDATE ON objects WHEN OLD.kind='task' BEGIN SELECT RAISE(ABORT, 'injected'); END")
    with pytest.raises(sqlite3.IntegrityError):
        repo.update_review(run['id'], {'decisions': {'x': 'applied'}}, run['revision'], editable=True, strict=False)
    assert repo.get(run['id']) == run
    assert repo.get(task['id'])['status'] == 'completed'


def test_catalog_concurrent_uniqueness_and_history_rollback(tmp_path):
    repo = Repository(tmp_path / 'test.db')
    def create(index):
        try:
            return repo.create('category', {'name': ' Same ', 'code': str(index)})['id']
        except HTTPException:
            return None
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(value is not None for value in pool.map(create, range(4))) == 1
    checklist = repo.create('checklist', {'name': 'list', 'version': 1})
    repo.update(checklist['id'], {'version': 2}, 1)
    with pytest.raises(HTTPException):
        repo.update(checklist['id'], {'version': 3}, 1)
    assert len(repo.list('checklist_version', checklist['id'])) == 1
    with pytest.raises(HTTPException):
        repo.create('checklist', {'category_id': 'deleted'})


def test_source_database_failure_removes_published_file(tmp_path, monkeypatch):
    repo = Repository(tmp_path / 'test.db')
    def fail(*args, **kwargs):
        raise OSError('disk failure')
    monkeypatch.setattr(repo, 'create', fail)
    with pytest.raises(OSError):
        save_source(repo, tmp_path / 'sources', {'extension': '.txt'}, b'contract')
    assert list((tmp_path / 'sources').iterdir()) == []


def test_global_queue_capacity_and_release():
    async def scenario():
        queue = LocalReviewQueue(global_limit=2, max_waiting=1)
        tickets = [queue.enqueue(str(i), i, lambda state: None) for i in range(3)]
        assert [ticket.status for ticket in tickets] == ['running', 'running', 'queued']
        with pytest.raises(HTTPException) as error:
            queue.enqueue('extra', 4, lambda state: None)
        assert error.value.status_code == 429
        queue.release(tickets[0])
        assert tickets[2].status == 'running'
        for ticket in tickets:
            queue.release(ticket)
        assert not queue.groups
    asyncio.run(scenario())


def test_parser_timeout_and_zip_budget(monkeypatch):
    import subprocess
    from io import BytesIO
    from zipfile import ZipFile, ZIP_DEFLATED
    from backend.document_parse import extract
    from backend import document_import
    archive = BytesIO()
    with ZipFile(archive, 'w', ZIP_DEFLATED) as output:
        for index in range(2049):
            output.writestr(str(index) + '.xml', b'x')
    with pytest.raises(HTTPException) as error:
        extract(archive.getvalue(), '.docx')
    assert error.value.status_code == 413
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 45)
    monkeypatch.setattr(document_import.subprocess, 'run', timeout)
    with pytest.raises(HTTPException) as error:
        document_import.parse_document(b'text', '.txt')
    assert error.value.status_code == 413
    # Capacity is returned even on forced termination.
    assert document_import._slots.acquire(blocking=False)
    document_import._slots.release()


def test_backup_roundtrip_and_hash_verification(tmp_path, monkeypatch):
    import sys
    from backend import data_maintenance
    root = tmp_path / 'data'
    repo = Repository(root / 'lexis.db')
    sources = root / 'sources'
    source = save_source(repo, sources, {'extension': '.txt'}, b'contract')
    backup = tmp_path / 'backup'
    monkeypatch.setattr(data_maintenance, 'Repository', lambda *args: Repository(*args) if args else repo)
    monkeypatch.setattr(data_maintenance, 'SOURCES', sources)
    monkeypatch.setattr(sys, 'argv', ['maintenance', 'backup', str(backup)])
    data_maintenance.main()
    restored = Repository(tmp_path / 'restored' / 'lexis.db')
    restored_sources = tmp_path / 'restored' / 'sources'
    monkeypatch.setattr(data_maintenance, 'Repository', lambda *args: Repository(*args) if args else restored)
    monkeypatch.setattr(data_maintenance, 'SOURCES', restored_sources)
    monkeypatch.setattr(sys, 'argv', ['maintenance', 'restore', str(backup)])
    data_maintenance.main()
    assert data_maintenance.verify(restored, restored_sources)['issues'] == []
    (restored_sources / (source['id'] + '.txt')).write_bytes(b'changed')
    assert data_maintenance.verify(restored, restored_sources)['issues'][0]['problem'] == 'checksum'


def test_unsaved_editor_refresh_protection(isolated_workspace):
    from test_ui_composition import live_server
    from playwright.sync_api import sync_playwright, expect
    with live_server() as base, sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        task = page.request.post(base + '/api/tasks', data={'title': 'Refresh protection', 'text': 'Original contract'}).json()
        page.goto(base + '/workbench?task=' + task['id'])
        page.get_by_role('button', name='编辑正文', exact=True).click()
        page.get_by_role('textbox', name='编辑合同正文').fill('Changed contract')
        assert page.evaluate("() => !window.dispatchEvent(new Event('beforeunload', {cancelable: true}))")
        page.get_by_role('button', name='保存正文', exact=True).click()
        page.get_by_role('button', name='保存', exact=True).click()
        expect(page.get_by_text('工作内容已保存', exact=True)).to_be_visible()
        assert not page.evaluate("() => !window.dispatchEvent(new Event('beforeunload', {cancelable: true}))")
        assert page.request.get(base + '/api/tasks/' + task['id']).json()['text'] == 'Changed contract'
        browser.close()


def test_source_commit_then_response_failure_preserves_bytes(tmp_path, monkeypatch):
    repo = Repository(tmp_path / 'test.db')
    create = repo.create
    def committed_then_failed(*args, **kwargs):
        create(*args, **kwargs)
        raise OSError('response failed after commit')
    monkeypatch.setattr(repo, 'create', committed_then_failed)
    directory = tmp_path / 'sources'
    with pytest.raises(OSError):
        save_source(repo, directory, {'extension': '.txt'}, b'contract')
    source = repo.list('source')[0]
    assert (directory / (source['id'] + '.txt')).read_bytes() == b'contract'


def test_slow_subscriber_survives_bounded_replay(tmp_path):
    import json
    from backend import review_jobs
    repo = Repository(tmp_path / 'test.db')
    _, run = finished(repo)
    async def scenario():
        job = review_jobs.ReviewJob()
        review_jobs._jobs[review_jobs.key(repo, run['id'])] = job
        job.publish('progress', {'index': -1})
        subscription = review_jobs.subscribe(repo, run['id'])
        await anext(subscription)
        for index in range(1024):
            job.publish('progress', {'index': index})
        job.done = True
        values = [json.loads(event.split('data: ')[1])['index'] async for event in subscription]
        assert values == list(range(512, 1024))
        assert len(job.events) == 512
        review_jobs._jobs.pop(review_jobs.key(repo, run['id']))
    asyncio.run(scenario())


def test_upload_body_limit_precedes_multipart_parsing():
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app) as client:
        response = client.post('/api/contracts/import', content=b'x', headers={'Content-Length': str(12 * 1024 * 1024), 'Content-Type': 'multipart/form-data; boundary=x'})
        assert response.status_code == 413
