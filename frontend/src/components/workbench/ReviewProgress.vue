<script setup>
import { computed, unref } from "vue";
const props = defineProps({ context: { type: Object, required: true } });
const value = (key) => unref(props.context[key]);
const running = computed(() => value("isReviewing"));
const trace = computed(() => value("reviewTrace") || []);
const steps = [
  "准入与计划",
  "条款提取",
  "法务研判",
  "边界校验",
  "归并问题",
  "要求与修订核验",
  "发布结果",
];
const activeStep = computed(() => {
  if (!running.value && value('reviewResult')) return 7;
  let step = 0;
  for (const event of trace.value) {
    const stages = {
      prepare: 0,
      admission: 0,
      plan: 0,
      segment: 1,
      scope: 1,
      segment_contract: 2,
      compliance_check: 2,
      review: 2,
      analysis: 2,
      analysis_summary: 2,
      validate: 3,
      finding: 3,
      balance_review: 4,
      aggregate_and_redline: 4,
      synthesize_summary: 4,
      rewrite: 5,
      requirements: 5,
      evidence_tool: 5,
    };
    if (event.stage in stages) step = Math.max(step, stages[event.stage]);
    if (event.stage === "retry" || event.stage === "review")
      step = stages[event.stage] ?? 2;
  }
  return step;
});
const items = computed(() => {
  if (running.value) return value("publicAnalysis") || [];
  return (value("reviewResult")?.issues || []).map((item) => ({
    title: item.issue_title,
    clause: item.clause_title,
    analysis: item.risk_analysis,
    evidence: item.redline?.original_text || item.evidence,
    proposal: item.negotiation_strategy,
    severity: item.severity,
  }));
});
const severityName = (severity) =>
  ({ high: "高风险", critical: "高风险", medium: "中风险", warning: "中风险", low: "低风险", info: "优化建议", favorable: "有利条款" })[
    severity
  ] || "待核验";
</script>

<template>
  <div v-if="value('reviewDialogOpen')" class="review-overlay">
    <section
      class="review-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="review-dialog-title"
      :aria-busy="running"
    >
      <header class="review-dialog-header">
        <h3 id="review-dialog-title">合同合规性审查分析</h3>
        <button
          v-if="running"
          @click="context.cancelReview"
          class="review-cancel"
        >
          取消审查
        </button>
        <button
          v-else
          @click="context.closeReviewDialog"
          class="review-cancel"
          aria-label="关闭审查结果"
        >
          ✕
        </button>
      </header>
      <div class="review-dialog-body">
        <ol class="review-stage-list" aria-label="审查处理阶段">
          <li
            v-for="(step, index) in steps"
            :key="step"
            :class="{ done: index < activeStep, active: index === activeStep }"
            :aria-current="index === activeStep ? 'step' : undefined"
          >
            <span class="review-stage-icon">{{
              index < activeStep ? "✓" : index + 1
            }}</span
            >{{ step }}
          </li>
        </ol>
        <section class="review-process" aria-label="实时处理过程">
          <div class="review-dialog-status" role="status">
            <i v-if="running"></i
            ><span>{{
              running
                ? value("latestLogMessage") || "正在连接模型服务…"
                : "审查完成，意见和修订建议已生成。"
            }}</span>
          </div>
          <details class="review-execution" open>
            <summary>
              处理记录 <span>{{ trace.length }} 条</span>
            </summary>
            <ol data-review-trace aria-live="polite" aria-relevant="additions">
              <li v-for="(item, index) in trace" :key="index">
                <time>{{
                  new Date(item.time).toLocaleTimeString("zh-CN", {
                    hour12: false,
                  })
                }}</time
                ><span>{{ item.detail }}</span>
              </li>
            </ol>
          </details>
        </section>
        <div class="review-analysis-heading">
          <h4>条款审查意见清单（已识别 {{ items.length }} 项）</h4>
          <span>{{ running ? "实时更新 · 待最终校验" : "已完成校验" }}</span>
        </div>
        <div v-if="!items.length" class="review-waiting">
          <div v-if="running" class="review-waiting-line"></div>
          <h4>{{ running ? "正在分析合同条款" : "本次未识别出审查问题" }}</h4>
          <p v-if="running">
            处理记录持续更新，收到完整的条款意见后会逐项展示。
          </p>
        </div>
        <div
          v-else
          data-public-analysis
          class="review-analysis-list"
          aria-live="polite"
          aria-relevant="additions"
        >
          <article
            v-for="(item, index) in items"
            :key="index"
            class="review-finding-card"
          >
            <div class="review-finding-title">
              <h5>
                <span class="review-finding-clause">{{ item.clause }}</span>
                {{ item.title }}
              </h5>
              <span class="review-risk" :class="item.severity"
                >● {{ severityName(item.severity) }}</span
              >
            </div>
            <p v-if="item.evidence" class="review-finding-evidence">
              <span>原文依据：</span>{{ item.evidence }}
            </p>
            <p class="review-finding-analysis">
              <span>法务评述：</span>{{ item.analysis }}
            </p>
            <p v-if="item.proposal" class="review-finding-proposal">
              <span>修改方向：</span>{{ item.proposal }}
            </p>
          </article>
        </div>
      </div>
      <footer class="review-dialog-footer">
        <span>{{
          running
            ? "正在处理：" + steps[activeStep]
            : "共 " + items.length + " 项审查意见"
        }}</span
        ><button
          v-if="!running"
          class="review-result-button"
          @click="context.closeReviewDialog"
        >
          查看审查修订稿</button
        ><span v-else>阶段完成后自动更新</span>
      </footer>
    </section>
  </div>
</template>
