<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div v-if="showModel" class="modal">
    <div class="modal-panel max-w-md p-6 space-y-4">
      <div class="flex justify-between">
        <h2 class="font-bold">模型配置</h2>
        <button @click="showModel = false" aria-label="关闭模型配置">✕</button>
      </div>
      <label class="block"
        ><span class="label">模型名称</span
        ><input v-model="model.model_name" class="field" /></label
      ><label class="block"
        ><span class="label">API 端点</span
        ><input v-model="model.base_url" class="field" /></label
      ><label class="block"
        ><span class="label">API Key</span
        ><input
          type="password"
          v-model="model.api_key"
          class="field"
          autocomplete="off"
      /></label>
      <p class="text-xs text-slate-500">
        配置保存在当前浏览器。留空时使用服务端配置；无模型时可使用快速规则检查。
      </p>
      <p
        v-if="modelTest"
        class="text-xs"
        :class="modelTest.success ? 'text-emerald-700' : 'text-red-700'"
      >
        {{ modelTest.message }}
      </p>
      <div class="flex justify-between">
        <button @click="testModel" :disabled="busy" class="button">
          测试连接</button
        ><button @click="saveModel" class="button primary">保存配置</button>
      </div>
    </div>
  </div>
</template>
