import { ref, reactive, computed } from "vue";

export function setup(context) {
  const draftSteps = [
    "起草要求",
    "确认交易信息",
    "确认条款大纲",
    "编辑合同正文",
  ];
  const draftStep = ref(0),
    draftVersions = ref([]),
    previewDraftVersion = ref(null);
  const rewriteSelection = reactive({
    original: "",
    instruction: "",
    proposal: "",
  });
  const draft = reactive({
    id: null,
    title: "",
    background: "",
    details: {
      甲方: "",
      乙方: "",
      标的: "",
      金额: "",
      交付: "",
      付款: "",
      期限: "",
      其他要求: "",
    },
    outline: "",
    text: "",
    template_text: "",
    references: [],
    revision: null,
  });

  return {
    draftSteps,
    draftStep,
    draftVersions,
    previewDraftVersion,
    rewriteSelection,
    draft,
  };
}
