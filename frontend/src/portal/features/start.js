import { appendMaterial } from "../services/documents.js";
import { watch } from "vue";

export function setup(context) {
  const {
    categoryFilter,
    chooseChecklist,
    samples,
    busy,
    importing,
    error,
    inputMethod,
    sampleKey,
    form,
    api,
    navigate,
    replaceRoute,
    sourceDrafts,
    model,
  } = context;
  const extractRequirements = async (material) => {
    busy.value = true;
    error.value = "";
    try {
      const data = await api('/api/requirements/extract', 'POST', { material, model_config_data: model });
      const retained = form.requirements.filter(item => item.source !== material.name);
      if (retained.length + data.requirements.length > 100) throw new Error('审核要求最多100条，请整理后重试');
      form.requirements = [...retained, ...data.requirements];
      material.confirmed = false;
    } catch (err) { error.value = err.message; }
    finally { busy.value = false; }
  };
  const addRequirement = (source = '用户要求') => {
    if (form.requirements.length >= 100) { error.value = '审核要求最多100条'; return; }
    form.requirements.push({ id: 'custom-' + crypto.randomUUID(), text: '', priority: 'required', source });
  };
  const removeMaterial = (index) => {
    const material = form.references[index];
    form.requirements = form.requirements.filter(item => item.source !== material.name);
    form.references.splice(index, 1);
  };
  const switchSource = (next) => {
    if (next === inputMethod.value || importing.value) return;
    sourceDrafts[inputMethod.value] = {
      text: form.text,
      sampleKey: sampleKey.value,
      source_id: form.source_id,
    };
    const saved = sourceDrafts[next] || {
      text: "",
      sampleKey: "",
      source_id: null,
    };
    form.text = saved.text;
    form.source_id = saved.source_id;
    sampleKey.value = saved.sampleKey;
    inputMethod.value = next;
  };
  const selectSample = (key) => {
    const sample = samples.value[key];
    if (!sample) return;
    form.title = sample.title;
    form.type = sample.type;
    form.text = sample.text;
    form.source_id = null;
    sampleKey.value = key;
  };
  const createTask = async () => {
    busy.value = true;
    error.value = "";
    try {
      const body = {
        ...form,
        type: form.type?.trim() || "商务合同",
        focus: form.mode === "checklist" ? "" : form.focus,
        references: form.references,
        requirements: form.requirements.filter(item => item.text?.trim() || !item.id?.startsWith('custom-')),
        checklist_item_ids:
          form.mode === "checklist" ? form.checklist_item_ids : null,
      };
      const task = await api("/api/tasks", "POST", body);
      sessionStorage.removeItem("LEXIS_HOME_DRAFT");
      await navigate("/workbench?task=" + task.id);
    } catch (err) {
      error.value = err.message;
    } finally {
      busy.value = false;
    }
  };
  watch(categoryFilter, () => {
    form.checklist_id = "";
    form.checklist_item_ids = null;
  });
  watch(
    form,
    () => {
      try {
        sessionStorage.setItem(
          "LEXIS_HOME_DRAFT",
          JSON.stringify({ ...form, inputMethod: inputMethod.value }),
        );
      } catch {}
    },
    { deep: true },
  );
  const initialize = async () => {
    const saved = JSON.parse(
      sessionStorage.getItem("LEXIS_HOME_DRAFT") || "null",
    );
    if (saved) {
      const { inputMethod: source, ...values } = saved;
      Object.assign(form, values);
      if (!form.type?.trim()) form.type = '商务合同';
      if (!['deep', 'checklist'].includes(form.mode)) form.mode = 'deep';
      inputMethod.value = source || "paste";
    }
    const query = new URLSearchParams(location.search);
    if (query.has("checklist")) {
      form.mode = "checklist";
      form.checklist_id = query.get("checklist");
      chooseChecklist();
    }
  };

  const importHandlers = {
    contract(data) {
      form.text = data.text;
      form.title = data.title;
      form.source_id = data.source_id;
      sampleKey.value = "";
    },
    reference(data) {
      form.reference_text = data.text;
    },
    material(data, file) {
      appendMaterial(form.references, file, data);
    },
  };
  return { importHandlers, switchSource, selectSample, createTask, initialize, extractRequirements, addRequirement, removeMaterial };
}
