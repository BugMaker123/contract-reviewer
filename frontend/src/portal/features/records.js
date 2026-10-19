export function setup(context) {
  const { busy, error, api, notify, loadRecords } = context;
  const archive = async (kind, row) => {
    busy.value = true;
    error.value = "";
    try {
      await api("/api/" + kind + "/" + row.id + "/archive", "POST", {
        archived: !row.archived,
        revision: row.revision,
      });
      await loadRecords();
      await context.refreshRecent?.();
      notify(row.archived ? "已恢复记录" : "已归档，可在已归档列表恢复");
    } catch (err) {
      error.value = err.message;
    } finally {
      busy.value = false;
    }
  };

  return { archive };
}
