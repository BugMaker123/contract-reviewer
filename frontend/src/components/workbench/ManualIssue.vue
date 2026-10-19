<script setup>
import { ref, reactive } from 'vue';
const props = defineProps({context:{type:Object,required:true}});
const open = ref(false);
const draft = reactive({title:'',evidence:'',analysis:'',suggestion:'',severity:'warning'});
const save = async () => { if (await props.context.workspace.addManualIssue({...draft})) { open.value = false; Object.assign(draft,{title:'',evidence:'',analysis:'',suggestion:'',severity:'warning'}); } };
</script>
<template>
  <div class="wb-manual-issue">
    <button :disabled="!context.reviewReady.value || context.workspace.historical || context.resultStale.value" @click="open = !open">{{ open ? '收起人工意见' : '＋ 添加人工意见' }}</button>
    <form v-if="open" @submit.prevent="save" class="wb-functional-overview">
      <label>意见标题<input v-model="draft.title" required maxlength="200" /></label>
      <label>风险等级<select v-model="draft.severity"><option value="critical">重大风险</option><option value="warning">一般风险</option><option value="info">优化建议</option></select></label>
      <label>原文证据<textarea v-model="draft.evidence" maxlength="20000" placeholder="粘贴合同中可唯一定位的原文；缺失条款可留空" /></label>
      <label>风险说明<textarea v-model="draft.analysis" required maxlength="5000" /></label>
      <label>建议修订<textarea v-model="draft.suggestion" maxlength="20000" placeholder="填写后可采纳为替换条款；无原文证据时作为新增条款" /></label>
      <button :disabled="context.workspace.manualBusy" type="submit">{{ context.workspace.manualBusy ? '正在保存…' : '保存人工意见' }}</button>
    </form>
  </div>
</template>
