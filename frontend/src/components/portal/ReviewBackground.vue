<script>
export default {
  props: { context: { type: Object, required: true }, expanded: Boolean },
  setup: (props) => props.context,
};
</script>

<template>
  <details :open="expanded" class="border-t border-slate-200 px-6 py-4">
    <summary class="cursor-pointer text-xs font-semibold text-slate-600">
      补充交易背景、重点要求{{ form.mode === "deep" ? "与参考资料" : "" }}
    </summary>
    <div class="mt-4 space-y-4">
      <label class="block"
        ><span class="label">交易背景</span
        ><textarea
          v-model="form.background"
          class="field h-24"
          placeholder="业务目的、交易安排、已沟通的条件…"
        ></textarea></label
      ><label class="block"
        ><span class="label">重点要求</span
        ><textarea
          v-model="form.focus"
          class="field h-20"
          placeholder="本次重点关注或不可接受的条件…"
        ></textarea>
      </label>
      <div v-if="form.mode === 'deep'">
        <div class="flex items-center justify-between mb-3">
          <span class="label mb-0">参考资料（最多 5 份，合计 5 万字）</span
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
              @click="form.references.splice(index, 1)"
              class="text-slate-400"
            >
              移除
            </button>
          </div>
          <details class="mt-2">
            <summary class="text-blue-600 cursor-pointer">核对内容</summary>
            <textarea
              v-model="material.text"
              class="field mt-2 h-28"
            ></textarea>
          </details>
        </div>
      </div>
    </div>
  </details>
</template>
