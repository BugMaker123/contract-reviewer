<script setup>
import { ref, reactive, computed, onMounted, onActivated, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import ReviewIcon from '../components/portal/ReviewIcon.vue';
import { readDocument } from '../portal/services/documents.js';
import { usePortalShell } from '../stores/portal.js';

const route = useRoute();
const router = useRouter();
const { api, notify } = usePortalShell();

const status = ref('all');
const actionMenu = ref(null);
const menuElement = ref(null);
const uploadedFilename = ref('');
const statusNames = { unconfigured: '待配置', reviewing: '待核验', ready: '待发布', published: '已发布' };

const dateTime = value => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  } catch {
    return '—';
  }
};

function more(row, event) {
  const rect = event.currentTarget.getBoundingClientRect();
  actionMenu.value = {
    row,
    x: Math.max(12, Math.min(rect.right - 164, window.innerWidth - 176)),
    y: Math.max(12, Math.min(rect.bottom + 6, window.innerHeight - 210)),
  };
  nextTick(() => menuElement.value?.focus());
}

function menuAction(action) {
  const row = actionMenu.value.row;
  actionMenu.value = null;
  if (action === 'preview') showPreview(row);
  else if (action === 'validate') router.push({ path: '/template-checks/new', query: { template_id: row.id } });
  else if (action === 'edit') edit('template', row);
  else askDelete('template', row);
}

const groups = ref([]), rows = ref([]), total = ref(0), page = ref(1), search = ref(''), group = ref('');
const busy = ref(false), loading = ref(false), error = ref(''), modalError = ref('');
const editor = ref(null), preview = ref(null), removal = ref(null), selectedFile = ref(null);
const fileInput = ref(null), dragging = ref(false);
const form = reactive({ name: '', description: '', group_id: '', source_id: '', revision: null });
const pages = computed(() => Math.max(1, Math.ceil(total.value / 10)));
const totalTemplates = computed(() => groups.value.reduce((sum, g) => sum + (g.template_count || 0), 0));
const groupName = id => groups.value.find(g => g.id === id)?.name || '未分组';
const activeGroupName = computed(() => group.value ? groupName(group.value) : '全部模板');

let requestSequence = 0;
async function load() {
  const sequence = ++requestSequence;
  loading.value = true;
  try {
    const [g, result] = await Promise.all([
      api('/api/template-groups'),
      api('/api/contract-templates?' + new URLSearchParams({
        q: search.value,
        group_id: group.value,
        page: page.value,
        status: status.value,
      })),
    ]);
    if (sequence !== requestSequence) return;
    groups.value = g;
    rows.value = result.items.map(row => {
      const fields = row.review_draft?.source_id === row.source_id ? row.review_draft.fields || [] : [];
      const count = row.field_count ?? fields.length;
      const confirmed = row.confirmed_count ?? fields.filter(f => f.confirmed).length;
      return {
        ...row,
        field_count: count,
        confirmed_count: confirmed,
        configuration_status: row.configuration_status || (
          row.review_status === 'published' ? 'published' : count ? confirmed === count ? 'ready' : 'reviewing' : 'unconfigured'
        ),
      };
    });
    total.value = result.total;
    if (page.value > pages.value) page.value = pages.value;
    error.value = '';
  } catch (e) {
    if (sequence === requestSequence) error.value = e.message;
  } finally {
    if (sequence === requestSequence) loading.value = false;
  }
}

if (route.query.group) {
  group.value = String(route.query.group);
}
watch(() => route.query.group, newGroup => {
  if (newGroup !== undefined && group.value !== String(newGroup || '')) {
    group.value = String(newGroup || '');
  }
});

watch([search, group, status], () => {
  if (page.value !== 1) page.value = 1;
  else load();
});
watch(page, load);
onMounted(load);
onActivated(load);

function edit(kind, row = null) {
  modalError.value = '';
  selectedFile.value = null;
  uploadedFilename.value = '';
  Object.assign(form, {
    name: row?.name || '',
    description: row?.description || '',
    group_id: row?.group_id || group.value || groups.value.find(g => g.name === '未分组')?.id || '',
    source_id: row?.source_id || '',
    revision: row?.revision || null,
  });
  editor.value = { kind, row };
}

