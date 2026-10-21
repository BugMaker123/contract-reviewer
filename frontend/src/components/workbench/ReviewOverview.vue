<script setup>
import { computed } from 'vue';
const props = defineProps({ context: { type: Object, required: true } });
const workspace = props.context.workspace;
const result = computed(() => workspace.run?.result);
</script>
<template>
  <details class="wb-functional-overview" >
    <summary>审查结论与执行记录</summary>
    <label>审查版本<select aria-label="审查历史版本" :value="workspace.run?.id || ''" @change="workspace.selectVersion($event.target.value)"><option value="">当前任务</option><option v-for="version in workspace.versions" :key="version.id" :value="version.id">第 {{ version.number }} 次 · {{ ({queued:'排队中',running:'审查中',completed:'审查完成',failed:'失败',interrupted:'中断'})[version.status] || version.status }}</option></select></label>
    <div v-if="workspace.task?.running_run"><p>审查已在后台执行或排队，刷新不会取消任务。</p><button @click="context.startReview(workspace.task.running_run)">重新连接审查进度</button><button @click="context.cancelReview()">取消后台审查</button></div>
    <p v-if="['failed','interrupted'].includes(workspace.task?.status)">上次审查失败或中断，已有结果保留；可点击顶部重新审查。</p>
    <template v-if="result">
      <p v-if="result.warning" class="wb-functional-warning">{{ result.warning }}</p>
      <p><strong>本轮审查稿件：</strong>{{ workspace.run?.baseline_kind === 'accepted' ? '上一版已采纳修订稿' : '当时保存的正文快照' }}</p>
      <p><strong>准入结论：</strong>{{ result.admission?.reason || '历史版本未记录' }}</p>
      <p><strong>审查总评：</strong>{{ result.summary?.verdict || '未记录' }}</p>
      <p><strong>审查范围：</strong>{{ result.coverage || '未记录覆盖范围' }}</p>
      <details><summary>执行计划与轨迹</summary><p v-for="(step,index) in (result.audit_trace || [])" :key="index">{{ step.detail }}</p></details>
      <p v-if="context.resultStale.value" class="wb-functional-warning">正文或条件已改变，请重新审查；以下结论属于旧版本。</p>
    </template>
  </details>
</template>
