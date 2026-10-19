<script>
import ManualIssue from "./ManualIssue.vue";
import RevisionActions from "./RevisionActions.vue";
export default {
  components: { RevisionActions, ManualIssue },
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
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
        <span class="wb-sidebar-count">{{
          reviewIssues.length
        }}</span></strong
      >

      <button
        v-if="opinionsOpen && reviewReady && revisionMode !== 'compare'"
        class="batch-accept"
        :disabled="revisionReadOnly || !pendingApplicableCount"
        @click="acceptAllRevisions"
      >
        一键全部采纳
      </button>
    </div>
    <div
      v-show="opinionsOpen"
      id="review-opinion-content"
      class="wb-opinion-content"
    >

      <section class="wb-opinion-toolbar" aria-label="审查建议筛选">
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
      <div class="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/30">
        <div
          v-for="issue in filteredIssues"
          :key="issue.id"
          :id="'card-' + issue.id"
          @click="highlightInContract(issue)"
          :data-decision="appliedIssueIds.includes(issue.id) ? 'applied' : (workspace.decisions[issue.id] || 'pending')"
          :class="
            focusedIssueId === issue.id
              ? 'border-blue-500 ring-2 ring-blue-500/20 shadow-md'
              : 'border-slate-200 hover:border-slate-300 shadow-sm'
          "
          class="prototype-risk-card bg-white border rounded-xl p-5 transition cursor-pointer"
        >
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
            <summary class="revision-more-tools-label">备注与更多处理</summary>
            <div class="wb-issue-actions flex gap-2 text-xs">
              <button
                @click="workspace.setDecision(issue, 'rejected')"
                :aria-pressed="workspace.decisionName(issue.id) === '不采纳'"
                :class="
                  workspace.decisionName(issue.id) === '不采纳'
                    ? 'bg-blue-50 ring-2 ring-blue-500 font-semibold'
                    : ''
                "
                :disabled="
                  workspace.historical ||
                  workspace.loading ||
                  isReviewing ||
                  revisionBusy
                "
                class="px-2 py-1 border border-slate-200 rounded text-slate-600"
              >
                不采纳</button
              ><button
                @click="workspace.setDecision(issue, 'needs_review')"
                :aria-pressed="workspace.decisionName(issue.id) === '待复核'"
                :class="
                  workspace.decisionName(issue.id) === '待复核'
                    ? 'bg-blue-50 ring-2 ring-blue-500 font-semibold'
                    : ''
                "
                :disabled="
                  workspace.historical ||
                  workspace.loading ||
                  isReviewing ||
                  revisionBusy
                "
                class="px-2 py-1 border border-slate-200 rounded text-amber-700"
              >
                待复核</button
              ><button
                @click="workspace.setDecision(issue, 'pending')"
                :aria-pressed="workspace.decisionName(issue.id) === '待处理'"
                :class="
                  workspace.decisionName(issue.id) === '待处理'
                    ? 'bg-blue-50 ring-2 ring-blue-500 font-semibold'
                    : ''
                "
                :disabled="
                  workspace.historical ||
                  workspace.loading ||
                  isReviewing ||
                  revisionBusy
                "
                class="px-2 py-1 text-slate-400"
              >
                重置状态</button
              ><button
                @click="openClauseEditor(issue)"
                :disabled="
                  documentSaving ||
                  workspace.historical ||
                  workspace.loading ||
                  isReviewing
                "
                class="px-2 py-1 text-blue-600"
              >
                编辑条款</button
              ><button
                @click="
                  workspace.followupIssue =
                    workspace.followupIssue === issue.id ? null : issue.id
                "
                class="ml-auto px-2 py-1 text-blue-600"
              >
                追问意见
              </button>
            </div>
            <textarea
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
              workspace.task?.status === 'running' ||
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
            >正在进行法务深度研判...</span
          >
          <span class="text-xs text-slate-400 mt-1">请查看中央浮动进度条</span>
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
    </div>
  </aside>
</template>
