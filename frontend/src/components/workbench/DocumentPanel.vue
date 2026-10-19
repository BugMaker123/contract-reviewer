<script>
import ChevronIcon from "../ChevronIcon.vue";
import RevisionRibbon from "./RevisionRibbon.vue";
export default {
  components: { ChevronIcon, RevisionRibbon },
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <section class="flex-1 min-w-0 flex flex-col bg-slate-100/60 overflow-hidden">
    <div v-if="reviewReady" class="wb-document-toolbar">
      <RevisionRibbon :context="context" />
      <div v-if="reviewReady" class="prototype-issue-nav">
        <button
          @click="moveRevision(-1)"
          :disabled="!reviewIssues.length"
          aria-label="上一处修订"
          title="上一处风险 (Alt+↑)"
        >
          <ChevronIcon direction="up" />
        </button>
        <span
          >{{ reviewIssues.length ? revisionIndex + 1 : 0 }} /
          {{ reviewIssues.length }}</span
        >
        <button
          @click="moveRevision(1)"
          :disabled="!reviewIssues.length"
          aria-label="下一处修订"
          title="下一处风险 (Alt+↓)"
        >
          <ChevronIcon />
        </button>
      </div>
    </div>
    <div
      v-if="workspace.historical"
      class="px-6 py-3 text-xs text-blue-700 bg-blue-50 border-b border-blue-200"
    >
      正在查看历史审查版本，原文和结果保留不变。<RouterLink
        :to="'/workbench?task=' + workspace.taskId"
        class="ml-2 underline"
        >返回当前任务</RouterLink
      >
    </div>
    <div
      v-if="workspace.error"
      class="px-6 py-3 text-xs text-red-700 bg-red-50 border-b border-red-200"
      role="alert"
    >
      {{ workspace.error }}
    </div>
    <div
      v-if="reviewError"
      class="px-6 py-3 text-xs text-amber-800 bg-amber-50 border-b border-amber-200"
      role="alert"
    >
      {{ reviewError }}
    </div>

    <div
      v-if="resultStale && useRevisionDocument"
      class="px-6 py-3 text-xs text-amber-800 bg-amber-50 border-b border-amber-200"
      role="status"
    >
      审查条件已改变，当前展示上次审查的文档与意见。请重新审查后再处理修订。
    </div>
    <div
      v-if="useRevisionDocument"
      class="revision-document-surface"
      data-testid="tracked-document-pane"
      :aria-busy="!revisionDocumentLoaded"
      :data-rendered-revision="revisionRenderedVersion"
    >
      <iframe
        :src="revisionDocumentUrl"
        title="合同修订文档"
        sandbox="allow-scripts allow-same-origin allow-downloads"
      ></iframe>
    </div>
    <div
      v-else
      class="wb-document-grid"
      :class="{ 'is-comparing': showDocumentComparison }"
    >
      <div
        v-if="showDocumentComparison"
        class="wb-document-pane"
        data-testid="original-document-pane"
      >
        <div v-if="!reviewBaseline.sourceId" class="wb-pane-heading">
          原始文档<small>本次审查前的正文 · 只读</small>
        </div>
        <iframe
          v-if="reviewBaseline.sourceId"
          :src="
            '/static/document-preview.html?source=' +
            reviewBaseline.sourceId +
            '&readonly=1&pane=original&shared=1'
          "
          title="原始合同文档"
          sandbox="allow-scripts allow-same-origin allow-downloads"
          class="border-0"
        ></iframe>
        <div v-else class="wb-original-text">{{ reviewBaseline.text }}</div>
      </div>
      <div class="wb-document-pane" data-testid="revised-document-pane">
        <div
          v-if="
            showDocumentComparison &&
            (isReviewing ||
              viewMode !== 'original' ||
              !workspace.conditions.source_id)
          "
          class="wb-pane-heading"
        >
          修改后的文档<small>{{
            isReviewing
              ? reviewQueue?.status === "queued" ? "排队等待中…" : "正在生成修订建议…"
              : resultStale
                ? "当前编辑稿"
                : revisionScope === "all"
                  ? "全部建议稿 · 未自动采纳"
                  : "仅包含已采纳修改"
          }}</small>
        </div>
        <div
          v-if="showDocumentComparison && isReviewing"
          class="wb-review-placeholder"
        >
          <strong>{{ reviewQueue?.status === "queued" ? "审查任务排队中" : "正在审查合同" }}</strong><span>完成后在此展示修订后的文档</span>
        </div>
        <iframe
          v-else-if="viewMode === 'original' && workspace.conditions.source_id"
          :src="
            '/static/document-preview.html?source=' +
            workspace.conditions.source_id +
            '&pane=' +
            (showDocumentComparison ? 'revised' : 'original') +
            (resultStale ? '&edited=1' : '') +
            (showDocumentComparison && !resultStale && workspace.run && reviewResult
              ? '&run=' +
                workspace.run.id +
                '&scope=' +
                revisionScope +
                '&applied=' +
                encodeURIComponent((workspace.run.applied || []).join(','))
              : '')
          "
          title="合同原件预览"
          sandbox="allow-scripts allow-same-origin allow-downloads"
          class="flex-1 w-full border-0"
          style="min-height: 400px"
        ></iframe>
        <div v-else class="flex-1 overflow-y-auto p-8" id="contract-viewer">
          <div
            v-if="viewMode === 'raw'"
            class="max-w-4xl mx-auto bg-white border border-slate-200 rounded-xl p-10 shadow-sm"
          >
            <div
              v-for="(line, idx) in formattedLines"
              :key="idx"
              :id="'line-' + (idx + 1)"
              :class="[
                line.highlightClass,
                focusedIssueId && line.issueId === focusedIssueId
                  ? 'clause-active'
                  : '',
              ]"
              @click="line.issueId && selectIssue(line.issueId)"
              class="py-1 px-3 text-[15px] leading-relaxed transition-all cursor-pointer flex items-start space-x-4 hover:bg-slate-50/80"
            >
              <span
                class="w-8 shrink-0 text-right text-xs font-mono text-slate-400 select-none pt-1"
              >
                {{ idx + 1 }}
              </span>

              <div
                class="flex-1 text-slate-800 whitespace-pre-wrap font-normal"
              >
                {{ line.text }}
              </div>

              <span
                v-if="line.severity"
                class="shrink-0 text-xs px-2 py-0.5 rounded font-semibold uppercase self-center"
                :class="
                  line.severity === 'critical'
                    ? 'bg-red-100 text-red-700 border border-red-200'
                    : 'bg-amber-100 text-amber-700 border border-amber-200'
                "
              >
                {{ severityLabel(line.severity) }}
              </span>
            </div>

            <div
              v-if="!contractText.trim()"
              class="py-12 text-center text-slate-400"
            >
              <svg
                class="w-12 h-12 mx-auto mb-3 opacity-30 text-slate-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                stroke-width="2"
              >
                <path
                  d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
                ></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>
              <p class="text-base font-medium text-slate-600">
                在此处粘贴需要审查的合同全文
              </p>
              <p class="text-xs text-slate-400 mt-1">
                可返回首页上传文件，或使用示例合同熟悉流程
              </p>
              <button
                @click="openEditor"
                :disabled="
                  documentSaving ||
                  workspace.historical ||
                  workspace.loading ||
                  revisionBusy
                "
                class="mt-4 px-4 py-2 rounded-lg bg-blue-600 text-white text-xs"
              >
                粘贴合同正文
              </button>
            </div>
          </div>

          <div
            v-else-if="viewMode === 'comparison'"
            class="max-w-4xl mx-auto space-y-4"
          >
            <div
              v-for="diff in reviewResult?.differences || []"
              class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm"
            >
              <div class="flex justify-between mb-4 text-xs">
                <strong>{{
                  {
                    replace: "条款修改",
                    delete: "条款删除",
                    insert: "条款新增",
                  }[diff.change_type]
                }}</strong
                ><button @click="selectIssue(diff.id)" class="text-blue-600">
                  查看分析
                </button>
              </div>
              <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
                <div>
                  <h3 class="text-xs text-slate-500 mb-2">参考合同</h3>
                  <div
                    class="p-4 bg-red-50 border border-red-200 rounded-lg text-sm leading-relaxed whitespace-pre-wrap text-red-800"
                  >
                    {{ diff.original || "（无，此项为新增）" }}
                  </div>
                </div>
                <div>
                  <h3 class="text-xs text-slate-500 mb-2">待审合同</h3>
                  <div
                    class="p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm leading-relaxed whitespace-pre-wrap text-blue-900"
                  >
                    {{ diff.current || "（已删除）" }}
                  </div>
                </div>
              </div>
            </div>
            <div
              v-if="!reviewResult?.differences?.length"
              class="bg-white border border-slate-200 rounded-xl p-12 text-center text-sm text-slate-500"
            >
              两份合同未识别到文字差异
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
