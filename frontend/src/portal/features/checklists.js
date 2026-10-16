export function setup(context) {
  const { busy, checklistEditor, modalError, api, notify, loadRecords } =
    context;
  const addChecklistItem = () =>
    checklistEditor.value.items.push({
      id: crypto.randomUUID(),
      title: "",
      requirement: "",
      operator: "semantic",
      keywords: [],
      keywordText: "",
      severity: "warning",
      suggestion: "",
    });
  const editChecklist = (list) => {
    modalError.value = "";
    checklistEditor.value = list
      ? JSON.parse(JSON.stringify(list))
      : {
          name: "",
          contract_type: "通用合同",
          description: "",
          items: [],
          published: false,
        };
    checklistEditor.value.items.forEach(
      (item) => (item.keywordText = (item.keywords || []).join(",")),
    );
    if (!list) addChecklistItem();
  };
  const saveChecklist = async (published) => {
    busy.value = true;
    modalError.value = "";
    try {
      const editor = checklistEditor.value;
      if (
        !editor.name.trim() ||
        !editor.items.length ||
        editor.items.some(
          (item) => !item.title.trim() || !item.requirement.trim(),
        )
      )
        throw new Error("请填写清单名称，并为每个检查项填写标题和具体要求");
      const body = {
        ...editor,
        published,
        items: editor.items.map((item) => ({
          ...item,
          keywords:
            item.operator === "semantic"
              ? []
              : item.keywordText
                  .split(/[,，\n]/)
                  .map((word) => word.trim())
                  .filter(Boolean),
        })),
      };
      await api(
        "/api/checklists" + (editor.id ? "/" + editor.id : ""),
        editor.id ? "PUT" : "POST",
        body,
      );
      checklistEditor.value = null;
      await loadRecords();
      notify(published ? "清单已发布，历史任务仍使用原版本" : "清单草稿已保存");
    } catch (err) {
      modalError.value = err.message;
    } finally {
      busy.value = false;
    }
  };

  const importHandlers = {
    checklist(data) {
      const lines = data.text
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);
      if (lines.length > 100)
        throw new Error("提取超过 100 行，请精简清单后导入");
      checklistEditor.value.items = lines.map((line) => ({
        id: crypto.randomUUID(),
        title: line.slice(0, 80),
        requirement: line,
        operator: "semantic",
        keywords: [],
        keywordText: "",
        severity: "warning",
        suggestion: "",
      }));
      if (!checklistEditor.value.name) checklistEditor.value.name = data.title;
      return "已按行提取清单草稿，请合并标题、核对要求后发布";
    },
  };
  return { importHandlers, addChecklistItem, editChecklist, saveChecklist };
}
