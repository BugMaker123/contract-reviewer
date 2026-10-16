<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div
    v-if="categoryEditor"
    class="modal"
    @keydown.esc="!busy && (categoryEditor = null)"
  >
    <form
      @submit.prevent="saveCategory"
      class="modal-panel max-w-lg p-6 space-y-4"
      role="dialog"
      aria-modal="true"
      aria-label="业务分类编辑"
    >
      <div class="flex justify-between">
        <h2 class="font-bold">
          {{ categoryEditor.id ? "编辑业务分类" : "新增业务分类" }}
        </h2>
        <button
          type="button"
          @click="categoryEditor = null"
          aria-label="关闭分类编辑"
        >
          ✕
        </button>
      </div>
      <p v-if="modalError" role="alert" class="text-xs text-red-700">
        {{ modalError }}
      </p>
      <label class="block"
        ><span class="label">分类名称</span
        ><input
          required
          maxlength="100"
          v-model="categoryEditor.name"
          class="field" /></label
      ><label class="block"
        ><span class="label">分类编码</span
        ><input
          aria-label="分类编码"
          required
          pattern="[A-Z][A-Z0-9_]{1,49}"
          v-model="categoryEditor.code"
          class="field"
          placeholder="如 TECH_DEV"
        /><span class="text-xs text-slate-500"
          >2–50 位大写字母、数字或下划线，以字母开头</span
        ></label
      ><label class="block"
        ><span class="label">说明与适用范围</span
        ><textarea
          maxlength="1000"
          v-model="categoryEditor.description"
          class="field"
        ></textarea></label
      ><label class="block"
        ><span class="label">排序号</span
        ><input
          type="number"
          min="0"
          max="9999"
          required
          v-model.number="categoryEditor.sort_order"
          class="field"
      /></label>
      <div class="flex justify-end">
        <button :disabled="busy" class="button primary">
          {{ busy ? "保存中…" : "保存分类" }}
        </button>
      </div>
    </form>
  </div>
</template>
