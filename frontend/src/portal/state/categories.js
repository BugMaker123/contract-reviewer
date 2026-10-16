import { ref, reactive, computed } from "vue";

export function setup(context) {
  const { search } = context;
  const categories = ref([]),
    categoryFilter = ref(""),
    categoryEditor = ref(null);
  const categoryName = (id) =>
    categories.value.find((row) => row.id === id)?.name || "未分类";
  const filteredCategories = computed(() =>
    categories.value.filter((row) =>
      (row.name + row.code + row.description)
        .toLowerCase()
        .includes(search.value.trim().toLowerCase()),
    ),
  );

  return {
    categories,
    categoryFilter,
    categoryEditor,
    categoryName,
    filteredCategories,
  };
}
