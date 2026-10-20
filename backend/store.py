"""Small, durable repository. Each review input is an immutable snapshot."""
import json
import hashlib
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException


def now():
    return datetime.now(timezone.utc).isoformat()


class Repository:
    def __init__(self, path=None):
        self.path = str(path or os.environ.get('LEXIS_DB_PATH') or Path(os.environ.get('LEXIS_DATA_DIR') or Path(__file__).parent.parent / 'data') / 'lexis.db')
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS objects (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, parent TEXT,
                data TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
                created TEXT NOT NULL, updated TEXT NOT NULL)''')
            db.execute('CREATE INDEX IF NOT EXISTS objects_kind_parent ON objects(kind, parent)')
            db.execute('CREATE TABLE IF NOT EXISTS review_events (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, data TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS review_events_run ON review_events(run_id,id)')
            for field in ('name', 'code'):
                try:
                    db.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS category_unique_{field} ON objects(lower(trim(json_extract(data,'$.{field}')))) WHERE kind='category' AND trim(coalesce(json_extract(data,'$.{field}'),''))!=''")
                except sqlite3.IntegrityError as error:
                    raise RuntimeError('分类名称或编码存在重复，请备份后合并重复分类再启动') from error
            db.execute('CREATE INDEX IF NOT EXISTS objects_kind_updated ON objects(kind, updated DESC, id)')
            db.execute("CREATE INDEX IF NOT EXISTS objects_checklist_category ON objects(json_extract(data,'$.category_id')) WHERE kind='checklist'")

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def unpack(row):
        return {**json.loads(row['data']), 'id': row['id'], 'revision': row['revision'],
                'created_at': row['created'], 'updated_at': row['updated']}

    def get(self, identifier, kind=None):
        with self.connect() as db:
            row = db.execute('SELECT * FROM objects WHERE id=?', (identifier,)).fetchone()
        if row is None or (kind and row['kind'] != kind):
            raise HTTPException(404, '记录不存在')
        return self.unpack(row)

    def list(self, kind, parent=None):
        with self.connect() as db:
            if parent is None:
                rows = db.execute('SELECT * FROM objects WHERE kind=? ORDER BY updated DESC', (kind,)).fetchall()
            else:
                rows = db.execute('SELECT * FROM objects WHERE kind=? AND parent=? ORDER BY created DESC', (kind, parent)).fetchall()
        return [self.unpack(row) for row in rows]

    def checklist_summaries(self):
        with self.connect() as db:
            rows = db.execute("SELECT id,revision,created,updated,json_remove(data,'$.items') AS data,json_array_length(data,'$.items') AS item_count FROM objects WHERE kind='checklist' ORDER BY updated DESC").fetchall()
        return [{**self.unpack(row), 'item_count': row['item_count']} for row in rows]

    def catalog_page(self, kind, page, page_size, search='', category_id=None, archived=None, published=None):
        """Filter/count/page in SQLite; list cards never load checklist bodies."""
        clauses, params = ['o.kind=?'], [kind]
        if search.strip():
            fields = ['name', 'code', 'description'] if kind == 'category' else ['name', 'description', 'contract_type']
            terms = [f"instr(lower(coalesce(json_extract(o.data,'$.{field}'),'')),lower(?))>0" for field in fields]
            params.extend([search.strip()] * len(fields))
            if kind == 'checklist':
                terms.append("EXISTS (SELECT 1 FROM json_each(o.data,'$.items') i WHERE instr(lower(coalesce(json_extract(i.value,'$.title'),'') || ' ' || coalesce(json_extract(i.value,'$.requirement'),'')),lower(?))>0)")
                params.append(search.strip())
            clauses.append('(' + ' OR '.join(terms) + ')')
        if category_id:
            clauses.append("json_extract(o.data,'$.category_id')=?")
            params.append(category_id)
        for field, value in [('archived', archived), ('published', published)]:
            if value is not None:
                clauses.append(f"coalesce(json_extract(o.data,'$.{field}'),0)=?")
                params.append(int(value))
        where = ' AND '.join(clauses)
        if kind == 'category':
            projection = "o.*, (SELECT count(*) FROM objects c WHERE c.kind='checklist' AND json_extract(c.data,'$.category_id')=o.id) AS checklist_count"
            order = "coalesce(json_extract(o.data,'$.sort_order'),0), json_extract(o.data,'$.name'), o.id"
        else:
            projection = "o.id,o.kind,o.parent,json_remove(o.data,'$.items') AS data,o.revision,o.created,o.updated,json_array_length(o.data,'$.items') AS item_count"
            order = 'o.updated DESC, o.id'
        with self.connect() as db:
            total = db.execute('SELECT count(*) FROM objects o WHERE ' + where, params).fetchone()[0]
            page = min(page, max(1, (total + page_size - 1) // page_size))
            rows = db.execute(f'SELECT {projection} FROM objects o WHERE {where} ORDER BY {order} LIMIT ? OFFSET ?', [*params, page_size, (page - 1) * page_size]).fetchall()
        count_key = 'checklist_count' if kind == 'category' else 'item_count'
        return {'items': [{**self.unpack(row), count_key: row[count_key]} for row in rows],
                'total': total, 'page': page, 'page_size': page_size}

    def delete_catalog(self, identifier, kind, expected_revision):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM objects WHERE id=? AND kind=?', (identifier, kind)).fetchone()
            if row is None:
                raise HTTPException(404, '记录不存在')
            if row['revision'] != expected_revision:
                raise HTTPException(409, '记录已被修改，请刷新后重试')
            if kind == 'category' and db.execute("SELECT 1 FROM objects WHERE kind='checklist' AND json_extract(data,'$.category_id')=? LIMIT 1", (identifier,)).fetchone():
                raise HTTPException(409, '该分类下仍有清单（含已归档清单），请先迁移或删除清单')
            db.execute('DELETE FROM objects WHERE id=?', (identifier,))
            if kind == 'checklist':
                db.execute("DELETE FROM objects WHERE kind='checklist_version' AND parent=?", (identifier,))
        return {'deleted': identifier}

    def _catalog_constraints(self, db, kind, data, identifier=None):
        if kind == 'category':
            for field in ('name', 'code'):
                value = data.get(field, '').strip().casefold()
                if value and any(json.loads(row['data']).get(field, '').strip().casefold() == value for row in db.execute("SELECT data FROM objects WHERE kind='category' AND id!=?", (identifier or '',))):
                    raise HTTPException(409, '分类名称或编码已存在')
        if kind == 'checklist' and data.get('category_id'):
            if not db.execute("SELECT 1 FROM objects WHERE kind='category' AND id=?", (data['category_id'],)).fetchone():
                raise HTTPException(409, '分类已删除，请重新选择')

    def create(self, kind, data, parent=None, identifier=None):
        identifier, stamp = identifier or uuid4().hex, now()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self._catalog_constraints(db, kind, data)
            db.execute('INSERT INTO objects(id,kind,parent,data,created,updated) VALUES(?,?,?,?,?,?)',
                       (identifier, kind, parent, json.dumps(data, ensure_ascii=False), stamp, stamp))
        return self.get(identifier, kind)

    def summaries(self, kind):
        """Lists never load full contract bodies or perform a query for each review result."""
        if kind == 'task':
            query = '''SELECT t.id,t.revision,t.created AS created_at,t.updated AS updated_at,
                json_extract(t.data,'$.title') AS title,json_extract(t.data,'$.type') AS type,
                json_extract(t.data,'$.mode') AS mode,json_extract(t.data,'$.scale') AS scale,
                json_extract(t.data,'$.status') AS status,json_extract(t.data,'$.archived') AS archived,
                json_extract(t.data,'$.active_run') AS active_run,
                json_extract(r.data,'$.result.summary.compliance_score') AS score,
                COALESCE(json_array_length(json_extract(r.data,'$.applied')),0) AS applied_count
                FROM objects t LEFT JOIN objects r ON r.id=json_extract(t.data,'$.active_run')
                WHERE t.kind='task' ORDER BY t.updated DESC'''
        else:
            query = '''SELECT id,revision,created AS created_at,updated AS updated_at,
                json_extract(data,'$.title') AS title,json_extract(data,'$.status') AS status,
                json_extract(data,'$.archived') AS archived FROM objects WHERE kind='draft' ORDER BY updated DESC'''
        with self.connect() as db:
            return [dict(row) for row in db.execute(query).fetchall()]

    def task_page(self, page=1, page_size=10, search='', mode=None, status=None, archived=None, from_stamp=None, to_stamp=None):
        clauses, params = ["t.kind='task'"], []
        updated = "CASE WHEN r.updated > t.updated THEN r.updated ELSE t.updated END"
        if search.strip():
            clauses.append("instr(lower(coalesce(json_extract(t.data,'$.title'),'')),lower(?))>0")
            params.append(search.strip())
        for field, value in (('mode', mode), ('status', status), ('archived', archived)):
            if value is not None:
                clauses.append(f"coalesce(json_extract(t.data,'$.{field}'),0)=?")
                params.append(int(value) if field == 'archived' else value)
        for operator, stamp in (('>=', from_stamp), ('<', to_stamp)):
            if stamp:
                clauses.append(f'{updated} {operator} ?'); params.append(stamp)
        source = " FROM objects t LEFT JOIN objects r ON r.id=json_extract(t.data,'$.active_run') WHERE " + ' AND '.join(clauses)
        projection = f"""t.id,t.revision,t.created AS created_at,{updated} AS updated_at,
            json_extract(t.data,'$.title') AS title,json_extract(t.data,'$.type') AS type,
            json_extract(t.data,'$.mode') AS mode,json_extract(t.data,'$.status') AS status,
            json_extract(t.data,'$.archived') AS archived,json_extract(t.data,'$.active_run') AS active_run,
            json_extract(r.data,'$.number') AS run_number,json_extract(r.data,'$.status') AS run_status,
            coalesce(json_array_length(json_extract(r.data,'$.applied')),0) AS applied_count"""
        with self.connect() as db:
            total = db.execute('SELECT count(*)' + source, params).fetchone()[0]
            page = min(page, max(1, (total + page_size - 1) // page_size))
            rows = db.execute('SELECT ' + projection + source + f' ORDER BY {updated} DESC,t.id LIMIT ? OFFSET ?',
                              [*params, page_size, (page - 1) * page_size]).fetchall()
        return {'items': [dict(row) for row in rows], 'total': total, 'page': page, 'page_size': page_size}

    def update(self, identifier, changes, expected_revision=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM objects WHERE id=?', (identifier,)).fetchone()
            if row is None:
                raise HTTPException(404, '记录不存在')
            if expected_revision is not None and expected_revision != row['revision']:
                raise HTTPException(409, '记录已在其他页面修改，请重新打开后再保存')
            data = json.loads(row['data'])
            data.update(changes)
            self._catalog_constraints(db, row['kind'], data, identifier)
            if row['kind'] == 'checklist' and 'version' in changes:
                stamp = now()
                db.execute('INSERT INTO objects(id,kind,parent,data,created,updated) VALUES(?,?,?,?,?,?)',
                           (uuid4().hex, 'checklist_version', identifier, json.dumps(self.unpack(row), ensure_ascii=False), stamp, stamp))
            db.execute('UPDATE objects SET data=?, revision=revision+1, updated=? WHERE id=?',
                       (json.dumps(data, ensure_ascii=False), now(), identifier))
        return self.get(identifier)

    def append_trace(self, run_id, entry):
        """Append small telemetry rows without rewriting contract/result snapshots."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT INTO review_events(run_id,data) VALUES(?,?)', (run_id, json.dumps(entry, ensure_ascii=False)))
            db.execute('DELETE FROM review_events WHERE run_id=? AND id NOT IN (SELECT id FROM review_events WHERE run_id=? ORDER BY id DESC LIMIT 256)', (run_id, run_id))

    def update_review(self, run_id, changes, expected_revision=None, *, task_changes=None, editable=False, strict=True):
        """Validate and commit the run and its task under one write lock."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT * FROM objects WHERE id=? AND kind='run'", (run_id,)).fetchone()
            if row is None:
                raise HTTPException(404, '审查版本不存在')
            run = self.unpack(row)
            task_row = db.execute("SELECT * FROM objects WHERE id=? AND kind='task'", (run['task_id'],)).fetchone()
            if task_row is None:
                raise HTTPException(404, '任务不存在')
            task = self.unpack(task_row)
            if expected_revision is not None and row['revision'] != expected_revision:
                raise HTTPException(409, '审查版本已改变，请刷新后重试')
            if editable:
                if run['status'] != 'completed' or task.get('active_run') != run_id or task['status'] in ('running', 'queued'):
                    raise HTTPException(409, '只能修改当前已完成的审查版本')
                if strict:
                    from .revisions import matching_input
                    if not matching_input(task, run['input']):
                        raise HTTPException(409, '合同或审查条件已改变，请重新审查')
                if task_changes is None and task['status'] == 'completed':
                    task_changes = {'status': 'pending_review'}
            for record, delta in ((run, changes), (task, task_changes)):
                if not delta:
                    continue
                data = {k: v for k, v in record.items() if k not in ('id', 'revision', 'created_at', 'updated_at')}
                data.update(delta)
                db.execute('UPDATE objects SET data=?,revision=revision+1,updated=? WHERE id=?',
                           (json.dumps(data, ensure_ascii=False), now(), record['id']))
        return self.get(run_id, 'run')

    def run_summaries(self, task_id):
        with self.connect() as db:
            rows = db.execute("SELECT id,revision,created,updated,json_object('number',json_extract(data,'$.number'),'status',json_extract(data,'$.status'),'error',json_extract(data,'$.error'),'baseline_kind',json_extract(data,'$.baseline_kind'),'parent_run_id',json_extract(data,'$.parent_run_id'),'queue',json_extract(data,'$.queue')) AS data FROM objects WHERE kind='run' AND parent=? ORDER BY created DESC", (task_id,)).fetchall()
        return [self.unpack(row) for row in rows]

    def complete_review(self, task_id, task_revision, run_id, run_revision, confirmations):
        """Commit confirmation and completion together after validating both versions."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            rows = {}
            for identifier, revision in ((task_id, task_revision), (run_id, run_revision)):
                row = db.execute('SELECT * FROM objects WHERE id=?', (identifier,)).fetchone()
                if row is None or row['revision'] != revision:
                    raise HTTPException(409, '审核期间记录已改变，请刷新后重新确认')
                rows[identifier] = json.loads(row['data'])
            task, run = rows[task_id], rows[run_id]
            if task.get('active_run') != run_id or task['status'] != 'pending_review' or run['status'] != 'completed':
                raise HTTPException(409, '审查状态已改变，请刷新后重新确认')
            task['status'] = 'completed'
            run.update(completion_confirmations=confirmations, confirmed_at=now())
            for identifier, data in ((task_id, task), (run_id, run)):
                db.execute('UPDATE objects SET data=?,revision=revision+1,updated=? WHERE id=?',
                           (json.dumps(data, ensure_ascii=False), now(), identifier))
        return self.get(task_id, 'task')

    def start_run(self, task_id, baseline_kind='task', baseline_data=None, expected_task_revision=None, expected_run_revision=None):
        """Claim a task and capture its input atomically, preventing parallel starts."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT * FROM objects WHERE id=? AND kind='task'", (task_id,)).fetchone()
            if not row:
                raise HTTPException(404, '任务不存在')
            task = json.loads(row['data'])
            if expected_task_revision is not None and row['revision'] != expected_task_revision:
                raise HTTPException(409, '合同或审查条件已改变，请刷新后重新选择稿件')
            parent_run_id = task.get('active_run')
            if expected_run_revision is not None:
                previous = db.execute("SELECT revision,data FROM objects WHERE id=? AND kind='run'", (parent_run_id,)).fetchone()
                if previous is None or previous['revision'] != expected_run_revision or json.loads(previous['data'])['status'] != 'completed':
                    raise HTTPException(409, '采纳状态已改变，请刷新后重新选择稿件')
            if task.get('status') in ('running', 'queued'):
                raise HTTPException(409, '此任务已在审查中')
            if task.get('archived'):
                raise HTTPException(409, '请先恢复已归档任务')
            if baseline_data:
                task.update(baseline_data)
            task['status'] = 'running'
            identifier, stamp = uuid4().hex, now()
            snapshot = {key: task.get(key) for key in ('title', 'type', 'text', 'role', 'mode', 'scale', 'background', 'focus', 'references', 'requirements', 'execution', 'reference_text', 'checklist', 'source_id')}
            count = db.execute("SELECT count(*) FROM objects WHERE kind='run' AND parent=?", (task_id,)).fetchone()[0]
            run = {'task_id': task_id, 'number': count + 1, 'input': snapshot, 'status': 'running',
                   'parent_run_id': parent_run_id, 'baseline_kind': baseline_kind,
                   'document_digest': hashlib.sha256(snapshot['text'].encode('utf-8')).hexdigest(),
                   'result': None, 'decisions': {}, 'applied': [], 'comments': {}, 'followups': {}}
            db.execute('INSERT INTO objects(id,kind,parent,data,created,updated) VALUES(?,?,?,?,?,?)',
                       (identifier, 'run', task_id, json.dumps(run, ensure_ascii=False), stamp, stamp))
            db.execute('UPDATE objects SET data=?,revision=revision+1,updated=? WHERE id=?',
                       (json.dumps(task, ensure_ascii=False), stamp, task_id))
        return self.get(identifier, 'run')

    def interrupt_running(self):
        for kind in ('task', 'run', 'draft'):
            for obj in self.list(kind):
                if obj.get('status') in ('running', 'queued'):
                    data = {'status': 'interrupted', 'error': '服务重启，任务已中断，请重试'}
                    if obj.get('queue'):
                        data['queue'] = {**obj['queue'], 'status':'interrupted', 'position':0, 'finished_at':now()}
                    self.update(obj['id'], data)


repository = Repository()
