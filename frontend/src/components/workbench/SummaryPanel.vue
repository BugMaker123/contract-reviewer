<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <aside
    id="review-summary-panel"
    data-testid="review-summary"
    class="wb-sidebar wb-summary-panel"
    :class="{ 'is-collapsed': !summaryOpen }"
  >
    <div class="wb-sidebar-heading">
      <button
        @click="toggleSummary"
        :aria-expanded="summaryOpen"
        aria-controls="review-summary-content"
        :aria-label="summaryOpen ? '收起审查概览' : '展开审查概览'"
        :title="summaryOpen ? '收起审查概览' : '展开审查概览'"
        class="wb-sidebar-toggle"
      >
        <svg
          viewBox="0 0 20 20"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="m12 5-5 5 5 5" />
        </svg></button
      ><strong v-show="summaryOpen">审查概览</strong>
    </div>
    <div
      v-show="summaryOpen"
      id="review-summary-content"
      class="wb-summary-content space-y-4"
    >
      <div
        v-if="reviewResult?.checklist_findings"
        class="border border-slate-200 rounded-xl p-4 bg-white shadow-sm"
      >
        <h3 class="text-xs font-semibold text-slate-700">
          {{ workspace.conditions.checklist?.name }} · v{{
            workspace.conditions.checklist?.version
          }}
        </h3>
        <div
          v-for="finding in reviewResult.checklist_findings"
          class="border-t border-slate-100 pt-3 mt-3 text-xs"
        >
          <div class="flex justify-between gap-2">
            <span class="font-medium">{{ finding.title }}</span
            ><span
              class="shrink-0"
              :class="
                finding.status === 'pass'
                  ? 'text-emerald-700'
                  : finding.status === 'fail'
                    ? 'text-red-700'
                    : 'text-amber-700'
              "
              >{{
                {
                  pass: "通过",
                  fail: "未通过",
                  needs_review: "待确认",
                  not_applicable: "不适用",
                }[finding.status]
              }}</span
            >
          </div>
          <p class="text-[11px] text-slate-500 mt-1 leading-relaxed">
            {{ finding.explanation }}
          </p>
        </div>
      </div>
      <div
        v-if="reviewResult?.differences"
        class="border border-slate-200 rounded-xl p-4 bg-white shadow-sm text-xs"
      >
        <h3 class="font-semibold mb-2">合同差异概览</h3>
        <p class="text-slate-500">
          共 {{ reviewResult.differences.length }} 处变更
        </p>
        <p class="text-[11px] text-slate-400 mt-2">
          文字变化需结合交易背景评估，删除内容可在右栏查看。
        </p>
      </div>
      <div
        v-if="!['checklist', 'compare'].includes(workspace.conditions.mode)"
        class="border border-slate-200 rounded-xl p-4 bg-slate-50/60 shadow-sm"
      >
        <div class="text-xs font-semibold text-slate-700">风险概览</div>
        <p v-if="!reviewResult" class="text-xs text-slate-400 py-3 text-center">
          审查完成后展示风险统计
        </p>

        <div
          v-if="reviewResult"
          class="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-slate-200 text-center"
        >
          <div class="bg-white border border-slate-200 rounded-lg py-1.5">
            <div class="text-base font-bold font-mono text-red-600">
              {{ reviewResult.summary.critical_count }}
            </div>
            <div class="text-[11px] text-slate-500">重大风险</div>
          </div>
          <div class="bg-white border border-slate-200 rounded-lg py-1.5">
            <div class="text-base font-bold font-mono text-amber-600">
              {{ reviewResult.summary.warning_count }}
            </div>
            <div class="text-[11px] text-slate-500">一般风险</div>
          </div>
          <div class="bg-white border border-slate-200 rounded-lg py-1.5">
            <div class="text-base font-bold font-mono text-slate-700">
              {{ reviewResult.summary.info_count }}
            </div>
            <div class="text-[11px] text-slate-500">优化建议</div>
          </div>
        </div>
      </div>

      <div
        v-if="
          workspace.conditions.mode === 'quick' ||
          workspace.conditions.mode === 'deep'
        "
        class="border border-slate-200 rounded-xl p-4 bg-white shadow-sm"
      >
        <div
          class="flex items-center justify-between mb-3 pb-2 border-b border-slate-100"
        >
          <span
            class="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center space-x-1.5"
          >
            <svg
              class="w-3.5 h-3.5 text-blue-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"
              />
              <path d="M16 8h-6" />
              <path d="M16 12h-6" />
              <path d="M14 16h-4" />
            </svg>
            <span>财税与结算专项审核 (4大要件)</span>
          </span>
        </div>

        <div
          v-if="reviewResult && currentTaxSettlement"
          class="space-y-2.5 text-xs"
        >
          <div
            class="p-2.5 rounded-lg border flex flex-col space-y-1 transition"
            :class="
              currentTaxSettlement.has_separate_vat_amount
                ? 'bg-emerald-50/50 border-emerald-200'
                : 'bg-red-50/50 border-red-200'
            "
          >
            <div class="flex items-center justify-between font-semibold">
              <span class="flex items-center space-x-1.5">
                <span
                  class="w-2 h-2 rounded-full"
                  :class="
                    currentTaxSettlement.has_separate_vat_amount
                      ? 'bg-emerald-500'
                      : 'bg-red-500'
                  "
                ></span>
                <span
                  :class="
                    currentTaxSettlement.has_separate_vat_amount
                      ? 'text-emerald-900'
                      : 'text-red-900'
                  "
                  >1. 增值税税额单列</span
                >
              </span>
              <span
                class="text-[11px] font-bold"
                :class="
                  currentTaxSettlement.has_separate_vat_amount
                    ? 'text-emerald-700'
                    : 'text-red-700'
                "
              >
                {{
                  currentTaxSettlement.has_separate_vat_amount
                    ? "已单列"
                    : "未单列(总额混淆)"
                }}
              </span>
            </div>
            <p class="text-[11px] text-slate-500 leading-snug">
              {{ currentTaxSettlement.vat_amount_detail }}
            </p>
          </div>

          <div
            class="p-2.5 rounded-lg border flex flex-col space-y-1 transition"
            :class="
              currentTaxSettlement.vat_rate !== '未明确税率'
                ? 'bg-slate-50 border-slate-200'
                : 'bg-amber-50/50 border-amber-200'
            "
          >
            <div class="flex items-center justify-between font-semibold">
              <span class="flex items-center space-x-1.5">
                <span
                  class="w-2 h-2 rounded-full"
                  :class="
                    currentTaxSettlement.vat_rate !== '未明确税率'
                      ? 'bg-blue-500'
                      : 'bg-amber-500'
                  "
                ></span>
                <span
                  :class="
                    currentTaxSettlement.vat_rate !== '未明确税率'
                      ? 'text-slate-900'
                      : 'text-amber-900'
                  "
                  >2. 增值税税率核验</span
                >
              </span>
              <span
                class="text-[11px] font-bold font-mono px-1.5 py-0.5 rounded"
                :class="
                  currentTaxSettlement.vat_rate !== '未明确税率'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-amber-100 text-amber-800'
                "
              >
                {{ currentTaxSettlement.vat_rate }}
              </span>
            </div>
            <p class="text-[11px] text-slate-500 leading-snug">
              {{ currentTaxSettlement.vat_rate_evaluation }}
            </p>
          </div>

          <div
            class="p-2.5 rounded-lg border flex flex-col space-y-1 transition"
            :class="
              currentTaxSettlement.is_special_vat_invoice
                ? 'bg-emerald-50/50 border-emerald-200'
                : 'bg-red-50/50 border-red-200'
            "
          >
            <div class="flex items-center justify-between font-semibold">
              <span class="flex items-center space-x-1.5">
                <span
                  class="w-2 h-2 rounded-full"
                  :class="
                    currentTaxSettlement.is_special_vat_invoice
                      ? 'bg-emerald-500'
                      : 'bg-red-500'
                  "
                ></span>
                <span
                  :class="
                    currentTaxSettlement.is_special_vat_invoice
                      ? 'text-emerald-900'
                      : 'text-red-900'
                  "
                  >3. 增值税专用发票</span
                >
              </span>
              <span
                class="text-[11px] font-bold"
                :class="
                  currentTaxSettlement.is_special_vat_invoice
                    ? 'text-emerald-700'
                    : 'text-red-700'
                "
              >
                {{
                  currentTaxSettlement.is_special_vat_invoice
                    ? "明确专票"
                    : "未锁定专票(普票风险)"
                }}
              </span>
            </div>
            <p class="text-[11px] text-slate-500 leading-snug">
              {{ currentTaxSettlement.invoice_detail }}
            </p>
          </div>

          <div
            class="p-2.5 rounded-lg border flex flex-col space-y-1 transition bg-amber-50/40 border-amber-200"
          >
            <div class="flex items-center justify-between font-semibold">
              <span class="flex items-center space-x-1.5">
                <span class="w-2 h-2 rounded-full bg-amber-500"></span>
                <span class="text-amber-900">4. 结算方式与条件</span>
              </span>
              <span class="text-[11px] font-bold text-amber-800">
                {{
                  currentTaxSettlement.settlement_method &&
                  currentTaxSettlement.settlement_method.includes("承兑")
                    ? "承兑汇票(高危)"
                    : "需关注前置"
                }}
              </span>
            </div>
            <p class="text-[11px] text-slate-600 leading-snug">
              {{ currentTaxSettlement.settlement_condition_analysis }}
            </p>
          </div>
        </div>

        <div v-else class="text-xs text-slate-400 py-3 text-center">
          审查后即刻呈现增值税与结算 4 大核验详情
        </div>
      </div>

      <div
        class="border border-slate-200 rounded-xl p-4 bg-white shadow-sm flex-1 flex flex-col"
      >
        <div
          class="flex items-center justify-between mb-3 pb-2 border-b border-slate-100"
        >
          <span
            class="text-xs font-semibold text-slate-700 uppercase tracking-wider flex items-center space-x-1.5"
          >
            <svg
              class="w-3.5 h-3.5 text-blue-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <circle cx="12" cy="12" r="3"></circle>
              <line x1="3" y1="12" x2="9" y2="12"></line>
              <line x1="15" y1="12" x2="21" y2="12"></line>
            </svg>
            <span>审查进度</span>
          </span>
        </div>

        <div class="space-y-3 relative text-xs">
          <div
            v-for="(node, idx) in pipelineNodes"
            :key="node.id"
            class="flex items-start space-x-3"
          >
            <div
              class="w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5 text-[11px] font-semibold"
              :class="
                nodeStates[node.id] === 'completed'
                  ? 'bg-emerald-100 text-emerald-700'
                  : nodeStates[node.id] === 'running'
                    ? 'bg-blue-100 text-blue-700 ring-2 ring-blue-500/30'
                    : 'bg-slate-100 text-slate-400'
              "
            >
              <svg
                v-if="nodeStates[node.id] === 'completed'"
                class="w-3 h-3 text-emerald-700"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="3"
              >
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              <span v-else>{{ idx + 1 }}</span>
            </div>

            <div class="flex-1">
              <div
                class="font-medium text-xs text-slate-800"
                :class="
                  nodeStates[node.id] === 'running'
                    ? 'text-blue-700 font-bold'
                    : ''
                "
              >
                {{ node.name }}
              </div>
              <div class="text-[11px] text-slate-400 mt-0.5">
                {{ node.description }}
              </div>
            </div>
          </div>
        </div>

        <details
          v-if="reviewTrace.length"
          class="mt-3 border-t border-slate-100 pt-3"
        >
          <summary class="text-xs text-slate-500 cursor-pointer">
            查看本次审查记录 · {{ reviewTrace.length }} 条
          </summary>
          <ol
            class="mt-3 max-h-64 overflow-auto space-y-2 text-[11px] text-slate-500"
          >
            <li
              v-for="(item, index) in reviewTrace"
              :key="index"
              class="leading-relaxed"
            >
              <span class="text-slate-400 mr-2">{{
                new Date(item.time).toLocaleTimeString("zh-CN", {
                  hour12: false,
                })
              }}</span
              >{{ item.detail }}
            </li>
          </ol>
        </details>
        <div
          v-if="latestLogMessage"
          class="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg leading-relaxed"
        >
          <span class="font-semibold text-blue-600">当前：</span
          >{{ latestLogMessage }}
        </div>
      </div>
    </div>
    <details v-show="summaryOpen" class="wb-review-usage">
      <summary>使用说明</summary>
      <p v-if="reviewResult?.coverage">{{ reviewResult.coverage }}</p>
      <p>审查建议仅供辅助参考，不替代专业法律意见。签署前请结合交易背景与实际履行情况复核。</p>
    </details>
  </aside>
</template>
