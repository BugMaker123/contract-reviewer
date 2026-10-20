import { computed, ref, watch, onScopeDispose } from "vue";
import { useRoute } from "vue-router";

export function setup(context) {
  const route = useRoute();
  const { api, search, categoryFilter, showArchived, error, busy, notify } = context;
  const kind = context.page;
  const rows = ref([]), total = ref(0), currentPage = ref(1), pageSize = ref(10);
  const fetching = ref(false), publicationFilter = ref("");
  const deleteTarget = ref(null), deleteError = ref("");
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)));
  const originalLoad = context.loadRecords;
  let requestId = 0, timer;
  const loadCatalog = async () => {
    clearTimeout(timer);
    const id = ++requestId;
    fetching.value = true;
    error.value = "";
    const query = new URLSearchParams({ page: currentPage.value, page_size: pageSize.value, q: search.value.trim() });
    if (kind === "checklists") {
      if (categoryFilter.value) query.set("category_id", categoryFilter.value);
      query.set("archived", showArchived.value);
      if (publicationFilter.value) query.set("published", publicationFilter.value);
    }
    try {
      const result = await api(`/api/${kind}?${query}`);
      if (id !== requestId) return;
      rows.value = result.items;
      total.value = result.total;
      currentPage.value = result.page;
    } catch (err) {
      if (id === requestId) { rows.value = []; total.value = 0; error.value = err.message; }
    } finally {
      if (id === requestId) fetching.value = false;
    }
  };
  const loadRecords = async () => { await originalLoad(); await loadCatalog(); };
  const resetQuery = () => { currentPage.value = 1; return loadCatalog(); };
  watch(search, () => {
    ++requestId;
    fetching.value = true;
    clearTimeout(timer);
    timer = setTimeout(resetQuery, 250);
  });
  watch([categoryFilter, showArchived, publicationFilter, pageSize], resetQuery);
  const goPage = (page) => { currentPage.value = page; return loadCatalog(); };
  const requestDelete = (row) => { deleteError.value = ""; deleteTarget.value = row; };
  const confirmDelete = async () => {
    busy.value = true;
    deleteError.value = "";
    try {
      const row = deleteTarget.value;
      await api(`/api/${kind}/${row.id}?revision=${row.revision}`, "DELETE");
      deleteTarget.value = null;
      await loadRecords();
      notify(kind === "categories" ? "业务分类已删除" : "清单已删除，历史审查任务中的快照已保留");
    } catch (err) { deleteError.value = err.message; }
    finally { busy.value = false; }
  };
  const initialize = () => {
    if (kind !== "checklists") return;
    const category = typeof route.query.category === "string" ? route.query.category : "";
    if (categoryFilter.value !== category) {
      search.value = "";
      showArchived.value = false;
      publicationFilter.value = "";
      categoryFilter.value = category;
    }
    if (route.query.create === "1") {
      context.editChecklist();
      const query = { ...route.query };
      delete query.create;
      context.replaceRoute({ path: route.path, query });
    }
  };
  onScopeDispose(() => { clearTimeout(timer); ++requestId; });
  return { rows, total, currentPage, pageSize, totalPages, fetching, publicationFilter,
    deleteTarget, deleteError, requestDelete, confirmDelete, loadRecords, goPage, initialize };
}
