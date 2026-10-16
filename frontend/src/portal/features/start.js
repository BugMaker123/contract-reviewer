import { appendMaterial } from "../services/documents.js";
import { watch } from "vue";

export function setup(context) {
  const {
    categoryFilter,
    chooseChecklist,
    roles,
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
  } = context;
  const switchSource = (next) => {
    if (next === inputMethod.value || importing.value) return;
    sourceDrafts[inputMethod.value] = {
      text: form.text,
      title: form.title,
      sampleKey: sampleKey.value,
      source_id: form.source_id,
    };
    const saved = sourceDrafts[next] || {
      text: "",
      title: "",
      sampleKey: "",
      source_id: null,
    };
    form.text = saved.text;
    form.title = saved.title;
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
    form.role = sample.recommended_role || roles[0].value;
    sampleKey.value = key;
  };
  const createTask = async () => {
    busy.value = true;
    error.value = "";
    try {
      const body = {
        ...form,
        references: form.mode === "deep" ? form.references : [],
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
  return { importHandlers, switchSource, selectSample, createTask, initialize };
}
