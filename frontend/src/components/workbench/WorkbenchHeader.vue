<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>
<template>
  <header
    class="prototype-navbar"
    @click="
      $event.target
        .closest('button')
        ?.closest('details.wb-menu')
        ?.removeAttribute('open')
    "
  >
    <div class="prototype-nav-left">
      <a
        href="/records"
        @click.prevent="workspace.leaveFor('/records')"
        class="prototype-back"
        title="返回审查记录"
        aria-label="返回审查记录"
        >←</a
      >
      <h1 :title="contractTitle">{{ contractTitle }}</h1>
      <span class="prototype-status">{{
        isReviewing
          ? "审查中"
          : workspace.task?.status === "completed"
            ? "已完成"
            : reviewReady
              ? pendingRevisionCount + " 处待复核"
              : "待审查"
      }}</span>

    </div>
    <div class="prototype-nav-right">
      <button @click="showReportModal = true" :disabled="!reviewResult" class="wb-report-action">审查意见书</button>
      <details class="wb-menu">
        <summary>审查设置 ▾</summary>
        <div class="wb-popover">
          <section>
            <h3>本次审查立场</h3>
            <select
              v-model="partyRole"
              aria-label="审查立场"
              :disabled="workspace.historical || workspace.loading"
              class="border border-slate-200 rounded-lg px-3 py-2"
            >
              <option value="乙方(卖方/开发方/服务方)">
                乙方 · 供应商 / 服务方
              </option>
              <option value="甲方(买方/采购方/委托方)">
                甲方 · 买方 / 委托方
              </option>
              <option value="中立审慎">中立审查</option>
            </select>
          </section>
          <section>
            <h3>审查方式与条件</h3>
            <span
              >{{ workspace.modeName }} · {{ workspace.conditions.scale }}</span
            ><button @click="workspace.showConditions = true">
              修改审查条件
            </button>
          </section>
          <section>
            <h3>审查模型</h3>
            <div
              class="flex items-center space-x-1.5 bg-slate-100 border border-slate-200 rounded-lg px-2.5 py-1.5"
            >
              <span class="text-slate-500 text-xs">模型:</span>
              <select
                v-model="selectedModel"
                class="bg-transparent text-xs text-slate-800 font-semibold outline-none cursor-pointer"
              >
                <option
                  v-if="
                    ![
                      'deepseek-v4-flash',
                      'deepseek-chat',
                      'deepseek-reasoner',
                      'gpt-4o',
                      'qwen-plus',
                      'custom',
                    ].includes(selectedModel)
                  "
                  :value="selectedModel"
                >
                  {{ selectedModel }}
                </option>
                <option value="deepseek-v4-flash">DeepSeek-V4 Flash</option>
                <option value="deepseek-chat">DeepSeek-V3</option>
                <option value="deepseek-reasoner">
                  DeepSeek-R1 (深度推理)
                </option>
                <option value="gpt-4o">GPT-4o (OpenAI)</option>
                <option value="qwen-plus">通义千问 Qwen-Plus</option>
                <option value="custom">自定义端点...</option>
              </select>
              <button
                @click="openModelModal"
                title="设置 API Key 与 Base URL"
                class="text-slate-400 hover:text-blue-600 transition ml-1 cursor-pointer"
              >
                <svg
                  class="w-3.5 h-3.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                >
                  <circle cx="12" cy="12" r="3"></circle>
                  <path
                    d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"
                  ></path>
                </svg>
              </button>
            </div>
          </section>
        </div>
      </details>

      <button
        @click="startReview"
        :disabled="
          isReviewing ||
          revisionBusy ||
          workspace.loading ||
          workspace.historical ||
          workspace.task?.status === 'running' ||
          !contractText.trim()
        "
        class="flex items-center space-x-2 text-sm font-semibold px-5 py-2 rounded-lg transition shadow-sm cursor-pointer"
        :class="
          isReviewing
            ? 'bg-blue-400 text-white cursor-wait'
            : 'bg-blue-600 hover:bg-blue-700 text-white shadow-blue-600/20 active:scale-95'
        "
      >
        <svg
          v-if="isReviewing"
          class="animate-spin w-4 h-4 text-white"
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
        <svg
          v-else
          class="w-4 h-4 text-white"
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
        <span>{{
          isReviewing ? "正在审查…" : reviewResult ? "重新审查" : "开始审查"
        }}</span>
      </button>
      <button
        @click="saveDocument"
        :disabled="
          documentSaving ||
          workspace.saving ||
          workspace.historical ||
          revisionBusy
        "
        class="px-3 py-2 text-blue-600"
      >
        {{ workspace.saving ? "保存中…" : "保存" }}
      </button>
      <button
        @click="
          reviewReady && revisionMode !== 'compare'
            ? exportReviewDocument()
            : exportDocument()
        "
        :disabled="documentSaving || workspace.loading || !contractText.trim()"
        :title="documentCompare ? '导出右侧显示的文档' : '导出当前合同'"
        class="px-3 py-2 rounded-lg border border-slate-200 text-slate-700"
      >
        导出
      </button>

      <button @click="openEditor" :disabled="documentSaving || workspace.historical || workspace.loading || revisionBusy">编辑正文</button>
      <button @click="workspace.finish" :disabled="workspace.historical || resultStale || workspace.saving || workspace.task?.status !== 'pending_review'" :title="resultStale ? '请先重新审查当前正文' : ''" class="wb-finish-action">{{ workspace.task?.status === 'completed' ? '已完成审核' : '完成审核' }}</button>
    </div>
  </header>
</template>
