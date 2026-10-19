"""Only the current, manually completed review may be delivered."""
from fastapi import HTTPException
from .revisions import matching_input


def exportable_run(repo, run_id):
    if not run_id:
        raise HTTPException(409, '请先完成审核，再导出文件')
    run = repo.get(run_id, 'run')
    task = repo.get(run['task_id'], 'task')
    if task.get('status') != 'completed' or task.get('active_run') != run_id or run.get('status') != 'completed' or not matching_input(task, run['input']):
        raise HTTPException(409, '请先完成审核，再导出文件')
    return run


def exportable_report(repo, run_id):
    run = repo.get(run_id, 'run')
    task = repo.get(run['task_id'], 'task')
    if task.get('status') not in ('pending_review', 'completed') or task.get('active_run') != run_id or run.get('status') != 'completed' or not matching_input(task, run['input']):
        raise HTTPException(409, '请先完成当前合同审查，再导出审查意见书')
    return run
