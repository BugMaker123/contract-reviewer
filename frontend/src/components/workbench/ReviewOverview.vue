<script setup>
import { computed } from 'vue';
const props = defineProps({ context: { type: Object, required: true } });
const workspace = props.context.workspace;
const result = computed(() => workspace.run?.result);
const label = value => ({pass:'符合',fail:'不符合',needs_review:'待确认',not_applicable:'不适用'})[value] || value;
const groups = computed(() => [
  {name:'原文要求核验',items:result.value?.requirement_findings || []},
  {name:'全部建议稿要求核验',items:result.value?.proposed_requirement_findings || []},
  {name:'当前采纳稿要求核验',items:workspace.run?.current_verification?.findings || [],current:true},
]);
</script>
<template>
  <details class="wb-functional-overview">
    <summary>审查结论与要求核验</summary>
    <label>审查版本<select aria-label="审查历史版本" :value="workspace.run?.id || ''" @change="workspace.selectVersion($event.target.value)"><option value="">当前任务</option><option v-for="version in workspace.versions" :key="version.id" :value="version.id">第 {{ version.number }} 次 · {{ ({running:'审查中',completed:'审查完成',failed:'失败',interrupted:'中断'})[version.status] || version.status }}</option></select></label>
    <div v-if="workspace.task?.running_run"><p>审查正在后台执行，刷新不会停止任务。</p><button @click="context.startReview(workspace.task.running_run)">重新连接审查进度</button><button @click="context.cancelReview()">取消后台审查</button></div>
    <p v-if="['failed','interrupted'].includes(workspace.task?.status)">上次审查失败或中断，已有结果保留；可点击顶部重新审查。</p>
    <template v-if="result">
      <p><strong>本轮审查稿件：</strong>{{ workspace.run?.baseline_kind === 'accepted' ? '上一版已采纳修订稿' : '当时保存的正文快照' }}</p>
      <p><strong>准入结论：</strong>{{ result.admission?.reason || '历史版本未记录' }}</p>
      <p><strong>审查总评：</strong>{{ result.summary?.verdict || '未记录' }}</p>
      <p><strong>审查范围：</strong>{{ result.coverage || '未记录覆盖范围' }}</p>
      <details><summary>执行计划与轨迹</summary><p v-for="(step,index) in (result.audit_trace || [])" :key="index">{{ step.detail }}</p></details>
      <p v-if="context.resultStale.value" class="wb-functional-warning">正文或条件已改变，请重新审查；以下结论属于旧版本。</p>
      <button :disabled="workspace.historical || workspace.verifying || context.resultStale.value || context.isReviewing.value" @click="workspace.verifyCurrent()">{{ workspace.verifying ? '正在核验当前稿…' : '核验当前稿' }}</button>
      <p>{{ workspace.run?.current_verification_valid ? '当前稿核验有效' : '当前稿未核验或核验已失效' }}</p>
      <details v-for="group in groups" :key="group.name" :open="group.current">
        <summary>{{ group.name }} · {{ group.items.length }} 项</summary>
        <p v-if="!group.current">{{ group.name === '全部建议稿要求核验' ? '基于全部建议组合，不代表当前采纳稿。' : '基于本次原始输入。' }}</p>
        <p v-if="!group.items.length">本版本没有核验结果。</p>
        <article v-for="item in group.items" :key="item.id">
          <strong>{{ label(item.status) }} · {{ item.text }}</strong>
          <p>{{ item.source }} · {{ item.priority === 'required' ? '硬性要求' : '优先偏好' }}</p>
          <p>{{ item.explanation }}</p><blockquote v-if="item.evidence">{{ item.evidence }}</blockquote>
          <p v-if="item.conflict_with?.length" class="wb-functional-warning">冲突要求：{{ item.conflict_with.join('、') }}，请修改条件并重新审查。</p>
          <label v-if="group.current && !['pass','not_applicable'].includes(item.status) && !item.conflict_with?.length">人工确认理由（5至3000字）<textarea v-model="workspace.confirmations[item.id]" :disabled="workspace.historical || workspace.task?.status === 'completed' || !workspace.run?.current_verification_valid" maxlength="3000" placeholder="说明处理方式、确认依据或接受风险的理由" /></label>
        </article>
      </details>
    </template>
  </details>
</template>
