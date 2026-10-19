<script setup>
import { ref, onActivated, onMounted } from 'vue';
const report = ref(null);
const error = ref('');
let loading = false;
async function refresh() {
  if (loading) return;
  loading = true;
  try {
    const response = await fetch('/api/reports/reviews');
    if (!response.ok) throw new Error('统计暂时无法加载');
    report.value = await response.json();
    error.value = '';
  } catch (err) { error.value = err.message; }
  finally { loading = false; }
}
onMounted(refresh);
onActivated(refresh);
</script>

<template>
  <div class="records-statistics" title="全部审查尝试统计，包含历史版本与归档任务；不随列表筛选变化">
    <span class="records-statistics-label">全部审查</span>
    <div v-if="report" class="records-statistics-values">
      <span>累计 <strong>{{ report.total }}</strong></span>
      <span>已出结果 <strong class="is-success">{{ report.statuses.completed }}</strong></span>
      <span>失败 <strong class="is-danger">{{ report.statuses.failed }}</strong></span>
      <span>已中断 <strong>{{ report.statuses.interrupted }}</strong></span>
      <span>排队中 <strong>{{ report.statuses.queued || 0 }}</strong></span>
      <span>执行中 <strong class="is-running">{{ report.statuses.running }}</strong></span>
    </div>
    <span class="records-statistics-scope">含历史版本与归档任务</span>
    <span v-if="error" class="text-amber-700">{{ error }}</span>
    <button class="records-statistics-refresh" @click="refresh">刷新统计</button>
  </div>
</template>
