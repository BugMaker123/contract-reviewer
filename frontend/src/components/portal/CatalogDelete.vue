<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>
<template>
  <div v-if="deleteTarget" class="modal" @keydown.esc="!busy && (deleteTarget = null)">
    <section class="modal-panel max-w-lg p-6 space-y-4" role="alertdialog" aria-modal="true" aria-labelledby="delete-title">
      <h2 id="delete-title" class="font-bold">删除{{ page === 'categories' ? '业务分类' : '审查清单' }}</h2>
      <p class="text-sm">确定删除「{{ deleteTarget.name }}」？此操作无法撤销。</p>
      <p class="text-xs text-slate-500">{{ page === 'categories' ? '分类下有清单时无法删除，请先迁移或删除关联清单（含已归档清单）。' : '已创建审查任务使用的清单快照会保留，不受影响。' }}</p>
      <p v-if="deleteError" role="alert" class="text-xs text-red-700">{{ deleteError }}</p>
      <div class="flex justify-end gap-3"><button class="button" :disabled="busy" @click="deleteTarget = null">取消</button><button class="button danger" :disabled="busy" @click="confirmDelete">{{ busy ? '删除中…' : '确认删除' }}</button></div>
    </section>
  </div>
</template>
