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
  <div class="card p-4 text-xs space-y-3">
    <div class="flex justify-between"><strong>全部审查尝试统计（含历史版本与归档任务）</strong><button class="text-blue-600" @click="refresh">刷新统计</button></div>
    <p v-if="error" class="text-amber-700">{{ error }}</p>
    <div v-if="report" class="flex flex-wrap gap-5">
      <span>总计 {{ report.total }}</span><span>已出结果 {{ report.statuses.completed }}</span>
      <span>失败／未通过准入 {{ report.statuses.failed }}</span><span>已中断 {{ report.statuses.interrupted }}</span><span>执行中 {{ report.statuses.running }}</span>
    </div>
    <p class="text-slate-500">以下列表筛选不改变此统计及“导出全部审查报表”的范围。</p>
  </div>
</template>
