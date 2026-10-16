<script>
import { usePortalPage } from "../composables/usePortalPage.js";
import PageFrame from "../components/PageFrame.vue";
import ChecklistEditor from "../components/portal/ChecklistEditor.vue";
export default {
  components: { PageFrame, ChecklistEditor },
  setup() {
    const context = usePortalPage("checklists");
    return { ...context, context };
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
      <div class="card p-4 flex gap-3 items-center">
        <input
          v-model="search"
          class="field max-w-xs"
          placeholder="搜索清单、要点或条款内容"
        /><select v-model="categoryFilter" class="field max-w-xs">
          <option value="">全部业务分类</option>
          <option v-for="row in categories" :value="row.id">
            {{ row.name }}
          </option></select
        ><label class="flex items-center gap-2 text-xs text-slate-500"
          ><input type="checkbox" v-model="showArchived" />已归档</label
        >
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <article v-for="list in filteredLists" class="card p-5">
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
            {{ list.items.length }} 项检查
          </p>
          <p class="text-xs text-slate-500 mt-3 leading-relaxed">
            {{ list.description || "尚未填写清单说明" }}
          </p>
          <div class="flex gap-3 mt-5 pt-4 border-t border-slate-100">
            <button @click="editChecklist(list)" class="text-xs text-blue-600">
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
          </div>
        </article>
      </div>
      <div v-if="!filteredLists.length" class="card empty">
        暂无{{
          showArchived ? "已归档" : "可用"
        }}清单，创建或导入你们的企业检查要求
      </div>
    </section>
    <ChecklistEditor :context="context" />
  </PageFrame>
</template>
