<script>
import { usePortalPage } from "../composables/usePortalPage.js";
import PageFrame from "../components/PageFrame.vue";

export default {
  components: { PageFrame },
  setup() {
    const context = usePortalPage("drafts");
    return { ...context, context };
  },
};
</script>
<template>
  <PageFrame :context="context">
    <section class="max-w-6xl mx-auto space-y-5">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-xl font-bold">起草记录</h1>
          <p class="text-xs text-slate-500 mt-2">
            保留背景、交易信息、大纲与正文，随时继续起草
          </p>
        </div>
        <RouterLink to="/draft" class="button primary">＋ 新建起草</RouterLink>
      </div>
      <div class="card p-4 flex items-center gap-3">
        <input
          v-model="search"
          class="field max-w-xs"
          placeholder="搜索草稿名称"
        /><label class="flex gap-2 text-xs text-slate-500"
          ><input type="checkbox" v-model="showArchived" />已归档</label
        >
      </div>
      <div class="card overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>合同名称</th>
              <th>更新时间</th>
              <th>当前阶段</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredDrafts">
              <td class="font-semibold">{{ item.title }}</td>
              <td>{{ dateTime(item.updated_at) }}</td>
              <td>
                <span class="pill">{{ statusName(item.status) }}</span>
              </td>
              <td>
                <div class="flex gap-3">
                  <RouterLink :to="'/draft?id=' + item.id" class="text-blue-600"
                    >继续起草</RouterLink
                  ><button
                    @click="archive('drafts', item)"
                    :disabled="busy || item.status === 'running'"
                    class="text-slate-400"
                  >
                    {{ item.archived ? "恢复" : "归档" }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!filteredDrafts.length" class="empty">
          暂无匹配的起草记录
        </div>
      </div>
    </section>
  </PageFrame>
</template>
