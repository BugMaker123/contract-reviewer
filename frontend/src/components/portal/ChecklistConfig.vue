<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div v-if="form.mode === 'checklist'" class="px-6 pb-5 checklist-picker">
    <label
      ><span class="label">业务分类</span
      ><select v-model="categoryFilter" class="field mb-3">
        <option value="">全部业务分类</option>
        <option v-for="row in categories" :value="row.id">
          {{ row.name }}
        </option>
      </select></label
    ><label
      ><span class="label">选择审查清单</span
      ><select
        v-model="form.checklist_id"
        @change="chooseChecklist"
        class="field"
      >
        <option value="">请选择可用清单</option>
        <option v-for="list in availableLists" :value="list.id">
          {{ list.name }} · {{ list.item_count ?? list.items?.length ?? 0 }} 条要求
        </option>
      </select></label
    >
    <p v-if="!availableLists.length" class="review-list-empty">当前分类暂无可用清单。可切换分类，或创建一份清单。</p>
    <div class="text-xs text-slate-500 mt-2">
      全文审查 + 清单专项核验，默认勾选全部要求。<RouterLink to="/checklists" class="text-blue-600"
        >管理清单</RouterLink
      >
    </div>
  </div>
</template>
