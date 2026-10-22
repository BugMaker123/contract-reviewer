import { computed, nextTick, onScopeDispose, reactive, ref, watch } from "vue";
import { onBeforeRouteLeave, onBeforeRouteUpdate } from "vue-router";

export function useTrackedReview(context) {
  const {
    workspace,
    reviewResult,
    resultStale,
    appliedIssueIds,
    focusedIssueId,
    isReviewing,
  } = context;
  const displayKey = () => `LEXIS_REVIEW_DISPLAY:${workspace.taskId || "unsaved"}`;
  let savedMode = "markup";
  try {
    const taskMode = sessionStorage.getItem(displayKey());
    const legacyMode = sessionStorage.getItem("LEXIS_REVIEW_DISPLAY");
    savedMode = taskMode || (["markup", "current", "original"].includes(legacyMode) ? legacyMode : "markup");
  } catch {}
  const revisionMode = ref(
    ["markup", "current", "original", "compare"].includes(savedMode) ? savedMode : "markup",
  );
  watch(revisionMode, (mode) => {
    try { sessionStorage.setItem(displayKey(), mode); } catch {}
  });
  watch(isReviewing, (running) => {
    if (running) revisionMode.value = "markup";
  }, { flush: "sync" });
  const showDocumentComparison = computed(() =>
    revisionMode.value === "compare" && context.documentCompare.value &&
    !isReviewing.value && !["running", "queued"].includes(workspace.task?.status));
  const revisionBusy = ref(false);
  const revisionDocumentLoaded = ref(false);
  const revisionRenderedVersion = ref(0);
  const revisionInstructions = reactive({});
  const revisionErrors = reactive({});
  const revisionWarnings = reactive({});
  const revisionEdits = reactive({});
  const revisionTargets = reactive({});
  const needsRevisionTarget = issue => {
    if (issue.redline) return false;
    const text = workspace.run?.input?.text || '';
    const segment = workspace.run?.result?.segments?.find(s => s.id === issue.segment_id);
    const original = issue.evidence || segment?.content;
    return !original || text.split(original).length !== 2;
  };
  const revisionTarget = issue => revisionTargets[issue.id] ||= {change_type:'replace', original_text:''};
  const targetPayload = issue => needsRevisionTarget(issue) ? {...revisionTarget(issue)} : {};

  const editingRevisionId = ref(null);
  const reviewReady = computed(
    () =>
      !!reviewResult.value &&
      workspace.run?.status === "completed" &&
      // Settings can invalidate findings without changing the document layout.
      // Changed body text still needs the current document/editor instead.
      workspace.run?.input?.text === context.contractText.value &&
      !isReviewing.value &&
      !workspace.loading,
  );
  const useRevisionDocument = computed(
    () => reviewReady.value && revisionMode.value !== "compare",
  );
  const documentIssueOrder = ref([]);
  const reviewIssues = computed(() => {
    const order = new Map(documentIssueOrder.value.map((id, index) => [id, index]));
    const normalize = (text) => (text || '').replace(/\s+/g, '');
    const text = normalize(context.contractText.value);
    const position = (issue) => {
      if (order.has(issue.id)) return order.get(issue.id);
      const evidence = normalize(issue.redline?.original_text || issue.evidence);
      const index = evidence ? text.indexOf(evidence) : -1;
      if (index >= 0) return documentIssueOrder.value.length + index;
      const segment = reviewResult.value?.segments?.find(item => item.id === issue.segment_id);
      const segmentIndex = segment ? text.indexOf(normalize(segment.content)) : -1;
      return segmentIndex >= 0 ? documentIssueOrder.value.length + segmentIndex : Number.MAX_SAFE_INTEGER;
    };
    return [...(reviewResult.value?.issues || [])].sort((a, b) => position(a) - position(b));
  });
  const originalFilteredIssues = context.filteredIssues;
  const filteredIssues = computed(() => {
    const ids = new Set(originalFilteredIssues.value.map(issue => issue.id));
    return reviewIssues.value.filter(issue => ids.has(issue.id));
  });
  const activeRevision = computed(
    () =>
      reviewIssues.value.find((issue) => issue.id === focusedIssueId.value) ||
      reviewIssues.value[0],
  );
  const revisionIndex = computed(() =>
    reviewIssues.value.findIndex(
      (issue) => issue.id === activeRevision.value?.id,
    ),
  );
  const pendingRevisionCount = computed(
    () =>
      reviewIssues.value.filter(
        (issue) =>
          !appliedIssueIds.value.includes(issue.id) &&
          workspace.decisions[issue.id] !== "rejected",
      ).length,
  );
  const revisionReadOnly = computed(
    () =>
      revisionBusy.value ||
      workspace.historical ||
      workspace.loading ||
      isReviewing.value ||
      ["running","queued"].includes(workspace.task?.status) ||
      resultStale.value,
  );
  let toastTimer;
  const message = (text) => {
    clearTimeout(toastTimer);
    context.toastMessage.value = text;
    toastTimer = setTimeout(() => {
      if (context.toastMessage.value === text) context.toastMessage.value = "";
    }, 3000);
  };
  onScopeDispose(() => clearTimeout(toastTimer));
  const frame = () => document.querySelector('iframe[title="合同修订文档"]');
  const focusDocument = (issue, scroll = true) =>
    frame()?.contentWindow?.postMessage(
      { type: "lexis-review-focus", issue: issue.id, scroll },
      location.origin,
    );

  // Comments and follow-up answers must not reload the document while someone reads it.
  const revisionDocumentUrl = computed(() => {
    const content = JSON.stringify([
      workspace.run?.id,
      (workspace.run?.result?.issues || []).map((issue) => [
        issue.id,
        issue.redline,
      ]),

    ]);
    let hash = 0;
    for (let index = 0; index < content.length; index++)
      hash = (Math.imul(31, hash) + content.charCodeAt(index)) | 0;
    return `/static/document-preview.html?review=1&readonly=1&run=${workspace.run?.id || ""}&display=${revisionMode.value === "compare" ? "markup" : revisionMode.value}&v=${hash >>> 0}`;
  });
  watch(revisionDocumentUrl, () => {
    revisionDocumentLoaded.value = false;
  });
  const syncReviewDocument = () => {
    if (!revisionDocumentLoaded.value || !useRevisionDocument.value) return;
    frame()?.contentWindow?.postMessage({type: 'lexis-review-update', run: workspace.run?.id, revision: workspace.run?.revision}, location.origin);
  };
  watch(() => workspace.run?.revision, syncReviewDocument, {flush: 'post'});
  const originalHighlight = context.highlightInContract;
  const originalSelect = context.selectIssue;
  const originalOpenEditor = context.openEditor;
  const highlightInContract = (issue) => {
    if (!useRevisionDocument.value) return originalHighlight(issue);
    focusedIssueId.value = issue.id;
    focusDocument(issue);
  };
  const selectIssue = (issueId) => {
    originalSelect(issueId);
    const issue = reviewIssues.value.find((item) => item.id === issueId);
    if (issue && useRevisionDocument.value)
      nextTick(() => focusDocument(issue));
  };
  const moveRevision = (direction) => {
    if (!reviewIssues.value.length) return;
    const index =
      (revisionIndex.value + direction + reviewIssues.value.length) %
      reviewIssues.value.length;
    selectIssue(reviewIssues.value[index].id);
  };
  const navigateByKeyboard = (event) => {
    if (
      !event.altKey ||
      !["ArrowUp", "ArrowDown"].includes(event.key) ||
      context.isReviewing.value
    )
      return;
    if (
      event.target.closest("input, textarea, select, [contenteditable]") ||
      document.querySelector('[aria-modal="true"]')
    )
      return;
    event.preventDefault();
    moveRevision(event.key === "ArrowUp" ? -1 : 1);
  };
  window.addEventListener("keydown", navigateByKeyboard);
  onScopeDispose(() =>
    window.removeEventListener("keydown", navigateByKeyboard),
  );
  watch(
    () => workspace.run?.id,
    () => {
      documentIssueOrder.value = [];
      if (!workspace.run) return;
      if (
        !reviewIssues.value.some((issue) => issue.id === focusedIssueId.value)
      )
        focusedIssueId.value = reviewIssues.value[0]?.id || null;
    },
    { flush: "post" },
  );

  const api = async (path, method, body) => {
    const response = await fetch(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok)
      throw new Error(
        typeof data.detail === "string" ? data.detail : "操作失败，请重试",
      );
    return data;
  };
  const writable = () => {
    if (revisionReadOnly.value || !workspace.run) return false;
    return true;
  };
  const setReviewDecision = async (issue, decision) => {
    if (!writable() || (decision === "applied" && !issue.redline)) return false;
    focusedIssueId.value = issue.id;
    revisionBusy.value = true;
    revisionErrors[issue.id] = "";
    const previousApplied = [...appliedIssueIds.value];
    const previousDecisions = { ...workspace.decisions };
    try {
      appliedIssueIds.value =
        decision === "applied"
          ? [...new Set([...previousApplied, issue.id])]
          : previousApplied.filter((id) => id !== issue.id);
      workspace.decisions = { ...workspace.decisions, [issue.id]: decision };
      await workspace.flush();
      focusedIssueId.value = issue.id;
      message(
        decision === "applied"
          ? "已采纳修订，当前稿已更新"
          : decision === "rejected"
            ? "已拒绝修订，保留原文"
            : "已撤销决定，恢复待采纳修订",
      );
      return true;
    } catch (error) {
      appliedIssueIds.value = previousApplied;
      workspace.decisions = previousDecisions;
      revisionErrors[issue.id] = error.message;
      return false;
    } finally {
      revisionBusy.value = false;
    }
  };
  const pendingApplicableCount = computed(
    () =>
      reviewIssues.value.filter(
        (issue) =>
          issue.redline &&
          !appliedIssueIds.value.includes(issue.id) &&
          !["applied", "rejected"].includes(workspace.decisions[issue.id]),
      ).length,
  );
  const acceptAllRevisions = async () => {
    const issues = reviewIssues.value.filter(
      (issue) =>
        issue.redline &&
        !appliedIssueIds.value.includes(issue.id) &&
        !["applied", "rejected"].includes(workspace.decisions[issue.id]),
    );
    for (const issue of issues) {
      if (!(await setReviewDecision(issue, "applied"))) return;
    }
    if (issues.length) message("已采纳 " + issues.length + " 项修订");
  };
  const pendingCriticalCount = computed(
    () =>
      reviewIssues.value.filter(
        (issue) =>
          issue.redline &&
          issue.severity === "critical" &&
          !appliedIssueIds.value.includes(issue.id) &&
          !["applied", "rejected"].includes(workspace.decisions[issue.id]),
      ).length,
  );
  const pendingLowRiskCount = computed(
    () =>
      reviewIssues.value.filter(
        (issue) =>
          issue.redline &&
          issue.severity !== "critical" &&
          !appliedIssueIds.value.includes(issue.id) &&
          !["applied", "rejected"].includes(workspace.decisions[issue.id]),
      ).length,
  );
  const acceptLowRiskRevisions = async () => {
    const issues = reviewIssues.value.filter(
      (issue) =>
        issue.redline &&
        issue.severity !== "critical" &&
        !appliedIssueIds.value.includes(issue.id) &&
        !["applied", "rejected"].includes(workspace.decisions[issue.id]),
    );
    for (const issue of issues) {
      if (!(await setReviewDecision(issue, "applied"))) return;
    }
    if (issues.length) message("已采纳 " + issues.length + " 项一般与优化建议（已保留重大风险供人工复核）");
  };
  const undoableRevisionIds = computed(() => reviewIssues.value.filter(issue =>
    appliedIssueIds.value.includes(issue.id) || ['applied', 'rejected', 'needs_review'].includes(workspace.decisions[issue.id])
  ).map(issue => issue.id));
  const undoableRevisionCount = computed(() => undoableRevisionIds.value.length);
  const undoAllReviewDecisions = async () => {
    if (!writable() || !undoableRevisionCount.value) return false;
    const identifiers = [...undoableRevisionIds.value];
    revisionBusy.value = true;
    const previousApplied = [...appliedIssueIds.value];
    const previousDecisions = { ...workspace.decisions };
    try {
      const decisions = { ...previousDecisions };
      for (const id of identifiers) decisions[id] = "pending";
      appliedIssueIds.value = [];
      workspace.decisions = decisions;
      // Persist the whole batch once, with the run revision checked by the server.
      await workspace.flush();
      message(`已撤销 ${identifiers.length} 项处理决定，恢复为待处理`);
      return true;
    } catch (error) {
      appliedIssueIds.value = previousApplied;
      workspace.decisions = previousDecisions;
      message("一键撤销失败：" + error.message);
      return false;
    } finally {
      revisionBusy.value = false;
    }
  };
  const cancelAllAcceptedRevisions = async () => {
    if (!writable() || !appliedIssueIds.value.length) return false;
    const identifiers = [...appliedIssueIds.value];
    revisionBusy.value = true;
    const previousApplied = [...appliedIssueIds.value];
    const previousDecisions = { ...workspace.decisions };
    try {
      const decisions = { ...previousDecisions };
      for (const id of identifiers) decisions[id] = "pending";
      appliedIssueIds.value = [];
      workspace.decisions = decisions;
      await workspace.flush();
      message(`已取消 ${identifiers.length} 项采纳，恢复为待处理`);
      return true;
    } catch (error) {
      appliedIssueIds.value = previousApplied;
      workspace.decisions = previousDecisions;
      message("取消采纳失败：" + error.message);
      return false;
    } finally {
      revisionBusy.value = false;
    }
  };
  const modelConfig = () => ({
    ...context.modelConfig.value,
    model_name:
      context.selectedModel.value === "custom"
        ? context.modelConfig.value.model_name
        : context.selectedModel.value,
  });
  const updateProposal = async (issue, suffix, method, body) => {
    if (!writable()) return false;
    focusedIssueId.value = issue.id;
    revisionBusy.value = true;
    revisionErrors[issue.id] = "";
    try {
      await workspace.flush();
      const data = await api(
        `/api/runs/${workspace.run.id}/issues/${issue.id}/${suffix}`,
        method,
        { revision: workspace.run.revision, ...body },
      );
      await workspace.refresh(data.id);
      revisionMode.value = "markup";
      focusedIssueId.value = issue.id;
      message("新建议已放入文档修订，请核对后采纳；上一版已保留");
      return true;
    } catch (error) {
      revisionErrors[issue.id] = error.message;
      return false;
    } finally {
      revisionBusy.value = false;
    }
  };
  const generateRevision = (issue) =>
    updateProposal(issue, "regenerate", "POST", {
      ...targetPayload(issue),
      instruction: revisionInstructions[issue.id] || "",
      model_config_data: modelConfig(),
    });
  const beginRevisionEdit = (issue) => {
    if (!writable()) return;
    context.selectIssue(issue.id);
    revisionEdits[issue.id] =
      issue.redline?.suggested_text || issue.evidence || "";
    editingRevisionId.value = issue.id;
  };
  const saveRevisionEdit = async (issue) => {
    if (
      await updateProposal(issue, "revision", "PUT", {
        ...targetPayload(issue),
        suggested_text: revisionEdits[issue.id],
      })
    )
      editingRevisionId.value = null;
  };
  const restoreRevision = (issue, version) =>
    updateProposal(issue, "revision/restore", "POST", { version });
  const exportReviewDocument = async () => {
    try {
      await workspace.flush();
      workspace.requireExport();
      const display =
        revisionMode.value === "compare" ? "markup" : revisionMode.value;
      const response = await fetch(
        `/api/runs/${workspace.run.id}/review-document?display=${display}`,
      );
      if (!response.ok)
        throw new Error((await response.json()).detail || "导出失败");
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download =
        context.contractTitle.value +
        (display === "markup"
          ? "-修订稿.docx"
          : display === "current"
            ? "-当前稿.docx"
            : "-原始稿.docx");
      anchor.click();
      message("已发起 Word 下载，请查看浏览器下载列表");
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      message(error.message);
    }
  };
  let editWhenReady = false;
  const openEditor = async () => {
    if (!useRevisionDocument.value) return originalOpenEditor();
    revisionMode.value = "compare";
    if (workspace.conditions.source_id) {
      editWhenReady = true;
      message("正在打开原排版编辑器…");
    } else {
      await nextTick();
      await originalOpenEditor();
    }
  };
  const handleMessage = (event) => {
    if (event.origin !== location.origin) return;
    const data = event.data;
    if (
      editWhenReady &&
      data?.type === "lexis-document-ready" &&
      event.source ===
        document.querySelector('iframe[title="合同原件预览"]')?.contentWindow
    ) {
      editWhenReady = false;
      originalOpenEditor();
    }
    if (
      event.source !== frame()?.contentWindow ||
      data?.run !== workspace.run?.id
    )
      return;
    if (
      data.type === "lexis-review-navigate" &&
      !isReviewing.value &&
      !document.querySelector('[aria-modal="true"]')
    )
      moveRevision(data.direction === -1 ? -1 : 1);
    if (data.type === "lexis-review-ready") {
      if (
        String(data.token) !==
        new URL(revisionDocumentUrl.value, location.origin).searchParams.get(
          "v",
        )
      )
        return;
      documentIssueOrder.value = data.order || [];
      revisionDocumentLoaded.value = true;
      revisionRenderedVersion.value = data.revision;
      Object.keys(revisionWarnings).forEach(
        (key) => delete revisionWarnings[key],
      );
      for (const warning of data.warnings || [])
        revisionWarnings[warning.id] = warning.message;
      if (activeRevision.value) focusDocument(activeRevision.value);
    }
    if (data.type === 'lexis-review-updated') {
      revisionRenderedVersion.value = data.revision;
      documentIssueOrder.value = data.order || [];
    }
    if (data.type === 'lexis-review-update-error') message('文档更新失败，请刷新重试：' + data.message);
    if (
      data.type === "lexis-review-select" ||
      data.type === "lexis-review-edit"
    ) {
      originalSelect(data.issue);
      if (data.type === "lexis-review-edit") {
        const issue = reviewIssues.value.find(
          (issue) => issue.id === data.issue,
        );
        if (issue) beginRevisionEdit(issue);
      }
    }
  };
  window.addEventListener("message", handleMessage);
  onScopeDispose(() => window.removeEventListener("message", handleMessage));
  const guard = () => {
    if (revisionBusy.value) {
      message("本条修订正在处理，请等待完成后再切换");
      return false;
    }
  };
  onBeforeRouteLeave(guard);
  onBeforeRouteUpdate(guard);
  return {
    revisionMode,
    showDocumentComparison,
    reviewReady,
    useRevisionDocument,
    revisionDocumentUrl,
    revisionBusy,
    revisionDocumentLoaded,
    revisionRenderedVersion,
    revisionInstructions,
    revisionErrors,
    revisionWarnings,
    revisionTargets, revisionTarget, needsRevisionTarget,
    revisionEdits,
    editingRevisionId,
    activeRevision,
    revisionIndex,
    reviewIssues,
    filteredIssues,
    pendingRevisionCount,
    revisionReadOnly,
    highlightInContract,
    selectIssue,
    moveRevision,
    setReviewDecision,
    pendingApplicableCount,
    acceptAllRevisions,
    pendingCriticalCount,
    pendingLowRiskCount,
    acceptLowRiskRevisions,
    undoAllReviewDecisions,
    cancelAllAcceptedRevisions,
    undoableRevisionCount,
    generateRevision,
    beginRevisionEdit,
    saveRevisionEdit,
    restoreRevision,
    exportReviewDocument,
    openEditor,
  };
}
