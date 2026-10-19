<script>
import { ref } from "vue";
import CatalogPagination from "../components/portal/CatalogPagination.vue";
import RecordComparison from "../components/portal/RecordComparison.vue";
import { usePortalPage } from "../composables/usePortalPage.js";
import PageFrame from "../components/PageFrame.vue";
import ReviewStatistics from "../components/portal/ReviewStatistics.vue";

export default {
  components: { PageFrame, ReviewStatistics, CatalogPagination, RecordComparison },
  setup() {
    const context = usePortalPage("records");
    return { ...context, context, comparisonTask: ref(null) };
  },
};
</script>
<template>
  <PageFrame :context="context">
    <section class="records-page">
      <div class="records-heading">
        <div>
          <h1 class="text-xl font-bold">审查记录</h1>
          <p class="text-xs text-slate-500 mt-2">
            每次审查独立留档，可继续处理或查看历史版本
          </p>
        </div>
        <div class="records-heading-actions"><a href="/api/reports/reviews?format=csv" class="button">导出全部审查报表</a><RouterLink to="/" class="button primary">＋ 新建审查</RouterLink></div>
      </div>
      <ReviewStatistics />
      <div class="records-list card">
      <div class="records-filters" aria-label="审查记录筛选">
        <input v-model="search" class="field records-search" placeholder="搜索合同名称" aria-label="搜索审查记录" />
        <select v-model="modeFilter" class="field" aria-label="审查模式">
          <option value="all">全部审查模式</option><option v-for="mode in modes" :key="mode.id" :value="mode.id">{{ mode.name }}</option>
        </select>
        <select v-model="statusFilter" class="field" aria-label="审查状态">
          <option value="all">全部状态</option><option v-for="(name,id) in taskStatuses" :key="id" :value="id">{{ name }}</option>
        </select>
        <div class="records-date-range"><input type="date" v-model="fromDate" class="field" aria-label="开始日期" title="开始日期" /><span>至</span><input type="date" v-model="toDate" class="field" aria-label="结束日期" title="结束日期" /></div>
        <label class="records-archive"><input type="checkbox" v-model="showArchived" />已归档</label>
      </div>
      <div class="records-table-scroll">
        <table class="data-table records-table">

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
            <tr v-for="task in filteredTasks" :key="task.id">
              <td>
                <RouterLink
                  :to="'/workbench?task=' + task.id"
                  class="records-contract-title font-semibold text-slate-800"
                  :title="task.title"
                  >{{ task.title }}</RouterLink
                >
                <div class="text-slate-400 text-[11px] mt-1">
                  {{ task.type }} · {{ task.run_number ? '第 ' + task.run_number + ' 次审查结果' : '尚无审查结果' }}
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
                <div class="records-row-actions">
                  <RouterLink
                    :to="'/workbench?task=' + task.id"
                    class="records-open text-blue-600"
                    >打开</RouterLink
                  ><a v-if="task.active_run" :href="`/api/runs/${task.active_run}/export?scope=report`" class="text-blue-600">导出审核结果</a>
                  <a v-if="task.active_run" :href="`/api/runs/${task.active_run}/export?scope=current`" class="text-emerald-700" :title="`第 ${task.run_number} 次审查采纳稿`">导出采纳稿</a>
                  <button v-if="task.active_run" class="text-blue-600" @click="comparisonTask = task">前后对比</button>
                  <button
                    @click="archive('tasks', task)"
                    :disabled="['running','queued'].includes(task.status) || busy"
                    class="text-slate-400"
                  >
                    {{ task.archived ? "恢复" : "归档" }}
                  </button>
                </div>
                <p v-if="task.active_run && ['draft','failed','interrupted','running','queued'].includes(task.status)" class="text-xs text-amber-700 mt-2">导出及对比使用第 {{ task.run_number }} 次已留档结果</p>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!filteredTasks.length" class="empty">
          {{
            search || modeFilter !== 'all' || statusFilter !== 'all' || fromDate || toDate || showArchived
              ? "没有匹配的审查记录，请调整筛选条件"
              : "暂无审查记录，先创建一个审查任务"
          }}
        </div>
      </div>
      <CatalogPagination :context="context" />
      </div>
      <RecordComparison v-if="comparisonTask" :task="comparisonTask" @close="comparisonTask = null" />
    </section>
  </PageFrame>
</template>
