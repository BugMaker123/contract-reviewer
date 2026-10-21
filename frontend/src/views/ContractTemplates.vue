<script setup>
import { ref, reactive, computed, onMounted, onActivated, watch, nextTick } from 'vue';
import ReviewIcon from '../components/portal/ReviewIcon.vue';
import { readDocument } from '../portal/services/documents.js';
import { usePortalShell } from '../stores/portal.js';

const { api, notify } = usePortalShell();
const status=ref('all'), manageGroups=ref(false), actionMenu=ref(null), menuElement=ref(null), uploadedFilename=ref('');
const statusNames={unconfigured:'待配置',reviewing:'待核验',ready:'待发布',published:'已发布'};
const totalTemplates=computed(()=>groups.value.reduce((sum,g)=>sum+g.template_count,0));
const activeGroupName=computed(()=>group.value?groupName(group.value):'全部模板');
const dateTime=value=>new Date(value).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false});
function more(row,event){const rect=event.currentTarget.getBoundingClientRect();actionMenu.value={row,x:Math.max(12,Math.min(rect.right-164,window.innerWidth-176)),y:Math.max(12,Math.min(rect.bottom+6,window.innerHeight-210))};nextTick(()=>menuElement.value?.focus());}
function menuAction(action){const row=actionMenu.value.row;actionMenu.value=null;if(action==='preview')showPreview(row);else if(action==='edit')edit('template',row);else askDelete('template',row);}

const groups = ref([]), rows = ref([]), total = ref(0), page = ref(1), search = ref(''), group = ref('');
const busy = ref(false), loading = ref(false), error = ref(''), modalError = ref('');
const editor = ref(null), preview = ref(null), removal = ref(null), selectedFile = ref(null);
const fileInput = ref(null), dragging = ref(false);
const form = reactive({ name: '', description: '', group_id: '', source_id: '', revision: null });
const pages = computed(() => Math.max(1, Math.ceil(total.value / 10)));
const groupName = id => groups.value.find(g => g.id === id)?.name || '—';
let requestSequence = 0;
async function load() {
  const sequence = ++requestSequence;
  loading.value = true;
  try {
    const [g, result] = await Promise.all([api('/api/template-groups'), api('/api/contract-templates?' + new URLSearchParams({q: search.value, group_id: group.value, page: page.value, status:status.value}))]);
    if (sequence !== requestSequence) return;
    groups.value = g; rows.value = result.items.map(row=>{const fields=row.review_draft?.source_id===row.source_id?row.review_draft.fields||[]:[];const count=row.field_count??fields.length;const confirmed=row.confirmed_count??fields.filter(f=>f.confirmed).length;return {...row,field_count:count,confirmed_count:confirmed,configuration_status:row.configuration_status||(row.review_status==='published'?'published':count?confirmed===count?'ready':'reviewing':'unconfigured')};}); total.value = result.total;
    if (page.value > pages.value) page.value = pages.value;
    error.value = '';
  } catch (e) { if (sequence === requestSequence) error.value = e.message; }
  finally { if (sequence === requestSequence) loading.value = false; }
}
watch([search, group, status], () => { if (page.value !== 1) page.value = 1; else load(); });
watch(page, load);
onMounted(load);
onActivated(load);
function edit(kind, row = null) {
  modalError.value = ''; selectedFile.value = null; uploadedFilename.value='';
  Object.assign(form, {name: row?.name || '', description: row?.description || '', group_id: row?.group_id || group.value || groups.value.find(g=>g.name==='未分组')?.id || '', source_id: row?.source_id || '', revision: row?.revision || null});
  editor.value = {kind, row};
}
async function save() {
  busy.value = true; modalError.value = '';
  try {
    const {kind, row} = editor.value;
    let body = {name: form.name.trim(), description: form.description, revision: form.revision};
    if (!body.name) throw new Error('请填写名称');
    if (kind === 'template') {
      if (selectedFile.value) {
        const upload = await readDocument(selectedFile.value);
        form.source_id = upload.source_id;
        uploadedFilename.value=selectedFile.value.name;selectedFile.value = null;
      }
      if (!form.source_id) throw new Error('请上传模板文件');
      if (!form.group_id) {
        let fallback=groups.value.find(g=>g.name==='未分组');
        if(!fallback){
          try{fallback=await api('/api/template-groups','POST',{name:'未分组',description:''});}
          catch(e){const latest=await api('/api/template-groups');fallback=latest.find(g=>g.name==='未分组');if(!fallback)throw e;}
        }
        form.group_id=fallback.id;
      }
      body = {...body, group_id: form.group_id, source_id: form.source_id};
    }
    const base = kind === 'group' ? '/api/template-groups' : '/api/contract-templates';
    await api(base + (row ? '/' + row.id : ''), row ? 'PUT' : 'POST', body);
    editor.value = null; notify(row?'修改已保存':kind==='group'?'分组已创建':'模板已添加，可继续配置填写区域');await load();
  } catch (e) { modalError.value = e.message; }
  finally { busy.value = false; }
}
function chooseFile(event) {
  selectedFile.value = event.target.files[0] || null;
  if (selectedFile.value && !form.name) form.name = selectedFile.value.name.replace(/\.[^.]+$/, '');
}
function dropFile(event) {
  dragging.value = false;
  if (!busy.value && event.dataTransfer.files.length) chooseFile({target: {files: event.dataTransfer.files}});
}
function askDelete(kind, row) { modalError.value = ''; removal.value = {kind, row}; }
async function remove() {
  busy.value = true;
  try {
    const {kind, row} = removal.value;
    await api((kind === 'group' ? '/api/template-groups/' : '/api/contract-templates/') + row.id + '?revision=' + row.revision, 'DELETE');
    if (kind === 'group' && group.value === row.id) group.value = '';
    removal.value = null; await load();
  } catch (e) { modalError.value = e.message; }
  finally { busy.value = false; }
}
async function showPreview(row) {
  try { preview.value = await api('/api/contract-templates/' + row.id); }
  catch (e) { error.value = e.message; }
}
const previewUrl = computed(() => !preview.value ? '' : preview.value.extension === '.docx'
  ? '/static/document-preview.html?readonly=1&source=' + encodeURIComponent(preview.value.source_id)
  : '/api/sources/' + encodeURIComponent(preview.value.source_id) + '/file');
