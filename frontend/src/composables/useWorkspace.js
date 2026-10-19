/* Durable task adapter. Saves are serialized and use optimistic revisions. */
import { ref, computed, watch, nextTick, onScopeDispose } from "vue";
import { router } from "../router/index.js";

export function createWorkspaceWorkbench(refs) {
  onScopeDispose(() => clearTimeout(timer));
  const taskId = ref(new URLSearchParams(location.search).get("task"));
  const selectedRun = ref(new URLSearchParams(location.search).get("run"));
  const task = ref(null),
    run = ref(null),
    loading = ref(true),
    hydrating = ref(true),
    saving = ref(false);
  const conditions = ref({
    mode: "deep",
    scale: "中立",
    background: "",
    focus: "",
    references: [],
    requirements: [],
    execution: "plan",
    reference_text: "",
    checklist: null,
    source_id: null,
  });
  const decisions = ref({}),
    comments = ref({}),
    followups = ref({}),
    question = ref(""),
    followupIssue = ref(null),
    followupBusy = ref(false);
  const verifying = ref(false), manualBusy = ref(false), confirmations = ref({});
  const showConditions = ref(false),
    exportScope = ref("current"),
    versions = ref([]),
    error = ref("");
  let queue = Promise.resolve(),
    timer,
    lastInput = "",
    lastHandling = "";
  const api = async (path, method = "GET", body) => {
    const response = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await response.json();
    if (!response.ok)
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : data.detail?.map((item) => item.msg).join("；") ||
            "保存失败，请重试",
      );
    return data;
  };
  const modeName = computed(
    () =>
      ({
        quick: "快速审查",
        deep: "深度审查",
        checklist: "清单审查",
        compare: "对比审查",
      })[conditions.value.mode],
  );
  const historical = computed(
    () => !!selectedRun.value && selectedRun.value !== task.value?.active_run,
  );
  const input = () => ({
    title: refs.contractTitle.value,
    type: refs.contractType.value,
    text: refs.contractText.value,
    role: refs.partyRole.value,
    mode: conditions.value.mode,
    scale: conditions.value.scale,
    background: conditions.value.background,
    focus: conditions.value.focus,
    references: conditions.value.references,
    requirements: conditions.value.requirements,
    execution: conditions.value.execution,
    reference_text: conditions.value.reference_text,
    checklist_id: conditions.value.checklist?.id || null,
    source_id: conditions.value.source_id || null,
  });
  const handling = () => ({
    applied: [...refs.appliedIssueIds.value],
    decisions: { ...decisions.value },
    comments: { ...comments.value },
  });
  const isStale = computed(() => {
    if (!run.value?.result) return false;
    const snapshot = run.value.input;
    return (
      ["title", "type", "text", "role"].some(
        (key) => input()[key] !== snapshot[key],
      ) ||
      ["mode", "scale", "background", "focus", "reference_text", "execution"].some(
        (key) => conditions.value[key] !== (key === 'execution' ? snapshot[key] || 'plan' : snapshot[key]),
      ) ||
      JSON.stringify(conditions.value.requirements || []) !== JSON.stringify(snapshot.requirements || []) ||
      JSON.stringify(conditions.value.references) !==
        JSON.stringify(snapshot.references) ||
      (conditions.value.checklist?.id || null) !==
        (snapshot.checklist?.id || null) ||
      (conditions.value.source_id || null) !== (snapshot.source_id || null)
    );
  });
  const dirty = computed(() => !hydrating.value && !historical.value &&
    (JSON.stringify(input()) !== lastInput || (run.value?.status === "completed" && JSON.stringify(handling()) !== lastHandling)));
  const canExport = computed(() => task.value?.status === "completed" &&
    task.value?.active_run === run.value?.id && run.value?.status === "completed" &&
    !historical.value && !isStale.value && !dirty.value && !saving.value);
  const canExportReport = computed(() => ['pending_review', 'completed'].includes(task.value?.status) &&
    task.value?.active_run === run.value?.id && run.value?.status === "completed" &&
    !historical.value && !isStale.value && !dirty.value && !saving.value);
  const requireReportExport = () => {
    if (!canExportReport.value) throw new Error("请先完成当前合同审查，再导出审查意见书");
  };
  const requireExport = () => {
    if (!canExport.value) throw new Error("请先完成审核，再导出文件");
  };
  const checkExport = async (scope = "current") => {
    const check = scope === "report" ? requireReportExport : requireExport;
    try {
      check();
      const current = await api('/api/tasks/' + taskId.value);
      task.value = current;
      check();
      if (current.run?.revision !== run.value?.revision) throw new Error('审核记录已改变，请刷新后再导出');
      return true;
    } catch (err) {
      refs.showToast(err.message);
      return false;
    }
  };
  const beforeUnload = (event) => {
    if (!dirty.value && !saving.value) return;
    event.preventDefault();
    event.returnValue = "";
  };
  window.addEventListener("beforeunload", beforeUnload);
  onScopeDispose(() => window.removeEventListener("beforeunload", beforeUnload));
  const flush = async () => {
    clearTimeout(timer);
    if (hydrating.value || historical.value || refs.isReviewing.value || ["running","queued"].includes(task.value?.status)) return;
    const job = async () => {
      if (refs.isReviewing.value || ["running","queued"].includes(task.value?.status)) return;
      saving.value = true;
      error.value = "";
      refs.saveStatus.value = "正在保存…";
      try {
        const current = input();
        const signature = JSON.stringify(current);
        if (!taskId.value) {
          task.value = await api("/api/tasks", "POST", current);
          taskId.value = task.value.id;
          await router.replace("/workbench?task=" + taskId.value);
          lastInput = signature;
        } else if (signature !== lastInput) {
          task.value = await api("/api/tasks/" + taskId.value, "PUT", {
            ...current,
            revision: task.value.revision,
          });
          lastInput = signature;
        }
        if (run.value?.status === "completed") {
          const changes = handling(),
            signature = JSON.stringify(changes);
          if (signature !== lastHandling) {
            const saved = await api(
              "/api/runs/" + run.value.id + "/handling",
              "PUT",
              { ...changes, revision: run.value.revision },
            );
            // Preserve selections made while this request was in flight.
            const unchanged = JSON.stringify(handling()) === signature;
            run.value = saved;
            if (unchanged) decisions.value = saved.decisions;
            lastHandling = JSON.stringify({
              applied: saved.applied,
              decisions: saved.decisions,
              comments: saved.comments,
            });
            if (task.value.status === "completed")
              task.value = await api("/api/tasks/" + taskId.value);
          }
        }
        refs.saveStatus.value = dirty.value ? "有待保存的修改" : "已保存到本机服务";
      } catch (err) {
        error.value = err.message;
        refs.saveStatus.value = "保存失败，请重试";
        throw err;
      } finally {
        saving.value = false;
      }
    };
    queue = queue.catch(() => {}).then(job);
    return queue;
  };
  const schedule = () => {
    if (
      hydrating.value ||
      refs.isReviewing.value ||
      historical.value ||
      !taskId.value
    )
      return;
    refs.saveStatus.value = "有待保存的修改";
    clearTimeout(timer);
    timer = setTimeout(() => flush().catch(() => {}), 600);
  };
  watch(
    [
      refs.contractTitle,
      refs.contractType,
      refs.contractText,
      refs.partyRole,
      conditions,
      refs.appliedIssueIds,
      decisions,
      comments,
    ],
    schedule,
    { deep: true },
  );
  const applyRun = (record) => {
    run.value = record;
    confirmations.value = { ...(record?.completion_confirmations || {}) };
    refs.reviewResult.value = record?.result || null;
    refs.appliedIssueIds.value = record?.applied || [];
    decisions.value = record?.decisions || {};
    comments.value = record?.comments || {};
    followups.value = record?.followups || {};
    refs.reviewedAt.value = record?.completed_at
      ? new Date(record.completed_at).toLocaleString("zh-CN", {
          timeZone: "Asia/Shanghai",
        })
      : "";
    refs.reviewedInput.value = record
      ? {
          text: record.input.text,
          title: record.input.title,
          type: record.input.type,
          role: record.input.role,
        }
      : null;
    lastHandling = JSON.stringify(handling());
  };
  const refresh = async (runId) => {
    hydrating.value = true;
    try {
      task.value = await api("/api/tasks/" + taskId.value);
      versions.value = task.value.runs;
      if (runId) {
        selectedRun.value = null;
        await router.replace("/workbench?task=" + taskId.value);
      }
      applyRun(runId ? await api("/api/runs/" + runId) : task.value.run);
    } finally {
      await nextTick();
      hydrating.value = false;
    }
  };
  const load = async () => {
    try {
      if (taskId.value) {
        task.value = await api("/api/tasks/" + taskId.value);
        let record = task.value;
        if (selectedRun.value) {
          const previous = await api("/api/runs/" + selectedRun.value);
          if (previous.task_id !== taskId.value)
            throw new Error("此版本不属于当前任务");
          record = previous.input;
          applyRun(previous);
        } else applyRun(task.value.run);
        refs.contractTitle.value = record.title;
        refs.contractType.value = record.type;
        refs.contractText.value = record.text;
        refs.partyRole.value = record.role;
        conditions.value = {
          mode: record.mode,
          scale: record.scale,
          background: record.background,
          focus: record.focus,
          references: record.references,
          requirements: record.requirements || [],
          execution: record.execution || "plan",
          reference_text: record.reference_text,
          checklist: record.checklist,
          source_id: record.source_id || null,
        };
        versions.value = task.value.runs;
        if (["running","queued"].includes(task.value.status))
          error.value = task.value.status === "queued" ? "任务已排队，可查看后台进度或取消排队。" : "后台正在审查，可点击重新连接查看进度。";
        lastInput = JSON.stringify(input());
        refs.saveStatus.value = "已从本机服务恢复";
      }
    } catch (err) {
      error.value = err.message;
      refs.saveStatus.value = "读取失败";
    } finally {
      await nextTick();
      hydrating.value = false;
      loading.value = false;
    }
  };
  const save = async () => {
    try {
      await flush();
      refs.showToast("工作内容已保存");
    } catch (err) {
      refs.showToast(err.message);
    }
  };
  const leaveFor = async (path) => {
    try {
      if (taskId.value) await flush();
      await router.push(path);
    } catch (err) {
      refs.showToast("保存未完成：" + err.message);
    }
  };
  const setDecision = async (issue, state) => {
    if (historical.value || loading.value || refs.isReviewing.value) return;
    if (refs.appliedIssueIds.value.includes(issue.id)) {
      refs.showToast("请先撤销该项采纳，再改变处理状态");
      return;
    }
    decisions.value = { ...decisions.value, [issue.id]: state };
    try {
      await flush();
    } catch (err) {
      refs.showToast(err.message);
    }
  };
  const decisionName = (id) =>
    ({
      pending: "待处理",
      applied: "已采纳",
      rejected: "不采纳",
      needs_review: "待复核",
    })[
      refs.appliedIssueIds.value.includes(id)
        ? "applied"
        : decisions.value[id] || "pending"
    ];
  const exportDocument = async (original = false) => {
    try {
      await flush();
      requireExport();
      const suffix = historical.value ? "?run=" + run.value.id : "";
      const preview = original ? null : refs.getPreviewExport?.();
      const documentUrl = preview
        ? "/api/runs/" + preview.run + "/preview-file?scope=" + preview.scope
        : "/api/tasks/" + taskId.value + "/document" + suffix;
      const response = await fetch(documentUrl);
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "下载失败");
      }
      const url = URL.createObjectURL(await response.blob()),
        anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = decodeURIComponent(
        response.headers.get("Content-Disposition")?.split("UTF-8''")[1] ||
          "合同.docx",
      );
      anchor.click();
      refs.showToast("已发起 Word 下载，请查看浏览器下载列表");
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      if (response.headers.get("X-Word-Layout") === "reconstructed")
        refs.showToast("已下载当前正文，Word 使用统一版式");
    } catch (err) {
      refs.showToast(err.message);
      error.value = err.message;
    }
  };
  const exportWord = async () => {
    const scope = exportScope.value;
    try {
      await flush();
      if (["report", "applied_report"].includes(scope)) requireReportExport();
      else requireExport();
      if (!run.value) throw new Error("请先选择审查版本");
      const response = await fetch(
        "/api/runs/" + run.value.id + "/export?scope=" + scope,
      );
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "导出失败");
      }
      const url = URL.createObjectURL(await response.blob()),
        anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = decodeURIComponent(
        response.headers.get("Content-Disposition")?.split("UTF-8''")[1] ||
          "合同.docx",
      );
      anchor.click();
      refs.showToast("已发起 Word 下载，请查看浏览器下载列表");
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      if (response.headers.get("X-Word-Layout") === "reconstructed")
        refs.showToast("Word 已导出，正文按统一版式重新排版，请复核后使用");
    } catch (err) {
      refs.showToast(err.message);
      error.value = err.message;
    }
  };
  const finish = async () => {
    try {
      await flush();
      task.value = await api(
        "/api/tasks/" + taskId.value + "/complete",
        "POST",
        { archived: false, revision: task.value.revision, confirmations: confirmations.value },
      );
      await refresh();
      refs.showToast("已完成审核，现在可以导出文件");
    } catch (err) {
      refs.showToast(err.message);
    }
  };
  const verifyCurrent = async () => {
    if (verifying.value || historical.value || refs.isReviewing.value) return;
    verifying.value = true;
    try {
      await flush();
      const saved = await api(`/api/runs/${run.value.id}/verify-current`, "POST", {
        revision: run.value.revision, model_config_data: refs.getModel(),
      });
      applyRun(saved);
      task.value = await api("/api/tasks/" + taskId.value);
      refs.showToast("当前稿核验完成，请核对逐项结论");
    } catch (err) { error.value = err.message; refs.showToast(err.message); }
    finally { verifying.value = false; }
  };
  const addManualIssue = async (draft) => {
    if (manualBusy.value || historical.value) return false;
    manualBusy.value = true;
    try {
      await flush();
      applyRun(await api(`/api/runs/${run.value.id}/issues`, "POST", { ...draft, revision: run.value.revision }));
      task.value = await api("/api/tasks/" + taskId.value);
      refs.showToast("人工意见已保存");
      return true;
    } catch (err) { error.value = err.message; refs.showToast(err.message); return false; }
    finally { manualBusy.value = false; }
  };
  const selectVersion = async (id) => {
    await flush();
    await router.push(`/workbench?task=${taskId.value}${id ? '&run=' + id : ''}`);
  };
  const downloadAudit = async () => {
    await flush();
    const response = await fetch(`/api/runs/${run.value.id}/audit`);
    if (!response.ok) { refs.showToast("审核记录下载失败"); return; }
    const url = URL.createObjectURL(await response.blob());
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `review-audit-${run.value.id}.json`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const ask = async (issue) => {
    if (!question.value.trim() || followupBusy.value) return;
    followupBusy.value = true;
    try {
      await flush();
      const data = await api(
        "/api/runs/" + run.value.id + "/followup",
        "POST",
        {
          issue_id: issue.id,
          question: question.value,
          model_config_data: refs.getModel(),
        },
      );
      run.value = data;
      followups.value = data.followups;
      question.value = "";
    } catch (err) {
      refs.showToast(err.message);
      error.value = err.message;
    } finally {
      followupBusy.value = false;
    }
  };
  const previewFollowup = (answer) => {
    if (answer.suggested_text) refs.copyText(answer.suggested_text);
  };
  return {
    canExport, canExportReport, requireExport, checkExport,
    getModel: refs.getModel,
    verifying, manualBusy, confirmations, verifyCurrent, addManualIssue, selectVersion, downloadAudit,
    taskId,
    task,
    run,
    loading,
    conditions,
    decisions,
    comments,
    followups,
    question,
    followupIssue,
    followupBusy,
    showConditions,
    exportScope,
    versions,
    error,
    modeName,
    historical,
    isStale,
    saving,
    load,
    flush,
    refresh,
    save,
    leaveFor,
    setDecision,
    decisionName,
    exportDocument,
    exportWord,
    finish,
    ask,
    previewFollowup,
  };
}
