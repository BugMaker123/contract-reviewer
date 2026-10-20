<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>
<template>
  <nav class="catalog-pagination" aria-label="列表分页">
    <span role="status">共 {{ total }} 条 · 第 {{ currentPage }} / {{ totalPages }} 页</span>
    <div>
      <select v-model.number="pageSize" class="field" aria-label="每页条数" :disabled="fetching">
        <option :value="10">10 条 / 页</option><option :value="20">20 条 / 页</option><option :value="50">50 条 / 页</option>
      </select>
      <button class="button" @click="goPage(currentPage - 1)" :disabled="fetching || currentPage <= 1">上一页</button>
      <button class="button" @click="goPage(currentPage + 1)" :disabled="fetching || currentPage >= totalPages">下一页</button>
    </div>
  </nav>
</template>