</script>

<template>
  <section class="checklists-page templates-page">
    <header class="checklists-heading">
      <div><h1>合同模板</h1><p>管理模板分组、填写规则与发布版本。</p></div>
      <div class="catalog-heading-actions"><button class="button" :disabled="busy" @click="edit('group')"><ReviewIcon name="plus"/>新建分组</button><button class="button primary" :disabled="busy" @click="edit('template')"><ReviewIcon name="plus"/>新增模板</button></div>
    </header>
    <p v-if="error" class="notice" role="alert">{{error}} <button @click="load">重试</button></p>
    <div class="template-layout">
      <aside class="card group-panel">
        <div class="group-heading"><strong>模板分组</strong><button class="text-action" :class="{active:manageGroups}" @click="manageGroups=!manageGroups">{{manageGroups?'完成':'管理'}}</button></div>
        <button class="group-select" :class="{selected:!group}" @click="group='' "><ReviewIcon name="categories"/><span>全部模板</span><b>{{totalTemplates}}</b></button>
        <div class="group-divider"></div>
        <div v-for="g in groups" :key="g.id" class="group-row" :class="{selected:group===g.id}">
          <button class="group-name" :title="g.description||g.name" @click="group=g.id"><ReviewIcon name="templates"/><span>{{g.name}}</span><b>{{g.template_count}}</b></button>
          <div v-if="manageGroups" class="group-management"><button class="text-action" :aria-label="'编辑分组 '+g.name" @click="edit('group',g)">编辑</button><button class="text-action muted" :aria-label="'删除分组 '+g.name" @click="askDelete('group',g)">删除</button></div>
        </div>
        <p v-if="!groups.length" class="group-empty">暂未创建分组。新增模板时也可先保存到“未分组”。</p>
        <button class="group-new" @click="edit('group')"><ReviewIcon name="plus"/>新建模板分组</button>
      </aside>
      <div class="card template-list">
        <div class="template-filters"><div class="template-list-heading"><h2>{{activeGroupName}}</h2><span>{{total}} 个模板</span></div><div class="template-filter-controls"><div class="catalog-search"><ReviewIcon name="search"/><input v-model="search" aria-label="搜索合同模板" placeholder="搜索模板名称、文件名" maxlength="200"/></div><select v-model="status" class="field status-filter" aria-label="筛选配置状态"><option value="all">全部状态</option><option v-for="(name,key) in statusNames" :key="key" :value="key">{{name}}</option></select></div></div>
        <div class="checklists-table-scroll">
          <table class="data-table template-table"><thead><tr><th>模板名称</th><th>所属分组</th><th>配置状态</th><th>更新时间</th><th>操作</th></tr></thead>
            <tbody><tr v-for="row in rows" :key="row.id">
              <td><div class="template-name-cell"><span class="template-file-icon" :class="row.extension?.slice(1)"><ReviewIcon name="document"/><small>{{row.extension?.slice(1).toUpperCase()}}</small></span><div><RouterLink v-if="row.extension==='.docx'" class="template-name" :title="row.filename" :to="'/templates/'+row.id+'/review'">{{row.name}}</RouterLink><button v-else class="template-name" :title="row.filename" @click="showPreview(row)">{{row.name}}</button><p>{{row.description|| (row.extension==='.docx'?'支持填写区域配置与合同验证':'原件归档与预览')}}</p></div></div></td>
              <td><span class="template-group-tag">{{groupName(row.group_id)}}</span></td>
              <td><span class="template-state" :class="row.configuration_status"><i></i>{{statusNames[row.configuration_status]||'待配置'}}</span><small class="template-field-summary">{{row.field_count?`${row.confirmed_count} / ${row.field_count} 个字段已确认`:'尚未配置填写区域'}}</small></td>
              <td class="template-date">{{dateTime(row.updated_at)}}</td>
              <td><div class="template-row-actions"><RouterLink v-if="row.extension==='.docx'" class="configure-link" :to="'/templates/'+row.id+'/review'">{{row.configuration_status==='published'?'维护模板':'配置模板'}}</RouterLink><button v-else class="configure-link" @click="showPreview(row)">查看模板</button><button class="template-more" :aria-label="'更多操作 '+row.name" @click="more(row,$event)">更多 <span class="catalog-chevron"></span></button></div></td>
            </tr></tbody>
          </table>
        </div>
        <div v-if="loading" class="empty" role="status">正在加载模板…</div>
        <div v-else-if="!rows.length" class="catalog-empty"><ReviewIcon name="templates"/><h3>{{search||status!=='all'?'没有符合条件的模板':'这个分组还没有模板'}}</h3><p>{{search||status!=='all'?'调整关键词或配置状态后再试。':'填写模板名称并导入文件，即可开始配置。'}}</p><button v-if="!search&&status==='all'" class="button primary" @click="edit('template')">新增模板</button></div>
        <div class="template-pagination"><span>共 {{total}} 个模板 · 第 {{page}} / {{pages}} 页</span><div><button class="button" :disabled="page===1||loading" @click="page--">上一页</button><button class="button" :disabled="page>=pages||loading" @click="page++">下一页</button></div></div>
      </div>
    </div>
  </section>
  <Teleport to="body">
    <div v-if="actionMenu" class="catalog-menu-shade" @click="actionMenu=null" @keydown.esc="actionMenu=null"><div ref="menuElement" class="catalog-action-menu" role="menu" tabindex="-1" :style="{left:actionMenu.x+'px',top:actionMenu.y+'px'}" @click.stop><button role="menuitem" @click="menuAction('preview')">预览原件</button><a role="menuitem" :href="'/api/contract-templates/'+actionMenu.row.id+'/download'" @click="actionMenu=null">下载原件</a><button role="menuitem" @click="menuAction('edit')">编辑信息 / 调整分组</button><button role="menuitem" class="danger" @click="menuAction('delete')">删除模板</button></div></div>
    <div v-if="editor" class="template-overlay" @click.self="!busy && (editor = null)">
      <form class="template-dialog" role="dialog" aria-modal="true" aria-labelledby="template-edit-title" @submit.prevent="save">
        <header class="editor-heading"><div><h2 id="template-edit-title">{{ editor.row ? '编辑' : '新增' }}{{ editor.kind === 'group' ? '模板分组' : '合同模板' }}</h2><p>{{ editor.kind === 'group' ? '将同类合同归在一起，方便查找与维护。' : '填写模板名称并导入文件，之后可继续配置填写区域。' }}</p></div><button type="button" class="dialog-close" aria-label="关闭弹窗" :disabled="busy" @click="editor = null">×</button></header>
        <div class="editor-body">
        <label>{{editor.kind==='group'?'分组名称':'模板名称'}} <span class="required">*</span><input v-model="form.name" :aria-label="editor.kind==='group'?'分组名称':'模板名称'" class="field" :placeholder="editor.kind==='group'?'例如：采购合同、经销协议':'例如：年度采购协议模板'" required maxlength="100" :disabled="busy"/></label>
        <div v-if="editor.kind==='template'" class="upload-section">
          <span class="upload-label">导入文件 <span class="required">*</span></span>
          <input ref="fileInput" class="hidden-file" type="file" accept=".docx,.pdf,.txt" :disabled="busy" @change="chooseFile"/>
          <button type="button" class="upload-zone" :class="{dragging,'has-file':selectedFile||form.source_id}" :disabled="busy" @click="fileInput.click()" @dragover.prevent="dragging=true" @dragleave.prevent="dragging=false" @drop.prevent="dropFile">
            <span class="upload-icon"><ReviewIcon name="document"/></span><strong>{{selectedFile?.name||uploadedFilename||editor.row?.filename||(form.source_id?'文件已导入':'点击选择文件，或拖拽到此处')}}</strong><span>{{selectedFile||form.source_id?'点击可更换文件':'支持 DOCX、文字型 PDF、TXT，最大 10 MB'}}</span>
          </button>
        </div>
        <div v-if="editor.kind==='template'" class="editor-group-context"><span>保存到分组</span><select v-model="form.group_id" aria-label="所属分组" :disabled="busy"><option :value="groups.find(g=>g.name==='未分组')?.id||''">未分组</option><option v-for="g in groups.filter(g=>g.name!=='未分组')" :key="g.id" :value="g.id">{{g.name}}</option></select></div>
        <details class="editor-extra" :open="editor.kind==='group'||undefined"><summary>补充说明 <span class="optional">选填</span></summary><textarea v-model="form.description" class="field" aria-label="说明" placeholder="适用场景或版本说明" rows="3" maxlength="2000" :disabled="busy"></textarea></details>
        <p v-if="modalError" class="notice" role="alert">{{ modalError }}</p>
        </div>
        <footer><span class="footer-hint">{{ editor.kind === 'template' ? '原件格式将完整保留' : '' }}</span><button type="button" class="button" :disabled="busy" @click="editor = null">取消</button><button class="button primary" :disabled="busy">{{busy?'正在保存…':editor.kind==='template'&&!editor.row?'创建模板':'保存'}}</button></footer>
      </form>
    </div>
    <div v-if="removal" class="template-overlay" @click.self="!busy && (removal = null)"><div class="template-dialog" role="dialog" aria-modal="true" aria-labelledby="template-delete-title"><h2 id="template-delete-title">删除{{ removal.kind === 'group' ? '分组' : '模板' }}</h2><p>确定删除“{{ removal.row.name }}”？{{ removal.kind === 'group' ? '分组下有模板时，请先迁移或删除模板。' : '删除后将从模板列表移除。' }}</p><p v-if="modalError" class="notice" role="alert">{{ modalError }}</p><footer><button class="button" :disabled="busy" @click="removal = null">取消</button><button class="button primary" :disabled="busy" @click="remove">{{ busy ? '正在删除…' : '确认删除' }}</button></footer></div></div>
    <div v-if="preview" class="template-overlay" @click.self="preview = null"><div class="template-preview" role="dialog" aria-modal="true" aria-label="合同模板预览"><header><strong>{{ preview.name }}</strong><div><a class="button" :href="'/api/contract-templates/' + preview.id + '/download'">导出原件</a><button class="button" @click="preview = null">关闭</button></div></header><iframe :key="preview.source_id" :src="previewUrl" title="合同模板原件预览"></iframe></div></div>
  </Teleport>