async function save() {
  busy.value = true;
  modalError.value = '';
  try {
    const { kind, row } = editor.value;
    let body = { name: form.name.trim(), description: form.description, revision: form.revision };
    if (!body.name) throw new Error('请填写名称');
    if (kind === 'template') {
      if (selectedFile.value) {
        const upload = await readDocument(selectedFile.value);
        form.source_id = upload.source_id;
        uploadedFilename.value = selectedFile.value.name;
        selectedFile.value = null;
      }
      if (!form.source_id) throw new Error('请上传模板文件');
      if (!form.group_id) {
        let fallback = groups.value.find(g => g.name === '未分组');
        if (!fallback) {
          try { fallback = await api('/api/template-groups', 'POST', { name: '未分组', description: '' }); }
          catch (e) {
            const latest = await api('/api/template-groups');
            fallback = latest.find(g => g.name === '未分组');
            if (!fallback) throw e;
          }
        }
        form.group_id = fallback.id;
      }
      body = { ...body, group_id: form.group_id, source_id: form.source_id };
    }
    const base = kind === 'group' ? '/api/template-groups' : '/api/contract-templates';
    await api(base + (row ? '/' + row.id : ''), row ? 'PUT' : 'POST', body);
    editor.value = null;
    notify(row ? '修改已保存' : kind === 'group' ? '分组已创建' : '模板已添加，可继续配置填写区域');
    await load();
  } catch (e) {
    modalError.value = e.message;
  } finally {
    busy.value = false;
  }
}

function chooseFile(event) {
  selectedFile.value = event.target.files[0] || null;
  if (selectedFile.value && !form.name) form.name = selectedFile.value.name.replace(/\.[^.]+$/, '');
}

function dropFile(event) {
  dragging.value = false;
  if (!busy.value && event.dataTransfer.files.length) chooseFile({ target: { files: event.dataTransfer.files } });
}

function askDelete(kind, row) {
  modalError.value = '';
  removal.value = { kind, row };
}

async function remove() {
  busy.value = true;
  try {
    const { kind, row } = removal.value;
    await api((kind === 'group' ? '/api/template-groups/' : '/api/contract-templates/') + row.id + '?revision=' + row.revision, 'DELETE');
    if (kind === 'group' && group.value === row.id) group.value = '';
    removal.value = null;
    await load();
  } catch (e) {
    modalError.value = e.message;
  } finally {
    busy.value = false;
  }
}

async function showPreview(row) {
  try {
    preview.value = await api('/api/contract-templates/' + row.id);
  } catch (e) {
    error.value = e.message;
  }
}

const previewUrl = computed(() => !preview.value ? '' : preview.value.extension === '.docx'
  ? '/static/document-preview.html?readonly=1&source=' + encodeURIComponent(preview.value.source_id)
  : '/api/sources/' + encodeURIComponent(preview.value.source_id) + '/file');
</script>

