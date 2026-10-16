<script>
import { useTrackedReview } from "../composables/useTrackedReview.js";
import { useWorkbench } from "../composables/useWorkbench.js";
import WorkbenchHeader from "../components/workbench/WorkbenchHeader.vue";
import SummaryPanel from "../components/workbench/SummaryPanel.vue";
import DocumentPanel from "../components/workbench/DocumentPanel.vue";
import OpinionsPanel from "../components/workbench/OpinionsPanel.vue";
import WorkbenchToast from "../components/workbench/WorkbenchToast.vue";
import ReviewProgress from "../components/workbench/ReviewProgress.vue";
import ClauseEditor from "../components/workbench/ClauseEditor.vue";
import ReviewConditions from "../components/workbench/ReviewConditions.vue";
import DocumentEditor from "../components/workbench/DocumentEditor.vue";
import WorkbenchModelSettings from "../components/workbench/WorkbenchModelSettings.vue";
import ReportPreview from "../components/workbench/ReportPreview.vue";
export default {
  components: {
    WorkbenchHeader,
    SummaryPanel,
    DocumentPanel,
    OpinionsPanel,
    WorkbenchToast,
    ReviewProgress,
    ClauseEditor,
    ReviewConditions,
    DocumentEditor,
    WorkbenchModelSettings,
    ReportPreview,
  },
  emits: ["ready"],
  setup(_props, { emit }) {
    const context = useWorkbench();
    Object.assign(context, useTrackedReview(context));
    emit("ready", context);
    return { ...context, context };
  },
};
</script>
<template>
  <div class="workbench-view flex flex-col h-screen overflow-hidden">
    <WorkbenchToast :context="context" />
    <ReviewProgress :context="context" />
    <header class="workbench-global-header">
      <div class="workbench-global-brand">
        <a href="/" @click.prevent="workspace.leaveFor('/')" title="返回首页"><span>⚖</span><strong>LexisGraph</strong></a>
        <details class="wb-menu"><summary>工作台 ▾</summary><div class="wb-popover workbench-global-menu"><a href="/" @click.prevent="workspace.leaveFor('/')">开始审查</a><a href="/records" @click.prevent="workspace.leaveFor('/records')">审查记录</a><a href="/categories" @click.prevent="workspace.leaveFor('/categories')">业务分类维护</a><a href="/checklists" @click.prevent="workspace.leaveFor('/checklists')">审查清单维护</a></div></details>
      </div>
    </header>
    <WorkbenchHeader :context="context" />
    <main class="flex-1 flex overflow-hidden">
      <SummaryPanel :context="context" />
      <DocumentPanel :context="context" />
      <OpinionsPanel :context="context" />
    </main>
    <ClauseEditor :context="context" />
    <ReviewConditions :context="context" />
    <DocumentEditor :context="context" />
    <WorkbenchModelSettings :context="context" />
    <ReportPreview :context="context" />
  </div>
</template>
<style src="../styles/workbench.css"></style>
