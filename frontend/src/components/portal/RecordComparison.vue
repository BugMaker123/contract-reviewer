<script setup>
import { ref, watch } from 'vue';
const props = defineProps({task:{type:Object,required:true}}); const emit = defineEmits(['close']);
const versions = ref([]), before = ref(''), after = ref(props.task.active_run), result = ref(null), error = ref(''), loading = ref(false);
let generation = 0;
const load = async () => {
  const ticket = ++generation; loading.value = true; error.value = '';
  try { const query = new URLSearchParams({after_run:after.value}); if (before.value) query.set('before_run',before.value);
    const response = await fetch(`/api/tasks/${props.task.id}/comparison?${query}`); const data = await response.json();
    if (!response.ok) throw new Error(data.detail || '对比失败'); if (ticket === generation) result.value = data;
  } catch (err) { if (ticket === generation) { result.value = null; error.value = err.message; } }
  finally { if (ticket === generation) loading.value = false; }
};
watch(() => props.task.id, async () => {
  try { const response = await fetch(`/api/tasks/${props.task.id}`); if (!response.ok) throw new Error('版本列表读取失败');
    const data = await response.json(); versions.value = data.runs.filter(r => r.status === 'completed'); await load();
  } catch (err) { error.value = err.message; }
}, {immediate:true});
watch([before,after],load);
</script>
<template>
  <div class="modal" @click.self="emit('close')"><section class="modal-panel record-comparison" role="dialog" aria-modal="true" aria-label="审核前后对比">
    <header class="flex items-center justify-between"><h2 class="font-semibold">{{ task.title }} · 审核前后对比</h2><button class="button" @click="emit('close')">关闭对比</button></header>
    <div class="flex flex-wrap gap-3 my-4">
      <label>比较基准<select v-model="before" class="field"><option value="">本轮审查原文 → 当前采纳稿</option><option v-for="v in versions" :key="v.id" :value="v.id">第 {{ v.number }} 次审查输入快照</option></select></label>
      <label>目标版本<select v-model="after" class="field"><option v-for="v in versions" :key="v.id" :value="v.id">第 {{ v.number }} 次审查</option></select></label>
      <a :href="`/api/runs/${after}/export?scope=report`" class="button">导出此版意见书</a>
      <RouterLink :to="`/workbench?task=${task.id}&run=${after}`" class="button">打开此版本</RouterLink>
    </div>
    <p v-if="loading" role="status">正在对比…</p><p v-if="error" role="alert" class="text-red-600">{{ error }}</p>
    <template v-if="result && !loading">
      <p class="text-xs text-slate-500 mb-3">{{ result.kind === 'versions' ? '对比两次审查时固定的输入快照；后续处理不会改变快照。' : '对比本轮原文与已采纳修订，不包含未采纳建议。' }} 共 {{ result.changes.length }} 处文本变化。</p>
      <table v-if="result.changes.length" class="data-table comparison-table"><thead><tr><th>修改前</th><th>修改后</th></tr></thead><tbody><tr v-for="(change,index) in result.changes" :key="index"><td class="comparison-before">{{ change.original || '（无）' }}</td><td class="comparison-after">{{ change.revised || '（已删除）' }}</td></tr></tbody></table>
      <p v-else class="empty">两个稿件没有文本差异。</p>
    </template>
  </section></div>
</template>
