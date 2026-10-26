<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import ReviewIcon from '../components/portal/ReviewIcon.vue';
import { usePortalShell } from '../stores/portal.js';

const router = useRouter();
const { api, notify } = usePortalShell();

const groups = ref([]);
const loading = ref(false);
const busy = ref(false);
const error = ref('');
const modalError = ref('');
const search = ref('');

const editor = ref(null); // { mode: 'create' | 'edit', row?: any }
const removal = ref(null); // row
const form = reactive({ name: '', description: '', revision: null });

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

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const list = await api('/api/template-groups');
    groups.value = Array.isArray(list) ? list : [];
  } catch (e) {
    error.value = e.message || '加载分组失败';
  } finally {
    loading.value = false;
  }
}

onMounted(load);

const filteredGroups = computed(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return groups.value;
  return groups.value.filter(g =>
    (g.name || '').toLowerCase().includes(q) ||
    (g.description || '').toLowerCase().includes(q)
  );
});

const totalCount = computed(() => groups.value.length);
const totalTemplates = computed(() => groups.value.reduce((sum, g) => sum + (g.template_count || 0), 0));

function openEdit(row = null) {
  modalError.value = '';
  Object.assign(form, {
    name: row?.name || '',
    description: row?.description || '',
    revision: row?.revision ?? null,
  });
  editor.value = { mode: row ? 'edit' : 'create', row };
}

function closeEditor() {
  if (busy.value) return;
  editor.value = null;
  modalError.value = '';
}

async function save() {
  const name = form.name.trim();
  if (!name) {
    modalError.value = '请填写分组名称';
    return;
  }
  busy.value = true;
  modalError.value = '';
  try {
    const { mode, row } = editor.value;
    const body = {
      name,
      description: form.description?.trim() || '',
      revision: form.revision,
    };
    if (mode === 'edit') {
      await api(`/api/template-groups/${row.id}`, 'PUT', body);
      notify('分组信息已修改');
    } else {
      await api('/api/template-groups', 'POST', { name: body.name, description: body.description });
      notify('新分组已创建');
    }
    editor.value = null;
    await load();
  } catch (e) {
    modalError.value = e.message || '保存失败，请稍后重试';
  } finally {
    busy.value = false;
  }
}

function askDelete(row) {
  modalError.value = '';
  removal.value = row;
}

function closeRemoval() {
  if (busy.value) return;
  removal.value = null;
  modalError.value = '';
}

async function remove() {
  if (!removal.value) return;
  busy.value = true;
  modalError.value = '';
  try {
    const row = removal.value;
    await api(`/api/template-groups/${row.id}?revision=${row.revision}`, 'DELETE');
    notify(`分组“${row.name}”已删除`);
    removal.value = null;
    await load();
  } catch (e) {
    modalError.value = e.message || '删除失败，该分组下可能仍有合同模板';
  } finally {
    busy.value = false;
  }
}

function viewTemplates(groupId) {
  router.push({ path: '/templates', query: { group: groupId } });
}
</script>