<template>
  <section class="checklists-page templates-page">
    <header class="checklists-heading">
      <div>
        <h1>合同模板</h1>
        <p>统一管理标准合同模板、填写规则与已发布范本。</p>
      </div>
      <div class="catalog-heading-actions">
        <RouterLink to="/template-groups" class="button">
          <ReviewIcon name="categories" />维护分组
        </RouterLink>
        <button v-can="'catalog.maintain'" class="button" :disabled="busy" @click="edit('group')">
          <ReviewIcon name="plus" />新建分组
        </button>
        <button v-can="'templates.maintain'" class="button primary" :disabled="busy" @click="edit('template')">
          <ReviewIcon name="plus" />新增模板
        </button>
      </div>
    </header>

    <p v-if="error" class="notice" role="alert">{{ error }} <button class="text-button" @click="load">重试</button></p>

    <!-- 单栏卡片列表，不再被左侧面板挤压 -->
    <div class="card template-list-card">
      <div v-if="groups.length" class="template-groups-nav">
        <button
          type="button"
          class="group-nav-pill"
          :class="{ active: !group }"
          @click="group = ''"
        >
          <span>全部模板</span>
          <span class="nav-count">{{ totalTemplates }}</span>
        </button>
        <button
          v-for="g in groups"
          :key="g.id"
          type="button"
          class="group-nav-pill"
          :class="{ active: group === g.id }"
          :title="g.description || g.name"
          @click="group = g.id"
        >
          <span>{{ g.name }}</span>
          <span class="nav-count">{{ g.template_count || 0 }}</span>
        </button>
      </div>

      <div class="template-filters">
        <div class="template-list-heading">
          <h2>{{ activeGroupName }}</h2>
          <span class="total-tag">{{ total }} 个模板</span>
        </div>
        <div class="template-filter-controls">
          <div class="catalog-search">
            <ReviewIcon name="search" />
            <input
              v-model="search"
              aria-label="搜索合同模板"
              placeholder="搜索模板名称、文件名"
              maxlength="200"
            />
          </div>
          <select v-model="group" class="field group-filter" aria-label="筛选所属分组">
            <option value="">全部分组</option>
            <option v-for="g in groups" :key="g.id" :value="g.id">
              {{ g.name }} ({{ g.template_count }})
            </option>
          </select>
          <select v-model="status" class="field status-filter" aria-label="筛选配置状态">
            <option value="all">全部状态</option>
            <option v-for="(name, key) in statusNames" :key="key" :value="key">{{ name }}</option>
          </select>
        </div>
      </div>

      <div class="checklists-table-scroll">
        <table class="data-table template-table">
          <thead>
            <tr>
              <th>模板名称</th>
              <th>所属分组</th>
              <th>配置状态</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td>
                <div class="template-name-cell">
                  <span class="template-file-icon" :class="row.extension?.slice(1)">
                    <ReviewIcon name="document" />
                    <small>{{ row.extension?.slice(1).toUpperCase() }}</small>
                  </span>
                  <div>
                    <button class="template-name" :title="row.filename" @click="showPreview(row)">
                      {{ row.name }}
                    </button>
                    <p>{{ row.description || (row.extension === '.docx' ? '支持填写区域配置与合同验证' : '原件归档与预览') }}</p>
                  </div>
                </div>
              </td>
              <td>
                <button
                  type="button"
                  class="template-group-tag"
                  :title="'筛选 ' + groupName(row.group_id)"
                  @click="group = row.group_id"
                >
                  {{ groupName(row.group_id) }}
                </button>
              </td>
              <td>
                <span class="template-state" :class="row.configuration_status">
                  <i></i>{{ statusNames[row.configuration_status] || '待配置' }}
                </span>
                <small class="template-field-summary">
                  {{ row.field_count ? `${row.confirmed_count} / ${row.field_count} 个字段已确认` : '尚未配置填写区域' }}
                </small>
              </td>
              <td class="template-date">{{ dateTime(row.updated_at) }}</td>
              <td>
                <div class="template-row-actions">
                  <RouterLink
                    v-if="row.extension === '.docx'"
                    v-can="'templates.maintain'" class="configure-link"
                    :to="'/templates/' + row.id + '/review'"
                  >
                    {{ row.configuration_status === 'published' ? '维护规则' : '配置规则' }}
                  </RouterLink>
                  <span v-else class="configure-link-disabled" title="仅 DOCX 格式支持规则配置">不支持规则配置</span>
                  <button class="template-more" :aria-label="'更多操作 ' + row.name" @click="more(row, $event)">
                    更多 <span class="catalog-chevron"></span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="loading" class="empty" role="status">正在加载模板…</div>
      <div v-else-if="!rows.length" class="catalog-empty">
        <ReviewIcon name="templates" />
        <h3>{{ search || status !== 'all' || group ? '没有符合条件的模板' : '暂无合同模板' }}</h3>
        <p>{{ search || status !== 'all' || group ? '调整关键词或筛选条件后再试。' : '填写模板名称并导入文件，即可开始配置标准规则。' }}</p>
        <button v-can="'templates.maintain'" v-if="!search && status === 'all' && !group" class="button primary" @click="edit('template')">
          新增模板
        </button>
      </div>

      <div class="template-pagination">
        <span>共 {{ total }} 个模板 · 第 {{ page }} / {{ pages }} 页</span>
        <div>
          <button class="button" :disabled="page === 1 || loading" @click="page--">上一页</button>
          <button class="button" :disabled="page >= pages || loading" @click="page++">下一页</button>
        </div>
      </div>
    </div>
  </section>

  <!-- 浮层菜单与对话框 -->
  <Teleport to="body">
    <div v-if="actionMenu" class="catalog-menu-shade" @click="actionMenu = null" @keydown.esc="actionMenu = null">
      <div
        ref="menuElement"
        class="catalog-action-menu"
        role="menu"
        tabindex="-1"
        :style="{ left: actionMenu.x + 'px', top: actionMenu.y + 'px' }"
        @click.stop
      >
        <button role="menuitem" @click="menuAction('preview')">预览原件</button>
        <button
          v-if="actionMenu.row.configuration_status === 'published'"
          role="menuitem"
          @click="menuAction('validate')"
        >
          以此模板发起核验
        </button>
        <a role="menuitem" :href="'/api/contract-templates/' + actionMenu.row.id + '/download'" @click="actionMenu = null">
          下载原件
        </a>
        <button v-can="'templates.maintain'" role="menuitem" @click="menuAction('edit')">编辑信息 / 调整分组</button>
        <button v-can="'templates.maintain'" role="menuitem" class="danger" @click="menuAction('delete')">删除模板</button>
      </div>
    </div>

    <!-- 新建/编辑弹窗 (包括 group 和 template) -->
    <div v-if="editor" class="template-overlay" @click.self="!busy && (editor = null)">
      <form
        class="template-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="template-edit-title"
        @submit.prevent="save"
      >
        <header class="editor-heading">
          <div>
            <h2 id="template-edit-title">
              {{ editor.row ? '编辑' : '新增' }}{{ editor.kind === 'group' ? '模板分组' : '合同模板' }}
            </h2>
            <p>{{ editor.kind === 'group' ? '将同类合同归在一起，方便查找与维护。' : '填写模板名称并导入文件，之后可继续配置填写区域。' }}</p>
          </div>
          <button type="button" class="dialog-close" aria-label="关闭弹窗" :disabled="busy" @click="editor = null">×</button>
        </header>

        <div class="editor-body">
          <label>
            {{ editor.kind === 'group' ? '分组名称' : '模板名称' }} <span class="required">*</span>
            <input
              v-model="form.name"
              :aria-label="editor.kind === 'group' ? '分组名称' : '模板名称'"
              class="field"
              :placeholder="editor.kind === 'group' ? '例如：采购合同、经销协议' : '例如：年度采购协议模板'"
              required
              maxlength="100"
              :disabled="busy"
            />
          </label>

          <div v-if="editor.kind === 'template'" class="upload-section">
            <span class="upload-label">导入文件 <span class="required">*</span></span>
            <input
              ref="fileInput"
              class="hidden-file"
              type="file"
              accept=".docx,.pdf,.txt"
              :disabled="busy"
              @change="chooseFile"
            />
            <button
              type="button"
              class="upload-zone"
              :class="{ dragging, 'has-file': selectedFile || form.source_id }"
              :disabled="busy"
              @click="fileInput.click()"
              @dragover.prevent="dragging = true"
              @dragleave.prevent="dragging = false"
              @drop.prevent="dropFile"
            >
              <span class="upload-icon"><ReviewIcon name="document" /></span>
              <strong>{{ selectedFile?.name || uploadedFilename || editor.row?.filename || (form.source_id ? '文件已导入' : '点击选择文件，或拖拽到此处') }}</strong>
              <span>{{ selectedFile || form.source_id ? '点击可更换文件' : '支持 DOCX、文字型 PDF、TXT，最大 10 MB' }}</span>
            </button>
          </div>

          <div v-if="editor.kind === 'template'" class="editor-group-context">
            <span>保存到分组</span>
            <select v-model="form.group_id" aria-label="所属分组" :disabled="busy">
              <option :value="groups.find(g => g.name === '未分组')?.id || ''">未分组</option>
              <option v-for="g in groups.filter(g => g.name !== '未分组')" :key="g.id" :value="g.id">
                {{ g.name }}
              </option>
            </select>
          </div>

          <details class="editor-extra" :open="editor.kind === 'group' || undefined">
            <summary>补充说明 <span class="optional">选填</span></summary>
            <textarea
              v-model="form.description"
              class="field"
              aria-label="说明"
              placeholder="适用场景或版本说明"
              rows="3"
              maxlength="2000"
              :disabled="busy"
            ></textarea>
          </details>

          <p v-if="modalError" class="notice" role="alert">{{ modalError }}</p>
        </div>

        <footer>
          <span class="footer-hint">{{ editor.kind === 'template' ? '原件格式将完整保留' : '' }}</span>
          <button type="button" class="button" :disabled="busy" @click="editor = null">取消</button>
          <button class="button primary" :disabled="busy">
            {{ busy ? '正在保存…' : editor.kind === 'template' && !editor.row ? '创建模板' : '保存' }}
          </button>
        </footer>
      </form>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="removal" class="template-overlay" @click.self="!busy && (removal = null)">
      <div class="template-dialog" role="dialog" aria-modal="true" aria-labelledby="template-delete-title">
        <h2 id="template-delete-title">删除{{ removal.kind === 'group' ? '分组' : '模板' }}</h2>
        <p>确定删除“{{ removal.row.name }}”？{{ removal.kind === 'group' ? '分组下有模板时，请先迁移或删除模板。' : '删除后将从模板列表移除。' }}</p>
        <p v-if="modalError" class="notice" role="alert">{{ modalError }}</p>
        <footer>
          <button class="button" :disabled="busy" @click="removal = null">取消</button>
          <button v-can="'templates.maintain'" class="button primary" :disabled="busy" @click="remove">
            {{ busy ? '正在删除…' : '确认删除' }}
          </button>
        </footer>
      </div>
    </div>

    <!-- 原件预览弹窗 -->
    <div v-if="preview" class="template-overlay" @click.self="preview = null">
      <div class="template-preview" role="dialog" aria-modal="true" aria-label="合同模板预览">
        <header>
          <strong>{{ preview.name }}</strong>
          <div>
            <a class="button" :href="'/api/contract-templates/' + preview.id + '/download'">导出原件</a>
            <button class="button" @click="preview = null">关闭</button>
          </div>
        </header>
        <iframe :key="preview.source_id" :src="previewUrl" title="合同模板原件预览"></iframe>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.templates-page {
  max-width: 1180px;
  margin: 0 auto;
  color: #334155;
}
.catalog-heading-actions {
  display: flex;
  gap: 10px;
}
.catalog-heading-actions svg {
  width: 14px;
  height: 14px;
}
.template-list-card {
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  background: #fff;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}
.template-groups-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: #f8fafc;
  border-bottom: 1px solid #edf2f7;
  overflow-x: auto;
}
.group-nav-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #475569;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}
.group-nav-pill:hover {
  border-color: #cbd5e1;
  background: #f1f5f9;
}
.group-nav-pill.active {
  background: #eff6ff;
  border-color: #93c5fd;
  color: #2563eb;
  font-weight: 500;
}
.nav-count {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 10px;
  background: #f1f5f9;
  color: #64748b;
}
.group-nav-pill.active .nav-count {
  background: #dbeafe;
  color: #1d4ed8;
}
.template-filters {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid #e8edf4;
}
.template-list-heading {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.template-list-heading h2 {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
  color: #1e293b;
}
.total-tag {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
}
.template-filter-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.catalog-search {
  display: flex;
  align-items: center;
  gap: 7px;
  border: 1px solid #e0e7f0;
  border-radius: 7px;
  padding: 8px 10px;
  width: 240px;
  min-width: 0;
  background: #fff;
}
.catalog-search svg {
  width: 14px;
  height: 14px;
  color: #9eacc0;
}
.catalog-search input {
  font-size: 12px;
  color: #334155;
  outline: 0;
  border: 0;
  width: 100%;
  background: none;
}
.catalog-search input::placeholder {
  color: #94a3b8;
}
.catalog-search:focus-within {
  border-color: #60a5fa;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.08);
}
.group-filter {
  min-width: 130px;
  max-width: 170px;
  font-size: 12px;
  padding: 7px 10px;
  border-radius: 7px;
  border: 1px solid #e0e7f0;
  color: #334155;
  background: #fff;
}
.status-filter {
  width: 110px;
  font-size: 12px;
  padding: 7px 10px;
  border-radius: 7px;
  border: 1px solid #e0e7f0;
  color: #334155;
  background: #fff;
}
.template-table {
  min-width: 860px;
  width: 100%;
  table-layout: fixed;
}
.template-table th {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  background: #f8fafc;
  padding: 12px 16px;
  text-align: left;
}
.template-table th:nth-child(1) { width: 36%; }
.template-table th:nth-child(2) { width: 14%; }
.template-table th:nth-child(3) { width: 18%; }
.template-table th:nth-child(4) { width: 16%; }
.template-table th:nth-child(5) { width: 16%; }
.template-table td {
  font-size: 13px;
  padding: 16px;
  vertical-align: middle;
  border-bottom: 1px solid #f1f5f9;
}
.template-table tbody tr:hover {
  background: #f8fafc;
}
.template-name-cell {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.template-name-cell > div {
  min-width: 0;
  flex: 1;
}
.template-file-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 2px;
  width: 36px;
  min-width: 36px;
  height: 42px;
  background: #eff5ff;
  border: 1px solid #dbeafe;
  border-radius: 7px;
  color: #2563eb;
}
.template-file-icon svg {
  width: 17px;
  height: 17px;
}
.template-file-icon small {
  font-size: 8px;
  letter-spacing: 0.5px;
  font-weight: 600;
}
.template-file-icon.pdf {
  background: #fff1f2;
  color: #e11d48;
  border-color: #fecdd3;
}
.template-name {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.6;
  text-align: left;
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
  overflow-wrap: anywhere;
}
.template-name:hover {
  color: #2563eb;
}
.template-name-cell p {
  font-size: 11px;
  color: #94a3b8;
  margin: 4px 0 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.template-group-tag {
  display: inline-block;
  max-width: 100%;
  font-size: 11px;
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 5px;
  padding: 3px 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.template-group-tag:hover {
  color: #2563eb;
  background: #eff6ff;
  border-color: #bfdbfe;
}
.template-state {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 5px;
  background: #f1f5f9;
  color: #64748b;
  white-space: nowrap;
}
.template-state i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}
.template-state.published {
  background: #f0fdf4;
  color: #16a34a;
}
.template-state.ready {
  background: #eff6ff;
  color: #2563eb;
}
.template-state.reviewing {
  background: #fffbeb;
  color: #d97706;
}
.template-field-summary {
  display: block;
  font-size: 11px;
  color: #94a3b8;
  margin-top: 4px;
}
.template-table .template-date {
  font-size: 12px;
  color: #64748b;
  font-variant-numeric: tabular-nums;
}
.template-row-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  white-space: nowrap;
}
.configure-link {
  color: #2563eb;
  font-size: 12px;
  white-space: nowrap;
  text-decoration: none;
}
.configure-link:hover {
  text-decoration: underline;
}
.configure-link-disabled {
  color: #94a3b8;
  font-size: 11px;
}
.template-more {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #64748b;
  background: none;
  border: 0;
  cursor: pointer;
  padding: 2px 4px;
}
.template-more:hover {
  color: #2563eb;
}
.catalog-chevron {
  width: 4px;
  height: 4px;
  border-right: 1.5px solid currentColor;
  border-bottom: 1.5px solid currentColor;
  transform: rotate(45deg);
  margin-top: -2px;
}
.template-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  color: #64748b;
  font-size: 12px;
}
.template-pagination > div {
  display: flex;
  gap: 8px;
}
.template-pagination .button {
  font-size: 12px;
  padding: 5px 12px;
}
.catalog-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 16px;
  color: #64748b;
  gap: 10px;
}
.catalog-empty > svg {
  width: 32px;
  height: 32px;
  color: #94a3b8;
}
.catalog-empty h3 {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
  margin: 0;
}
.catalog-empty p {
  font-size: 12px;
  color: #64748b;
  margin: 0;
}
.catalog-empty .button {
  margin-top: 6px;
}
.notice {
  color: #b91c1c;
  background: #fef2f2;
  padding: 10px 14px;
  border-radius: 6px;
  margin-bottom: 12px;
  font-size: 12px;
  border: 1px solid #fee2e2;
}
.text-button {
  color: #2563eb;
  text-decoration: underline;
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
}
.catalog-menu-shade {
  position: fixed;
  inset: 0;
  z-index: 65;
}
.catalog-action-menu {
  position: fixed;
  width: 170px;
  padding: 6px;
  background: #fff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.12);
  border-radius: 8px;
  outline: 0;
  z-index: 66;
}
.catalog-action-menu > button,
.catalog-action-menu > a {
  display: block;
  text-align: left;
  width: 100%;
  padding: 8px 10px;
  border-radius: 5px;
  font-size: 12px;
  color: #334155;
  text-decoration: none;
  background: none;
  border: 0;
  cursor: pointer;
}
.catalog-action-menu > *:hover {
  background: #f1f5f9;
  color: #2563eb;
}
.catalog-action-menu .danger {
  color: #dc2626;
  border-top: 1px solid #f1f5f9;
  margin-top: 3px;
  border-radius: 0;
}
.template-overlay {
  position: fixed;
  inset: 0;
  z-index: 70;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.template-dialog {
  width: 540px;
  max-width: 100%;
  max-height: 90vh;
  overflow: auto;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.18);
  color: #334155;
}
.editor-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 1px solid #edf0f5;
  gap: 16px;
}
.editor-heading h2 {
  font-size: 17px;
  font-weight: 600;
  margin: 0;
  color: #0f172a;
}
.editor-heading p {
  font-size: 12px;
  color: #64748b;
  margin: 4px 0 0;
}
.dialog-close {
  color: #94a3b8;
  font-size: 24px;
  line-height: 24px;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: none;
  border: 0;
  cursor: pointer;
}
.dialog-close:hover {
  background: #f1f5f9;
  color: #0f172a;
}
.editor-body {
  padding: 20px 24px;
}
.template-dialog label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 16px;
}
.template-dialog label > .field {
  display: block;
  margin-top: 6px;
}
.template-dialog .field {
  font-size: 13px;
  border: 1px solid #dce3ed;
  border-radius: 7px;
  padding: 8px 12px;
  min-height: 38px;
  background: #fff;
  color: #334155;
  width: 100%;
  box-sizing: border-box;
}
.template-dialog .field:focus {
  outline: 0;
  border-color: #60a5fa;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
}
.required {
  color: #ef4444;
  font-size: 12px;
}
.upload-section {
  margin-bottom: 16px;
}
.upload-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 8px;
}
.hidden-file {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
}
.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 22px 16px;
  border: 1px dashed #bfdbfe;
  background: #f8faff;
  border-radius: 8px;
  gap: 6px;
  cursor: pointer;
}
.upload-zone:hover,
.upload-zone.dragging {
  background: #eff6ff;
  border-color: #60a5fa;
}
.upload-icon {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  color: #3b82f6;
  margin-bottom: 2px;
}
.upload-icon svg {
  width: 26px;
  height: 26px;
}
.upload-zone strong {
  font-size: 12px;
  font-weight: 600;
  color: #334155;
}
.upload-zone > span:last-child {
  font-size: 11px;
  color: #94a3b8;
}
.upload-zone.has-file strong {
  color: #2563eb;
}
.editor-group-context {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 6px;
  margin-bottom: 16px;
  color: #64748b;
  border: 1px solid #e2e8f0;
}
.editor-group-context select {
  margin-left: auto;
  max-width: 65%;
  background-color: transparent;
  border: 0;
  color: #1e293b;
  font-size: 12px;
  outline: 0;
}
.editor-extra > summary {
  cursor: pointer;
  font-size: 12px;
  color: #64748b;
  padding: 2px 0;
}
.optional {
  font-size: 11px;
  color: #94a3b8;
  margin-left: 4px;
}
.editor-extra textarea {
  margin-top: 8px;
  resize: vertical;
}
.template-dialog footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 24px;
  background: #f8fafc;
  border-top: 1px solid #edf0f5;
  align-items: center;
}
.template-dialog footer .button {
  font-size: 12px;
  min-height: 34px;
  padding: 6px 16px;
}
.footer-hint {
  margin-right: auto;
  font-size: 11px;
  color: #94a3b8;
}
.template-dialog > h2 {
  font-size: 16px;
  margin: 20px 24px 10px;
  font-weight: 600;
  color: #0f172a;
}
.template-dialog > p {
  font-size: 13px;
  line-height: 1.7;
  margin: 0 24px 16px;
  color: #475569;
}
.template-preview {
  background: #fff;
  border-radius: 12px;
  width: 1200px;
  max-width: 100%;
  height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.template-preview header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid #e2e8f0;
  gap: 16px;
}
.template-preview header div {
  display: flex;
  gap: 10px;
}
.template-preview iframe {
  width: 100%;
  flex: 1;
  border: 0;
  min-height: 0;
}
@media (max-width: 800px) {
  .template-filters {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  .template-filter-controls {
    flex-wrap: wrap;
  }
  .catalog-search {
    width: 100%;
  }
}
</style>
