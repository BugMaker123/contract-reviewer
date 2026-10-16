"""Small, durable repository. Each review input is an immutable snapshot."""
import json
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
        self.path = str(path or os.environ.get('LEXIS_DB_PATH') or Path(__file__).parent.parent / 'data' / 'lexis.db')
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS objects (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, parent TEXT,
                data TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
                created TEXT NOT NULL, updated TEXT NOT NULL)''')
            db.execute('CREATE INDEX IF NOT EXISTS objects_kind_parent ON objects(kind, parent)')
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

    def create(self, kind, data, parent=None):
        identifier, stamp = uuid4().hex, now()
        with self.connect() as db:
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
            db.execute('UPDATE objects SET data=?, revision=revision+1, updated=? WHERE id=?',
                       (json.dumps(data, ensure_ascii=False), now(), identifier))
        return self.get(identifier)

    def start_run(self, task_id):
        """Claim a task and capture its input atomically, preventing parallel starts."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT * FROM objects WHERE id=? AND kind='task'", (task_id,)).fetchone()
            if not row:
                raise HTTPException(404, '任务不存在')
            task = json.loads(row['data'])
            if task.get('status') == 'running':
                raise HTTPException(409, '此任务已在审查中')
            if task.get('archived'):
                raise HTTPException(409, '请先恢复已归档任务')
            task['status'] = 'running'
            identifier, stamp = uuid4().hex, now()
            snapshot = {key: task.get(key) for key in ('title', 'type', 'text', 'role', 'mode', 'scale', 'background', 'focus', 'references', 'reference_text', 'checklist', 'source_id')}
            count = db.execute("SELECT count(*) FROM objects WHERE kind='run' AND parent=?", (task_id,)).fetchone()[0]
            run = {'task_id': task_id, 'number': count + 1, 'input': snapshot, 'status': 'running',
                   'result': None, 'decisions': {}, 'applied': [], 'comments': {}, 'followups': {}}
            db.execute('INSERT INTO objects(id,kind,parent,data,created,updated) VALUES(?,?,?,?,?,?)',
                       (identifier, 'run', task_id, json.dumps(run, ensure_ascii=False), stamp, stamp))
            db.execute('UPDATE objects SET data=?,revision=revision+1,updated=? WHERE id=?',
                       (json.dumps(task, ensure_ascii=False), stamp, task_id))
        return self.get(identifier, 'run')

    def interrupt_running(self):
        for kind in ('task', 'run', 'draft'):
            for obj in self.list(kind):
                if obj.get('status') == 'running':
                    self.update(obj['id'], {'status': 'interrupted', 'error': '服务重启，任务已中断，请重试'})


repository = Repository()
