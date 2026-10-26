<script>
import { ref } from "vue";
import { useTrackedReview } from "../composables/useTrackedReview.js";
import { useWorkbench } from "../composables/useWorkbench.js";
import WorkbenchHeader from "../components/workbench/WorkbenchHeader.vue";
import DocumentPanel from "../components/workbench/DocumentPanel.vue";
import OpinionsPanel from "../components/workbench/OpinionsPanel.vue";
import WorkbenchToast from "../components/workbench/WorkbenchToast.vue";
import ReviewProgress from "../components/workbench/ReviewProgress.vue";
import ClauseEditor from "../components/workbench/ClauseEditor.vue";
import ReviewConditions from "../components/workbench/ReviewConditions.vue";
import DocumentEditor from "../components/workbench/DocumentEditor.vue";
import WorkbenchModelSettings from "../components/workbench/WorkbenchModelSettings.vue";
import ReportPreview from "../components/workbench/ReportPreview.vue";
import UserAccountMenu from "../components/portal/UserAccountMenu.vue";
import Help from "../components/portal/Help.vue";
import { usePortalShell } from "../stores/portal.js";
import WorkspaceSidebar from "../components/portal/WorkspaceSidebar.vue";


export default {
  components: {
    WorkbenchHeader,
    DocumentPanel,
    OpinionsPanel,
    WorkbenchToast,
    ReviewProgress,
    ClauseEditor,
    ReviewConditions,
    DocumentEditor,
    WorkbenchModelSettings,
    ReportPreview,
    WorkspaceSidebar, UserAccountMenu, Help,
  },
  emits: ["ready"],
  setup(_props, { emit }) {
    const shell = usePortalShell();
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

    const searchParams = new URLSearchParams(location.search);
    const fromDraftUrl = ref(searchParams.get('draft_id') ? '/drafting/' + searchParams.get('draft_id') + '/edit' : '');
    return {
      ...context,
      context,
      leftWidth,
      rightWidth,
      startLeftResize,
      startRightResize,
      resetLeftWidth,
      resetRightWidth,
      fromDraftUrl, shell,
    };
  },
};
</script>
<template>
  <div class="workbench-view flex flex-col h-screen overflow-hidden" :class="{'navigation-collapsed': !summaryOpen}">
    <WorkspaceSidebar active="records" :before-navigate="workspace.leaveFor" />
    <WorkbenchToast :context="context" />
    <ReviewProgress :context="context" />
    <header class="workbench-global-header">
      <div class="prototype-breadcrumb">合同工作 <span>/</span> <strong>合同审查</strong></div>
      <div class="workbench-nav-actions flex items-center gap-4">
        <a v-if="fromDraftUrl" class="app-draft-link flex items-center gap-1 text-xs text-blue-600 hover:underline" :href="fromDraftUrl" @click.prevent="workspace.leaveFor(fromDraftUrl)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m12 5-7 7 7 7M5 12h14" /></svg>
          返回合同草稿
        </a>
        <UserAccountMenu @help="shell.showHelp.value = true" />
      </div>
    </header>
    <WorkbenchHeader :context="context" />
    <main class="review-workbench-main flex-1 flex overflow-hidden">
      <DocumentPanel :context="context" />
      <div class="review-workbench-rail" :style="rightWidth ? { width:rightWidth, flex:'0 0 auto' } : {}">
        <OpinionsPanel :context="context" />
      </div>
    </main>
    <ClauseEditor :context="context" />
    <ReviewConditions :context="context" />
    <DocumentEditor :context="context" />
    <WorkbenchModelSettings :context="context" />
    <ReportPreview :context="context" />
    <Help :context="shell" />
  </div>
</template>
<style src="../styles/workbench.css"></style>

<style scoped>
.workbench-view .workbench-global-header{height:64px!important;min-height:64px!important;justify-content:space-between;padding:0 24px!important;overflow:visible}.workbench-nav-actions{margin-left:auto}
</style>
