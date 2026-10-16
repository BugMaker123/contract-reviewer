<script>
import { ref } from "vue";
import { usePortalPage } from "../composables/usePortalPage.js";
import PageFrame from "../components/PageFrame.vue";
import ChecklistEditor from "../components/portal/ChecklistEditor.vue";
import CatalogPagination from "../components/portal/CatalogPagination.vue";
import CatalogDelete from "../components/portal/CatalogDelete.vue";
export default {
  components: { PageFrame, ChecklistEditor, CatalogPagination, CatalogDelete },
  setup() {
    const context = usePortalPage("checklists");
    const detail = ref(null);
    const viewChecklist = async (list) => {
      context.busy.value = true;
      try { detail.value = await context.api('/api/checklists/' + list.id); }
      catch (err) { context.error.value = err.message; }
      finally { context.busy.value = false; }
    };
    return { ...context, context, detail, viewChecklist };
  },
};
</script>
<template>
  <PageFrame :context="context">
    <section class="max-w-6xl mx-auto space-y-5">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-xl font-bold">企业审查清单</h1>
          <p class="text-xs text-slate-500 mt-2">
            维护适用范围与检查要求，发布后用于逐项审查
          </p>
        </div>
        <button @click="editChecklist()" class="button primary">
          ＋ 创建审查清单
        </button>
      </div>
      <div class="card p-4 flex gap-3 items-center catalog-filters">
        <input
          v-model="search"
          class="field max-w-xs"
          placeholder="搜索清单、要点或条款内容"
        /><select aria-label="筛选业务分类" v-model="categoryFilter" class="field max-w-xs">
          <option value="">全部业务分类</option>
          <option v-for="row in categories" :value="row.id">
            {{ row.name }}
          </option></select
        ><select v-model="publicationFilter" class="field max-w-xs" aria-label="发布状态"><option value="">全部发布状态</option><option value="true">已发布</option><option value="false">草稿</option></select><label class="flex items-center gap-2 text-xs text-slate-500"
          ><input type="checkbox" v-model="showArchived" />已归档</label
        >
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <article v-for="list in rows" :key="list.id" class="card p-5">
          <div class="flex justify-between items-start gap-3">
            <h2 class="font-semibold text-sm">{{ list.name }}</h2>
            <span class="pill" :class="list.published ? 'green' : ''"
              >{{ list.published ? "已发布" : "草稿" }} · v{{
                list.version
              }}</span
            >
          </div>
          <p class="text-xs text-slate-500 mt-2">
            {{ categoryName(list.category_id) }} · {{ list.contract_type }} ·
            {{ list.item_count }} 项检查
          </p>
          <p class="text-xs text-slate-500 mt-3 leading-relaxed">
            {{ list.description || "尚未填写清单说明" }}
          </p>
          <div class="flex gap-3 mt-5 pt-4 border-t border-slate-100">
            <button :disabled="busy" @click="viewChecklist(list)" class="text-xs text-blue-600">查看</button>
            <button :disabled="busy" @click="editChecklist(list)" class="text-xs text-blue-600">
              编辑清单</button
            ><RouterLink
              v-if="list.published && !list.archived"
              :to="'/?checklist=' + list.id"
              class="text-xs text-blue-600"
              >使用清单审查 →</RouterLink
            ><button
              @click="archive('checklists', list)"
              :disabled="busy"
              class="ml-auto text-xs text-slate-400"
            >
              {{ list.archived ? "恢复" : "归档" }}
            </button>
            <button :disabled="busy" @click="requestDelete(list)" class="text-xs text-red-700">删除</button>
          </div>
        </article>
      </div>
      <div v-if="fetching" class="catalog-loading" role="status">正在查询…</div>
      <div v-else-if="!rows.length" class="card empty">
        暂无{{
          showArchived ? "已归档" : "可用"
        }}清单，创建或导入你们的企业检查要求
      </div>
      <CatalogPagination :context="context" />
    </section>
    <div v-if="detail" class="modal" @keydown.esc="detail = null">
      <section class="modal-panel max-w-4xl p-6 space-y-4" role="dialog" aria-modal="true" aria-label="清单详情">
        <div class="flex justify-between gap-3"><h2 class="font-bold">{{ detail.name }}</h2><button @click="detail = null" aria-label="关闭清单详情">✕</button></div>
        <p class="text-xs text-slate-500">{{ categoryName(detail.category_id) }} · {{ detail.contract_type }} · v{{ detail.version }} · {{ detail.published ? '已发布' : '草稿' }}</p>
        <p class="text-sm">{{ detail.description || '暂无说明' }}</p>
        <article v-for="(item, index) in detail.items" :key="item.id" class="card p-4">
          <h3 class="text-sm font-semibold">{{ index + 1 }}. {{ item.title }} <span class="pill" :class="item.severity === 'critical' ? 'red' : 'amber'">{{ {critical:'高风险',warning:'中风险',info:'低风险'}[item.severity] }}</span></h3>
          <p class="text-xs mt-3">{{ item.requirement }}</p>
          <p class="text-xs text-slate-500 mt-2">核验方式：{{ {semantic:'语义核验',contains_all:'包含全部文字',contains_any:'包含任一文字',forbidden:'禁止包含'}[item.operator] }}{{ item.keywords?.length ? ' · ' + item.keywords.join('、') : '' }}</p>
          <p v-if="item.suggestion" class="text-xs text-slate-500 mt-2">处理建议：{{ item.suggestion }}</p>
        </article>
      </section>
    </div>
    <CatalogDelete :context="context" />
    <ChecklistEditor :context="context" />
  </PageFrame>
</template>
