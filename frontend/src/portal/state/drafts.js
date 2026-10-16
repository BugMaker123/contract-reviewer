import { ref, reactive, computed } from "vue";

export function setup(context) {
  const { matches } = context;
  const drafts = ref([]);
  const filteredDrafts = computed(() => drafts.value.filter(matches));

  return { drafts, filteredDrafts };
}
