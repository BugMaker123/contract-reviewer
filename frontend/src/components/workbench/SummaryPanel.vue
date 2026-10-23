<script>
import { computed } from "vue";
import ReviewOverview from "./ReviewOverview.vue";
import StaleReviewNotice from "./StaleReviewNotice.vue";

export default {
  components: { ReviewOverview, StaleReviewNotice },
  props: { context: { type: Object, required: true } },
  setup(props) {
    const handledCount = computed(() =>
      props.context.reviewIssues.value.filter((issue) =>
        props.context.appliedIssueIds.value.includes(issue.id) ||
        ["applied", "rejected"].includes(props.context.workspace.decisions[issue.id]),
      ).length,
    );
    const criticalCount = computed(() => props.context.reviewIssues.value.filter(issue => issue.severity === 'critical').length);
    const warningCount = computed(() => props.context.reviewIssues.value.filter(issue => issue.severity === 'warning').length);
    const infoCount = computed(() => props.context.reviewIssues.value.filter(issue => issue.severity === 'info').length);
    return { ...props.context, handledCount, criticalCount, warningCount, infoCount };
  },
};
</script>

<template>
  <aside id="review-summary-panel" data-testid="review-summary" class="wb-sidebar wb-summary-panel" :class="{ 'is-collapsed': !summaryOpen }">
    <div class="wb-sidebar-heading">
      <strong v-show="summaryOpen">审查导航</strong>
      <button class="wb-navigation-collapse" @click="toggleSummary" :aria-expanded="summaryOpen" aria-controls="review-summary-content" :aria-label="summaryOpen ? '收起审查导航' : '展开审查导航'" :title="summaryOpen ? '收起导航，扩大文档对照区' : '展开审查导航'">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" :class="{'is-collapsed':!summaryOpen}" aria-hidden="true"><path d="m14 6-6 6 6 6M20 4v16"/></svg><span v-if="summaryOpen">收起</span>
      </button>
    </div>
    <span v-if="!summaryOpen" class="wb-navigation-rail" aria-hidden="true">审查导航</span>
    <div v-show="summaryOpen" id="review-summary-content" class="wb-summary-content wb-review-navigation">
      <StaleReviewNotice v-if="resultStale" :context="context" />
      <template v-else>
      <ReviewOverview :context="context" />
      <section class="wb-nav-card wb-nav-status-card">
        <div class="wb-nav-status-heading"><span class="wb-nav-section-title">处理进度</span><div v-if="reviewResult" class="wb-nav-progress-number"><strong>{{ handledCount }}</strong><span>/ {{ reviewIssues.length }} 项已处理</span></div></div>
        <p v-if="!reviewResult" class="wb-nav-empty">开始审查后，这里会显示审查进度和问题位置。</p>
        <div v-if="reviewResult" class="wb-nav-progress-track"><span :style="{ width: reviewIssues.length ? `${handledCount / reviewIssues.length * 100}%` : '100%' }"></span></div>
        <div v-if="reviewResult" class="wb-nav-risk-grid" aria-label="风险分布">
          <div><strong class="wb-nav-critical">{{ reviewIssues.filter(issue => issue.severity === 'critical').length }}</strong><span>重大</span></div>
          <div><strong class="wb-nav-warning">{{ reviewIssues.filter(issue => issue.severity === 'warning').length }}</strong><span>一般</span></div>
          <div><strong>{{ reviewIssues.filter(issue => issue.severity === 'info').length }}</strong><span>提示</span></div>
        </div>
      </section>

      <p v-if="reviewResult && !reviewIssues.length" class="wb-nav-empty">本次审查没有需要处理的问题。</p>
      </template>
    </div>
    <div
      v-if="summaryOpen"
      class="wb-edge-resize wb-edge-right"
      title="拖拽调整导航大纲宽度，双击恢复默认"
      @mousedown="context.startLeftResize"
      @dblclick="context.resetLeftWidth"
    />
  </aside>
</template>
