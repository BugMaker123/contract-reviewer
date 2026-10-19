<script>
import { computed } from "vue";
import ReviewOverview from "./ReviewOverview.vue";

export default {
  components: { ReviewOverview },
  props: { context: { type: Object, required: true } },
  setup(props) {
    const handledCount = computed(() =>
      props.context.reviewIssues.value.filter((issue) =>
        props.context.appliedIssueIds.value.includes(issue.id) ||
        ["applied", "rejected"].includes(props.context.workspace.decisions[issue.id]),
      ).length,
    );
    return { ...props.context, handledCount };
  },
};
</script>

<template>
  <aside id="review-summary-panel" data-testid="review-summary" class="wb-sidebar wb-summary-panel" :class="{ 'is-collapsed': !summaryOpen }">
    <div class="wb-sidebar-heading">
      <strong v-show="summaryOpen">审查导航</strong>
    </div>
    <div v-show="summaryOpen" id="review-summary-content" class="wb-summary-content wb-review-navigation">
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

      <section v-if="reviewIssues.length" class="wb-nav-issues">
        <div class="wb-nav-section-title">问题定位 <span>{{ reviewIssues.length }}</span></div>
        <button v-for="(issue, index) in reviewIssues" :key="issue.id" type="button" class="wb-nav-issue" :class="{ active: focusedIssueId === issue.id }" @click="selectIssue(issue.id)">
          <span class="wb-nav-index">{{ index + 1 }}</span>
          <span class="wb-nav-issue-copy"><strong>{{ issue.issue_title }}</strong><small>{{ issue.clause_title }}</small></span>
          <span class="wb-nav-dot" :class="'is-' + issue.severity" :title="severityLabel(issue.severity)"></span>
        </button>
      </section>
      <p v-else-if="reviewResult" class="wb-nav-empty">本次审查没有需要处理的问题。</p>
    </div>
  </aside>
</template>
