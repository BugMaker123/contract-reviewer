import { ref, computed, watch, onScopeDispose } from 'vue';
export function setup(context) {
  const { tasks, api, error, search, modeFilter, statusFilter, showArchived, fromDate, toDate } = context;
  const currentPage = ref(1), pageSize = ref(10), total = ref(0), fetching = ref(false);
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)));
  let generation = 0, timer;
  const loadRecords = async () => {
    clearTimeout(timer);
    const ticket = ++generation; fetching.value = true; error.value = '';
    const query = new URLSearchParams({page:currentPage.value,page_size:pageSize.value,q:search.value.trim(),archived:showArchived.value});
    if (modeFilter.value !== 'all') query.set('mode',modeFilter.value);
    if (statusFilter.value !== 'all') query.set('status',statusFilter.value);
    if (fromDate.value) query.set('from_date',fromDate.value);
    if (toDate.value) query.set('to_date',toDate.value);
    try { const data = await api('/api/tasks?' + query);
      if (ticket !== generation) return;
      tasks.value = data.items; total.value = data.total; currentPage.value = data.page;
    } catch (err) { if (ticket === generation) { tasks.value = []; total.value = 0; error.value = err.message; } }
    finally { if (ticket === generation) fetching.value = false; }
  };
  const reset = () => { currentPage.value = 1; return loadRecords(); };
  watch(search, () => { ++generation; fetching.value = true; clearTimeout(timer); timer = setTimeout(reset,250); });
  watch([modeFilter,statusFilter,showArchived,fromDate,toDate,pageSize], reset);
  const goPage = page => { currentPage.value = page; return loadRecords(); };
  onScopeDispose(() => { ++generation; clearTimeout(timer); });
  return { filteredTasks: tasks, currentPage, pageSize, total, totalPages, fetching, loadRecords, goPage };
}
