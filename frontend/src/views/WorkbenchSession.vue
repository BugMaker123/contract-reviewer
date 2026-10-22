<script>
import { ref } from "vue";
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

    const leftWidth = ref("");
    const rightWidth = ref("");

    const startLeftResize = (e) => {
      e.preventDefault();
      const startX = e.clientX;
      const panel = document.getElementById("review-summary-panel");
      if (!panel) return;
      const initialWidth = panel.getBoundingClientRect().width;
      const onMouseMove = (moveEvent) => {
        const delta = moveEvent.clientX - startX;
        const newWidth = Math.max(220, Math.min(560, initialWidth + delta));
        leftWidth.value = `${newWidth}px`;
      };
      const onMouseUp = () => {
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("mouseup", onMouseUp);
      };
      window.addEventListener("mousemove", onMouseMove);
      window.addEventListener("mouseup", onMouseUp);
    };

    const startRightResize = (e) => {
      e.preventDefault();
      const startX = e.clientX;
      const panel = document.getElementById("opinion-drawer");
      if (!panel) return;
      const initialWidth = panel.getBoundingClientRect().width;
      const onMouseMove = (moveEvent) => {
        const delta = startX - moveEvent.clientX;
        const newWidth = Math.max(320, Math.min(760, initialWidth + delta));
        rightWidth.value = `${newWidth}px`;
      };
      const onMouseUp = () => {
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("mouseup", onMouseUp);
      };
      window.addEventListener("mousemove", onMouseMove);
      window.addEventListener("mouseup", onMouseUp);
    };

    const resetLeftWidth = () => {
      leftWidth.value = "";
    };

    const resetRightWidth = () => {
      rightWidth.value = "";
    };

    Object.assign(context, {
      leftWidth,
      rightWidth,
      startLeftResize,
      startRightResize,
      resetLeftWidth,
      resetRightWidth,
    });

    return {
      ...context,
      context,
      leftWidth,
      rightWidth,
      startLeftResize,
      startRightResize,
      resetLeftWidth,
      resetRightWidth,
    };
  },
};
</script>
<template>
  <div class="workbench-view flex flex-col h-screen overflow-hidden" :class="{'navigation-collapsed': !summaryOpen}">
    <WorkbenchToast :context="context" />
    <ReviewProgress :context="context" />
    <header class="workbench-global-header">
      <div class="workbench-global-brand">
        <a href="/" @click.prevent="workspace.leaveFor('/')" title="返回主页"><span>⚖</span><strong>LexisGraph</strong></a>
      </div>
      <a class="app-home-link" href="/" @click.prevent="workspace.leaveFor('/')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m12 5-7 7 7 7M5 12h14" /></svg>
        返回主页
      </a>
    </header>
    <WorkbenchHeader :context="context" />
    <main class="flex-1 flex overflow-hidden">
      <SummaryPanel :context="context" :style="leftWidth ? { width: leftWidth, flex: '0 0 auto' } : {}" />
      <DocumentPanel :context="context" />
      <OpinionsPanel :context="context" :style="rightWidth ? { width: rightWidth, flex: '0 0 auto' } : {}" />
    </main>
    <ClauseEditor :context="context" />
    <ReviewConditions :context="context" />
    <DocumentEditor :context="context" />
    <WorkbenchModelSettings :context="context" />
    <ReportPreview :context="context" />
  </div>
</template>
<style src="../styles/workbench.css"></style>
