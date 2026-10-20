export function setup(context) {
  const {
    categories,
    categoryEditor,
    busy,
    modalError,
    api,
    notify,
    loadRecords,
  } = context;
  const editCategory = (row) => {
    modalError.value = "";
    categoryEditor.value = row
      ? { ...row }
      : {
          name: "",
          code: "",
          description: "",
          sort_order: (context.total?.value ?? categories.value.length) + 1,
        };
  };
  const saveCategory = async () => {
    busy.value = true;
    modalError.value = "";
    try {
      const row = categoryEditor.value;
      await api(
        "/api/categories" + (row.id ? "/" + row.id : ""),
        row.id ? "PUT" : "POST",
        row,
      );
      categoryEditor.value = null;
      await loadRecords();
      notify("业务分类已保存");
    } catch (err) {
      modalError.value = err.message;
    } finally {
      busy.value = false;
    }
  };

  return { editCategory, saveCategory };
}
