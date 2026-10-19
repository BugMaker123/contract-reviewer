<script>
import ChevronIcon from "../ChevronIcon.vue";
export default {
  components: { ChevronIcon },
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
      <h1 :title="contractTitle">{{ contractTitle }}</h1>
      <span class="prototype-status">{{
        isReviewing
          ? reviewQueue?.status === "queued" ? "排队中" : "审查中"
          : resultStale
            ? "需重新审查"
          : workspace.task?.status === "completed"
            ? "已完成"
            : reviewReady
              ? pendingRevisionCount + " 处待复核"
              : "待审查"
      }}</span>

    </div>
    <div class="prototype-nav-right">
      <button @click="openEditor" :disabled="documentSaving || workspace.historical || workspace.loading || revisionBusy || isReviewing || ['running','queued'].includes(workspace.task?.status)" class="wb-edit-action">编辑正文</button>
      <button @click="showReportModal = true" :disabled="!reviewResult" class="wb-report-action">审查意见书</button>
      <details class="wb-menu">
        <summary>审查设置 <ChevronIcon /></summary>
        <div class="wb-popover">
          <section>
            <h3>本次审查立场</h3>
            <select
              v-model="partyRole"
              aria-label="审查立场"
              :disabled="workspace.historical || workspace.loading || isReviewing || ['running','queued'].includes(workspace.task?.status)"
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
            <div class="wb-conditions-row">
              <span>{{ workspace.modeName }} · {{ workspace.conditions.scale }}</span>
              <button class="wb-conditions-edit" @click="workspace.showConditions = true">修改审查条件</button>
            </div>
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

      <button v-if="!isReviewing && workspace.task?.running_run" class="wb-background-progress" @click="startReview(workspace.task.running_run)">查看后台进度</button>
      <button
        @click="requestReview"
        :disabled="
          isReviewing ||
          revisionBusy ||
          workspace.loading ||
          workspace.historical ||
          ['running','queued'].includes(workspace.task?.status) ||
          !contractText.trim()
        "
        class="wb-review-action flex items-center space-x-2 text-sm font-semibold px-5 py-2 rounded-lg transition shadow-sm cursor-pointer"
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
          isReviewing ? reviewQueue?.status === "queued" ? "排队等待…" : "正在审查…" : reviewResult ? "重新审查" : "开始审查"
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
        class="wb-save-action"
      >
        {{ workspace.saving ? "保存中…" : "保存" }}
      </button>
      <details class="wb-menu wb-export-menu">
        <summary class="wb-export-action">导出 <ChevronIcon /></summary>
        <div class="wb-popover">
          <p class="text-xs text-slate-500 p-2">{{ contractTitle }} · {{ workspace.run ? '第 ' + workspace.run.number + ' 次审查' : '待审正文' }}</p>
          <button @click="workspace.exportDocument(true)" :disabled="documentSaving || workspace.loading">待审正文</button>
          <button v-for="option in [{id:'current',name:'当前采纳稿（清洁版）'},{id:'tracked',name:'当前采纳稿（修订痕迹）'},{id:'all',name:'全部建议稿（未自动采纳）'},{id:'report',name:'全部审查意见书'},{id:'applied_report',name:'已采纳意见书'}]" :key="option.id" :disabled="!workspace.run?.result || resultStale || workspace.saving" @click="workspace.exportScope = option.id; workspace.exportWord()">{{ option.name }}</button>
          <button :disabled="!workspace.run" @click="workspace.downloadAudit()">JSON 审核记录</button>
        </div>
      </details>

      <button @click="workspace.finish" :disabled="workspace.historical || resultStale || workspace.saving || workspace.task?.status !== 'pending_review'" :title="resultStale ? '请先重新审查当前正文' : ''" class="wb-finish-action">{{ workspace.task?.status === 'completed' ? '已完成审核' : '完成审核' }}</button>
    </div>
  </header>
  <div v-if="showReviewBaseline" class="fixed inset-0 z-50 bg-slate-900/40 flex items-center justify-center p-6">
    <section class="bg-white rounded-xl p-6 w-full max-w-lg space-y-4" role="dialog" aria-modal="true" aria-label="选择重新审查稿件">
      <h2 class="font-semibold">重新审查哪个稿件？</h2>
      <label class="block text-sm"><input type="radio" v-model="reviewBaselineChoice" value="accepted" :disabled="resultStale || !appliedIssueIds.length" /> 当前采纳稿（合入 {{ appliedIssueIds.length }} 项已采纳修订）</label>
      <label class="block text-sm"><input type="radio" v-model="reviewBaselineChoice" value="task" /> {{ resultStale ? '当前已保存正文（含正文编辑）' : '本轮审查原文（不合入本轮采纳修订）' }}</label>
      <p class="text-xs text-slate-500">新审查独立生成版本，保留旧版输入、意见、采纳记录与确认理由。这里的原文是本轮审查的基线，不一定是首次上传稿。</p>
      <p v-if="resultStale" class="text-xs text-amber-700">正文或条件已改变，请针对当前已保存正文审查。</p>
      <div class="flex justify-end gap-3"><button @click="showReviewBaseline = false" class="button">取消</button><button @click="confirmReviewBaseline" class="button primary">确认并开始审查</button></div>
    </section>
  </div>
</template>

<style scoped>
.wb-conditions-row { display:flex; align-items:center; justify-content:space-between; gap:16px; }
.wb-conditions-row > .wb-conditions-edit { width:auto; flex-shrink:0; margin-left:auto; padding:4px 0; color:#2563eb; font-weight:700; text-align:right; background:transparent; }
.wb-conditions-row > .wb-conditions-edit:hover { color:#1d4ed8; text-decoration:underline; }
</style>
