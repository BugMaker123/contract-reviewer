<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div
    v-if="showModelModal"
    class="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4"
  >
    <div
      class="bg-white border border-slate-200 rounded-xl w-full max-w-md shadow-xl p-6 space-y-4"
    >
      <div
        class="flex items-center justify-between border-b border-slate-100 pb-3"
      >
        <h3 class="text-base font-bold text-slate-900">大模型端点动态配置</h3>
        <button
          @click="showModelModal = false"
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

      <div class="space-y-3 text-xs">
        <div>
          <label class="block text-slate-700 font-semibold mb-1"
            >模型标识 (Model Identifier)</label
          >
          <input
            v-model="modelConfig.model_name"
            type="text"
            placeholder="deepseek-v4-flash 或 deepseek-chat"
            class="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 outline-none focus:border-blue-500 font-mono"
          />
          <p class="text-[11px] text-slate-400 mt-1">
            支持 DeepSeek 官方各版本、OpenAI、通义千问等
          </p>
        </div>

        <div>
          <label class="block text-slate-700 font-semibold mb-1"
            >API 基础端点 (Base URL)</label
          >
          <input
            v-model="modelConfig.base_url"
            type="text"
            placeholder="https://api.deepseek.com/v1"
            class="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 outline-none focus:border-blue-500 font-mono"
          />
        </div>

        <div>
          <label class="block text-slate-700 font-semibold mb-1"
            >API Key 授权凭据</label
          >
          <input
            v-model="modelConfig.api_key"
            type="password"
            placeholder="sk-..."
            class="w-full border border-slate-300 rounded-lg px-3 py-2 text-slate-800 outline-none focus:border-blue-500 font-mono"
          />
          <p class="text-[11px] text-slate-500 mt-1">
            配置保存在当前浏览器。留空时使用服务端配置；深度审查需要有效模型配置。
          </p>
        </div>

        <div>
          <label
            for="model-retries"
            class="block text-slate-700 font-semibold mb-1"
            >最大重试次数</label
          ><input
            id="model-retries"
            v-model.number="modelConfig.max_retries"
            type="number"
            min="0"
            max="10"
            step="1"
            class="w-full border border-slate-300 rounded-lg px-3 py-2"
          />
          <p class="text-[11px] text-slate-500 mt-1">
            默认 3
            次，不含首次请求。格式错误会反馈给模型修正，网络异常会等待后重试。
          </p>
        </div>

        <div
          v-if="testResult"
          class="p-3 rounded-lg text-xs"
          :class="
            testResult.success
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          "
        >
          {{ testResult.message }}
        </div>
      </div>

      <div
        class="flex items-center justify-between pt-3 border-t border-slate-100"
      >
        <button
          @click="testModelConnection"
          :disabled="isTestingModel"
          class="px-3.5 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 text-xs text-slate-700 font-medium transition cursor-pointer"
        >
          {{ isTestingModel ? "连接测试中..." : "测试连通性" }}
        </button>
        <div class="flex items-center space-x-2">
          <button
            @click="showModelModal = false"
            class="px-3 py-1.5 rounded-lg text-xs text-slate-500 hover:text-slate-700 cursor-pointer"
          >
            取消
          </button>
          <button
            @click="saveModelConfig"
            class="px-4 py-1.5 rounded-lg bg-blue-600 text-white font-semibold text-xs hover:bg-blue-700 transition cursor-pointer"
          >
            保存配置
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
