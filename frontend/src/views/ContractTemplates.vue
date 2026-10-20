<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { readDocument } from '../portal/services/documents.js';
import { usePortalShell } from '../stores/portal.js';

const { api } = usePortalShell();
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
    const [g, result] = await Promise.all([api('/api/template-groups'), api('/api/contract-templates?' + new URLSearchParams({q: search.value, group_id: group.value, page: page.value}))]);
    if (sequence !== requestSequence) return;
    groups.value = g; rows.value = result.items; total.value = result.total;
    if (page.value > pages.value) page.value = pages.value;
    error.value = '';
  } catch (e) { if (sequence === requestSequence) error.value = e.message; }
  finally { if (sequence === requestSequence) loading.value = false; }
}
watch([search, group], () => { if (page.value !== 1) page.value = 1; else load(); });
watch(page, load);
onMounted(load);
function edit(kind, row = null) {
  modalError.value = ''; selectedFile.value = null;
  Object.assign(form, {name: row?.name || '', description: row?.description || '', group_id: row?.group_id || group.value || groups.value[0]?.id || '', source_id: row?.source_id || '', revision: row?.revision || null});
  editor.value = {kind, row};
}
async function save() {
  busy.value = true; modalError.value = '';
  try {
    const {kind, row} = editor.value;
    let body = {name: form.name.trim(), description: form.description, revision: form.revision};
    if (!body.name) throw new Error('请填写名称');
    if (kind === 'template') {
      if (!form.group_id) throw new Error('请选择分组');
      if (selectedFile.value) {
        const upload = await readDocument(selectedFile.value);
        form.source_id = upload.source_id;
        selectedFile.value = null;
      }
      if (!form.source_id) throw new Error('请上传模板文件');
      body = {...body, group_id: form.group_id, source_id: form.source_id};
    }
    const base = kind === 'group' ? '/api/template-groups' : '/api/contract-templates';
    await api(base + (row ? '/' + row.id : ''), row ? 'PUT' : 'POST', body);
    editor.value = null; await load();
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
      <div><h1>合同模板</h1><p>按分组管理标准合同，上传、预览并导出原始模板。</p></div>
      <button class="button primary" :disabled="busy || !groups.length" @click="edit('template')">＋ 上传模板</button>
    </header>
    <p v-if="error" class="notice" role="alert">{{ error }} <button @click="load">重试</button></p>
    <div class="template-layout">
      <aside class="card group-panel">
        <div class="group-heading"><strong>模板分组</strong><button class="text-action" @click="edit('group')">＋ 新建</button></div>
        <button class="group-select" :class="{selected: !group}" @click="group = ''">全部模板</button>
        <div v-for="g in groups" :key="g.id" class="group-row" :class="{selected: group === g.id}">
          <button class="group-name" :title="g.description || g.name" @click="group = g.id">{{ g.name }} <span>{{ g.template_count }}</span></button>
          <button class="text-action" :aria-label="'编辑分组 ' + g.name" @click="edit('group', g)">编辑</button>
          <button class="text-action muted" :aria-label="'删除分组 ' + g.name" @click="askDelete('group', g)">删除</button>
        </div>
        <p v-if="!groups.length" class="group-empty">新建分组后即可上传模板。</p>
      </aside>
      <div class="card template-list">
        <div class="template-filters"><input v-model="search" class="field" aria-label="搜索合同模板" placeholder="搜索模板名称、文件名或说明" maxlength="200" /><span>{{ group ? groupName(group) : '全部分组' }}</span></div>
        <div class="checklists-table-scroll">
          <table class="data-table"><thead><tr><th>模板名称</th><th>所属分组</th><th>更新时间</th><th>操作</th></tr></thead>
            <tbody><tr v-for="row in rows" :key="row.id">
              <td><strong>{{ row.name }}</strong><small>{{ row.filename }}</small><small v-if="row.description">{{ row.description }}</small></td>
              <td>{{ groupName(row.group_id) }}</td><td>{{ new Date(row.updated_at).toLocaleString('zh-CN', {timeZone:'Asia/Shanghai'}) }}</td>
              <td><div class="checklists-row-actions"><button @click="showPreview(row)">预览</button><a :href="'/api/contract-templates/' + row.id + '/download'">导出</a><button @click="edit('template', row)">编辑</button><button class="muted" @click="askDelete('template', row)">删除</button></div></td>
            </tr></tbody>
          </table>
        </div>
        <div v-if="loading" class="empty" role="status">正在加载模板…</div>
        <div v-else-if="!rows.length" class="empty">{{ search ? '没有匹配的模板' : '暂无模板，请先新建分组并上传合同模板' }}</div>
        <div class="template-pagination"><span>共 {{ total }} 条 · 第 {{ page }} / {{ pages }} 页</span><div><button class="button" :disabled="page === 1 || loading" @click="page--">上一页</button> <button class="button" :disabled="page >= pages || loading" @click="page++">下一页</button></div></div>
      </div>
    </div>
  </section>
  <Teleport to="body">
    <div v-if="editor" class="template-overlay" @click.self="!busy && (editor = null)">
      <form class="template-dialog" role="dialog" aria-modal="true" aria-labelledby="template-edit-title" @submit.prevent="save">
        <header class="editor-heading"><div><h2 id="template-edit-title">{{ editor.row ? '编辑' : '新增' }}{{ editor.kind === 'group' ? '模板分组' : '合同模板' }}</h2><p>{{ editor.kind === 'group' ? '将同类合同归在一起，方便查找与维护。' : '保存标准合同原件，供团队查阅和使用。' }}</p></div><button type="button" class="dialog-close" aria-label="关闭弹窗" :disabled="busy" @click="editor = null">×</button></header>
        <div class="editor-body">
        <div v-if="editor.kind === 'template'" class="upload-section">
          <span class="upload-label">模板文件 <span class="required">*</span></span>
          <input ref="fileInput" class="hidden-file" type="file" accept=".docx,.pdf,.txt" :disabled="busy" @change="chooseFile" />
          <button type="button" class="upload-zone" :class="{dragging, 'has-file': selectedFile || form.source_id}" :disabled="busy" @click="fileInput.click()" @dragover.prevent="dragging = true" @dragleave.prevent="dragging = false" @drop.prevent="dropFile">
            <span class="upload-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M12 17v-6m-3 3 3-3 3 3"/></svg></span>
            <strong>{{ selectedFile?.name || editor.row?.filename || (form.source_id ? '文件已上传' : '点击上传，或将文件拖到这里') }}</strong>
            <span>{{ selectedFile || form.source_id ? '点击替换文件' : 'DOCX、文字型 PDF、TXT · 最大 10 MB' }}</span>
          </button>
        </div>
        <div :class="{'editor-grid': editor.kind === 'template'}">
        <label>名称<input v-model="form.name" class="field" required maxlength="100" :disabled="busy" /></label>
        <label v-if="editor.kind === 'template'">所属分组<select v-model="form.group_id" class="field" required :disabled="busy"><option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option></select></label>
        </div>
        <label>说明 <span class="optional">选填</span><textarea v-model="form.description" class="field" placeholder="可填写适用场景、版本说明等" rows="3" maxlength="2000" :disabled="busy"></textarea></label>
        <p v-if="modalError" class="notice" role="alert">{{ modalError }}</p>
        </div>
        <footer><span class="footer-hint">{{ editor.kind === 'template' ? '原件格式将完整保留' : '' }}</span><button type="button" class="button" :disabled="busy" @click="editor = null">取消</button><button class="button primary" :disabled="busy">{{ busy ? '正在保存…' : '保存' }}</button></footer>
      </form>
    </div>
    <div v-if="removal" class="template-overlay" @click.self="!busy && (removal = null)"><div class="template-dialog" role="dialog" aria-modal="true" aria-labelledby="template-delete-title"><h2 id="template-delete-title">删除{{ removal.kind === 'group' ? '分组' : '模板' }}</h2><p>确定删除“{{ removal.row.name }}”？{{ removal.kind === 'group' ? '分组下有模板时，请先迁移或删除模板。' : '删除后将从模板列表移除。' }}</p><p v-if="modalError" class="notice" role="alert">{{ modalError }}</p><footer><button class="button" :disabled="busy" @click="removal = null">取消</button><button class="button primary" :disabled="busy" @click="remove">{{ busy ? '正在删除…' : '确认删除' }}</button></footer></div></div>
    <div v-if="preview" class="template-overlay" @click.self="preview = null"><div class="template-preview" role="dialog" aria-modal="true" aria-label="合同模板预览"><header><strong>{{ preview.name }}</strong><div><a class="button" :href="'/api/contract-templates/' + preview.id + '/download'">导出原件</a><button class="button" @click="preview = null">关闭</button></div></header><iframe :key="preview.source_id" :src="previewUrl" title="合同模板原件预览"></iframe></div></div>
  </Teleport>
</template>

<style scoped>
.template-layout{display:grid;grid-template-columns:250px minmax(0,1fr);gap:20px;align-items:start}.group-panel{padding:12px}.group-heading{display:flex;justify-content:space-between;padding:8px 4px 16px}.text-action{color:#2563eb;font-size:12px;white-space:nowrap}.muted{color:#64748b!important}.group-select,.group-row{width:100%;border-radius:7px;text-align:left;padding:10px 8px;margin-bottom:4px}.group-row{display:flex;align-items:center;gap:8px}.group-name{flex:1;min-width:0;overflow-wrap:anywhere;text-align:left;font-size:13px}.group-name span{color:#64748b;font-size:11px;margin-left:6px}.selected{background:#eff6ff;color:#2563eb}.group-empty{font-size:12px;color:#64748b;padding:12px 4px}.template-list{min-width:0;overflow:hidden}.template-filters{display:flex;align-items:center;gap:16px;padding:14px 16px;border-bottom:1px solid #e2e8f0}.template-filters .field{flex:1;min-width:0}.template-filters span{font-size:12px;color:#64748b}.data-table{min-width:720px}.data-table td{font-size:12px;max-width:340px;overflow-wrap:anywhere}.data-table small{display:block;color:#64748b;margin-top:5px;white-space:pre-wrap}.template-pagination{display:flex;align-items:center;justify-content:space-between;padding:16px;color:#64748b;font-size:12px}.notice{color:#b91c1c;background:#fef2f2;padding:12px;border-radius:6px;margin-bottom:12px}.template-overlay{position:fixed;inset:0;z-index:60;background:#0f172a66;display:flex;align-items:center;justify-content:center;padding:24px}.template-dialog{background:white;border-radius:12px;padding:24px;width:520px;max-width:100%;max-height:90vh;overflow:auto;box-shadow:0 20px 60px #0003}.template-dialog h2{font-size:20px;font-weight:600;margin-bottom:20px}.template-dialog label{display:grid;gap:8px;margin-bottom:16px;font-size:13px}.template-dialog small{color:#64748b;font-size:12px}.template-dialog footer{display:flex;justify-content:flex-end;gap:10px;margin-top:24px}.template-preview{background:#fff;border-radius:12px;width:1200px;max-width:100%;height:90vh;display:flex;flex-direction:column;overflow:hidden}.template-preview header{display:flex;justify-content:space-between;align-items:center;padding:14px 20px;border-bottom:1px solid #e2e8f0;gap:16px}.template-preview header div{display:flex;gap:10px}.template-preview iframe{width:100%;flex:1;border:0;min-height:0}@media(max-width:900px){.template-layout{grid-template-columns:1fr}.template-overlay{padding:12px}}
</style>
<style scoped>
.template-dialog{width:600px;padding:0;border:1px solid #e2e8f0;border-radius:16px;box-shadow:0 24px 80px #0f172a26;color:#1e293b}.template-overlay{background:rgba(15,23,42,.34);backdrop-filter:blur(3px)}.editor-heading{display:flex;align-items:flex-start;justify-content:space-between;padding:24px 28px 20px;border-bottom:1px solid #edf0f5;gap:20px}.editor-heading h2{font-size:19px;line-height:1.5;margin:0;font-weight:650;letter-spacing:-.3px}.editor-heading p{font-size:12px;color:#64748b;margin:6px 0 0}.dialog-close{border:0;background:transparent;color:#94a3b8;font-size:26px;line-height:28px;width:30px;border-radius:6px}.dialog-close:hover{background:#f1f5f9;color:#334155}.editor-body{padding:24px 28px 8px}.template-dialog label{font-size:12px;font-weight:500;gap:7px;margin-bottom:18px}.template-dialog .field{font-size:13px;border:1px solid #dce3ed;border-radius:7px;padding:10px 12px;min-height:40px;box-shadow:0 1px 2px #0f172a03;background:#fff;color:#334155;width:100%;box-sizing:border-box}.template-dialog .field:focus{outline:0;border-color:#6090f5;box-shadow:0 0 0 3px #2563eb12}.template-dialog textarea.field{min-height:84px;resize:vertical}.editor-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.optional{font-size:11px;color:#94a3b8;font-weight:400;position:absolute;margin-left:34px}.upload-section{margin-bottom:22px}.upload-label{display:block;font-size:12px;font-weight:500;margin-bottom:9px}.required{color:#ef4444;margin-left:3px}.hidden-file{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}.upload-zone{display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%;padding:22px 16px;border:1px dashed #b9cdf0;background:#f8faff;border-radius:10px;transition:background .15s,border-color .15s;gap:7px}.upload-zone:hover,.upload-zone.dragging{background:#eff6ff;border-color:#2563eb}.upload-icon{display:grid;place-items:center;width:40px;height:44px;color:#3b70dc;margin-bottom:3px}.upload-icon svg{width:32px;height:32px}.upload-zone strong{font-size:13px;font-weight:500;max-width:100%;overflow-wrap:anywhere;color:#334155}.upload-zone>span:last-child{font-size:11px;color:#8391a8}.upload-zone.has-file strong{color:#2563eb}.template-dialog footer{margin:0;padding:16px 28px;background:#fafbfd;border-top:1px solid #edf0f5;align-items:center;border-radius:0 0 16px 16px}.template-dialog footer .button{font-size:12px;min-height:36px;padding:8px 18px;border-radius:7px}.footer-hint{margin-right:auto;font-size:11px;color:#94a3b8}.template-dialog>.notice,.template-dialog>p{margin:20px 28px}.group-row .text-action{font-size:11px;opacity:0;transition:opacity .15s}.group-row:hover .text-action,.group-row:focus-within .text-action{opacity:1}.group-row{gap:10px;padding:11px 9px}.group-name span{background:#f1f5f9;border-radius:5px;padding:2px 5px}.selected .group-name span{background:#dbeafe;color:#2563eb}.group-heading strong{font-size:13px}.group-select{font-size:13px}.template-dialog .notice{font-size:12px}@media(max-width:650px){.editor-grid{grid-template-columns:1fr;gap:0}.editor-heading,.editor-body{padding-left:20px;padding-right:20px}.template-dialog footer{padding:16px 20px}.footer-hint{display:none}.group-row .text-action{opacity:1}}
</style>
