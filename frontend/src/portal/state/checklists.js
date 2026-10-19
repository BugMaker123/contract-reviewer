import { ref, reactive, computed } from "vue";

export function setup(context) {
  const { search, showArchived, categoryFilter } = context;
  const lists = ref([]),
    checklistEditor = ref(null);
  const publishedLists = computed(() =>
    lists.value.filter((list) => list.published && !list.archived),
  );
  const filteredLists = computed(() =>
    lists.value.filter(
      (list) =>
        !!list.archived === showArchived.value &&
        (!categoryFilter.value || list.category_id === categoryFilter.value) &&
        (
          list.name +
          list.description +
          (list.items || []).map((item) => item.title + item.requirement).join(" ")
        )
          .toLowerCase()
          .includes(search.value.trim().toLowerCase()),
    ),
  );

  return { lists, checklistEditor, publishedLists, filteredLists };
}
