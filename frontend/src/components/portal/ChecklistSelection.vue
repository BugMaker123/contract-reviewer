<script>
export default {
  props:{context:{type:Object,required:true}},
  setup(props) {
    const toggleItem = (id,checked) => {
      const form = props.context.form;
      const ids = new Set(form.checklist_item_ids ?? props.context.selectedList.value.items.map(item => item.id));
      if (checked) ids.add(id); else ids.delete(id);
      form.checklist_item_ids = [...ids];
    };
    return {...props.context,toggleItem};
  },
};
</script>
<template>
  <details v-if="form.mode === 'checklist' && selectedList" :key="selectedList.id" class="checklist-selection">
    <summary class="checklist-selection-summary"><strong>调整检查项（默认全选）</strong><span class="pill blue">已勾选 {{ form.checklist_item_ids?.length ?? selectedList.items.length }} 项</span></summary>
    <div class="selection-heading"><span>本次检查范围</span><button class="text-xs text-blue-600" @click="form.checklist_item_ids = (form.checklist_item_ids?.length ?? selectedList.items.length) === selectedList.items.length ? [] : selectedList.items.map(item => item.id)">{{ (form.checklist_item_ids?.length ?? selectedList.items.length) === selectedList.items.length ? '取消全选' : '全选' }}</button></div>
    <div class="checklist-options">
      <label v-for="item in selectedList.items" :key="item.id" class="checklist-option" :class="{selected:form.checklist_item_ids === null || form.checklist_item_ids.includes(item.id)}"><input type="checkbox" :checked="form.checklist_item_ids === null || form.checklist_item_ids.includes(item.id)" @change="toggleItem(item.id,$event.target.checked)" /><div><strong v-if="item.title !== item.requirement && item.title !== item.requirement.slice(0,60)">{{ item.title }}</strong><p>{{ item.requirement }}</p></div></label>
    </div>
  </details>
</template>
