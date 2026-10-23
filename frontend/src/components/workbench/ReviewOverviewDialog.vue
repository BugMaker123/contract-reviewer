<script setup>
import { onMounted, ref } from 'vue';
import ReviewOverview from './ReviewOverview.vue';
defineProps({ context: { type:Object, required:true } });
const emit = defineEmits(['close']);
const dialog = ref(null);
onMounted(() => dialog.value.showModal());
</script>
<template>
  <dialog ref="dialog" class="wb-overview-dialog" aria-labelledby="review-overview-title" @close="emit('close')" @click="($event.target === dialog) && dialog.close()">
    <header class="wb-overview-dialog-heading">
      <h2 id="review-overview-title">审查结论与执行记录</h2>
      <button autofocus aria-label="关闭审查结论与执行记录" @click="dialog.close()">关闭</button>
    </header>
    <div class="wb-overview-dialog-body"><ReviewOverview :context="context" /></div>
  </dialog>
</template>
<style scoped>
.wb-overview-dialog { width:min(820px,calc(100vw - 48px)); max-height:85vh; padding:0; border:1px solid #dce5f1; border-radius:12px; color:#1e293b; background:#fff; box-shadow:0 24px 80px #0f172a33; }
.wb-overview-dialog::backdrop { background:#0f172a80; }
.workbench-view .wb-overview-dialog-heading { display:flex; align-items:center; justify-content:space-between; padding:16px 20px !important; min-height:60px !important; height:auto !important; border-bottom:1px solid #e2e8f0; }
.wb-overview-dialog-heading h2 { margin:0; font-size:16px; font-weight:600; }
.wb-overview-dialog-heading button { padding:6px 12px; border:1px solid #dce5f1; border-radius:6px; background:#fff; font-size:12px; cursor:pointer; }
.wb-overview-dialog-body { overflow:auto; max-height:calc(85vh - 70px); padding:16px 20px; }
.wb-overview-dialog-body :deep(.wb-functional-overview) { margin:0; border:0; background:transparent; }
.wb-overview-dialog-body :deep(.overview-body) { padding:0; }
</style>