<template>
  <section class="checklists-page template-groups-page">
    <header class="checklists-heading">
      <div>
        <h1>模板分组维护</h1>
        <p>统一维护合同模板业务分组与部门归属，方便各业务条线规范检索与使用。</p>
      </div>
      <div class="catalog-heading-actions">
        <RouterLink to="/templates" class="button">
          <ReviewIcon name="templates" />查看合同模板
        </RouterLink>
        <button v-can="'catalog.maintain'" class="button primary" :disabled="busy" @click="openEdit()">
          <ReviewIcon name="plus" />新建分组
        </button>
      </div>
    </header>

    <p v-if="error" class="notice" role="alert">
      {{ error }} <button class="text-button" @click="load">重试</button>
    </p>

    <div class="card groups-card">
      <div class="groups-filters">
        <div class="catalog-search">
          <ReviewIcon name="search" />
          <input
            v-model="search"
            aria-label="搜索模板分组"
            placeholder="搜索分组名称或说明"
            maxlength="100"
          />
        </div>
        <div class="groups-stat">
          <span>共 {{ totalCount }} 个分组</span>
          <span class="stat-divider">·</span>
          <span>共收录 {{ totalTemplates }} 个模板</span>
        </div>
      </div>

      <div class="checklists-table-scroll">
        <table class="data-table groups-table">
          <thead>
            <tr>
              <th>分组名称</th>
              <th>说明与适用业务</th>
              <th>关联模板数量</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredGroups" :key="row.id">
              <td>
                <div class="group-title-cell">
                  <span class="group-icon-badge">
                    <ReviewIcon name="categories" />
                  </span>
                  <div>
                    <strong class="group-title">{{ row.name }}</strong>
                    <span v-if="row.name === '未分组'" class="system-badge">系统默认</span>
                  </div>
                </div>
              </td>
              <td>
                <p class="group-desc" :title="row.description">
                  {{ row.description || '—' }}
                </p>
              </td>
              <td>
                <button
                  type="button"
                  class="count-badge"
                  :class="{ 'has-templates': row.template_count > 0 }"
                  :title="`查看该分组下的 ${row.template_count} 个模板`"
                  @click="viewTemplates(row.id)"
                >
                  <ReviewIcon name="templates" />
                  <span>{{ row.template_count || 0 }} 个模板</span>
                </button>
              </td>
              <td class="tabular-date">{{ dateTime(row.updated_at) }}</td>
              <td>
                <div class="row-actions">
                  <button
                    type="button"
                    class="action-link"
                    @click="viewTemplates(row.id)"
                  >
                    查看模板
                  </button>
                  <button v-can="'catalog.maintain'"
                    type="button"
                    class="action-link"
                    :disabled="busy"
                    @click="openEdit(row)"
                  >
                    编辑
                  </button>
                  <button
                    type="button"
                    class="action-link danger"
                    :disabled="busy || row.name === '未分组'"
                    :title="row.name === '未分组' ? '系统默认分组不可删除' : ''"
                    @click="askDelete(row)"
                  >
                    删除
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="loading" class="empty" role="status">正在加载分组…</div>
      <div v-else-if="!filteredGroups.length" class="catalog-empty">
        <ReviewIcon name="categories" />
        <h3>{{ search ? '没有匹配的模板分组' : '暂无模板分组' }}</h3>
        <p>{{ search ? '调整搜索词后再试。' : '创建业务部门或合同类别分组，让模板归类井然有序。' }}</p>
        <button v-can="'catalog.maintain'" v-if="!search" class="button primary" @click="openEdit()">
          立即新建分组
        </button>
      </div>
    </div>
  </section>

  <!-- 编辑/新建分组弹窗 -->
  <Teleport to="body">
    <div
      v-if="editor"
      class="template-overlay"
      @click.self="closeEditor"
      @keydown.esc="closeEditor"
    >
      <form
        class="template-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="group-edit-title"
        @submit.prevent="save"
      >
        <header class="editor-heading">
          <div>
            <h2 id="group-edit-title">
              {{ editor.mode === 'edit' ? '编辑' : '新建' }}模板分组
            </h2>
            <p>维护同类合同模板的归集分类，便于规范查找与权限归属。</p>
          </div>
          <button
            type="button"
            class="dialog-close"
            aria-label="关闭弹窗"
            :disabled="busy"
            @click="closeEditor"
          >
            ×
          </button>
        </header>

        <div class="editor-body">
          <label>
            分组名称 <span class="required">*</span>
            <input
              v-model="form.name"
              aria-label="分组名称"
              class="field"
              placeholder="例如：采购供应链、劳动人事、市场营销"
              required
              maxlength="100"
              :disabled="busy"
              autofocus
            />
          </label>

          <label>
            分组说明 <span class="optional">选填</span>
            <textarea
              v-model="form.description"
              class="field"
              aria-label="说明"
              placeholder="简要描述该分组所适用的合同类型、业务部门或流转场景"
              rows="3"
              maxlength="2000"
              :disabled="busy"
            ></textarea>
          </label>

          <p v-if="modalError" class="notice" role="alert">{{ modalError }}</p>
        </div>

        <footer>
          <button
            type="button"
            class="button"
            :disabled="busy"
            @click="closeEditor"
          >
            取消
          </button>
          <button class="button primary" :disabled="busy">
            {{ busy ? '正在保存…' : '保存' }}
          </button>
        </footer>
      </form>
    </div>

    <!-- 删除确认弹窗 -->
    <div
      v-if="removal"
      class="template-overlay"
      @click.self="closeRemoval"
      @keydown.esc="closeRemoval"
    >
      <div
        class="template-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="group-delete-title"
      >
        <h2 id="group-delete-title">删除模板分组</h2>
        <p>
          确定删除分组“<strong>{{ removal.name }}</strong>”？
        </p>
        <div v-if="removal.template_count > 0" class="delete-warning">
          <strong>提示：</strong>该分组下目前包含 <b>{{ removal.template_count }}</b> 个合同模板。请先在“合同模板”中将模板迁移至其他分组或删除模板，否则无法删除该分组。
        </div>
        <p v-if="modalError" class="notice" role="alert">{{ modalError }}</p>
        <footer>
          <button class="button" :disabled="busy" @click="closeRemoval">
            取消
          </button>
          <button v-can="'catalog.maintain'" class="button primary" :disabled="busy" @click="remove">
            {{ busy ? '正在删除…' : '确认删除' }}
          </button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.template-groups-page {
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
.groups-card {
  border-radius: 12px;
  box-shadow: 0 1px 3px #0f172a06;
  background: #fff;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}
.groups-filters {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid #e8edf4;
}
.catalog-search {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #e0e7f0;
  border-radius: 8px;
  padding: 8px 12px;
  width: 320px;
  max-width: 100%;
  background: #fff;
}
.catalog-search svg {
  width: 14px;
  height: 14px;
  color: #9eacc0;
}
.catalog-search input {
  font-size: 13px;
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
.groups-stat {
  font-size: 12px;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 6px;
}
.stat-divider {
  color: #cbd5e1;
}
.groups-table {
  width: 100%;
  min-width: 860px;
  table-layout: fixed;
}
.groups-table th {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  background: #f8fafc;
  padding: 12px 18px;
  text-align: left;
}
.groups-table th:nth-child(1) { width: 28%; }
.groups-table th:nth-child(2) { width: 34%; }
.groups-table th:nth-child(3) { width: 14%; }
.groups-table th:nth-child(4) { width: 14%; }
.groups-table th:nth-child(5) { width: 10%; }
.groups-table td {
  font-size: 13px;
  padding: 16px 18px;
  vertical-align: middle;
  border-bottom: 1px solid #f1f5f9;
}
.groups-table tbody tr:hover {
  background: #f8fafc;
}
.group-title-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}
.group-icon-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #eff6ff;
  color: #2563eb;
  border: 1px solid #dbeafe;
  shrink: 0;
}
.group-icon-badge svg {
  width: 16px;
  height: 16px;
}
.group-title {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}
.system-badge {
  display: inline-block;
  font-size: 10px;
  color: #64748b;
  background: #f1f5f9;
  border-radius: 4px;
  padding: 1px 5px;
  margin-top: 3px;
}
.group-desc {
  margin: 0;
  font-size: 12px;
  color: #64748b;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.6;
}
.count-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  cursor: pointer;
  transition: all 0.15s ease;
}
.count-badge svg {
  width: 13px;
  height: 13px;
}
.count-badge.has-templates {
  color: #2563eb;
  background: #eff6ff;
  border-color: #bfdbfe;
  font-weight: 500;
}
.count-badge:hover {
  border-color: #60a5fa;
  background: #dbeafe;
}
.tabular-date {
  font-size: 12px;
  color: #64748b;
  font-variant-numeric: tabular-nums;
}
.row-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.action-link {
  font-size: 12px;
  color: #2563eb;
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
}
.action-link:hover {
  text-decoration: underline;
}
.action-link.danger {
  color: #dc2626;
}
.action-link:disabled {
  color: #cbd5e1;
  cursor: not-allowed;
  text-decoration: none;
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
.delete-warning {
  margin: 12px 26px 16px;
  padding: 10px 12px;
  background: #fffbeb;
  border: 1px solid #fef3c7;
  border-radius: 6px;
  font-size: 12px;
  color: #b45309;
  line-height: 1.6;
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
  width: 520px;
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
  color: #334155;
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
.optional {
  font-size: 11px;
  color: #94a3b8;
  font-weight: normal;
  margin-left: 4px;
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
@media (max-width: 650px) {
  .groups-filters {
    flex-direction: column;
    align-items: stretch;
  }
  .catalog-search {
    width: 100%;
  }
}
</style>
