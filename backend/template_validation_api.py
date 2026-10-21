"""Read-only saved template validations; pass/fail is computed from the rules."""
from typing import Literal
from fastapi import APIRouter, Query
from .template_review import repo

router = APIRouter(prefix='/api/template-validations')


@router.get('')
def records(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100),
            q: str = Query('', max_length=200), passed: Literal['all','true','false'] = 'all'):
    clauses, params = ["kind='template_validation'"], []
    if q.strip():
        clauses.append("instr(lower(json_extract(data,'$.filename') || ' ' || json_extract(data,'$.template_name')), lower(?))>0")
        params.append(q.strip())
    if passed != 'all':
        clauses.append("CASE WHEN json_extract(data,'$.report.status')='pass' THEN 1 ELSE 0 END=?")
        params.append(1 if passed == 'true' else 0)
    where = ' AND '.join(clauses)
    with repo().connect() as db:
        total = db.execute('SELECT count(*) FROM objects WHERE '+where,params).fetchone()[0]
        rows = db.execute("SELECT id,revision,created AS created_at,updated AS updated_at, "
            "json_extract(data,'$.filename') AS filename,json_extract(data,'$.template_name') AS template_name, "
            "json_extract(data,'$.version') AS version, "
            "json_extract(data,'$.report.status') AS check_status,CASE WHEN json_extract(data,'$.report.status')='pass' THEN 1 ELSE 0 END AS passed "
            'FROM objects WHERE '+where+' ORDER BY created DESC,id DESC LIMIT ? OFFSET ?',
            [*params,page_size,(page-1)*page_size]).fetchall()
    return {'items':[{**dict(row),'passed':bool(row['passed'])} for row in rows], 'total':total}


@router.get('/{identifier}')
def detail(identifier: str):
    record = repo().get(identifier,'template_validation')
    # Legacy human decisions remain in storage but never determine the computed outcome.
    return {**{k:v for k,v in record.items() if k != 'confirmation'},
            'status':'completed','passed':record['report']['status'] == 'pass'}
