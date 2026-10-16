import { appendMaterial } from "../services/documents.js";

export function setup(context) {
  const {
    roles,
    busy,
    error,
    model,
    draftStep,
    draftVersions,
    draft,
    rewriteSelection,
    api,
    navigate,
    replaceRoute,
    notify,
  } = context;
  const signature = () =>
    JSON.stringify([
      draft.title,
      draft.background,
      draft.details,
      draft.outline,
      draft.text,
      draft.template_text,
      draft.references,
    ]);
  let savedSignature = signature();
  const hasDraftChanges = () => savedSignature !== signature();
  const persistDraft = async (updateRoute = true) => {
    const saved = await api(
      "/api/drafts" + (draft.id ? "/" + draft.id : ""),
      draft.id ? "PUT" : "POST",
      draft,
    );
    Object.assign(draft, saved);
    if (updateRoute) await replaceRoute("/draft?id=" + draft.id);
    savedSignature = signature();
    draftVersions.value = (
      await api("/api/drafts/" + draft.id + "/versions")
    ).items;
    return saved;
  };
  const saveDraft = async () => {
    busy.value = true;
    error.value = "";
    try {
      await persistDraft();
      notify("草稿已保存");
    } catch (err) {
      error.value = err.message;
    } finally {
      busy.value = false;
    }
  };
  const generateDraft = async (stage) => {
    busy.value = true;
    error.value = "";
    try {
      await persistDraft();
      const generated = await api(
        "/api/drafts/" + draft.id + "/generate",
        "POST",
        { stage, model_config_data: model },
      );
      Object.assign(draft, generated);
      draftStep.value = { details: 1, outline: 2, text: 3 }[stage];
      draftVersions.value = (
        await api("/api/drafts/" + draft.id + "/versions")
      ).items;
      notify("已生成，请核对内容");
    } catch (err) {
      error.value = err.message;
      if (draft.id)
        try {
          const fresh = await api("/api/drafts/" + draft.id);
          draft.revision = fresh.revision;
          draft.status = fresh.status;
        } catch {}
    } finally {
      busy.value = false;
    }
  };
  const sendDraftToReview = async () => {
    busy.value = true;
    error.value = "";
    try {
      await persistDraft();
      const task = await api("/api/tasks", "POST", {
        title: draft.title,
        type: "起草合同",
        text: draft.text,
        role: roles[0].value,
        mode: "deep",
        scale: "中立",
        background: draft.background,
        focus: "",
        references: draft.references,
      });
      await navigate("/workbench?task=" + task.id);
    } catch (err) {
      error.value = err.message;
    } finally {
      busy.value = false;
    }
  };
  const captureSelection = (event) => {
    const start = event.target.selectionStart,
      end = event.target.selectionEnd;
    if (end > start) {
      rewriteSelection.original = draft.text.slice(start, end);
      rewriteSelection.proposal = "";
    }
  };
  const requestRewrite = async () => {
    busy.value = true;
    error.value = "";
    try {
      await persistDraft();
      const response = await api(
        "/api/drafts/" + draft.id + "/rewrite",
        "POST",
        {
          original_text: rewriteSelection.original,
          instruction: rewriteSelection.instruction,
          revision: draft.revision,
          model_config_data: model,
        },
      );
      draft.revision = response.revision;
      rewriteSelection.proposal = response.suggested_text;
    } catch (err) {
      error.value = err.message;
      if (draft.id)
        try {
          draft.revision = (await api("/api/drafts/" + draft.id)).revision;
        } catch {}
    } finally {
      busy.value = false;
    }
  };
  const applyRewrite = async () => {
    if (
      !rewriteSelection.original ||
      draft.text.split(rewriteSelection.original).length !== 2
    ) {
      error.value = "原文已变更或存在多处匹配，请重新选取";
      return;
    }
    draft.text = draft.text.replace(
      rewriteSelection.original,
      rewriteSelection.proposal,
    );
    rewriteSelection.proposal = "";
    rewriteSelection.original = "";
    await saveDraft();
  };
  const initialize = async () => {
    const query = new URLSearchParams(location.search);
    if (query.has("id")) {
      const saved = await api("/api/drafts/" + query.get("id"));
      Object.assign(draft, saved);
      draftStep.value = saved.text ? 3 : saved.outline ? 2 : 0;
      draftVersions.value = (
        await api("/api/drafts/" + draft.id + "/versions")
      ).items;
      savedSignature = signature();
    }
  };

  const importHandlers = {
    draft_material(data, file) {
      appendMaterial(draft.references, file, data);
    },
    template(data) {
      if (data.text.length > 50000)
        throw new Error("模板超过 5 万字，请精简后导入");
      draft.template_text = data.text;
    },
  };
  return {
    importHandlers,
    hasDraftChanges,
    persistDraft,
    saveDraft,
    generateDraft,
    sendDraftToReview,
    captureSelection,
    requestRewrite,
    applyRewrite,
    initialize,
  };
}
