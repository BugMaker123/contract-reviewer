<script>
import { usePortalPage } from "../composables/usePortalPage.js";
import PageFrame from "../components/PageFrame.vue";
import CategoryEditor from "../components/portal/CategoryEditor.vue";
import CatalogPagination from "../components/portal/CatalogPagination.vue";
import CatalogDelete from "../components/portal/CatalogDelete.vue";
export default {
  components: { PageFrame, CategoryEditor, CatalogPagination, CatalogDelete },
  setup() {
    const context = usePortalPage("categories");
    return { ...context, context };
  },
};
</script>
<template>
  <PageFrame :context="context">
    <section class="checklists-page categories-page">
      <header class="checklists-heading">
        <div>
          <h1>业务分类维护</h1>
          <p>
            统一业务分类与适用范围，为企业审查清单绑定专项标准
          </p>
        </div>
        <button @click="editCategory()" :disabled="busy" class="button primary">
          ＋ 新增业务分类
        </button>
      </header>
      <div class="checklists-list card">
      <div class="categories-filters">
        <input
          v-model="search"
          class="field"
          placeholder="搜索分类名称或编码"
          aria-label="搜索业务分类"
        />
        <span>{{ fetching ? '正在查询…' : `共 ${total} 个业务分类` }}</span>
      </div>
      <div class="checklists-table-scroll">
        <table class="data-table categories-table">
          <thead>
            <tr>
              <th>业务分类名称</th>
              <th>分类编码</th>
              <th>分类说明与适用范围</th>
              <th>清单数量</th><th>排序号</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td><strong :title="row.name">{{ row.name }}</strong></td>
              <td>
                <span class="category-code">{{ row.code }}</span>
              </td>
              <td><p class="category-description" :title="row.description">{{ row.description || "—" }}</p></td>
              <td>{{ row.checklist_count }}</td><td>{{ row.sort_order }}</td>
              <td>{{ dateTime(row.updated_at) }}</td>
              <td><div class="checklists-row-actions">
                <RouterLink :to="'/checklists?category=' + row.id" class="checklists-use">查看清单</RouterLink>
                <RouterLink :to="'/checklists?category=' + row.id + '&create=1'">添加清单</RouterLink>
                <button :disabled="busy" @click="editCategory(row)">
                  编辑
                </button>
                <button :disabled="busy" @click="requestDelete(row)" class="is-secondary">删除</button>
              </div></td>
            </tr>
          </tbody>
        </table>
        </div>
        <div v-if="fetching" class="catalog-loading" role="status">正在查询…</div>
        <div v-else-if="!rows.length" class="empty">{{ search ? '没有匹配的业务分类' : '暂无业务分类，新增后可在分类下添加清单' }}</div>
        <CatalogPagination :context="context" />
      </div>
    </section>
    <CategoryEditor :context="context" /><CatalogDelete :context="context" />
  </PageFrame>
</template>

<style scoped>
.categories-filters { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:12px 16px; border-bottom:1px solid #e2e8f0; }
.categories-filters .field { width:360px; max-width:100%; height:34px; padding:5px 9px; font-size:12px; border-radius:6px; }
.categories-filters > span { font-size:11px; color:#94a3b8; white-space:nowrap; }
.categories-table { width:100%; min-width:1040px; table-layout:fixed; }
.categories-table th,.categories-table td { padding:13px 16px; }
.categories-table th:first-child { width:150px; }.categories-table th:nth-child(2) { width:140px; }.categories-table th:nth-child(4) { width:80px; }.categories-table th:nth-child(5) { width:70px; }.categories-table th:nth-child(6) { width:165px; }.categories-table th:last-child { width:280px; }
.categories-table td:first-child strong { display:block; font-size:13px; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.categories-table td { font-size:12px; }.categories-table td:nth-child(n+3):nth-child(-n+6) { color:#64748b; }
.category-code { display:inline-block; max-width:100%; overflow:hidden; text-overflow:ellipsis; vertical-align:middle; font-family:ui-monospace,monospace; font-size:11px; color:#64748b; }
.category-description { margin:0; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; line-height:1.7; }
@media(max-width:650px) { .categories-filters { flex-wrap:wrap; gap:8px; }.categories-filters .field { width:100%; } }
</style>
