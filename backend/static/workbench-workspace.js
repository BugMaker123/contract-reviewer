/* Durable task adapter. Saves are serialized and use optimistic revisions. */
window.createWorkspaceWorkbench = function (refs) {
  const {ref, computed, watch, nextTick} = Vue;
  const taskId=ref(new URLSearchParams(location.search).get('task'));
  const selectedRun=ref(new URLSearchParams(location.search).get('run'));
  const task=ref(null), run=ref(null), loading=ref(true), hydrating=ref(true), saving=ref(false);
  const conditions=ref({mode:'deep',scale:'中立',background:'',focus:'',references:[],reference_text:'',checklist:null,source_id:null});
  const decisions=ref({}), comments=ref({}), followups=ref({}), question=ref(''), followupIssue=ref(null), followupBusy=ref(false);
  const showConditions=ref(false), exportScope=ref('current'), versions=ref([]), error=ref('');
  let queue=Promise.resolve(), timer, lastInput='', lastHandling='';
  const api=async(path,method='GET',body)=>{
    const response=await fetch(path,{method,headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});
    const data=await response.json();
    if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:data.detail?.map(item=>item.msg).join('；')||'保存失败，请重试');
    return data;
  };
  const modeName=computed(()=>({quick:'快速审查',deep:'深度审查',checklist:'清单审查',compare:'对比审查'})[conditions.value.mode]);
  const historical=computed(()=>!!selectedRun.value && selectedRun.value!==task.value?.active_run);
  const input=()=>({title:refs.contractTitle.value,type:refs.contractType.value,text:refs.contractText.value,role:refs.partyRole.value,
    mode:conditions.value.mode,scale:conditions.value.scale,background:conditions.value.background,focus:conditions.value.focus,
    references:conditions.value.references,reference_text:conditions.value.reference_text,checklist_id:conditions.value.checklist?.id||null,source_id:conditions.value.source_id||null});
  const handling=()=>({applied:[...refs.appliedIssueIds.value],decisions:{...decisions.value},comments:{...comments.value}});
  const isStale=computed(()=>{
    if(!run.value?.result) return false;
    const snapshot=run.value.input;
    return ['title','type','text','role'].some(key=>input()[key]!==snapshot[key]) ||
      ['mode','scale','background','focus','reference_text'].some(key=>conditions.value[key]!==snapshot[key]) ||
      JSON.stringify(conditions.value.references)!==JSON.stringify(snapshot.references);
  });
  const flush=async()=>{
    clearTimeout(timer);
    if(hydrating.value || historical.value) return;
    const job=async()=>{
      saving.value=true;error.value='';refs.saveStatus.value='正在保存…';
      try {
        const current=input();
        const signature=JSON.stringify(current);
        if(!taskId.value) {
          task.value=await api('/api/tasks','POST',current);taskId.value=task.value.id;
          history.replaceState(null,'','/workbench?task='+taskId.value);lastInput=signature;
        } else if(signature!==lastInput) {
          task.value=await api('/api/tasks/'+taskId.value,'PUT',{...current,revision:task.value.revision});lastInput=signature;
        }
        if(run.value?.status==='completed') {
          const changes=handling(), signature=JSON.stringify(changes);
          if(signature!==lastHandling) {
            run.value=await api('/api/runs/'+run.value.id+'/handling','PUT',{...changes,revision:run.value.revision});
            decisions.value=run.value.decisions;lastHandling=JSON.stringify(handling());
            if(task.value.status==='completed') task.value=await api('/api/tasks/'+taskId.value);
          }
        }
        refs.saveStatus.value='已保存到本机服务';
      } catch(err){error.value=err.message;refs.saveStatus.value='保存失败，请重试';throw err;}
      finally{saving.value=false;}
    };
    queue=queue.catch(()=>{}).then(job);
    return queue;
  };
  const schedule=()=>{
    if(hydrating.value||refs.isReviewing.value||historical.value||!taskId.value) return;
    refs.saveStatus.value='有待保存的修改';clearTimeout(timer);timer=setTimeout(()=>flush().catch(()=>{}),600);
  };
  watch([refs.contractTitle,refs.contractType,refs.contractText,refs.partyRole,conditions,refs.appliedIssueIds,decisions,comments],schedule,{deep:true});
  const applyRun=record=>{
    run.value=record;refs.reviewResult.value=record?.result||null;
    refs.appliedIssueIds.value=record?.applied||[];decisions.value=record?.decisions||{};comments.value=record?.comments||{};followups.value=record?.followups||{};
    refs.reviewedAt.value=record?.completed_at?new Date(record.completed_at).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai'}):'';
    refs.reviewedInput.value=record ? {text:record.input.text,title:record.input.title,type:record.input.type,role:record.input.role} : null;
    lastHandling=JSON.stringify(handling());
  };
  const refresh=async(runId)=>{
    hydrating.value=true;
    try {
      task.value=await api('/api/tasks/'+taskId.value);versions.value=task.value.runs;
      if(runId){selectedRun.value=null;history.replaceState(null,'','/workbench?task='+taskId.value);}
      applyRun(runId?await api('/api/runs/'+runId):task.value.run);
    } finally {await nextTick();hydrating.value=false;}
  };
  const load=async()=>{
    try {
      if(taskId.value) {
        task.value=await api('/api/tasks/'+taskId.value);
        let record=task.value;
        if(selectedRun.value) {
          const previous=await api('/api/runs/'+selectedRun.value);
          if(previous.task_id!==taskId.value) throw new Error('此版本不属于当前任务');
          record=previous.input;applyRun(previous);
        } else applyRun(task.value.run);
        refs.contractTitle.value=record.title;refs.contractType.value=record.type;refs.contractText.value=record.text;refs.partyRole.value=record.role;
        conditions.value={mode:record.mode,scale:record.scale,background:record.background,focus:record.focus,references:record.references,reference_text:record.reference_text,checklist:record.checklist,source_id:record.source_id||null};
        versions.value=task.value.runs;
        if(task.value.status==='running') error.value='此任务已在其他页面审查中，请稍后重新打开。';
        lastInput=JSON.stringify(input());refs.saveStatus.value='已从本机服务恢复';
      }
    } catch(err){error.value=err.message;refs.saveStatus.value='读取失败';}
    finally{await nextTick();hydrating.value=false;loading.value=false;}
  };
  const save=async()=>{try{await flush();refs.showToast('工作内容已保存');}catch(err){refs.showToast(err.message);}};
  const leaveFor=async(path)=>{try{if(taskId.value) await flush();location.href=path;}catch(err){refs.showToast('保存未完成：'+err.message);}};
  const setDecision=(issue,state)=>{
    if(isStale.value||historical.value) return;
    if(refs.appliedIssueIds.value.includes(issue.id)){refs.showToast('请先撤销该项采纳，再改变处理状态');return;}
    decisions.value={...decisions.value,[issue.id]:state};
  };
  const decisionName=id=>({pending:'待处理',applied:'已采纳',rejected:'不采纳',needs_review:'待复核'})[refs.appliedIssueIds.value.includes(id)?'applied':decisions.value[id]||'pending'];
  const exportWord=async()=>{
    try {
      await flush();if(!run.value||isStale.value) throw new Error('请先审查当前版本');
      const response=await fetch('/api/runs/'+run.value.id+'/export?scope='+exportScope.value);
      if(!response.ok){const data=await response.json();throw new Error(data.detail||'导出失败');}
      const url=URL.createObjectURL(await response.blob()),anchor=document.createElement('a');anchor.href=url;
      anchor.download=decodeURIComponent(response.headers.get('Content-Disposition')?.split("UTF-8''")[1]||'合同.docx');anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      if(response.headers.get('X-Word-Layout')==='reconstructed') refs.showToast('Word 已导出，正文按统一版式重新排版，请复核后使用');
    } catch(err){refs.showToast(err.message);error.value=err.message;}
  };
  const finish=async()=>{
    try{await flush();task.value=await api('/api/tasks/'+taskId.value+'/complete','POST',{archived:false,revision:task.value.revision});refs.showToast('已完成复核，任务记录已更新');}
    catch(err){refs.showToast(err.message);}
  };
  const ask=async(issue)=>{
    if(!question.value.trim()||followupBusy.value) return;
    followupBusy.value=true;
    try {
      await flush();
      const data=await api('/api/runs/'+run.value.id+'/followup','POST',{issue_id:issue.id,question:question.value,model_config_data:refs.getModel()});
      run.value=data;followups.value=data.followups;question.value='';
    } catch(err){refs.showToast(err.message);error.value=err.message;}
    finally{followupBusy.value=false;}
  };
  const previewFollowup=answer=>{if(answer.suggested_text) refs.copyText(answer.suggested_text);};
  return {taskId,task,run,loading,conditions,decisions,comments,followups,question,followupIssue,followupBusy,showConditions,
    exportScope,versions,error,modeName,historical,isStale,saving,load,flush,refresh,save,leaveFor,setDecision,decisionName,exportWord,finish,ask,previewFollowup};
};
