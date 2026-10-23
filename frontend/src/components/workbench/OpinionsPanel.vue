<script>
import { ref, watch } from "vue";
import ManualIssue from "./ManualIssue.vue";
import RevisionActions from "./RevisionActions.vue";
import StaleReviewNotice from "./StaleReviewNotice.vue";
export default {
  components: { RevisionActions, ManualIssue, StaleReviewNotice },
  props: { context: { type: Object, required: true } },
  setup(props) {
    const expandedIssueId = ref(null);
    watch(props.context.focusedIssueId, (id) => {
      if (id) expandedIssueId.value = id;
    });
    watch(props.context.reviewIssues, (issues) => {
      if (!issues.some((issue) => issue.id === expandedIssueId.value)) {
        expandedIssueId.value = props.context.focusedIssueId.value || issues[0]?.id || null;
      }
    }, { immediate: true });
    const toggleIssue = (issue) => {
      if (expandedIssueId.value === issue.id) {
        expandedIssueId.value = null;
      } else {
        expandedIssueId.value = issue.id;
        props.context.selectIssue(issue.id);
      }
    };
    return { ...props.context, expandedIssueId, toggleIssue };
  },
};
</script>

<template>
  <aside
    id="opinion-drawer"
    role="region"
    aria-labelledby="opinion-drawer-title"
    class="wb-sidebar wb-opinion-drawer"
    :class="{
      'is-compact-review': revisionMode !== 'compare',
      'is-collapsed': !opinionsOpen,
    }"
  >
    <div class="wb-sidebar-heading">
      <strong v-show="opinionsOpen" id="opinion-drawer-title">审查建议
        <span v-if="!resultStale" class="wb-sidebar-count">{{
          reviewIssues.length
        }}</span></strong
      >


    </div>
    <div
      v-show="opinionsOpen"
      id="review-opinion-content"
      class="wb-opinion-content"
    >

      <StaleReviewNotice v-if="resultStale && revisionMode !== 'compare'" :context="context" />
      <p v-if="resultStale && revisionMode === 'compare'" role="status">正文或条件已改变，请重新审查；以下结论属于旧版本。</p>
      <template v-if="!resultStale || revisionMode === 'compare'">

      <div class="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/30">
      <section class="wb-opinion-toolbar" aria-label="审查建议筛选">
        <div v-if="opinionsOpen && reviewReady && !resultStale && revisionMode !== 'compare'" class="wb-batch-actions" role="group" aria-label="批量处理本轮审查意见">
          <button class="batch-accept" :disabled="revisionReadOnly || !pendingApplicableCount" @click="acceptAllRevisions" title="采纳本轮全部待处理修订建议"><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m3 12 4 4 9-9M12 16l9-9"/></svg><span>一键全部采纳</span></button>
          <button class="batch-cancel" :disabled="revisionReadOnly || !undoableRevisionCount" @click="undoAllReviewDecisions" title="撤销本轮全部采纳、拒绝及待复核决定，恢复待处理"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 5 4 10l5 5M4 10h9a6 6 0 0 1 0 12" transform="translate(0 -2)"/></svg><span>一键撤销</span></button>
          <button class="batch-cancel batch-cancel-accepted" :disabled="revisionReadOnly || !appliedIssueIds.length" @click="cancelAllAcceptedRevisions" title="仅取消本轮已采纳修订"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg><span>一键取消已采纳</span></button>
          <button v-if="pendingCriticalCount && pendingLowRiskCount" class="batch-safe-accept" :disabled="revisionReadOnly || !pendingLowRiskCount" @click="acceptLowRiskRevisions" :title="`保留 ${pendingCriticalCount} 项重大风险供人工复核，仅批量采纳 ${pendingLowRiskCount} 项一般与优化建议`"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg><span>仅采纳低风险 ({{ pendingLowRiskCount }})</span></button>
        </div>
        <input v-model="issueSearch" placeholder="搜索条款或意见" aria-label="搜索审查意见" class="wb-opinion-search" />
        <div class="wb-opinion-filter-row">
          <select v-model="severityFilter" aria-label="筛选风险等级">
            <option value="all">全部风险等级</option><option value="critical">重大风险</option><option value="warning">一般风险</option><option value="info">优化建议</option><option value="favorable">有利条款</option>
          </select>
          <select v-model="handlingFilter" aria-label="筛选处理状态">
            <option value="all">全部处理状态</option><option value="pending">待处理</option><option value="applied">已采纳</option><option value="rejected">不采纳</option><option value="needs_review">待复核</option>
          </select>
          <button v-if="severityFilter !== 'all' || handlingFilter !== 'all' || issueSearch" type="button" class="wb-opinion-reset" @click="severityFilter = 'all'; handlingFilter = 'all'; issueSearch = ''">重置</button>
        </div>
        <div class="wb-opinion-secondary">
          <ManualIssue :context="context" />
          <span v-if="severityFilter !== 'all' || handlingFilter !== 'all' || issueSearch" class="wb-opinion-match-count" role="status">显示 {{ filteredIssues.length }} / {{ reviewIssues.length }} 项</span>
        </div>

      </section>
        <h3 v-if="reviewResult && !isReviewing" class="wb-full-analysis-title">问题定位与审查建议 <span>{{ filteredIssues.length }} 项意见</span></h3>
        <div
          v-for="(issue, index) in filteredIssues"
          :key="issue.id"
          :id="'card-' + issue.id"
          :data-decision="appliedIssueIds.includes(issue.id) ? 'applied' : (workspace.decisions[issue.id] || 'pending')"
          :class="
            focusedIssueId === issue.id
              ? 'border-blue-500 ring-2 ring-blue-500/20 shadow-md'
              : 'border-slate-200 hover:border-slate-300 shadow-sm'
          "
          class="prototype-risk-card wb-issue-accordion bg-white border rounded-xl transition"
        >
          <button type="button" class="wb-issue-accordion-trigger" :aria-expanded="expandedIssueId === issue.id" :aria-controls="'issue-detail-' + issue.id" @click="toggleIssue(issue)">
            <span class="wb-nav-index">{{ String(index + 1).padStart(2, '0') }}</span>
            <span class="wb-issue-accordion-copy"><strong>{{ issue.issue_title }}</strong><small>{{ issue.clause_title }} · {{ severityLabel(issue.severity) }} · {{ workspace.decisionName(issue.id) }}</small></span>
            <span class="wb-issue-accordion-chevron" aria-hidden="true">⌄</span>
          </button>
          <div v-show="expandedIssueId === issue.id" :id="'issue-detail-' + issue.id" class="wb-issue-accordion-detail">
          <div class="compact-card-top flex items-center justify-between mb-2">
            <span
              class="text-xs font-bold text-slate-600 truncate max-w-[240px]"
            >
              {{ issue.clause_title }}
            </span>
            <span
              class="text-xs px-2 py-0.5 rounded font-bold uppercase shrink-0 whitespace-nowrap"
              :class="
                issue.checklist_status === 'needs_review' ||
                (issue.diff && !issue.model_assessed)
                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                  : issue.severity === 'critical'
                    ? 'bg-red-50 text-red-700 border border-red-200'
                    : issue.severity === 'warning'
                      ? 'bg-amber-50 text-amber-700 border border-amber-200'
                      : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              "
            >
              {{
                issue.checklist_status === "needs_review"
                  ? "待人工确认"
                  : issue.diff && !issue.model_assessed
                    ? "变更待评估"
                    : severityLabel(issue.severity)
              }}
            </span>
          </div>

          <div class="compact-decision mb-2 text-[11px] text-blue-700">
            处理状态：{{ workspace.decisionName(issue.id) }}
          </div>
          <h3 class="prototype-card-title">{{ issue.issue_title }}</h3>
          <p class="prototype-card-analysis">{{ issue.risk_analysis }}</p>
          <button
            class="prototype-locate"
            @click.stop="selectIssue(issue.id)"
            :aria-label="'定位条款：' + issue.clause_title"
          >
            ⌖ 定位原文
          </button>
          <details
            class="revision-risk-details"
            :open="revisionMode === 'compare'"
            @click.stop
          >
            <summary>风险说明与依据</summary>
            <div v-if="issue.diff" class="text-xs space-y-2 mb-3">
              <div
                class="p-3 bg-red-50 text-red-800 border border-red-200 rounded-lg whitespace-pre-wrap"
              >
                <strong>参考合同：</strong
                >{{ issue.diff.original || "（无，此项为新增）" }}
              </div>
              <div
                class="p-3 bg-blue-50 text-blue-900 border border-blue-200 rounded-lg whitespace-pre-wrap"
              >
                <strong>待审合同：</strong
                >{{ issue.diff.current || "（已删除）" }}
              </div>
            </div>
            <div
              v-else-if="issue.evidence"
              class="wb-evidence text-xs mb-3 p-3 text-slate-600 rounded-lg whitespace-pre-wrap"
            >
              <strong>原文证据：</strong>{{ issue.evidence }}
            </div>

            <div
              class="wb-risk-area"
              :class="issue.severity === 'favorable' ? 'wb-risk-favorable' : ''"
            >
              <h4 class="text-sm font-bold text-slate-900 leading-snug">
                {{ issue.issue_title }}
              </h4>

              <div
                v-if="issue.risk_points?.length > 1"
                class="wb-risk-description space-y-3"
              >
                <div v-for="(point, index) in issue.risk_points" :key="index">
                  <strong>{{ index + 1 }}. {{ point.title }}</strong>
                  <p class="mt-1">{{ point.analysis }}</p>
                </div>
              </div>
              <div v-else class="wb-risk-description">
                {{ issue.risk_analysis }}
              </div>
            </div>
            <p
              v-if="issue.rewrite_warning"
              class="mt-2 p-2 rounded bg-amber-50 text-amber-800 text-xs"
            >
              {{ issue.rewrite_warning }}
            </p>
            <p v-else-if="issue.redline" class="mt-2 text-xs text-red-700">
              AI 建议已标记在正文中，采纳后将写入当前稿。
            </p>

            <details class="mt-3 text-xs" @click.stop>
              <summary class="text-slate-500 cursor-pointer">
                依据与处理建议
              </summary>

              <div
                class="mt-2.5 text-xs text-slate-500 flex items-start space-x-1.5"
              >
                <svg
                  class="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
                  <path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
                  <path d="M7 21h10" />
                  <path d="M12 3v18" />
                  <path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2" />
                </svg>
                <span class="leading-relaxed">{{ issue.legal_basis }}</span>
              </div>

              <div
                class="mt-2 text-xs text-amber-800 bg-amber-50/80 border border-amber-200/60 p-2.5 rounded-lg leading-relaxed"
              >
                <strong>谈判策略：</strong>{{ issue.negotiation_strategy }}
              </div>
            </details>
          </details>
          <RevisionActions
            v-if="workspace.run"
            :context="context"
            :issue="issue"
          />
          <details
            :open="revisionMode === 'compare'"
            v-if="workspace.run"
            class="compact-extra-tools mt-4 pt-3 border-t border-slate-100 space-y-3"
            @click.stop
          >
            <summary class="revision-more-tools-label">备注与复核<span>记录处理理由或继续追问</span></summary>
            <div class="wb-issue-actions issue-review-actions">
              <button @click="setReviewDecision(issue, 'needs_review')" :disabled="revisionReadOnly || workspace.decisions[issue.id] === 'needs_review'" :aria-pressed="workspace.decisions[issue.id] === 'needs_review'">标记待复核</button>
              <button @click="workspace.followupIssue = workspace.followupIssue === issue.id ? null : issue.id" :aria-expanded="workspace.followupIssue === issue.id" :disabled="workspace.historical || isReviewing">追问意见</button>
            </div>
            <label class="issue-note-label" :for="'issue-note-'+issue.id">处理备注</label>
            <textarea
              :id="'issue-note-'+issue.id"
              v-model="workspace.comments[issue.id]"
              :disabled="
                workspace.historical ||
                workspace.loading ||
                isReviewing ||
                revisionBusy
              "
              placeholder="添加人工备注或处理理由…"
              aria-label="条目处理备注"
              class="w-full border border-slate-200 rounded-lg p-2 text-xs leading-relaxed outline-none focus:border-blue-500"
              rows="2"
            ></textarea>
            <div v-if="workspace.followupIssue === issue.id" class="space-y-3">
              <div
                v-for="answer in workspace.followups[issue.id] || []"
                class="p-3 border border-slate-200 bg-slate-50 rounded-lg text-xs leading-relaxed"
              >
                <div class="font-semibold text-slate-700">
                  {{ answer.question }}
                </div>
                <p class="mt-2 whitespace-pre-wrap text-slate-600">
                  {{ answer.answer }}
                </p>
                <p
                  v-if="answer.suggested_text"
                  class="mt-2 whitespace-pre-wrap text-emerald-800"
                >
                  {{ answer.suggested_text }}
                </p>
                <button
                  v-if="answer.suggested_text"
                  @click="workspace.previewFollowup(answer)"
                  class="mt-2 text-blue-600"
                >
                  复制替代条款，核对后编辑正文
                </button>
              </div>
              <textarea
                v-model="workspace.question"
                placeholder="例如：解释这一风险，或提出更温和的修改方案…"
                class="w-full p-2 text-xs border border-slate-200 rounded-lg"
                rows="3"
              ></textarea
              ><button
                @click="workspace.ask(issue)"
                :disabled="
                  workspace.followupBusy ||
                  !workspace.question.trim() ||
                  workspace.historical
                "
                class="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs"
              >
                {{ workspace.followupBusy ? "正在回答…" : "发送追问" }}
              </button>
            </div>
          </details>

          </div>
        </div>

        <div
          v-if="!reviewResult && !isReviewing"
          class="text-center py-20 px-6 text-slate-400 text-sm flex flex-col items-center"
        >
          <div
            class="w-12 h-12 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 mb-3 shadow-sm"
          >
            <svg
              class="w-6 h-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
          </div>
          <p class="font-bold text-slate-700 text-base">待发起合同审查</p>
          <p class="text-xs text-slate-500 mt-1.5 leading-relaxed max-w-xs">
            核对正文与审查条件后，按所选模式发起审查。
          </p>
          <button
            @click="startReview"
            :disabled="
              workspace.loading ||
              workspace.historical ||
              ['running','queued'].includes(workspace.task?.status) ||
              !contractText.trim()
            "
            class="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-sm transition active:scale-95 cursor-pointer"
          >
            立即开始审查
          </button>
        </div>

        <div
          v-else-if="isReviewing"
          class="text-center py-24 text-slate-500 text-sm flex flex-col items-center"
        >
          <svg
            class="animate-spin w-8 h-8 text-blue-600 mb-3"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
            ></circle>
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v8H4z"
            ></path>
          </svg>
          <span class="font-semibold text-slate-700"
            >{{ reviewQueue?.status === "queued" ? "正在排队等待审查" : "正在进行法务深度研判…" }}</span
          >
          <span class="text-xs text-slate-400 mt-1">可通过进度窗口或右下角入口查看进展</span>
        </div>

        <div
          v-else-if="filteredIssues.length === 0"
          class="text-center py-24 text-slate-400 text-sm"
        >
          <svg
            class="w-10 h-10 mx-auto mb-2 text-emerald-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p class="font-semibold text-slate-700">当前没有匹配的条目</p>
          <p class="text-xs text-slate-400 mt-1">
            可调整风险等级、处理状态或搜索条件；此状态不代表合同整体合规
          </p>
        </div>
      </div>
      </template>
    </div>
    <div
      v-if="opinionsOpen"
      class="wb-edge-resize wb-edge-left"
      title="拖拽调整审查建议抽屉宽度，双击恢复默认"
      @mousedown="context.startRightResize"
      @dblclick="context.resetRightWidth"
    />
  </aside>
</template>
