<script setup>
import { computed, ref, watch, nextTick } from 'vue';
import { operationManual } from '../../content/operationManual.js';
const props = defineProps({ context: { type: Object, required: true } });
const selected = ref('start'), dialog = ref(null), article = ref(null);
const current = computed(() => operationManual.find(item => item.id === selected.value) || operationManual[0]);
let previousFocus;
const close = () => { props.context.showHelp.value = false; };
watch(() => props.context.showHelp.value, async (open) => {
  if (open) { previousFocus = document.activeElement; selected.value = 'start'; await nextTick(); dialog.value?.focus(); }
  else previousFocus?.focus?.();
});
const select = async (id) => { selected.value = id; await nextTick(); article.value?.scrollTo(0,0); };
const keydown = (event) => {
  if (event.key === 'Escape') { event.preventDefault(); close(); }
  if (event.key !== 'Tab') return;
  const elements = [...dialog.value.querySelectorAll('button, a[href], [tabindex="0"]')];
  const first = elements[0], last = elements.at(-1);
  if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog.value)) { event.preventDefault(); last?.focus(); }
  else if (!event.shiftKey && (document.activeElement === last || document.activeElement === dialog.value)) { event.preventDefault(); first?.focus(); }
};
</script>
<template>
  <div v-if="context.showHelp.value" class="modal manual-overlay" @click.self="close">
    <section ref="dialog" class="manual-dialog" role="dialog" aria-modal="true" aria-labelledby="manual-title" tabindex="-1" @keydown="keydown">
      <header class="manual-header"><div><h2 id="manual-title">操作手册</h2><p>从准备合同到完成审核，按主题查看操作方法。</p></div><button class="manual-close" @click="close" aria-label="关闭操作手册">关闭</button></header>
      <div class="manual-layout">
        <nav class="manual-directory" aria-label="操作手册目录"><button v-for="item in operationManual" :key="item.id" :aria-current="selected === item.id ? 'page' : undefined" :class="{active:selected === item.id}" @click="select(item.id)">{{ item.title }}</button></nav>
        <article ref="article" class="manual-content" tabindex="0" aria-label="手册正文">
          <h3>{{ current.title }}</h3><p class="manual-intro">{{ current.intro }}</p>
          <section v-for="section in current.sections" :key="section.title"><h4>{{ section.title }}</h4><ul><li v-for="text in section.items" :key="text">{{ text }}</li></ul></section>
        </article>
      </div>
    </section>
  </div>
</template>
