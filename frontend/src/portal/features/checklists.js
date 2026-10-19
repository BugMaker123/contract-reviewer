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
  const editChecklist = async (list) => {
    if (list && !list.items) {
      busy.value = true;
      try { list = await api('/api/checklists/' + list.id); }
      catch (err) { context.error.value = err.message; return; }
      finally { busy.value = false; }
    }
    modalError.value = "";
    checklistEditor.value = list
      ? JSON.parse(JSON.stringify(list))
      : {
          name: "",
          category_id: context.categoryFilter.value || null,
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
      const items = editor.items.filter(item => item.title.trim() || item.requirement.trim() || item.keywordText?.trim() || item.suggestion?.trim() || item.operator !== 'semantic' || item.severity !== 'warning');
      if (!editor.name.trim() || !items.length || items.some(item => !item.requirement.trim()))
        throw new Error('请填写清单名称和至少一条具体审查要求');
      if (items.length > 100) throw new Error('每份清单最多100条要求');
      const body = {
        ...editor,
        name: editor.name.trim(),
        published,
        items: items.map(item => ({
          ...item,
          title: item.title.trim() || item.requirement.trim().slice(0,60),
          requirement: item.requirement.trim(),
          keywords: item.operator === 'semantic' ? [] : (item.keywordText || '').split(/[,，\n]/).map(word => word.trim()).filter(Boolean),
        })),
      };
      await api(
        "/api/checklists" + (editor.id ? "/" + editor.id : ""),
        editor.id ? "PUT" : "POST",
        body,
      );
      checklistEditor.value = null;
      context.currentPage.value = 1;
      await loadRecords();
      notify(published ? "清单已启用，可在开始页直接选用" : "清单草稿已保存");
    } catch (err) {
      modalError.value = err.message;
    } finally {
      busy.value = false;
    }
  };

  const appendChecklistRequirements = (text) => {
    const editor = checklistEditor.value;
    if (!editor) throw new Error('请先打开清单编辑器');
    const lines = text.split('\n').map(line => line.trim().replace(/^(?:[-*•]\s+|\d+\.\s+|\d+[、)）]\s*)/, '')).filter(Boolean);
    if (!lines.length) throw new Error('请填写审查要求，每行一条');
    if (lines.some(line => line.length > 3000)) throw new Error('单条要求不能超过3000字，请拆分后添加');
    const retained = editor.items.filter(item => item.title.trim() || item.requirement.trim() || item.keywordText?.trim() || item.suggestion?.trim() || item.operator !== 'semantic' || item.severity !== 'warning');
    const seen = new Set(retained.map(item => item.requirement.trim()));
    const added = [];
    for (const line of lines) {
      if (seen.has(line)) continue;
      seen.add(line);
      added.push({id:crypto.randomUUID(),title:'',requirement:line,operator:'semantic',keywords:[],keywordText:'',severity:'warning',suggestion:''});
    }
    if (retained.length + added.length > 100) throw new Error('每份清单最多100条要求，请精简后添加');
    editor.items = [...retained,...added];
    return {added:added.length,duplicates:lines.length-added.length};
  };
  const importHandlers = {
    checklist(data) {
      const result = appendChecklistRequirements(data.text);
      if (!checklistEditor.value.name) checklistEditor.value.name = data.title;
      return `已追加 ${result.added} 条要求${result.duplicates ? '，跳过 '+result.duplicates+' 条重复内容' : ''}，请核对后启用`;
    },
  };
  return { importHandlers, addChecklistItem, editChecklist, saveChecklist, appendChecklistRequirements };
}
