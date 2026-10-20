<script>
export default {
  props: { context: { type: Object, required: true }, expanded: Boolean, hideFocus: Boolean },
  setup: (props) => props.context,
};
</script>

<template>
  <details :open="expanded" class="border-t border-slate-200 px-6 py-4">
    <summary class="cursor-pointer text-xs font-semibold text-slate-600">
      {{ hideFocus ? '补充交易背景与参考资料' : '补充交易背景、重点要求与资料' }}
    </summary>
    <div class="mt-4 space-y-4">
      <label class="block"
        ><span class="label">交易背景</span
        ><textarea
          v-model="form.background"
          class="field h-24"
          placeholder="业务目的、交易安排、已沟通的条件…"
        ></textarea></label
      ><label v-if="!hideFocus" class="block"
        ><span class="label">重点要求</span
        ><textarea
          v-model="form.focus"
          class="field h-20"
          placeholder="本次重点关注或不可接受的条件…"
        ></textarea>
      </label>
      <div>
        <div class="flex items-center justify-between mb-3">
          <span class="label mb-0">公司制度／参考资料（最多 5 份，合计 5 万字）</span
          ><button
            @click="$refs.materialInput.click()"
            :disabled="importing || form.references.length >= 5"
            class="button"
          >
            添加资料</button
          ><input
            ref="materialInput"
            type="file"
            class="hidden"
            accept=".docx,.pdf,.txt"
            @change="importDocument($event, 'material')"
          />
        </div>
        <div
          v-for="(material, index) in form.references"
          class="border border-slate-200 rounded-lg p-3 mt-2 text-xs"
        >
          <div class="flex justify-between">
            <span>{{ material.name }} · {{ material.text.length }} 字</span
            ><button
              @click="removeMaterial(index)"
              class="text-slate-400"
            >
              移除
            </button>
          </div>
          <label class="block mt-2">资料用途
            <select v-model="material.kind" class="field" @change="material.confirmed = false">
              <option value="reference">背景参考</option><option value="policy">公司制度（逐项核验）</option>
            </select>
          </label>
          <div v-if="material.kind === 'policy'" class="mt-2 space-y-2">
            <button class="button" :disabled="busy" @click="extractRequirements(material)">提取审核要求</button>
            <button class="button" @click="addRequirement(material.name)">手动录入要求</button>
            <label class="block"><input type="checkbox" v-model="material.confirmed" :disabled="!form.requirements.some(item => item.source === material.name && item.text.trim())" /> 我已核对下方要求，确认完整准确</label>
          </div>
          <details class="mt-2">
            <summary class="text-blue-600 cursor-pointer">核对内容</summary>
            <textarea
              v-model="material.text"
              @input="material.confirmed = false"
              class="field mt-2 h-28"
            ></textarea>
          </details>
        </div>
      </div>
      <div class="space-y-3">
        <div class="flex justify-between"><span class="label">逐项审核要求</span><button class="button" @click="addRequirement()">添加要求</button></div>
        <div v-for="(item, index) in form.requirements" :key="item.id" class="border rounded-lg p-3 space-y-2">
          <span class="text-xs text-slate-500">{{ item.source }}</span>
          <textarea v-model="item.text" class="field" placeholder="每条填写一项可核验的要求" @input="form.references.filter(ref => ref.name === item.source).forEach(ref => ref.confirmed = false)"></textarea>
          <select v-model="item.priority" class="field" @change="form.references.filter(ref => ref.name === item.source).forEach(ref => ref.confirmed = false)"><option value="required">硬性要求</option><option value="preferred">优先偏好</option></select>
          <p v-if="item.evidence" class="text-xs text-slate-500">制度原文：{{ item.evidence }}</p>
          <button class="button" @click="form.references.filter(ref => ref.name === item.source).forEach(ref => ref.confirmed = false); form.requirements.splice(index, 1)">移除要求</button>
        </div>
        <label class="block"><span class="label">执行方式</span><select v-model="form.execution" class="field"><option value="plan">按审查计划执行（默认）</option><option value="react">按计划审查并进行工具辅助证据核验</option></select></label>
      </div>
    </div>
  </details>
</template>
