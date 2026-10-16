<script>
import { usePortalPage } from "../composables/usePortalPage.js";
import PageFrame from "../components/PageFrame.vue";
import ReviewStatistics from "../components/portal/ReviewStatistics.vue";

export default {
  components: { PageFrame, ReviewStatistics },
  setup() {
    const context = usePortalPage("records");
    return { ...context, context };
  },
};
</script>
<template>
  <PageFrame :context="context">
    <section class="max-w-6xl mx-auto space-y-5">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-xl font-bold">审查记录</h1>
          <p class="text-xs text-slate-500 mt-2">
            每次审查独立留档，可继续处理或查看历史版本
          </p>
        </div>
        <div class="flex gap-2"><a href="/api/reports/reviews?format=csv" class="button">导出全部审查报表</a><RouterLink to="/" class="button primary">＋ 新建审查</RouterLink></div>
      </div>
      <ReviewStatistics />
      <div class="card p-4 flex flex-wrap items-center gap-3">
        <input
          v-model="search"
          class="field max-w-xs"
          placeholder="搜索合同名称"
          aria-label="搜索审查记录"
        /><select v-model="modeFilter" class="field w-auto">
          <option value="all">全部审查模式</option>
          <option v-for="mode in modes" :value="mode.id">
            {{ mode.name }}
          </option></select
        ><select v-model="statusFilter" class="field w-auto">
          <option value="all">全部状态</option>
          <option v-for="(name, id) in taskStatuses" :value="id">
            {{ name }}
          </option></select
        ><label class="text-xs text-slate-500"
          >开始日期<input
            type="date"
            v-model="fromDate"
            class="field mt-1" /></label
        ><label class="text-xs text-slate-500"
          >结束日期<input
            type="date"
            v-model="toDate"
            class="field mt-1" /></label
        ><label class="flex gap-2 items-center text-xs text-slate-500"
          ><input type="checkbox" v-model="showArchived" />已归档</label
        >
      </div>
      <div class="card overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>合同名称</th>
              <th>任务类型</th>
              <th>更新时间</th>
              <th>状态</th>
              <th>采纳修订</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in filteredTasks">
              <td>
                <RouterLink
                  :to="'/workbench?task=' + task.id"
                  class="font-semibold text-slate-800"
                  >{{ task.title }}</RouterLink
                >
                <div class="text-slate-400 text-[11px] mt-1">
                  {{ task.type }}
                </div>
              </td>
              <td>{{ modeName(task.mode) }}</td>
              <td class="whitespace-nowrap">{{ dateTime(task.updated_at) }}</td>
              <td>
                <span class="pill" :class="statusColor(task.status)">{{
                  statusName(task.status)
                }}</span>
              </td>
              <td>{{ task.applied_count || 0 }} 项</td>
              <td>
                <div class="flex gap-3">
                  <RouterLink
                    :to="'/workbench?task=' + task.id"
                    class="text-blue-600"
                    >打开</RouterLink
                  ><button
                    @click="archive('tasks', task)"
                    :disabled="task.status === 'running' || busy"
                    class="text-slate-400"
                  >
                    {{ task.archived ? "恢复" : "归档" }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!filteredTasks.length" class="empty">
          {{
            tasks.length
              ? "没有匹配的审查记录，请调整筛选条件"
              : "暂无审查记录，先创建一个审查任务"
          }}
        </div>
      </div>
    </section>
  </PageFrame>
</template>
