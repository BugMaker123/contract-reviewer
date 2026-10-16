<script>
import { computed } from "vue";
import { usePortalPage } from "../composables/usePortalPage.js";
import PageFrame from "../components/PageFrame.vue";
import ContractSource from "../components/portal/ContractSource.vue";
import ChecklistConfig from "../components/portal/ChecklistConfig.vue";
import ChecklistSelection from "../components/portal/ChecklistSelection.vue";
import ComparisonReference from "../components/portal/ComparisonReference.vue";
import ReviewBackground from "../components/portal/ReviewBackground.vue";
export default {
  components: {
    PageFrame,
    ContractSource,
    ChecklistConfig,
    ChecklistSelection,
    ComparisonReference,
    ReviewBackground,
  },
  setup() {
    const context = usePortalPage("start");
    const readiness = computed(() => {
      const { form, selectedList, importing, busy } = context;
      if (importing.value) return "正在提取合同正文，请稍候";
      if (busy.value) return "正在创建审查任务";
      if (!form.text.trim()) return "请先上传合同或粘贴正文";
      if (!form.title.trim()) return "请填写合同名称";
      if (form.mode === "checklist" && !selectedList.value) return "请选择已发布的审查清单";
      if (form.mode === "checklist" && !(form.checklist_item_ids ?? selectedList.value.items).length) return "请至少勾选一项审查要点";
      if (form.mode === "compare" && !form.reference_text.trim()) return "请添加用于对比的参考合同";
      return "";
    });
    return { ...context, context, readiness };
  },
};
</script>
<template>
  <PageFrame :context="context">
    <section class="review-start">
      <header class="review-intro">
        <div><div class="review-eyebrow">合同审查 / 新建任务</div><h1>新建合同审查</h1><p>从合同到审查标准，一次准备，逐项核对。</p></div>
        <RouterLink to="/records" class="button">查看审查记录 ↗</RouterLink>
      </header>
      <div class="review-modes" aria-label="审查模式">
        <button v-for="(mode, index) in modes" :key="mode.id" @click="form.mode = mode.id" class="mode-button" :class="{ active: form.mode === mode.id }" :aria-pressed="form.mode === mode.id">
          <span class="review-mode-icon" aria-hidden="true">{{ ['ϟ', '◎', '☑', '⇄'][index] }}</span>
          <span><strong>{{ mode.name }}</strong><small>{{ mode.description }}</small></span>
          <span class="review-mode-radio" aria-hidden="true"></span>
        </button>
      </div>
      <div class="review-columns">
        <div class="review-primary">
          <section class="card review-document">
            <div class="review-section-heading"><span class="review-step">01</span><div><h2>准备合同文档</h2><p>上传文件或直接粘贴需要审查的合同正文</p></div><span class="pill" :class="form.text.trim() ? 'green' : 'amber'">{{ form.text.trim() ? '已添加正文' : '待添加' }}</span></div>
            <div class="review-source-tabs">
              <button v-for="source in sources" :key="source.id" @click="switchSource(source.id)" :disabled="importing" class="button" :class="{ soft: inputMethod === source.id }" :aria-pressed="inputMethod === source.id">{{ source.name }}</button>
              <span>{{ form.text.length.toLocaleString() }} 字</span>
            </div>
            <ContractSource :context="context" />
            <div class="review-document-fields">
              <label><span class="label">合同名称 <em>*</em></span><input v-model="form.title" class="field" placeholder="填写便于识别的合同名称" /></label>
              <label><span class="label">合同类型</span><input v-model="form.type" class="field" placeholder="如：采购合同、服务协议" /></label>
            </div>
          </section>
          <section class="card review-standards">
            <div class="review-section-heading"><span class="review-step">02</span><div><h2>配置业务分类与审查标准</h2><p>按业务场景选择企业清单，明确本次核验范围</p></div><span v-if="form.mode === 'checklist' && selectedList" class="pill green">已选 {{ (form.checklist_item_ids ?? selectedList.items).length }} 项</span></div>
            <template v-if="form.mode === 'checklist'"><ChecklistConfig :context="context" /><ChecklistSelection :context="context" /></template>
            <div v-else class="review-standard-prompt">
              <span class="review-standard-icon" aria-hidden="true">☑</span>
              <div><strong>使用企业专项审查清单</strong><p>选择业务分类，勾选付款、违约责任、知识产权等审查要点。</p><small>启用后将切换为清单审查，按所选要点逐项核验。</small></div>
              <button class="button soft" @click="form.mode = 'checklist'">配置清单 →</button>
            </div>
            <ComparisonReference :context="context" />
          </section>
        </div>
        <aside class="review-settings card">
          <div class="review-section-heading"><span class="review-step">03</span><div><h2>设置审查条件</h2><p>让审查贴合我方立场与交易背景</p></div></div>
          <div class="review-condition-fields">
            <label><span class="label">我方立场</span><select v-model="form.role" class="field"><option v-for="role in roles" :key="role.value" :value="role.value">{{ role.label }}</option></select></label>
            <label><span class="label">审查尺度</span><select v-model="form.scale" class="field"><option>中立</option><option>强势</option><option>弱势</option></select></label>
          </div>
          <ReviewBackground :context="context" :expanded="true" />
          <div class="review-condition-note"><strong>审查后的下一步</strong><p>进入工作台核对风险与修改建议，逐条确认后导出审查结果。</p></div>
        </aside>
      </div>
      <footer class="review-submit">
        <div><strong>{{ readiness ? '完成准备后，开始合同审查' : '准备就绪，可以进入审查工作台' }}</strong><p role="status">{{ readiness || `${modes.find(mode => mode.id === form.mode)?.name} · 合同正文及审查条件已准备` }}</p></div>
        <button @click="createTask" :disabled="!!readiness" class="button primary">{{ busy ? '正在保存…' : '进入工作台核对合同' }} <span aria-hidden="true">→</span></button>
      </footer>
    </section>
  </PageFrame>
</template>
