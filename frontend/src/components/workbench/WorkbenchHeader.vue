<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <header
    class="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shrink-0 z-20"
  >
    <div class="flex items-center space-x-3">
      <a
        href="/"
        @click.prevent="workspace.leaveFor('/')"
        class="flex items-center space-x-2"
        title="返回首页"
        ><span
          class="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white"
          >⚖</span
        ><strong class="text-slate-900">LexisGraph</strong></a
      >
      <details class="wb-menu">
        <summary>工作台 ▾</summary>
        <div class="wb-popover" style="left: 0; right: auto; width: 180px">
          <a href="/" @click.prevent="workspace.leaveFor('/')">返回首页</a
          ><a href="/records" @click.prevent="workspace.leaveFor('/records')"
            >审查记录</a
          >
        </div>
      </details>
    </div>

    <div class="flex items-center space-x-3">
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
        @click="showReportModal = true"
        :disabled="!reviewResult"
        class="flex items-center space-x-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg px-3.5 py-2 transition shadow-sm cursor-pointer"
      >
        <svg
          class="w-4 h-4 text-slate-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
          ></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="16" y1="13" x2="8" y2="13"></line>
          <line x1="16" y1="17" x2="8" y2="17"></line>
        </svg>
        <span>审查意见书</span>
      </button>

      <button
        @click="startReview"
        :disabled="
          isReviewing ||
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
    </div>
  </header>
</template>