</template>

<style scoped>
.templates-page{max-width:1800px;margin:0 auto;color:#334155}.catalog-heading-actions{display:flex;gap:10px}.catalog-heading-actions svg{width:14px;height:14px}.template-layout{display:grid;grid-template-columns:224px minmax(0,1fr);gap:20px;align-items:start}.card{border-radius:12px;box-shadow:0 1px 3px #0f172a03}.group-panel{padding:14px 10px}.group-heading{display:flex;justify-content:space-between;align-items:center;padding:4px 10px 17px}.group-heading strong{font-size:13px}.text-action{color:#5376c7;font-size:11px;white-space:nowrap}.muted{color:#94a3b8!important}.group-select{display:flex;align-items:center;gap:9px;width:100%;border-radius:7px;text-align:left;padding:11px 10px;font-size:12px;color:#64748b}.group-select>span{flex:1}.group-select svg,.group-name svg{width:15px;height:15px;color:#9aa9bf}.group-select b,.group-name b{font-size:10px;font-weight:400;padding:2px 6px;color:#8b9bb1;background:#f2f5fa;border-radius:4px}.group-divider{height:1px;background:#edf1f6;margin:12px 8px}.group-row{border:1px solid transparent;border-radius:7px;margin-bottom:4px;overflow:hidden}.group-name{display:flex;align-items:center;gap:9px;width:100%;min-width:0;padding:11px 9px;text-align:left;font-size:12px;color:#65758c}.group-name>span{flex:1;overflow-wrap:anywhere}.group-select.selected,.group-row.selected{background:#eff6ff;color:#2563eb}.selected .group-name,.selected svg{color:#2563eb}.selected b{background:#dbeafe;color:#3b73d8}.group-row:hover:not(.selected){background:#f8fafc}.group-management{display:flex;justify-content:flex-end;gap:14px;padding:0 10px 9px}.group-empty{font-size:11px;line-height:1.9;color:#94a3b8;margin:10px;padding:0 2px}.group-new{display:flex;align-items:center;justify-content:center;gap:6px;width:calc(100% - 12px);padding:9px 8px;margin:14px 6px 2px;border:1px dashed #d9e3f1;border-radius:6px;color:#8398b7;font-size:11px}.group-new:hover{color:#2563eb;border-color:#93b4f4;background:#f8faff}.group-new svg{width:13px;height:13px}.template-list{min-width:0;overflow:hidden}.template-filters{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:18px 20px;border-bottom:1px solid #e8edf4}.template-list-heading{display:flex;align-items:center;gap:10px;min-width:0}.template-list-heading h2{font-size:14px;font-weight:600;margin:0;overflow-wrap:anywhere}.template-list-heading>span{font-size:11px;color:#99a6b8;white-space:nowrap}.template-filter-controls{display:flex;gap:10px;min-width:0}.catalog-search{display:flex;align-items:center;gap:7px;border:1px solid #e0e7f0;border-radius:7px;padding:9px 10px;width:260px;min-width:0;background:#fff}.catalog-search svg{width:14px;height:14px;color:#9eacc0}.catalog-search input{font-size:12px;color:#64748b;outline:0;border:0;width:100%;min-width:0;background:none}.catalog-search input::placeholder{color:#a2aec0}.catalog-search:focus-within{border-color:#8eacf0;box-shadow:0 0 0 2px #2563eb08}.status-filter{width:116px;font-size:11px;padding:8px 10px;min-height:35px}.template-table{min-width:840px;width:100%;table-layout:fixed}.template-table th{font-size:11px;font-weight:500;color:#8b99ad;background:#f8fafc;padding:13px 16px}.template-table th:nth-child(1){width:36%}.template-table th:nth-child(2){width:13%}.template-table th:nth-child(3){width:18%}.template-table th:nth-child(4){width:17%}.template-table th:nth-child(5){width:16%}.template-table td{font-size:12px;padding:20px 16px;vertical-align:middle;border-bottom:1px solid #edf1f6;overflow-wrap:anywhere}.template-table tbody tr:hover{background:#fcfdff}.template-name-cell{display:flex;align-items:center;gap:12px;min-width:0}.template-name-cell>div{min-width:0;flex:1}.template-file-icon{display:flex;align-items:center;justify-content:center;flex-direction:column;gap:2px;width:36px;min-width:36px;height:42px;background:#eff5ff;border:1px solid #e1eafa;border-radius:7px;color:#5e88d4}.template-file-icon svg{width:17px;height:17px}.template-file-icon small{font-size:7px;letter-spacing:.5px}.template-file-icon.pdf{background:#fff3f1;color:#c78a82;border-color:#f3e3e0}.template-name{display:block;font-size:13px;font-weight:600;color:#344862;line-height:1.7;text-align:left;text-decoration:none;overflow-wrap:anywhere}.template-name:hover{color:#2563eb}.template-name-cell p{font-size:10px;color:#a0adbf;margin:5px 0 0;line-height:1.7;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}.template-group-tag{display:inline-block;max-width:100%;font-size:11px;color:#8090a7;background:#f4f6fa;border:1px solid #e9edf4;border-radius:5px;padding:3px 7px;line-height:1.6}.template-state{display:inline-flex;align-items:center;gap:5px;font-size:11px;padding:3px 7px;border-radius:5px;background:#f2f4f8;color:#93a0b4;white-space:nowrap}.template-state i{width:4px;height:4px;border-radius:50%;background:currentColor}.template-state.published{background:#edf8f1;color:#6a9d7c}.template-state.ready{background:#edf3ff;color:#6f8ecf}.template-state.reviewing{background:#fff7e9;color:#b99b60}.template-field-summary{display:block;font-size:10px;color:#a2adbd;margin-top:6px;line-height:1.6}.template-table .template-date{font-size:11px;color:#91a0b5;font-variant-numeric:tabular-nums}.template-row-actions{display:flex;align-items:center;gap:13px;white-space:nowrap}.configure-link{color:#4676d0;font-size:11px;white-space:nowrap}.template-more{display:flex;align-items:center;gap:5px;font-size:11px;color:#92a0b5}.catalog-chevron{width:5px;height:5px;border-right:1px solid currentColor;border-bottom:1px solid currentColor;transform:rotate(45deg);margin-top:-3px}.template-pagination{display:flex;align-items:center;justify-content:space-between;padding:15px 20px;color:#a1adbd;font-size:11px}.template-pagination>div{display:flex;gap:7px}.template-pagination .button{font-size:11px;padding:6px 10px;font-weight:400}.catalog-empty{display:flex;align-items:center;flex-direction:column;justify-content:center;padding:48px 16px;color:#a6b2c4;gap:10px}.catalog-empty>svg{width:30px;height:30px;color:#b7c6df}.catalog-empty h3{font-size:14px;font-weight:500;color:#7f8fa7;margin:3px 0 0}.catalog-empty p{font-size:12px;margin:0}.catalog-empty .button{margin-top:6px;font-size:11px}.notice{color:#b91c1c;background:#fef2f2;padding:12px;border-radius:6px;margin-bottom:12px;font-size:12px}.catalog-menu-shade{position:fixed;inset:0;z-index:65}.catalog-action-menu{position:fixed;width:164px;padding:5px;background:#fff;border:1px solid #dde5f0;box-shadow:0 6px 25px #1e293b17;border-radius:8px;outline:0}.catalog-action-menu>button,.catalog-action-menu>a{display:block;text-align:left;width:100%;padding:10px;border-radius:5px;font-size:11px;color:#6d7e96;text-decoration:none}.catalog-action-menu>*:hover{background:#f4f7fc;color:#2563eb}.catalog-action-menu .danger{color:#ba8585;border-top:1px solid #edf1f6;margin-top:3px;border-radius:0}
.template-overlay{position:fixed;inset:0;z-index:70;background:#0f172a55;backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;padding:24px}.template-dialog{width:560px;max-width:100%;max-height:90vh;overflow:auto;background:#fff;border:1px solid #e2e8f0;border-radius:14px;box-shadow:0 24px 80px #0f172a26;color:#334155}.editor-heading{display:flex;align-items:flex-start;justify-content:space-between;padding:23px 26px 19px;border-bottom:1px solid #edf0f5;gap:20px}.editor-heading h2{font-size:19px;line-height:1.5;margin:0;font-weight:650;letter-spacing:-.3px}.editor-heading p{font-size:12px;color:#8b99ad;margin:6px 0 0;line-height:1.8}.dialog-close{color:#94a3b8;font-size:26px;line-height:28px;width:30px;border-radius:6px}.dialog-close:hover{background:#f1f5f9;color:#334155}.editor-body{padding:24px 26px 20px}.template-dialog label{display:block;font-size:12px;font-weight:500;margin-bottom:20px}.template-dialog label>.field{display:block;margin-top:8px}.template-dialog .field{font-size:13px;border:1px solid #dce3ed;border-radius:7px;padding:10px 12px;min-height:40px;background:#fff;color:#475569;width:100%;box-sizing:border-box}.template-dialog .field:focus{outline:0;border-color:#6090f5;box-shadow:0 0 0 3px #2563eb12}.required{color:#cf8c8c;font-size:11px}.upload-section{margin-bottom:18px}.upload-label{display:block;font-size:12px;font-weight:500;margin-bottom:9px}.hidden-file{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}.upload-zone{display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%;padding:24px 16px;border:1px dashed #c1d1ee;background:#f9fbff;border-radius:9px;gap:7px}.upload-zone:hover,.upload-zone.dragging{background:#eff6ff;border-color:#6793e5}.upload-icon{display:grid;place-items:center;width:40px;height:42px;color:#7d9ccf;margin-bottom:3px}.upload-icon svg{width:29px;height:29px}.upload-zone strong{font-size:12px;font-weight:500;max-width:100%;overflow-wrap:anywhere;color:#61738f}.upload-zone>span:last-child{font-size:11px;color:#a3aec0}.upload-zone.has-file strong{color:#4f79c7}.editor-group-context{display:flex;align-items:center;gap:12px;font-size:11px;padding:10px 12px;background:#f7f9fc;border-radius:6px;margin-bottom:17px;color:#98a6ba}.editor-group-context select{margin-left:auto;max-width:65%;background-color:transparent;border:0;color:#7186a7;font-size:11px;outline:0}.editor-extra>summary{cursor:pointer;font-size:11px;color:#8d9bb1;padding:3px 0}.optional{font-size:10px;color:#b0bac9;margin-left:5px}.editor-extra textarea{margin-top:12px;resize:vertical}.template-dialog footer{display:flex;justify-content:flex-end;gap:9px;margin:0;padding:15px 26px;background:#fafbfd;border-top:1px solid #edf0f5;align-items:center}.template-dialog footer .button{font-size:12px;min-height:36px;padding:8px 17px}.footer-hint{margin-right:auto;font-size:10px;color:#a2adbf}.template-dialog>h2{font-size:18px;margin:24px 26px 12px;font-weight:600}.template-dialog>p{font-size:12px;line-height:1.9;margin:0 26px 20px;color:#8796ab}.template-preview{background:#fff;border-radius:12px;width:1200px;max-width:100%;height:90vh;display:flex;flex-direction:column;overflow:hidden}.template-preview header{display:flex;justify-content:space-between;align-items:center;padding:14px 20px;border-bottom:1px solid #e2e8f0;gap:16px}.template-preview header div{display:flex;gap:10px}.template-preview iframe{width:100%;flex:1;border:0;min-height:0}
@media(max-width:1250px){.template-layout{grid-template-columns:190px minmax(0,1fr);gap:14px}.template-filters{align-items:flex-start;flex-direction:column;gap:13px}.template-filter-controls{width:100%}.catalog-search{flex:1;width:auto}.template-row-actions{gap:8px}}
@media(max-width:900px){.template-layout{grid-template-columns:1fr}.group-panel{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.group-heading{padding:4px 8px;min-width:100px}.group-select{width:auto}.group-row{margin:0}.group-name{width:auto;gap:6px}.group-divider{display:none}.group-new{width:auto;margin:0;padding:8px}.group-management{padding:0 8px 6px}.template-overlay{padding:12px}}
@media(max-width:650px){.checklists-heading{align-items:flex-start;flex-direction:column}.catalog-heading-actions{width:100%}.catalog-heading-actions>.button{flex:1}.template-filters{padding:15px}.template-filter-controls{gap:7px}.catalog-search{width:100%;min-width:0}.status-filter{width:108px}.editor-heading,.editor-body{padding-left:20px;padding-right:20px}.template-dialog footer{padding:15px 20px}.footer-hint{display:none}.template-pagination{padding:13px 15px}}
</style>
