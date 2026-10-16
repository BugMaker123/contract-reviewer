<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div
    v-if="showReportModal"
    class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
  >
    <div
      class="bg-white border border-slate-200 rounded-xl w-full max-w-4xl max-h-[90vh] shadow-2xl flex flex-col overflow-hidden"
    >
      <div
        class="h-14 border-b border-slate-200 px-6 flex items-center justify-between shrink-0 bg-slate-50"
      >
        <h3 class="text-base font-bold text-slate-900">
          审查意见书 · 第 {{ workspace.run?.number || 1 }} 次审查
        </h3>
        <div class="flex items-center space-x-3">
          <button
            onclick="window.print()"
            class="px-4 py-1.5 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 transition flex items-center space-x-1.5 shadow-sm cursor-pointer"
          >
            <svg
              class="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <polyline points="6 9 6 2 18 2 18 9"></polyline>
              <path
                d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"
              ></path>
              <rect width="12" height="8" x="6" y="14"></rect>
            </svg>
            <span>打印 / 存为 PDF</span>
          </button>
          <button
            aria-label="关闭意见书"
            @click="showReportModal = false"
            class="text-slate-400 hover:text-slate-600 cursor-pointer"
          >
            <svg
              class="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>

      <div
        class="flex-1 overflow-y-auto p-12 text-slate-900 text-sm leading-relaxed"
        id="printable-report"
      >
        <p v-if="resultStale" class="mb-4 text-xs text-amber-800">
          此意见书基于该次审查的合同正文；后续编辑尚未重新审查。
        </p>
        <div class="text-center border-b-2 border-slate-900 pb-6 mb-6">
          <h1 class="text-2xl font-bold tracking-tight">合同审查意见书</h1>
          <p class="text-slate-500 font-mono text-xs mt-1.5">
            LEXISGRAPH LEGAL REVIEW REPORT · 商业机密
          </p>
        </div>

        <div
          class="grid grid-cols-2 gap-4 mb-6 bg-slate-50 p-4 border border-slate-200 rounded-lg text-xs"
        >
          <div>
            <strong>合同名称：</strong
            >{{ workspace.run?.input.title || contractTitle }}
          </div>
          <div>
            <strong>审查立场：</strong
            >{{ workspace.run?.input.role || partyRole }}
          </div>
          <div><strong>合同类型：</strong>{{ contractType }}</div>
          <div><strong>审查时间：</strong>{{ reviewedAt }}</div>
          <div>
            <strong>修订处理：</strong>已采纳
            {{ appliedIssueIds.length }} 项
          </div>
          <div>
            <strong>风险评级：</strong
            ><span class="font-bold text-red-600">{{
              reviewResult?.summary?.risk_level
            }}</span>
          </div>
        </div>

        <div class="mb-6">
          <h3 class="text-sm font-bold border-l-4 border-blue-600 pl-2 mb-2">
            一、 法务终审结论与签署建议
          </h3>
          <p class="text-slate-700 leading-relaxed">
            {{ reviewResult?.summary?.verdict }}
          </p>
        </div>

        <div class="mb-6">
          <h3 class="text-sm font-bold border-l-4 border-blue-600 pl-2 mb-2">
            二、 财税与结算检查结果
          </h3>
          <div
            v-if="currentTaxSettlement"
            class="space-y-1.5 text-xs text-slate-700 bg-slate-50 p-3 rounded border border-slate-200"
          >
            <div>
              <strong>1. 增值税税额单列：</strong
              >{{
                currentTaxSettlement.has_separate_vat_amount
                  ? "已规范单列价税"
                  : "未单列税额 (含税总价混淆)"
              }}
              - {{ currentTaxSettlement.vat_amount_detail }}
            </div>
            <div>
              <strong>2. 增值税税率核验：</strong
              >{{ currentTaxSettlement.vat_rate }} -
              {{ currentTaxSettlement.vat_rate_evaluation }}
            </div>
            <div>
              <strong>3. 增值税专用发票：</strong
              >{{
                currentTaxSettlement.is_special_vat_invoice
                  ? "明确限定专票"
                  : "未锁定专用发票 (进项抵扣风险)"
              }}
              - {{ currentTaxSettlement.invoice_detail }}
            </div>
            <div>
              <strong>4. 结算方式与条件：</strong
              >{{ currentTaxSettlement.settlement_method }} -
              {{ currentTaxSettlement.settlement_condition_analysis }}
            </div>
          </div>
        </div>

        <div class="mb-6">
          <h3 class="text-sm font-bold border-l-4 border-red-600 pl-2 mb-2">
            三、 核心商业与合规否决项 (Dealbreakers)
          </h3>
          <ul class="list-disc pl-5 space-y-1 text-red-700 text-xs">
            <li
              v-for="(item, i) in reviewResult?.summary?.key_dealbreakers"
              :key="i"
            >
              {{ item }}
            </li>
          </ul>
        </div>

        <div class="mb-6">
          <h3 class="text-sm font-bold border-l-4 border-blue-600 pl-2 mb-2">
            四、 关键条款风险清单与红线修改对照表
          </h3>
          <div class="space-y-4">
            <div
              v-for="issue in reviewResult?.issues"
              :key="issue.id"
              class="border border-slate-200 p-4 rounded-lg text-xs"
            >
              <div
                class="font-bold text-slate-800 text-sm flex justify-between"
              >
                <span>{{ issue.clause_title }}：{{ issue.issue_title }}</span>
                <span class="font-bold text-red-600 uppercase"
                  >[{{
                    issue.checklist_status === "needs_review"
                      ? "待人工确认"
                      : issue.diff && !issue.model_assessed
                        ? "变更待评估"
                        : severityLabel(issue.severity)
                  }}]</span
                >
              </div>
              <div class="mt-1 text-blue-700">
                处理状态：{{ workspace.decisionName(issue.id) }}
              </div>
              <div class="text-slate-600 mt-1.5">
                <strong>法律依据：</strong>{{ issue.legal_basis }}
              </div>
              <div class="text-slate-600 mt-1">
                <strong>风险剖析：</strong>{{ issue.risk_analysis }}
              </div>
              <div class="text-amber-800 mt-1">
                <strong>谈判策略：</strong>{{ issue.negotiation_strategy }}
              </div>
              <div
                v-if="issue.redline"
                class="mt-2 bg-slate-50 p-3 rounded border border-slate-200"
              >
                <div class="text-red-700 line-through">
                  原：{{ issue.redline.original_text }}
                </div>
                <div class="text-emerald-700 font-bold mt-1">
                  改：{{ issue.redline.suggested_text }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div
          class="mt-10 pt-6 border-t border-slate-300 flex justify-between text-slate-500 text-xs"
        >
          <div>内部审查记录：LexisGraph</div>
          <div>确认签字：________________________</div>
        </div>
      </div>
    </div>
  </div>
</template>
