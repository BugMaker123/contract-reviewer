<script setup>
import { computed, nextTick, ref, watch } from 'vue';
const props = defineProps({task:{type:Object,required:true}}); const emit = defineEmits(['close']);
const versions = ref([]), before = ref(''), after = ref(props.task.active_run), result = ref(null), error = ref(''), loading = ref(false);
let generation = 0;
const onlyChanges = ref(false), selectedChange = ref(0), content = ref(null);
const rows = computed(() => {
  if (!result.value) return [];
  const left = result.value.original.split('\n'), right = result.value.revised.split('\n');
  const rows = []; let a = 0, b = 0;
  result.value.changes.forEach((change, index) => {
    if (!onlyChanges.value && change.original_start > a)
      rows.push({ original: left.slice(a, change.original_start).join('\n'), revised: right.slice(b, change.revised_start).join('\n'), kind: 'equal' });
    rows.push({ ...change, index }); a = change.original_end; b = change.revised_end;
  });
  if (!onlyChanges.value && (a < left.length || b < right.length))
    rows.push({ original: left.slice(a).join('\n'), revised: right.slice(b).join('\n'), kind: 'equal' });
  return rows;
});
const move = async direction => {
  const count = result.value?.changes.length || 0; if (!count) return;
  selectedChange.value = (selectedChange.value + direction + count) % count;
  await nextTick(); content.value?.querySelector(`[data-change="${selectedChange.value}"]`)?.scrollIntoView({block:'center', behavior:'smooth'});
};
const load = async () => {
  const ticket = ++generation; loading.value = true; error.value = '';
  try { const query = new URLSearchParams({after_run:after.value}); if (before.value) query.set('before_run',before.value);
    const response = await fetch(`/api/tasks/${props.task.id}/comparison?${query}`); const data = await response.json();
    if (!response.ok) throw new Error(data.detail || '对比失败'); if (ticket === generation) { result.value = data; selectedChange.value = 0; if (content.value) content.value.scrollTop = 0; }
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
  <div class="comparison-overlay" @click.self="emit('close')"><section class="comparison-dialog" role="dialog" aria-modal="true" aria-label="审核前后对比">
    <div class="comparison-header"><div><span class="comparison-eyebrow">DOCUMENT COMPARISON</span><h2>审核前后对比</h2><p :title="task.title">{{ task.title }}</p></div><button class="comparison-close" aria-label="关闭对比" @click="emit('close')">×</button></div>
    <div class="comparison-controls">
      <label>比较基准<select v-model="before" :disabled="!versions.length"><option value="">本轮审查原文</option><option v-for="v in versions" :key="v.id" :value="v.id">第 {{ v.number }} 次审查输入快照</option></select></label>
      <span class="comparison-arrow" aria-hidden="true">→</span>
      <label>目标版本<select v-model="after" :disabled="!versions.length"><option v-for="v in versions" :key="v.id" :value="v.id">第 {{ v.number }} 次审查{{ before ? '输入快照' : ' · 当前采纳稿' }}</option></select></label>
      <div class="comparison-links"><a :href="`/api/runs/${after}/export?scope=report`" :aria-disabled="loading" @click="loading && $event.preventDefault()">导出此版意见书</a><RouterLink :to="`/workbench?task=${task.id}&run=${after}`">打开此版本 ↗</RouterLink></div>
    </div>
    <div class="comparison-toolbar"><div class="comparison-metrics"><strong>{{ loading ? '—' : result?.changes.length ?? '—' }}</strong> 处文本变化<span class="comparison-legend removed">删除</span><span class="comparison-legend added">新增</span></div><div class="comparison-tools"><label><input type="checkbox" v-model="onlyChanges" />仅看差异</label><button aria-label="上一处差异" @click="move(-1)" :disabled="loading || !result?.changes.length">↑</button><span>{{ result?.changes.length ? selectedChange + 1 : 0 }} / {{ result?.changes.length || 0 }}</span><button aria-label="下一处差异" @click="move(1)" :disabled="loading || !result?.changes.length">↓</button></div></div>
    <div class="comparison-column-headings"><div><span class="comparison-dot before-dot"></span>修改前 <small>{{ before ? '输入快照' : '本轮审查原文' }}</small></div><div><span class="comparison-dot after-dot"></span>修改后 <small>{{ before ? '目标输入快照' : '当前采纳稿' }}</small></div></div>
    <div ref="content" class="comparison-content" :aria-busy="loading">
    <p v-if="loading" role="status" class="comparison-state">正在读取版本并生成对比…</p><div v-else-if="error" role="alert" class="comparison-state comparison-error">{{ error }}<button @click="load">重新加载</button></div>
    <template v-if="result && !loading">
      <p v-if="!result.changes.length" class="comparison-identical">两个稿件没有文本差异。{{ onlyChanges ? '取消「仅看差异」可查看全文。' : '' }}</p>
      <div v-for="(row,index) in rows" :key="index" class="comparison-row" :class="{ 'is-changed': row.kind !== 'equal', 'is-focused': row.kind !== 'equal' && selectedChange === row.index }" :data-change="row.kind !== 'equal' ? row.index : undefined">
        <div :class="{ 'text-removed': row.kind !== 'equal' && row.original }"><span v-if="row.kind !== 'equal'" class="comparison-change-label">{{ row.kind === 'insert' ? '新增位置' : `变更 ${row.index + 1}` }}</span><p>{{ row.original || '此处无原文' }}</p></div>
        <div :class="{ 'text-added': row.kind !== 'equal' && row.revised }"><span v-if="row.kind !== 'equal'" class="comparison-change-label">{{ row.kind === 'delete' ? '已删除' : `变更 ${row.index + 1}` }}</span><p>{{ row.revised || '此处内容已删除' }}</p></div>
      </div>
    </template>
    </div>
    <div class="comparison-footer"><span>{{ before ? '对比固定的输入快照，后续处理不会改变快照。' : '仅包含已采纳修改，未采纳建议不会出现在修改后正文中。' }}</span><span>纯文本对比 · 两栏同步阅读</span></div>
  </section></div>
</template>

<style scoped>
.comparison-overlay { position:fixed; inset:0; z-index:70; display:flex; align-items:center; justify-content:center; padding:24px; background:#0f172a66; backdrop-filter:blur(3px); }
.comparison-dialog { width:1440px; max-width:100%; height:calc(100dvh - 48px); max-height:1000px; display:flex; flex-direction:column; overflow:hidden; background:#fff; border-radius:16px; box-shadow:0 24px 80px #0f172a33; color:#334155; }
.comparison-header { display:flex; justify-content:space-between; gap:20px; padding:23px 28px 18px; border-bottom:1px solid #e2e8f0; }.comparison-header > div { min-width:0; }.comparison-eyebrow { font-size:10px; letter-spacing:1.6px; color:#94a3b8; font-weight:600; }.comparison-header h2 { margin:6px 0; font-size:21px; font-weight:650; color:#0f172a; }.comparison-header p { margin:0; font-size:12px; color:#64748b; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.comparison-close { width:32px; height:32px; border:1px solid #e2e8f0; border-radius:8px; background:#fff; font-size:23px; color:#64748b; flex-shrink:0; cursor:pointer; }
.comparison-controls { display:flex; align-items:center; gap:14px; padding:16px 28px; background:#f8fafc; border-bottom:1px solid #e2e8f0; }.comparison-controls label { flex:1; max-width:330px; font-size:11px; color:#64748b; }.comparison-controls select { display:block; width:100%; margin-top:6px; padding:9px 12px; border:1px solid #dce3ed; border-radius:7px; color:#334155; background:#fff; font-size:12px; }.comparison-arrow { padding-top:18px; color:#94a3b8; }.comparison-links { margin-left:auto; display:flex; gap:18px; font-size:12px; color:#2563eb; white-space:nowrap; }
.comparison-toolbar { display:flex; align-items:center; justify-content:space-between; padding:12px 28px; border-bottom:1px solid #e2e8f0; font-size:11px; }.comparison-metrics { display:flex; align-items:center; gap:8px; color:#64748b; }.comparison-metrics strong { color:#0f172a; font-size:17px; }.comparison-legend { padding:3px 7px; border-radius:4px; margin-left:6px; }.removed { background:#fff1f2; color:#be445d; }.added { background:#ecfdf5; color:#15805d; }.comparison-tools { display:flex; align-items:center; gap:12px; color:#64748b; }.comparison-tools label { display:flex; align-items:center; gap:6px; margin-right:12px; cursor:pointer; }.comparison-tools input { accent-color:#2563eb; }.comparison-tools button { width:28px; height:28px; border:1px solid #e2e8f0; border-radius:5px; background:#fff; color:#475569; cursor:pointer; }.comparison-tools button:disabled { opacity:.4; cursor:not-allowed; }
.comparison-column-headings { display:grid; grid-template-columns:1fr 1fr; background:#f8fafc; border-bottom:1px solid #e2e8f0; }.comparison-column-headings > div { padding:12px 24px; display:flex; align-items:center; gap:8px; font-size:12px; font-weight:600; }.comparison-column-headings > div + div { border-left:1px solid #e2e8f0; }.comparison-column-headings small { margin-left:auto; color:#94a3b8; font-size:10px; font-weight:400; }.comparison-dot { width:6px; height:6px; border-radius:50%; }.before-dot { background:#f18e9e; }.after-dot { background:#48b18c; }
.comparison-content { flex:1; min-height:0; overflow:auto; scrollbar-gutter:stable; background:#fff; }.comparison-row { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); border-bottom:1px solid #edf1f6; }.comparison-row > div { padding:18px 24px; min-width:0; }.comparison-row > div + div { border-left:1px solid #e2e8f0; }.comparison-row p { margin:0; white-space:pre-wrap; overflow-wrap:anywhere; line-height:2; font-size:13px; color:#475569; }.comparison-row .text-removed { background:#fff5f6; }.comparison-row .text-added { background:#f0fbf6; }.comparison-row .text-removed p { color:#9f4454; }.comparison-row .text-added p { color:#206b52; }.comparison-change-label { display:block; margin-bottom:8px; font-size:10px; color:#94a3b8; }.comparison-row.is-focused { box-shadow:inset 3px 0 #6495ed; }.comparison-state { padding:70px 20px; text-align:center; color:#64748b; font-size:13px; }.comparison-error { color:#b91c1c; }.comparison-error button { display:block; margin:15px auto; color:#2563eb; }.comparison-identical { margin:0; padding:16px 24px; color:#64748b; background:#f8fafc; font-size:12px; }
.comparison-footer { display:flex; justify-content:space-between; gap:16px; padding:14px 28px; border-top:1px solid #e2e8f0; color:#94a3b8; font-size:11px; background:#f8fafc; }.comparison-header,.comparison-controls,.comparison-toolbar,.comparison-column-headings,.comparison-footer { flex-shrink:0; }button:focus-visible,select:focus-visible,a:focus-visible { outline:2px solid #2563eb; outline-offset:3px; }
@media(max-width:800px) { .comparison-overlay { padding:10px; }.comparison-dialog { height:calc(100dvh - 20px); border-radius:10px; }.comparison-header,.comparison-controls { padding:16px; }.comparison-controls { flex-wrap:wrap; gap:10px; }.comparison-controls label { max-width:none; min-width:120px; }.comparison-links { width:100%; margin-left:0; }.comparison-toolbar { padding:10px 16px; flex-wrap:wrap; gap:10px; }.comparison-row > div { padding:12px; }.comparison-row p { font-size:12px; }.comparison-footer { padding:12px 16px; }.comparison-footer > span:last-child { display:none; }.comparison-column-headings > div { padding:10px 12px; }.comparison-column-headings small { display:none; } }
</style>
