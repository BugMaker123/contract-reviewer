<script setup>
import { computed, unref, ref, watch, onUnmounted } from "vue";
import { reviewActivities } from "../../workbench/reviewActivity.js";
import PriorityReview from "./PriorityReview.vue";
const props = defineProps({ context: { type: Object, required: true } });
const value = (key) => unref(props.context[key]);
const running = computed(() => value("isReviewing"));
const queued = computed(() => running.value && value("reviewQueue")?.status === "queued");
const queuePosition = computed(() => value("reviewQueue")?.position || 1);
const trace = computed(() => value("reviewTrace") || []);
const succeeded = computed(() => !running.value && !value('reviewError') && !!value('reviewResult'));
const admissionStopped = computed(() => !!value('reviewError') && trace.value.some(event => event.stage === 'admission' && event.admission && event.admission.status !== 'pass'));

const clock = ref(Date.now());
const startedAt = ref(Date.now());
let timer;
watch(running, (active) => {
  clearInterval(timer);
  if (active) {
    const firstTime = Date.parse(trace.value[0]?.time || "");
    startedAt.value = Number.isFinite(firstTime) ? firstTime : Date.now();
    clock.value = Date.now();
    timer = setInterval(() => { clock.value = Date.now(); }, 1000);
  } else {
    clock.value = Date.now();
  }
}, { immediate: true });
watch(() => value('reviewQueue')?.started_at, (stamp) => {
  if (stamp && Number.isFinite(Date.parse(stamp))) { startedAt.value = Date.parse(stamp); clock.value = Date.now(); }
});
onUnmounted(() => clearInterval(timer));
const elapsed = computed(() => {
  const seconds = Math.max(0, Math.floor((clock.value - startedAt.value) / 1000));
  return seconds >= 60 ? `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒` : `${seconds} 秒`;
});
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
  if (succeeded.value) return 7;
  if (trace.value.some(event => event.stage === 'admission') && !trace.value.some(event => event.admission?.status === 'pass')) return 0;
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
      checklist: 5,
      evidence_tool: 5,
    };
    if (event.stage in stages) step = Math.max(step, stages[event.stage]);
  }
  return step;
});
const items = computed(() => {
  if (running.value) return value("publicAnalysis") || [];
  if (!succeeded.value) return [];
  return (value("reviewResult")?.issues || []).map((item) => ({
    title: item.issue_title,
    clause: item.clause_title,
    analysis: item.risk_analysis,
    evidence: item.redline?.original_text || item.evidence,
    proposal: item.negotiation_strategy,
    severity: item.severity,
  }));
});
const phaseDescriptions = [
  '正在整理合同、审查立场、重点要求及背景资料，确认本轮审查范围。',
  '正在整理条款结构，定位付款、履约、责任及其他合同约定。',
  '正在结合我方立场与重点要求，分析合同主体、履约、价款、责任及相关财税安排。',
  '正在核对分析意见是否有原文依据，检查修订是否超出原条款范围。',
  '正在归并同一条款的问题，整理风险说明与修订建议。',
  '正在核验自定义与清单要求、参考资料证据及修订内容，保留需人工确认的项目。',
  '正在汇总重点要求结论与全文意见，准备本轮审查结果。',
];
const activity = computed(() => reviewActivities(trace.value, running.value ? items.value.length : 0));
const phaseDescription = computed(() => queued.value ? `当前排队第 ${queuePosition.value} 位，轮到后自动开始；可最小化窗口继续其他工作，也可取消排队。` : running.value ? phaseDescriptions[Math.min(activeStep.value,6)] : value('reviewError') ? '本轮未完成审查，不能作为审核结论；上次已完成的结果会保留。' : '重点要求与全文分析已整理完成，可进入工作台逐项复核。');
const metrics = computed(() => {
  const prepare = trace.value.find(item => item.stage === 'prepare') || {};
  const segment = [...trace.value].reverse().find(item => Number.isInteger(item.segment_count));
  return [segment ? `已整理 ${segment.segment_count} 个条款` : null, Number.isInteger(prepare.priority_count) ? `${prepare.priority_count} 条重点要求` : null, prepare.reference_count ? `${prepare.reference_count} 份参考资料` : null].filter(Boolean);
});
const activityTime = (time) => {
  const stamp = Date.parse(time);
  if (!Number.isFinite(stamp)) return '';
  const seconds = Math.max(0,Math.floor((stamp - startedAt.value)/1000));
  return seconds >= 60 ? `${Math.floor(seconds/60)}分${seconds%60}秒` : `${seconds}秒`;
};
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
        <div class="review-dialog-actions">
        <button v-if="running" @click="context.minimizeReview" class="review-minimize" aria-label="最小化审查进度"><span aria-hidden="true">−</span>最小化</button>
        <button
          v-if="running"
          @click="context.cancelReview"
          class="review-cancel"
        >
          {{ queued ? '取消排队' : '取消审查' }}
        </button>
        <button
          v-else
          @click="context.closeReviewDialog"
          class="review-cancel"
          aria-label="关闭审查结果"
        >
          ✕
        </button>
        </div>
      </header>
      <div class="review-dialog-body">
        <ol class="review-stage-list" aria-label="审查处理阶段">
          <li
            v-for="(step, index) in steps"
            :key="step"
            :class="{ done: index < activeStep, active: running && !queued && index === activeStep }"
            :aria-current="!queued && index === activeStep ? 'step' : undefined"
          >
            <span class="review-stage-icon">{{
              index < activeStep ? "✓" : index + 1
            }}</span
            >{{ step }}
          </li>
        </ol>
        <section class="review-process" aria-label="实时处理过程">
          <div class="review-dialog-status" role="status">
            <i v-if="running"></i>
            <span>{{ queued ? '等待执行 · 排队第 ' + queuePosition + ' 位' : running ? '正在处理：' + steps[activeStep] : value('reviewError') ? admissionStopped ? '未通过审查准入' : '本次审查已停止' : '审查完成，意见和修订建议已生成。' }}</span>
            <time class="review-elapsed" aria-label="累计处理用时">{{ queued ? '已等待' : '已用时' }} {{ elapsed }}</time>
          </div>
          <p v-if="value('reviewError')" class="review-failure-message" role="alert">{{ value('reviewError') }}</p>
          <div class="review-current-activity"><p>{{ phaseDescription }}</p><div v-if="metrics.length" class="review-activity-metrics"><span v-for="metric in metrics" :key="metric">{{ metric }}</span></div></div>
          <ol v-if="activity.length" class="review-activity-list" aria-label="审查动态" aria-live="polite" aria-relevant="additions text">
            <li v-for="(entry,index) in activity" :key="entry.id" :class="{'is-latest':index === activity.length - 1 && running}"><span class="review-activity-dot" aria-hidden="true"></span><span>{{ entry.text }}</span><time>{{ activityTime(entry.time) }}</time></li>
          </ol>
        </section>
        <PriorityReview v-if="succeeded" :context="context" :result="value('reviewResult')" />
        <div class="review-analysis-heading">
          <h4 v-if="running || succeeded">全文风险分析（已识别 {{ items.length }} 项）</h4>
          <h4 v-else>本轮未生成有效审查结果</h4>
          <span>{{ running ? "实时更新 · 待最终校验" : succeeded ? "已完成校验" : "未完成校验" }}</span>
        </div>
        <div v-if="!items.length" class="review-waiting">
          <div v-if="running" class="review-waiting-line"></div>
          <h4>{{ queued ? "任务已加入本地队列" : running ? "正在形成条款意见" : succeeded ? "本次未识别出审查问题" : "审查未完成，不能判断是否存在问题" }}</h4>
          <p v-if="running">
            {{ queued ? '同一服务凭证最多并发 5 个审查任务，排队期间尚未开始分析。' : '完成的条款意见将逐项出现在这里，初步意见仍需后续校验。' }}
          </p>
        </div>
        <TransitionGroup
          v-else
          name="review-finding"
          tag="div"
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
        </TransitionGroup>
      </div>
      <footer class="review-dialog-footer">
        <span>{{
          running
            ? queued ? "排队第 " + queuePosition + " 位" : "正在处理：" + steps[activeStep]
            : succeeded ? "共 " + items.length + " 项审查意见" : "本轮未完成审查"
        }}</span
        ><button v-if="!running && value('reviewError')" class="review-result-button" :disabled="value('retryingReview')" @click="context.retryReview">{{ value('retryingReview') ? '正在重试…' : value('workspace')?.task?.running_run ? '重新连接进度' : '重试本轮审查' }}</button><button
          v-if="!running"
          class="review-result-button"
          @click="context.closeReviewDialog"
        >
          {{ succeeded ? '查看审查修订稿' : '返回工作台' }}</button
        ><span v-else>阶段完成后自动更新</span>
      </footer>
    </section>
  </div>
  <button v-if="value('reviewMinimized') && !value('reviewDialogOpen')" class="review-background-indicator" @click="context.restoreReview" aria-label="恢复审查进度">
    <span class="review-background-dot" :class="{done:!running}" aria-hidden="true"></span>
    <span><strong>{{ queued ? '审查排队中 · 第 ' + queuePosition + ' 位' : running ? '审查正在后台进行' : value('reviewError') ? '审查已停止' : '审查已完成' }}</strong><small>{{ running ? '已等待 / 处理 ' + elapsed : '点击查看本轮结果' }}</small></span>
    <span class="review-background-open">{{ running ? '查看进度' : '查看结果' }}</span>
  </button>
</template>

<style scoped>
.review-failure-message { margin:16px; padding:12px 14px; border:1px solid #fecaca; border-radius:8px; background:#fef2f2; color:#991b1b; font-size:13px; line-height:1.7; white-space:pre-wrap; overflow-wrap:anywhere; }
</style>
