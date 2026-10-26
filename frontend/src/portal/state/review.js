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
    paste_html: "",
    role: roles[0].value,
    mode: "deep",
    scale: "中立",
    background: "",
    focus: "",
    references: [],
    requirements: [],
    knowledge_document_ids: [],
    knowledge_session_id: null,
    knowledge_message_ids: [],
    knowledge_context_confirmed: false,
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
    publishedLists.value.find((row) => row.id === form.checklist_id && row.items),
  );
  let selectionRequest = 0;
  const chooseChecklist = async () => {
    const request = ++selectionRequest;
    const id = form.checklist_id;
    if (!id) { form.checklist_item_ids = null; return; }
    context.busy.value = true;
    try {
      const detail = await context.api('/api/checklists/' + id);
      if (request !== selectionRequest || form.checklist_id !== id) return;
      context.lists.value = context.lists.value.map(row => row.id === id ? detail : row);
      form.checklist_item_ids = detail.items.map(item => item.id);
    } catch (error) {
      if (request === selectionRequest) context.error.value = error.message;
    } finally {
      if (request === selectionRequest) context.busy.value = false;
    }
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
