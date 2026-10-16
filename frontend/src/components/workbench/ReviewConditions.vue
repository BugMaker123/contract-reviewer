<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div
    v-if="workspace.showConditions"
    class="fixed inset-0 z-50 bg-slate-900/40 flex items-center justify-center p-6"
  >
    <div
      class="bg-white rounded-xl p-6 w-full max-w-2xl space-y-4 shadow-xl max-h-[90vh] overflow-y-auto"
    >
      <div class="flex justify-between">
        <h3 class="font-semibold">审查条件 · {{ workspace.modeName }}</h3>
        <button @click="workspace.showConditions = false">✕</button>
      </div>
      <p class="text-xs text-slate-500">
        修改条件后需要重新审查，原结果保留为历史版本。
      </p>
      <label class="block text-xs text-slate-600"
        >谈判尺度<select
          v-model="workspace.conditions.scale"
          :disabled="workspace.historical"
          class="block mt-2 w-full p-2 border rounded-lg"
        >
          <option>中立</option>
          <option>强势</option>
          <option>弱势</option>
        </select></label
      ><label class="block text-xs text-slate-600"
        >交易背景<textarea
          v-model="workspace.conditions.background"
          :disabled="workspace.historical"
          class="block mt-2 w-full p-3 h-24 border rounded-lg"
        ></textarea></label
      ><label class="block text-xs text-slate-600"
        >重点要求<textarea
          v-model="workspace.conditions.focus"
          :disabled="workspace.historical"
          class="block mt-2 w-full p-3 h-20 border rounded-lg"
        ></textarea>
      </label>
      <label class="block text-xs text-slate-600">执行方式
        <select v-model="workspace.conditions.execution" :disabled="workspace.historical" class="field"><option value="plan">按审查计划执行</option><option value="react">工具辅助证据核验（最多三轮）</option></select>
      </label>
      <div v-if="workspace.conditions.requirements?.length" class="space-y-3">
        <h4 class="text-xs font-semibold">已确认的逐项要求（随本次审查留档）</h4>
        <div v-for="item in workspace.conditions.requirements" :key="item.id" class="text-xs border rounded p-3">
          <p>{{ item.source }} · {{ item.priority === 'required' ? '硬性要求' : '优先偏好' }}</p>
          <textarea v-model="item.text" :disabled="workspace.historical" class="field mt-2" @input="workspace.conditions.references.filter(ref => ref.name === item.source).forEach(ref => ref.confirmed = false)"></textarea>
        </div>
      </div>
      <div v-if="workspace.conditions.checklist" class="text-xs text-slate-500">
        清单：{{ workspace.conditions.checklist.name }} · v{{
          workspace.conditions.checklist.version
        }}（固定本次版本）
      </div>
      <details
        v-for="material in workspace.conditions.references"
        class="text-xs text-slate-500"
      >
        <summary class="cursor-pointer">参考资料：{{ material.name }}</summary>
        <pre class="whitespace-pre-wrap mt-2">{{ material.text }}</pre>
        <label v-if="material.kind === 'policy'" class="block mt-2"><input type="checkbox" v-model="material.confirmed" :disabled="workspace.historical" /> 已核对并确认上述公司制度要求</label>
      </details>
      <details
        v-if="workspace.conditions.reference_text"
        class="text-xs text-slate-500"
      >
        <summary class="cursor-pointer">查看参考合同</summary>
        <pre class="whitespace-pre-wrap mt-2">{{
          workspace.conditions.reference_text
        }}</pre>
      </details>
      <button
        @click="
          workspace.showConditions = false;
          workspace.save();
        "
        :disabled="workspace.historical"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg text-xs"
      >
        保存审查条件
      </button>
    </div>
  </div>
</template>
