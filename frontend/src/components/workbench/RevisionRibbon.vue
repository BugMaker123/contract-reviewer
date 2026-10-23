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
      <button v-for="mode in [{id:'markup',name:'全部修订标记'},{id:'original',name:'原始文本'},{id:'current',name:'最终清洁效果'}]" :key="mode.id" role="tab" :aria-selected="revisionMode === mode.id" :class="{active:revisionMode === mode.id}" class="wb-visible-view-tab" @click="revisionMode = mode.id">{{ mode.name }}</button>
      <details class="wb-menu revision-view-menu">
        <summary aria-label="更多文档视图"><span v-if="revisionMode === 'compare'">前后对比</span><ChevronIcon /></summary>
        <div class="wb-popover" @click="$event.target.closest('button') && $event.currentTarget.closest('details').removeAttribute('open')">
          <button
            v-for="mode in [
              { id: 'markup', name: '全部修订标记', label: '所有标记', description: '查看原文及修订痕迹' },
              { id: 'original', name: '原始文本', label: '原始稿', description: '查看本轮审查前的正文' },
              { id: 'current', name: '当前采纳稿', label: '当前稿', description: '仅合入已采纳的修改，隐藏痕迹' },
              { id: 'compare', name: '前后对比', label: '前后对比', description: '并排核对原文和全部建议' },
            ]"
            :key="mode.id"
            role="tab"
            :aria-label="mode.label"
            :aria-selected="revisionMode === mode.id"
            :class="{ 'is-selected': revisionMode === mode.id }"
            @click="revisionMode = mode.id"
          >
            <span><strong>{{ mode.name }}</strong><small>{{ mode.description }}</small></span><span class="view-check" aria-hidden="true">{{ revisionMode === mode.id ? '✓' : '' }}</span>
          </button>
        </div>
      </details>
    </div>
  </section>
</template>

<style scoped>
.prototype-view-switch .revision-view-tabs.revision-view-tabs { padding:0; border:0; background:transparent; }
.prototype-view-switch .revision-view-tabs .revision-view-menu > summary { display:flex; align-items:center; gap:10px; padding:8px 12px; border:1px solid #dce5f1; border-radius:8px; background:#fff; color:#334155; cursor:pointer; }
.revision-view-caption { color:#94a3b8; font-size:11px; }.revision-view-menu summary strong { color:#334155; font-size:12px; font-weight:600; }.revision-view-menu summary:hover { border-color:#a8c5f7; background:#f8faff; }
.prototype-view-switch .revision-view-menu .wb-popover { left:0; right:auto; top:calc(100% + 6px); width:252px; max-width:calc(100vw - 32px); padding:5px; gap:2px; border-radius:9px; box-sizing:border-box; }
.prototype-view-switch .revision-view-menu .wb-popover > button { display:flex; align-items:center; justify-content:space-between; width:100%; padding:9px 11px; min-height:0; line-height:1.5; border:0; border-radius:6px; background:transparent; text-align:left; color:#475569; }
.revision-view-menu .wb-popover > button:hover { background:#f1f5f9; }.revision-view-menu .wb-popover > button.is-selected { background:#eff6ff; color:#2563eb; }
.revision-view-menu button strong { display:block; font-size:12px; font-weight:600; }.revision-view-menu button small { display:block; margin-top:4px; font-size:10px; font-weight:400; color:#94a3b8; }.view-check { color:#2563eb; padding-left:12px; }
</style>

<style scoped>
.prototype-view-switch .revision-view-tabs.revision-view-tabs { display:flex; align-items:center; padding:3px; border:1px solid #dce5f1; border-radius:7px; background:#f1f5f9; }
.wb-visible-view-tab { border:0; background:transparent; color:#647b9e; padding:6px 9px; font-size:12px; border-radius:4px; white-space:nowrap; }
.wb-visible-view-tab.active { background:#fff; color:#2563eb; box-shadow:0 1px 3px #1e355012; }
.prototype-view-switch .revision-view-tabs .revision-view-menu > summary { padding:6px; border:0; background:transparent; }
</style>
