<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div v-if="checklistEditor" class="modal">
    <div class="modal-panel max-w-4xl">
      <div
        class="sticky top-0 bg-white z-10 p-5 border-b border-slate-200 flex justify-between"
      >
        <h2 class="text-base font-bold">
          {{ checklistEditor.id ? "编辑审查清单" : "创建审查清单" }}
        </h2>
        <button @click="checklistEditor = null" aria-label="关闭清单编辑器">
          ✕
        </button>
      </div>
      <div class="p-6 space-y-5">
        <div
          v-if="modalError"
          role="alert"
          class="p-3 text-xs text-red-700 bg-red-50 rounded-lg"
        >
          {{ modalError }}
        </div>
        <div class="grid grid-cols-2 gap-4">
          <label
            ><span class="label">清单名称</span
            ><input
              v-model="checklistEditor.name"
              class="field"
              placeholder="如：采购合同企业标准" /></label
          ><label
            ><span class="label">适用合同类型</span
            ><input v-model="checklistEditor.contract_type" class="field"
          /></label>
        </div>
        <label class="block"
          ><span class="label">绑定业务分类</span
          ><select v-model="checklistEditor.category_id" class="field">
            <option :value="null">未分类</option>
            <option v-for="row in categories" :value="row.id">
              {{ row.name }}
            </option>
          </select></label
        ><label class="block"
          ><span class="label">说明</span
          ><input
            v-model="checklistEditor.description"
            class="field"
            placeholder="适用范围、业务部门或特殊要求"
        /></label>
        <div class="flex justify-between items-center">
          <h3 class="text-sm font-semibold">检查要求</h3>
          <div class="flex gap-2">
            <button
              @click="$refs.checklistInput.click()"
              class="button"
              :disabled="importing"
            >
              从文件提取草稿</button
            ><input
              type="file"
              ref="checklistInput"
              class="hidden"
              accept=".docx,.pdf,.txt"
              @change="importDocument($event, 'checklist')"
            /><button @click="addChecklistItem" class="button soft">
              ＋ 添加检查项
            </button>
          </div>
        </div>
        <p class="text-xs text-slate-500">
          文字规则按明确词语匹配；语义核验需要模型，无法判定时进入待人工确认。
        </p>
        <article
          v-for="(item, index) in checklistEditor.items"
          :key="item.id"
          class="border border-slate-200 rounded-xl p-4 space-y-3"
        >
          <div class="flex gap-3 items-center">
            <span class="pill">{{ index + 1 }}</span
            ><input
              v-model="item.title"
              class="field"
              placeholder="检查项标题"
              aria-label="检查项标题"
            /><button
              @click="checklistEditor.items.splice(index, 1)"
              class="text-xs text-slate-400"
            >
              移除
            </button>
          </div>
          <textarea
            v-model="item.requirement"
            class="field h-20"
            placeholder="描述具体判断要求，避免只写一个关键词…"
            aria-label="检查项要求"
          ></textarea>
          <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
            <label
              ><span class="label">核验方式</span
              ><select v-model="item.operator" class="field">
                <option value="semantic">语义核验</option>
                <option value="contains_all">必须包含全部文字</option>
                <option value="contains_any">至少包含一项文字</option>
                <option value="forbidden">不得包含这些文字</option>
              </select></label
            ><label
              ><span class="label">未通过风险等级</span
              ><select v-model="item.severity" class="field">
                <option value="critical">重大风险</option>
                <option value="warning">一般风险</option>
                <option value="info">优化建议</option>
              </select></label
            ><label v-if="item.operator !== 'semantic'"
              ><span class="label">匹配文字（逗号分隔）</span
              ><input
                v-model="item.keywordText"
                class="field"
                placeholder="如：付款,验收"
            /></label>
          </div>
          <input
            v-model="item.suggestion"
            class="field"
            placeholder="未通过时的处理建议（可选）"
          />
        </article>
        <div class="flex justify-end gap-3">
          <button
            @click="saveChecklist(false)"
            :disabled="busy || importing"
            class="button"
          >
            保存草稿</button
          ><button
            @click="saveChecklist(true)"
            :disabled="busy || importing"
            class="button primary"
          >
            发布清单
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
