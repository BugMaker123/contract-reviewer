<script setup>
import { ref, onMounted, onActivated } from 'vue';
const props = defineProps({ tasks: { type: Array, default: () => [] } });
defineEmits(['review', 'template']);
const activeCount = ref(null);
const draftCount = ref(null);
async function loadCounts() {
  try {
    const [pending, running, queued, awaiting, drafts] = await Promise.all([
      ...['pending_review', 'running', 'queued', 'draft'].map(status => fetch('/api/tasks?' + new URLSearchParams({ status, archived: 'false', page_size: '1' })).then(response => response.ok ? response.json() : Promise.reject())),
      fetch('/api/contract-drafts?page_size=1').then(response => response.ok ? response.json() : Promise.reject()),
    ]);
    activeCount.value = pending.total + running.total + queued.total + awaiting.total;
    draftCount.value = drafts.total;
  } catch {
    activeCount.value = null;
    draftCount.value = null;
  }
}
onMounted(loadCounts);
onActivated(loadCounts);
const statusLabel = status => ({completed:'已完成',pending_review:'复核中',running:'审查中',draft:'待审查',failed:'处理失败',interrupted:'已中断'})[status] || '处理中';
const taskDate = value => value ? new Date(value).toLocaleDateString('zh-CN', { month:'2-digit', day:'2-digit', timeZone:'Asia/Shanghai' }) : '';
</script>

<template>
  <div class="prototype-home">
    <header class="prototype-home-hero">
      <div><span class="prototype-kicker">合同工作台</span><h1>开始一项合同工作</h1><p>选择审查方式发起任务，或从最近的记录继续处理。</p></div>
    </header>
    <div class="prototype-home-grid">
      <div class="prototype-home-main">
      <section class="prototype-home-card">
        <header><div><h2>发起新任务</h2><p>按合同来源选择合适的处理方式。</p></div></header>
        <div class="prototype-paths">
          <button type="button" v-can="'review.create'" aria-label="AI 智能全面审查" @click="$emit('review')"><span class="prototype-path-icon">✧</span><span class="prototype-path-copy"><strong>审查合同风险</strong><small>适合外部拟定、非标准或复杂合同。查看风险、审查意见与修改建议。</small></span><b>开始风险审查 <span aria-hidden="true">→</span></b></button>
          <button type="button" v-can="'validation.execute'" aria-label="已有标准模板核验" @click="$emit('template')"><span class="prototype-path-icon green">☑</span><span class="prototype-path-copy"><strong>核验标准模板</strong><small>适合按已发布 DOCX 模板填写的合同。核对固定条款与字段规则。</small></span><b>开始模板核验 <span aria-hidden="true">→</span></b></button>
        </div>
      </section>
      <div class="prototype-home-metrics">
        <RouterLink to="/records"><small>进行中的审查</small><strong>{{ activeCount ?? '—' }}</strong><span>查看全部审查记录 →</span></RouterLink>
        <RouterLink to="/drafting"><small>合同草稿</small><strong>{{ draftCount ?? '—' }}</strong><span>查看并继续起草 →</span></RouterLink>
      </div>
      </div>
      <aside class="prototype-home-aside">
        <section class="prototype-home-card"><header><div><h2>最近审查</h2><p>显示最近 {{ tasks.length }} 条记录</p></div><RouterLink to="/records">查看全部</RouterLink></header><p v-if="!tasks.length" class="prototype-home-empty">暂无审查记录。可以先发起一项新任务。</p><RouterLink v-for="task in tasks" :key="task.id" class="prototype-recent" :to="'/workbench?task='+task.id"><strong>{{ task.title }}</strong><span><em>{{ statusLabel(task.status) }}</em><time v-if="task.updated_at">{{ taskDate(task.updated_at) }}</time><b>继续处理 →</b></span></RouterLink></section>
      </aside>
    </div>
  </div>
</template>
