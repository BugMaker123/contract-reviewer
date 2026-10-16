<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div v-if="form.mode === 'checklist'" class="px-6 pb-5">
    <h2 class="text-sm font-semibold mb-3">配置业务分类与审查清单标准</h2>
    <label
      ><span class="label">业务分类</span
      ><select v-model="categoryFilter" class="field mb-3">
        <option value="">全部业务分类</option>
        <option v-for="row in categories" :value="row.id">
          {{ row.name }}
        </option>
      </select></label
    ><label
      ><span class="label">选用企业审查清单</span
      ><select
        v-model="form.checklist_id"
        @change="chooseChecklist"
        class="field"
      >
        <option value="">请选择已发布的清单</option>
        <option v-for="list in availableLists" :value="list.id">
          {{ list.name }} · v{{ list.version }} · {{ list.items.length }} 项
        </option>
      </select></label
    >
    <div class="text-xs text-slate-500 mt-2">
      本次任务会固定清单版本。<RouterLink to="/checklists" class="text-blue-600"
        >管理清单 →</RouterLink
      >
    </div>
  </div>
</template>
