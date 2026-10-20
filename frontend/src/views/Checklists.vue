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
    <section class="checklists-page">
      <header class="checklists-heading"><div><h1>企业审查清单</h1><p>保存常用审查要求，下次直接选用。</p></div><button @click="editChecklist()" :disabled="busy || importing" class="button primary">＋ 创建审查清单</button></header>
      <div class="checklists-list card">
        <div class="checklists-filters"><input v-model="search" class="field" placeholder="搜索清单或审查要求" aria-label="搜索审查清单" /><select aria-label="筛选业务分类" v-model="categoryFilter" class="field"><option value="">全部业务分类</option><option v-for="row in categories" :key="row.id" :value="row.id">{{ row.name }}</option></select><select v-model="publicationFilter" class="field" aria-label="发布状态"><option value="">全部状态</option><option value="true">可用</option><option value="false">草稿</option></select><label><input type="checkbox" v-model="showArchived" />已归档</label></div>
        <div class="checklists-table-scroll"><table class="data-table checklists-table"><thead><tr><th>清单名称</th><th>业务分类</th><th>审查要求</th><th>状态</th><th>操作</th></tr></thead><tbody>
          <tr v-for="list in rows" :key="list.id"><td><strong :title="list.name">{{ list.name }}</strong><p v-if="list.description" :title="list.description">{{ list.description }}</p></td><td>{{ categoryName(list.category_id) }}</td><td>{{ list.item_count }} 条</td><td><span class="pill" :class="list.published && !list.archived ? 'green' : ''">{{ list.archived ? '已归档' : list.published ? '可用' : '草稿' }}</span></td><td><div class="checklists-row-actions"><RouterLink v-if="list.published && !list.archived" :to="'/?checklist=' + list.id" class="checklists-use">使用清单</RouterLink><button :disabled="busy || importing" @click="editChecklist(list)">编辑清单</button><button :disabled="busy || importing" @click="viewChecklist(list)">查看</button><button :disabled="busy || importing" @click="archive('checklists',list)" class="is-secondary">{{ list.archived ? '恢复' : '归档' }}</button><button :disabled="busy || importing" @click="requestDelete(list)" class="is-secondary">删除</button></div></td></tr>
        </tbody></table></div>
        <div v-if="fetching" class="catalog-loading" role="status">正在查询…</div>
        <div v-else-if="!rows.length" class="empty">{{ search || categoryFilter || publicationFilter || showArchived ? '没有匹配的清单，请调整筛选条件' : '还没有清单。创建一份，写下你常用的审查要求。' }}</div>
        <CatalogPagination :context="context" />
      </div>
    </section>
    <div v-if="detail" class="modal" @keydown.esc="detail = null">
      <section class="modal-panel checklist-detail" role="dialog" aria-modal="true" aria-label="清单详情">
        <header><div><h2>{{ detail.name }}</h2><p>{{ detail.items.length }} 条要求 · {{ categoryName(detail.category_id) }} · 第 {{ detail.version }} 版</p></div><button @click="detail = null" aria-label="关闭清单详情">关闭</button></header>
        <p v-if="detail.description" class="checklist-detail-description">{{ detail.description }}</p>
        <ol class="checklist-detail-items"><li v-for="(item,index) in detail.items" :key="item.id"><span>{{ index + 1 }}</span><div><strong v-if="item.title !== item.requirement && item.title !== item.requirement.slice(0,60)">{{ item.title }}</strong><p>{{ item.requirement }}</p></div></li></ol>
        <details class="checklist-detail-rules"><summary>查看高级规则配置</summary><p v-for="(item,index) in detail.items" :key="item.id">{{ index + 1 }}. {{ {semantic:'按要求理解并判断',contains_all:'包含全部文字',contains_any:'包含任一文字',forbidden:'禁止包含'}[item.operator] }} · {{ {critical:'重大风险',warning:'一般风险',info:'优化建议'}[item.severity] }}{{ item.keywords?.length ? ' · '+item.keywords.join('、') : '' }}{{ item.suggestion ? ' · 建议：'+item.suggestion : '' }}</p></details>
      </section>
    </div>
    <CatalogDelete :context="context" /><ChecklistEditor :context="context" />
  </PageFrame>
</template>
