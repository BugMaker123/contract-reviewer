<script>
import ChevronIcon from "../ChevronIcon.vue";
export default {
  components: { ChevronIcon },
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>
<template>
  <section class="prototype-view-switch" aria-label="文档修订工具栏">
    <div class="revision-view-tabs" role="tablist" aria-label="修订显示方式">
      <button
        v-for="mode in [
          { id: 'markup', name: '全部修订标记', label: '所有标记' },
          { id: 'original', name: '原始文本', label: '原始稿' },
          { id: 'current', name: '最终清洁效果', label: '当前稿' },
        ]"
        :key="mode.id"
        role="tab"
        :aria-label="mode.label"
        :aria-selected="revisionMode === mode.id"
        :class="{ active: revisionMode === mode.id }"
        @click="revisionMode = mode.id"
      >
        {{ mode.name }}
      </button>
      <details class="wb-menu">
        <summary aria-label="更多文档视图"><ChevronIcon /></summary>
        <div class="wb-popover">
          <button
            role="tab"
            :aria-selected="revisionMode === 'compare'"
            @click="revisionMode = 'compare'"
          >
            双栏对照
          </button>
        </div>
      </details>
    </div>
  </section>
</template>
