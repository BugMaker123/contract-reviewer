<script>
import { usePortalPage } from "../composables/usePortalPage.js";
import PageFrame from "../components/PageFrame.vue";
import CategoryEditor from "../components/portal/CategoryEditor.vue";
export default {
  components: { PageFrame, CategoryEditor },
  setup() {
    const context = usePortalPage("categories");
    return { ...context, context };
  },
};
</script>
<template>
  <PageFrame :context="context">
    <section class="max-w-6xl mx-auto space-y-5">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-xl font-bold">合同业务分类维护</h1>
          <p class="text-xs text-slate-500 mt-2">
            统一业务分类与适用范围，为企业审查清单绑定专项标准
          </p>
        </div>
        <button @click="editCategory()" class="button primary">
          ＋ 新增业务分类
        </button>
      </div>
      <div class="card p-4">
        <input
          v-model="search"
          class="field max-w-xs"
          placeholder="搜索分类名称或编码"
          aria-label="搜索业务分类"
        />
      </div>
      <div class="card overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>业务分类名称</th>
              <th>分类编码</th>
              <th>分类说明与适用范围</th>
              <th>排序号</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in filteredCategories" :key="row.id">
              <td class="font-semibold">{{ row.name }}</td>
              <td>
                <span class="pill blue">{{ row.code }}</span>
              </td>
              <td>{{ row.description || "—" }}</td>
              <td>{{ row.sort_order }}</td>
              <td>{{ dateTime(row.updated_at) }}</td>
              <td>
                <button @click="editCategory(row)" class="text-blue-600">
                  编辑
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!filteredCategories.length" class="empty">
          {{
            categories.length
              ? "没有匹配的业务分类"
              : "暂无业务分类，新增后可在清单中绑定"
          }}
        </div>
        <div class="table-summary">
          共 {{ filteredCategories.length }} 条记录
        </div>
      </div>
    </section>
    <CategoryEditor :context="context" />
  </PageFrame>
</template>
