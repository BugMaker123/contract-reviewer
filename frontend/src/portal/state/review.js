import { ref, reactive, computed } from "vue";

export function setup(context) {
  const { roles, publishedLists, categoryFilter } = context;
  const samples = ref({});
  const inputMethod = ref("file"),
    sampleKey = ref(""),
    dragging = ref(false),
    sourceDrafts = {};
  const form = reactive({
    title: "",
    type: "商务合作协议",
    text: "",
    role: roles[0].value,
    mode: "deep",
    scale: "中立",
    background: "",
    focus: "",
    references: [],
    requirements: [],
    execution: "plan",
    reference_text: "",
    checklist_id: "",
    checklist_item_ids: null,
    source_id: null,
  });
  const availableLists = computed(() =>
    publishedLists.value.filter(
      (row) =>
        !categoryFilter.value || row.category_id === categoryFilter.value,
    ),
  );
  const selectedList = computed(() =>
    publishedLists.value.find((row) => row.id === form.checklist_id),
  );
  const chooseChecklist = () => {
    form.checklist_item_ids =
      selectedList.value?.items.map((item) => item.id) || null;
  };

  return {
    samples,
    inputMethod,
    sampleKey,
    dragging,
    sourceDrafts,
    form,
    availableLists,
    selectedList,
    chooseChecklist,
  };
}
