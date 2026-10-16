import { createPresentation } from "./presentation.js";
import { ref, reactive, computed } from "vue";

export function createContext(page, requiredData) {
  const tasks = ref([]);
  const loading = ref(true),
    busy = ref(false),
    importing = ref(false),
    error = ref(""),
    toast = ref("");
  const search = ref(""),
    modeFilter = ref("all"),
    statusFilter = ref("all"),
    showArchived = ref(false),
    fromDate = ref(""),
    toDate = ref("");
  const modalError = ref(""),
    showModel = ref(false),
    showHelp = ref(false),
    modelTest = ref(null);
  const model = reactive({
    model_name: localStorage.getItem("LEXIS_MODEL_NAME") || "deepseek-chat",
    base_url:
      localStorage.getItem("LEXIS_BASE_URL") || "https://api.deepseek.com/v1",
    api_key: localStorage.getItem("LEXIS_API_KEY") || "",
  });
  const notify = (message) => {
    toast.value = message;
    setTimeout(() => {
      if (toast.value === message) toast.value = "";
    }, 2500);
  };
  const api = async (path, method = "GET", body) => {
    const response = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await response.json();
    if (!response.ok)
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : data.detail?.map((item) => item.msg).join("；") ||
            "请求失败，请重试",
      );
    return data;
  };
  const recentTasks = computed(() =>
    tasks.value.filter((task) => !task.archived),
  );
  const matches = (row) =>
    !!row.archived === showArchived.value &&
    row.title?.toLowerCase().includes(search.value.trim().toLowerCase());

  const context = {
    ...createPresentation(),
    page,
    tasks,
    loading,
    busy,
    importing,
    error,
    toast,
    search,
    modeFilter,
    statusFilter,
    showArchived,
    fromDate,
    toDate,
    modalError,
    showModel,
    showHelp,
    modelTest,
    model,
    notify,
    api,
    recentTasks,
    matches,
  };
  context.loadRecords = async () => {
    const paths = {
      tasks: "/api/tasks",
      lists: "/api/checklists",
      drafts: "/api/drafts",
      categories: "/api/categories",
      samples: "/api/samples",
    };
    const results = await Promise.allSettled(
      requiredData.map(async (key) => {
        const data = await api(paths[key]);
        context[key].value = key === "samples" ? data.samples : data.items;
      }),
    );
    const failure = results.find((result) => result.status === "rejected");
    if (failure) throw failure.reason;
  };
  return context;
}
