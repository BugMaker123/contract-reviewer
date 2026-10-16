<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <label class="block"
    ><span class="label">条款大纲</span
    ><textarea
      v-model="draft.outline"
      class="field h-80 leading-relaxed"
      placeholder="生成或手动填写条款大纲，一行一条…"
    ></textarea></label
  ><button
    @click="generateDraft('text')"
    :disabled="busy || !draft.outline.trim()"
    class="button primary"
  >
    {{ busy ? "正在生成…" : "确认大纲并生成正文" }}
  </button>
</template>
