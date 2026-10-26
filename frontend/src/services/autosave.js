import { ref, watch, onScopeDispose } from 'vue';
import { api } from './auth.js';

// Keep input on failure; serialize writes and never absorb a revision conflict.
export function serverDraft(key, snapshot, restore) {
  const initialPath=location.pathname;
  const status=ref('读取中'), error=ref('');
  let record=null, ready=false, timer, last='', queue=Promise.resolve(), stopped=false, localEdited=false;
  const serialize=()=>JSON.stringify(snapshot());
  async function save() {
    clearTimeout(timer);
    queue=queue.catch(()=>{}).then(async()=>{
      if(!ready || stopped) return;
      const value=serialize();
      if(value===last) return;
      status.value='保存中'; error.value='';
      try {
        const body={key,payload:JSON.parse(value),...(record?{revision:record.revision}:{})};
        record=await api('/api/work-copies'+(record?'/'+record.id:''),record?'PUT':'POST',body);
        last=value;
        if(location.pathname===initialPath){const url=new URL(location.href); url.searchParams.set('copy',record.id); history.replaceState(history.state,'',url);}
        status.value=serialize()===last?'已保存':'待保存';
      } catch(e){status.value='保存失败';error.value=e.message;throw e;}
    });
    await queue;
    if(ready && serialize()!==last) await save();
    return record;
  }
  const initialize=async()=>{
    const before=serialize();
    try {
      const identifier=new URLSearchParams(location.search).get('copy');
      record=identifier?await api('/api/work-copies/'+encodeURIComponent(identifier)):(await api('/api/work-copies?key='+encodeURIComponent(key))).items[0];
      if(record && record.key!==key) record=null;
      const changed=localEdited || serialize()!==before;
      if(record && !changed) restore(record.payload);
      last=changed?(record?JSON.stringify(record.payload):before):serialize();
      status.value=record?'已保存':'尚未保存'; ready=true;
      if(serialize()!==last){status.value='待保存';timer=setTimeout(()=>save().catch(()=>{}),600);}
    }catch(e){status.value='读取失败';error.value=e.message;throw e;}
  };
  const loaded=initialize();
  loaded.catch(()=>{});
  watch(snapshot,()=>{if(!ready){localEdited=true;return;}if(serialize()===last)return;status.value='待保存';clearTimeout(timer);timer=setTimeout(()=>save().catch(()=>{}),600);},{deep:true});
  const unload=(event)=>{if(ready && serialize()!==last){event.preventDefault();event.returnValue='';}};
  window.addEventListener('beforeunload',unload);
  onScopeDispose(()=>{clearTimeout(timer);stopped=true;window.removeEventListener('beforeunload',unload);});
  return {status,error,loaded,save:async()=>{if(!ready)await loaded.catch(()=>initialize());return save();},clear:async()=>{restore({});await save();}};
}
