<script>
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
    emit("ready", context);
    return { ...context, context };
  },
};
</script>
<template>
  <div class="workbench-view flex flex-col h-screen overflow-hidden">
    <WorkbenchToast :context="context" />
    <ReviewProgress :context="context" />
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
