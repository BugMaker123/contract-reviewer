import {
  ref,
  computed,
  onMounted,
  onScopeDispose,
  nextTick,
  watch,
  reactive,
} from "vue";
import { onBeforeRouteLeave, onBeforeRouteUpdate } from "vue-router";
import { createWorkspaceWorkbench } from "./useWorkspace.js";
import { LexisSession } from "../services/session.js";

export function useWorkbench() {
  const contractTitle = ref("未命名合同");
  const contractType = ref("商务合作协议");
  const partyRole = ref("乙方(卖方/开发方/服务方)");
  const contractText = ref("");
  const selectedModel = ref(
    localStorage.getItem("LEXIS_MODEL_NAME") || "deepseek-chat",
  );
  const selectedSampleKey = ref("");
  const reviewProgress = ref(0);

  const isReviewing = ref(false);
  const viewMode = ref("raw");
  const opinionsOpen = ref(true);
  const summaryOpen = ref(true);
  const fitDocuments = () =>
    nextTick(() =>
      requestAnimationFrame(() => {
        for (const title of ["原始合同文档", "合同原件预览"])
          document
            .querySelector(`iframe[title="${title}"]`)
            ?.contentWindow?.postMessage(
              documentCompare.value
                ? {
                    type: "lexis-set-zoom",
                    scale: summaryOpen.value && opinionsOpen.value ? 0.8 : 1,
                  }
                : { type: "lexis-fit-width" },
              location.origin,
            );
      }),
    );
  const toggleSummary = () => {
    summaryOpen.value = !summaryOpen.value;
    fitDocuments();
  };
  const toggleOpinions = () => {
    opinionsOpen.value = !opinionsOpen.value;
    fitDocuments();
  };
  const openOpinions = () => {
    opinionsOpen.value = true;
    fitDocuments();
  };
  const closeOpinions = () => {
    opinionsOpen.value = false;
    fitDocuments();
  };
  const documentCompare = ref(false);
  const reviewBaseline = ref({ sourceId: null, text: "" });
  const revisionScope = ref("all");
  const previewText = ref(null);
  const documentDraft = ref(null),
    documentSaving = ref(false);
  const focusedClauseId = ref(null);
  const focusedIssueId = ref(null);
  const clauseEdit = ref(null);
  const severityFilter = ref("all");
  const appliedIssueIds = ref([]);

  const showModelModal = ref(false);
  const showReportModal = ref(false);
  const isTestingModel = ref(false);
  const testResult = ref(null);
  const toastMessage = ref("");

  const latestLogMessage = ref("");
  const reviewTrace = ref([]);
  const publicAnalysis = computed(() => {
    const attempt = Math.max(
      1,
      ...reviewTrace.value.map((item) => item.attempt || 0),
    );
    return reviewTrace.value.filter(
      (item) => item.stage === "analysis_summary" && item.attempt === attempt,
    );
  });

  const modelConfig = ref({
    model_name: localStorage.getItem("LEXIS_MODEL_NAME") || "deepseek-v4-flash",
    base_url:
      localStorage.getItem("LEXIS_BASE_URL") || "https://api.deepseek.com/v1",
    api_key: localStorage.getItem("LEXIS_API_KEY") || "",
    max_retries: Number(localStorage.getItem("LEXIS_MAX_RETRIES") ?? 3),
  });

  const sampleContracts = ref({});

  const pipelineNodes = ref([
    {
      id: "segment_contract",
      name: "条款切片与解构",
      description: "识别条款编号与法律业务要素",
    },
    {
      id: "compliance_check",
      name: "强制法规范排查",
      description: "民法典格式条款效力核验",
    },
    {
      id: "balance_review",
      name: "商业权责对等审查",
      description: "排查单方无限责任与陷阱",
    },
    {
      id: "aggregate_and_redline",
      name: "红线修订与Diff对照",
      description: "生成可替代的修正条款",
    },
    {
      id: "synthesize_summary",
      name: "量化评分与总评意见",
      description: "生成综合评分与审查意见书",
    },
  ]);

  const nodeStates = ref({
    segment_contract: "idle",
    compliance_check: "idle",
    balance_review: "idle",
    aggregate_and_redline: "idle",
    synthesize_summary: "idle",
  });

  const reviewResult = ref(null);
  const issueSearch = ref("");
  const handlingFilter = ref("all");
  const reviewError = ref("");
  const reviewedAt = ref("");
  const reviewedInput = ref(null);
  const saveStatus = ref("当前会话自动保存");
  const showEditor = ref(false),
    editText = ref(""),
    editTitle = ref(""),
    editType = ref("");
  const severityLabel = LexisSession.severityLabel;
  let controller = null;
  const resultStale = computed(
    () =>
      !!reviewResult.value &&
      (!reviewedInput.value ||
        reviewedInput.value.text !== contractText.value ||
        reviewedInput.value.role !== partyRole.value ||
        reviewedInput.value.title !== contractTitle.value ||
        reviewedInput.value.type !== contractType.value ||
        workspace.isStale),
  );
  const persist = () => {
    try {
      LexisSession.write("LEXIS_WORK", {
        title: contractTitle.value,
        type: contractType.value,
        role: partyRole.value,
        text: contractText.value,
        result: reviewResult.value,
        applied: appliedIssueIds.value,
        reviewedAt: reviewedAt.value,
        reviewedInput: reviewedInput.value,
      });
      if (!workspace.taskId) saveStatus.value = "待保存到审查记录";
    } catch {
      saveStatus.value = "保存失败，请导出备份";
    }
  };
  watch(
    [
      contractTitle,
      contractType,
      partyRole,
      contractText,
      reviewResult,
      appliedIssueIds,
      reviewedAt,
    ],
    persist,
    { deep: true },
  );
  const readInlineSnapshot = () => {
    try {
      const snapshot = document
        .querySelector('iframe[title="合同原件预览"]')
        ?.contentWindow?.getLexisDocumentSnapshot?.();
      return snapshot?.source === workspace.conditions.source_id
        ? snapshot
        : null;
    } catch {
      return null;
    }
  };
  const currentDocumentText = () => {
    const snapshot = readInlineSnapshot();
    if (snapshot?.editing) return snapshot.text;
    if (documentDraft.value?.source === workspace.conditions.source_id)
      return documentDraft.value.text;
    return documentCompare.value && !resultStale.value && reviewResult.value
      ? (previewText.value ??
          revisedText(
            revisionScope.value === "all"
              ? reviewResult.value.issues
                  .filter((issue) => issue.redline)
                  .map((issue) => issue.id)
              : appliedIssueIds.value,
          ))
      : contractText.value;
  };
  const openEditor = async () => {
    if (
      viewMode.value === "original" &&
      (
        await (
          await fetch("/api/sources/" + workspace.conditions.source_id)
        ).json()
      ).extension !== ".txt"
    ) {
      document
        .querySelector('iframe[title="合同原件预览"]')
        ?.contentWindow.postMessage({ type: "lexis-edit" }, location.origin);
      return;
    }
    editText.value = currentDocumentText();
    editTitle.value = contractTitle.value;
    editType.value = contractType.value;
    showEditor.value = true;
  };
  let pendingEditLocation = null;
  const saveFormattedText = async (text) => {
    if (!workspace.conditions.source_id) return false;
    if (documentSaving.value) throw new Error("文档正在保存，请稍后重试");
    documentSaving.value = true;
    const sourceId = workspace.conditions.source_id,
      snapshot = readInlineSnapshot();
    const beforeText =
      snapshot?.editing && snapshot.text === text
        ? snapshot.baseText
        : currentDocumentText();
    const editorWindow = document.querySelector(
      'iframe[title="合同原件预览"]',
    )?.contentWindow;
    editorWindow?.setLexisDocumentSaving?.(true);
    try {
      const info = await (await fetch("/api/sources/" + sourceId)).json();
      if (info.extension === ".txt") return false;
      const response = await fetch(`/api/sources/${sourceId}/edit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "文档保存失败");
      if (workspace.conditions.source_id !== sourceId)
        throw new Error("文档版本已变化，请重新打开编辑器");
      const before = beforeText.split("\n"),
        after = data.text.split("\n");
      const index = after.findIndex((line, i) => line !== before[i]);
      pendingEditLocation =
        index >= 0
          ? {
              source: data.source_id,
              index,
              text: after[index],
              scroll: editorWindow?.scrollY || 0,
            }
          : null;
      documentDraft.value = null;
      workspace.conditions.source_id = data.source_id;
      contractText.value = data.text;
      previewText.value = data.text;
      await workspace.flush();
      viewMode.value = "original";
      return true;
    } finally {
      documentSaving.value = false;
      editorWindow?.setLexisDocumentSaving?.(false);
    }
  };
  const commitInlineDraft = async () => {
    const snapshot = readInlineSnapshot();
    if (!snapshot?.editing) return false;
    await saveFormattedText(snapshot.text);
    return true;
  };
  const saveDocument = async () => {
    try {
      await commitInlineDraft();
      await workspace.save();
    } catch (error) {
      showToast(error.message);
    }
  };
  const exportDocument = async () => {
    try {
      await commitInlineDraft();
      await workspace.exportDocument();
    } catch (error) {
      showToast(error.message);
    }
  };
  const saveEditor = async () => {
    if (editText.value.length > 200000) {
      showToast("正文超过 20 万字，请拆分后审查");
      return;
    }

    try {
      const formatted = await saveFormattedText(editText.value);
      contractText.value = editText.value;
      contractTitle.value = editTitle.value;
      contractType.value = editType.value;
      showEditor.value = false;
      if (!formatted) viewMode.value = "raw";
      showToast("已更新正文，请重新审查当前版本");
    } catch (error) {
      showToast(error.message);
    }
  };
  const openClauseEditor = async (issue) => {
    if (workspace.historical || workspace.loading || isReviewing.value) return;
    let original = issue.redline?.original_text || issue.evidence;
    const suggested = issue.redline?.suggested_text;
    if (
      !resultStale.value &&
      suggested &&
      currentDocumentText().split(suggested).length === 2 &&
      (!original || currentDocumentText().split(original).length !== 2)
    )
      original = suggested;
    {
      // Resolve the current DOCX paragraphs even when old evidence is still a substring.
      // Appending text leaves the old quote intact but does not make it the current clause.
      const baseline = reviewedInput.value?.text;
      const start = original && baseline?.indexOf(original);
      if (
        typeof start === "number" &&
        start >= 0 &&
        baseline.indexOf(original, start + 1) < 0 &&
        workspace.conditions.source_id
      ) {
        try {
          const info = await (
            await fetch("/api/sources/" + workspace.conditions.source_id)
          ).json();
          const before = baseline.split("\n"),
            after = currentDocumentText().split("\n");
          if (info.extension === ".docx" && before.length === after.length) {
            const first = baseline.slice(0, start).split("\n").length - 1;
            const last =
              baseline.slice(0, start + original.length - 1).split("\n")
                .length - 1;
            original = after.slice(first, last + 1).join("\n");
          }
        } catch (error) {
          showToast("无法读取当前文档，请重试");
          return;
        }
      }
    }
    if (!original || currentDocumentText().split(original).length !== 2) {
      showToast("该项无法唯一定位，请通过编辑正文人工核对");
      return;
    }
    clauseEdit.value = {
      original,
      text: original,
      title: issue.clause_title,
      baseText: currentDocumentText(),
    };
  };
  const saveClauseEditor = async () => {
    if (
      !clauseEdit.value ||
      currentDocumentText().split(clauseEdit.value.original).length !== 2
    ) {
      showToast("原文已变更，请重新定位");
      return;
    }
    try {
      const text = currentDocumentText().replace(
        clauseEdit.value.original,
        clauseEdit.value.text,
      );
      const formatted = await saveFormattedText(text);
      contractText.value = text;
      if (!formatted) viewMode.value = "raw";
      clauseEdit.value = null;
      showToast("已更新正文，请重新审查当前版本");
    } catch (error) {
      showToast(error.message);
    }
  };
  const cancelReview = () => {
    if (controller) controller.abort();
  };
  const exportContract = () => {
    if (resultStale.value) {
      showToast("审查信息已变更，请重新审查后导出修订稿");
      return;
    }
    const url = URL.createObjectURL(
      new Blob([finalizedContractText.value], {
        type: "text/plain;charset=utf-8",
      }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = (contractTitle.value || "合同") + "-修订稿.txt";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const reviewSource = computed(() => {
    const detail =
      reviewResult.value?.logs?.find((log) => log.node === "balance_review")
        ?.detail || "";
    return detail.match(/\[(.*?)\]/)?.[1] || "未记录";
  });
  const currentTaxSettlement = computed(() => {
    if (!reviewResult.value) return null;
    return (
      reviewResult.value.tax_settlement ||
      reviewResult.value.summary?.tax_settlement ||
      null
    );
  });

  const showToast = (msg) => {
    toastMessage.value = msg;
    setTimeout(() => {
      toastMessage.value = "";
    }, 2500);
  };

  const workspace = reactive(
    createWorkspaceWorkbench({
      contractTitle,
      contractType,
      contractText,
      partyRole,
      reviewResult,
      appliedIssueIds,
      reviewedAt,
      reviewedInput,
      saveStatus,
      isReviewing,
      showToast,
      getPreviewExport: () =>
        documentCompare.value && !resultStale.value && workspace.run
          ? { run: workspace.run.id, scope: revisionScope.value }
          : null,
      copyText: (text) => copyText(text),
      getModel: () => ({
        ...modelConfig.value,
        model_name:
          selectedModel.value === "custom"
            ? modelConfig.value.model_name
            : selectedModel.value,
      }),
    }),
  );

  const defaultPipeline = pipelineNodes.value.map((node) => ({ ...node }));
  watch(
    () => workspace.conditions.mode,
    (mode) => {
      const labels =
        mode === "checklist"
          ? [
              "合同条款解析",
              "载入企业清单",
              "逐项核验要求",
              "整理问题与证据",
              "汇总清单结果",
            ]
          : mode === "compare"
            ? [
                "解析待审合同",
                "载入参考合同",
                "逐条比对差异",
                "整理变更与证据",
                "汇总对比结果",
              ]
            : null;
      pipelineNodes.value = defaultPipeline.map((node, index) =>
        labels
          ? { ...node, name: labels[index], description: "" }
          : { ...node },
      );
    },
  );

  // 强健的正文行级高亮计算器
  const formattedLines = computed(() => {
    if (!contractText.value) return [];
    const lines = currentDocumentText().split("\n");
    const issues = resultStale.value ? [] : reviewResult.value?.issues || [];

    return lines.map((line, idx) => {
      let highlightClass = "";
      let severity = null;
      let issueId = null;
      let segmentId = null;
      const trimmedLine = line.trim();

      if (issues.length > 0 && trimmedLine.length > 0) {
        for (const issue of issues) {
          if (
            issue.evidence &&
            trimmedLine.length >= 5 &&
            issue.evidence.includes(trimmedLine)
          ) {
            severity = issue.severity;
            issueId = issue.id;
            segmentId = issue.segment_id;
            break;
          }
          // 1. 红线原文字符串匹配
          if (issue.redline && issue.redline.original_text) {
            const origClean = issue.redline.original_text.replace(/\s+/g, "");
            const lineClean = trimmedLine.replace(/\s+/g, "");

            if (lineClean.length >= 5 && origClean.includes(lineClean)) {
              severity = issue.severity;
              issueId = issue.id;
              segmentId = issue.segment_id;
              break;
            }
            if (
              trimmedLine.includes(issue.redline.original_text.slice(0, 14))
            ) {
              severity = issue.severity;
              issueId = issue.id;
              segmentId = issue.segment_id;
              break;
            }
          }

          // 2. 条款标题行精准命中
          if (
            issue.clause_title &&
            trimmedLine.includes(issue.clause_title.trim())
          ) {
            severity = issue.severity;
            issueId = issue.id;
            segmentId = issue.segment_id;
            break;
          }
        }
      }

      if (severity === "critical") highlightClass = "clause-critical";
      else if (severity === "warning") highlightClass = "clause-warning";
      else if (severity) highlightClass = "clause-info";

      return {
        text: line,
        highlightClass,
        severity,
        issueId,
        segmentId,
      };
    });
  });

  const filteredIssues = computed(() => {
    const rank = { critical: 0, warning: 1, info: 2, favorable: 3 };
    return (reviewResult.value?.issues || [])
      .filter(
        (issue) =>
          (severityFilter.value === "all" ||
            issue.severity === severityFilter.value) &&
          (handlingFilter.value === "all" ||
            (handlingFilter.value === "applied"
              ? appliedIssueIds.value.includes(issue.id)
              : !appliedIssueIds.value.includes(issue.id) &&
                (workspace.decisions[issue.id] || "pending") ===
                  handlingFilter.value)) &&
          (!issueSearch.value.trim() ||
            [
              issue.clause_title,
              issue.issue_title,
              issue.risk_analysis,
              issue.legal_basis,
            ]
              .join(" ")
              .toLowerCase()
              .includes(issueSearch.value.trim().toLowerCase())),
      )
      .sort((a, b) => (rank[a.severity] ?? 4) - (rank[b.severity] ?? 4));
  });

  const revisedText = (ids) => {
    let text = reviewedInput.value?.text || contractText.value;
    for (const id of ids) {
      const issue = reviewResult.value?.issues.find((i) => i.id === id);
      const redline = issue?.redline;
      if (!redline) continue;
      if (redline.change_type === "insert")
        text += "\n" + redline.suggested_text;
      else
        text = text.replace(
          redline.original_text,
          redline.change_type === "delete" ? "" : redline.suggested_text,
        );
    }
    return text;
  };
  const finalizedContractText = computed(() =>
    revisedText(appliedIssueIds.value),
  );

  const fetchSamples = async () => {
    const pending = LexisSession.read("LEXIS_PENDING_CONTRACT");
    const saved = pending || LexisSession.read("LEXIS_WORK");
    if (saved) {
      contractTitle.value = saved.title || "未命名合同";
      contractType.value = saved.type || "商务合作协议";
      partyRole.value = saved.role || partyRole.value;
      contractText.value = saved.text || "";
      reviewResult.value = saved.result || null;
      appliedIssueIds.value = saved.applied || [];
      reviewedAt.value = saved.reviewedAt || "";
      reviewedInput.value = saved.reviewedInput || null;
      if (saved.result) {
        reviewProgress.value = 100;
        Object.keys(nodeStates.value).forEach(
          (key) => (nodeStates.value[key] = "completed"),
        );
      }
      if (pending) sessionStorage.removeItem("LEXIS_PENDING_CONTRACT");
    }
    try {
      const res = await fetch("/api/samples");
      const data = await res.json();
      if (data.success) sampleContracts.value = data.samples;
    } catch {
      /* Existing work remains usable if examples are unavailable. */
    }
  };

  const loadSample = (key) => {
    selectedSampleKey.value = key;
    const sample = sampleContracts.value[key];
    if (!sample) return;
    contractTitle.value = sample.title;
    contractType.value = sample.type;
    partyRole.value = sample.recommended_role;
    contractText.value = sample.text;
    reviewResult.value = null;
    appliedIssueIds.value = [];
    resetNodeStates();
    showToast("已载入范本：" + sample.title);
  };

  const resetNodeStates = () => {
    for (const key in nodeStates.value) {
      nodeStates.value[key] = "idle";
    }
    reviewProgress.value = 0;
    latestLogMessage.value = "";
  };

  const clearText = () => {
    contractText.value = "";
    appliedIssueIds.value = [];
    reviewResult.value = null;
    resetNodeStates();
  };

  // 核心审查执行函数：带专业蒙版遮罩、平滑进度流转与彻底去除原生弹窗
  const startReview = async () => {
    if (
      !contractText.value.trim() ||
      isReviewing.value ||
      workspace.loading ||
      workspace.historical
    )
      return;
    try {
      await commitInlineDraft();
      await workspace.flush();
    } catch (error) {
      showToast(error.message);
      return;
    }
    const previousComparison = {
      baseline: { ...reviewBaseline.value },
      enabled: documentCompare.value,
    };
    reviewBaseline.value = {
      sourceId: workspace.conditions.source_id,
      text: contractText.value,
    };
    documentCompare.value = true;
    summaryOpen.value = true;
    opinionsOpen.value = true;
    pendingInitialRiskFocus = true;
    comparisonTexts.original = reviewBaseline.value.text;
    comparisonTexts.revised = null;
    comparisonData = null;
    comparisonSignature = "";
    comparisonGeneration++;
    previewText.value = null;
    const previousResult = reviewResult.value,
      previousApplied = [...appliedIssueIds.value];

    isReviewing.value = true;
    resetNodeStates();
    appliedIssueIds.value = [];

    reviewError.value = "";
    reviewTrace.value = [];
    reviewResult.value = null;
    controller = new AbortController();
    nodeStates.value.segment_contract = "running";
    latestLogMessage.value = "正在解析合同正文…";

    const payload = {
      contract_title: contractTitle.value,
      contract_type: contractType.value,
      party_role: partyRole.value,
      contract_text: contractText.value,
      model_config_data: {
        model_name:
          selectedModel.value === "custom"
            ? modelConfig.value.model_name
            : selectedModel.value,
        api_key: modelConfig.value.api_key,
        base_url: modelConfig.value.base_url,
        temperature: 0.1,
        max_retries: modelConfig.value.max_retries,
      },
    };

    try {
      const res = await fetch(
        "/api/tasks/" + workspace.taskId + "/review/stream",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          signal: controller.signal,
        },
      );
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(
          errorData.detail || "审查请求失败（" + res.status + "）",
        );
      }
      const reader = res.body.getReader(),
        decoder = new TextDecoder();
      let buffer = "",
        completed = false,
        completedRunId = null;
      const consume = (block) => {
        const event = block
          .split("\n")
          .find((line) => line.startsWith("event:"))
          ?.slice(6)
          .trim();
        const json = block
          .split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trim())
          .join("\n");
        if (!json) return;
        const data = JSON.parse(json);
        if (event === "progress") {
          reviewTrace.value.push(data);
          latestLogMessage.value = data.detail;
          nextTick(() => {
            const list = document.querySelector("[data-review-trace]");
            if (list) list.scrollTop = list.scrollHeight;
          });
        }
        if (event === "error") throw new Error(data.error || "审查失败");
        if (event === "node_update") {
          reviewTrace.value.push({
            stage: data.node,
            detail: data.log?.detail || "阶段已完成",
            time: new Date().toISOString(),
          });
          nodeStates.value[data.node] = "completed";
          const idx = pipelineNodes.value.findIndex(
            (node) => node.id === data.node,
          );
          reviewProgress.value = Math.min(
            95,
            Math.round(((idx + 1) / pipelineNodes.value.length) * 100),
          );
          if (idx + 1 < pipelineNodes.value.length)
            nodeStates.value[pipelineNodes.value[idx + 1].id] = "running";
          latestLogMessage.value = data.log?.detail || "正在执行下一步…";
        }
        if (event === "complete") {
          if (!data.success || !data.data?.summary)
            throw new Error("未返回有效审查结果");
          reviewResult.value = data.data;
          completed = true;
          completedRunId = data.run_id;
          reviewedAt.value = new Date().toLocaleString("zh-CN", {
            timeZone: "Asia/Shanghai",
          });
          reviewedInput.value = {
            text: payload.contract_text,
            title: payload.contract_title,
            type: payload.contract_type,
            role: payload.party_role,
          };
          reviewProgress.value = 100;
          showToast(
            "审查完成，共 " + (data.data.issues || []).length + " 项意见",
          );
        }
      };
      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder
          .decode(value || new Uint8Array(), { stream: !done })
          .replace(/\r/g, "");
        let boundary;
        while ((boundary = buffer.indexOf("\n\n")) >= 0) {
          consume(buffer.slice(0, boundary));
          buffer = buffer.slice(boundary + 2);
        }
        if (done) break;
      }
      if (!completed) throw new Error("连接中断，未收到完整结果，请重试");
      await workspace.refresh(completedRunId);
      summaryOpen.value = true;
      opinionsOpen.value = true;
      fitDocuments();
    } catch (err) {
      reviewBaseline.value = previousComparison.baseline;
      documentCompare.value = previousComparison.enabled;
      comparisonTexts.original = previousComparison.baseline.text;
      comparisonTexts.revised = null;
      comparisonData = null;
      comparisonSignature = "";
      comparisonGeneration++;
      reviewResult.value = previousResult;
      appliedIssueIds.value = previousApplied;
      reviewError.value =
        err.name === "AbortError"
          ? "已取消本次审查，可重新开始。"
          : err.message;
      latestLogMessage.value = reviewError.value;
      try {
        await workspace.refresh();
      } catch {}
      for (const key in nodeStates.value)
        if (nodeStates.value[key] === "running") nodeStates.value[key] = "idle";
      showToast(reviewError.value);
    } finally {
      isReviewing.value = false;
      controller = null;
      persist();
    }
  };

  const reviewAcceptedDraft = async () => {
    if (
      resultStale.value ||
      workspace.historical ||
      !appliedIssueIds.value.length
    )
      return;
    contractText.value = finalizedContractText.value;
    viewMode.value = "raw";
    await startReview();
  };

  const highlightInContract = (issue) => {
    if (viewMode.value === "original") {
      focusedClauseId.value = issue.segment_id;
      focusedIssueId.value = issue.id;
      const frame = document.querySelector('iframe[title="合同原件预览"]');
      const originalText = issue.redline?.original_text || issue.evidence || "";
      document
        .querySelector('iframe[title="原始合同文档"]')
        ?.contentWindow?.postMessage(
          { type: "lexis-locate", text: originalText },
          location.origin,
        );
      frame?.contentWindow?.postMessage(
        {
          type: "lexis-locate",
          text:
            documentCompare.value && !resultStale.value
              ? issue.redline?.suggested_text || originalText
              : originalText,
        },
        location.origin,
      );
      return;
    }
    viewMode.value = "raw";
    focusedClauseId.value = issue.segment_id;
    focusedIssueId.value = issue.id;
    nextTick(() => {
      const target = formattedLines.value.find(
        (l) =>
          l.issueId === issue.id ||
          (issue.segment_id && l.segmentId === issue.segment_id),
      );
      if (target) {
        const lineIdx = formattedLines.value.indexOf(target);
        const el = document.getElementById("line-" + (lineIdx + 1));
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }
    });
  };

  const selectIssue = (issueId) => {
    opinionsOpen.value = true;
    focusedIssueId.value = issueId;
    severityFilter.value = "all";
    handlingFilter.value = "all";
    issueSearch.value = "";
    nextTick(() => {
      const card = document.getElementById("card-" + issueId);
      if (card) {
        card.scrollIntoView({ behavior: "smooth", block: "nearest" });
        card.classList.add("ring-2", "ring-blue-600");
        setTimeout(
          () => card.classList.remove("ring-2", "ring-blue-600"),
          2000,
        );
      }
    });
  };

  // 采纳修订：直接替换原文对应内容
  const applyRedline = async (issue) => {
    if (resultStale.value || workspace.historical || !issue.redline) return;
    if (appliedIssueIds.value.includes(issue.id)) {
      const remaining = appliedIssueIds.value.filter((id) => id !== issue.id);
      // Removing an earlier edit must not silently invalidate a later edit.
      let text = reviewedInput.value?.text ?? contractText.value;
      for (const id of remaining) {
        const redline = reviewResult.value.issues.find(
          (i) => i.id === id,
        )?.redline;
        if (!redline) continue;
        if (
          redline.change_type !== "insert" &&
          (!redline.original_text || !text.includes(redline.original_text))
        ) {
          showToast("后续修订依赖此项，请先撤销后续采纳项");
          return;
        }
        text =
          redline.change_type === "insert"
            ? text + "\n" + redline.suggested_text
            : text.replace(
                redline.original_text,
                redline.change_type === "delete" ? "" : redline.suggested_text,
              );
      }
      appliedIssueIds.value = remaining;
      await workspace.save();
      viewMode.value = workspace.conditions.source_id ? "original" : "raw";
      showToast("已撤销采纳，合同文档已更新");
      return;
    }
    const redline = issue.redline,
      text = finalizedContractText.value;
    if (redline.change_type !== "insert") {
      const original = redline.original_text;
      if (!original || !text.includes(original)) {
        showToast("无法匹配原文，可能与已采纳修订冲突，请人工核对");
        return;
      }
      if (text.indexOf(original) !== text.lastIndexOf(original)) {
        showToast("原文存在多处相同内容，请人工核对后编辑");
        return;
      }
    }
    appliedIssueIds.value = [...appliedIssueIds.value, issue.id];
    await workspace.save();
    viewMode.value = workspace.conditions.source_id ? "original" : "raw";
    showToast("已采纳，合同文档已更新");
  };

  const copyText = async (txt) => {
    try {
      await navigator.clipboard.writeText(txt);
      showToast("修订建议已复制");
    } catch {
      showToast("复制失败，请手动选中并复制文本");
    }
  };

  const openModelModal = () => {
    if (selectedModel.value !== "custom")
      modelConfig.value.model_name = selectedModel.value;
    showModelModal.value = true;
    testResult.value = null;
  };

  const saveModelConfig = () => {
    localStorage.setItem("LEXIS_API_KEY", modelConfig.value.api_key || "");
    modelConfig.value.max_retries = Math.max(
      0,
      Math.min(10, Math.trunc(Number(modelConfig.value.max_retries) || 0)),
    );
    localStorage.setItem(
      "LEXIS_MAX_RETRIES",
      String(modelConfig.value.max_retries),
    );
    localStorage.setItem(
      "LEXIS_BASE_URL",
      modelConfig.value.base_url || "https://api.deepseek.com/v1",
    );
    localStorage.setItem(
      "LEXIS_MODEL_NAME",
      modelConfig.value.model_name || "deepseek-v4-flash",
    );
    selectedModel.value = modelConfig.value.model_name;
    showModelModal.value = false;
    showToast("模型与端点参数已成功保存！");
  };

  const testModelConnection = async () => {
    isTestingModel.value = true;
    testResult.value = null;
    try {
      const res = await fetch("/api/model/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_name: modelConfig.value.model_name,
          api_key: modelConfig.value.api_key,
          base_url: modelConfig.value.base_url,
        }),
      });
      testResult.value = await res.json();
    } catch (e) {
      testResult.value = { success: false, message: "请求失败: " + e.message };
    } finally {
      isTestingModel.value = false;
    }
  };

  const getScoreColor = (score) => {
    if (score == null) return "text-slate-400";
    if (score < 60) return "text-red-600";
    if (score < 80) return "text-amber-600";
    return "text-emerald-600";
  };

  const resetToDefault = () => {
    loadSample("business_cooperation_contract");
  };

  let comparisonData = null,
    comparisonSignature = "",
    comparisonGeneration = 0;
  let pendingInitialRiskFocus = false;
  const comparisonTexts = { original: null, revised: null };
  let differenceTimer;
  const scheduleDifferences = () => {
    clearTimeout(differenceTimer);
    comparisonGeneration++;
    differenceTimer = setTimeout(refreshDocumentDifferences, 100);
  };
  const refreshDocumentDifferences = async () => {
    if (
      !documentCompare.value ||
      comparisonTexts.original === null ||
      comparisonTexts.revised === null
    )
      return;
    const signature = JSON.stringify(comparisonTexts);
    if (signature === comparisonSignature && comparisonData) return;
    comparisonSignature = signature;
    const generation = ++comparisonGeneration;
    comparisonData = null;
    try {
      const response = await fetch("/api/documents/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          original: comparisonTexts.original,
          revised: comparisonTexts.revised,
        }),
      });
      if (!response.ok) throw new Error("差异标记加载失败");
      const data = await response.json();
      if (generation !== comparisonGeneration) return;
      comparisonData = data;
      const issues = (reviewResult.value?.issues || [])
        .filter((issue) => issue.severity !== "favorable")
        .map((issue) => {
          const original = issue.redline?.original_text || issue.evidence || "";
          const start = original
            ? comparisonTexts.original.indexOf(original)
            : -1;
          let range = null;
          if (
            start >= 0 &&
            comparisonTexts.original.indexOf(original, start + 1) < 0
          ) {
            const first =
              comparisonTexts.original.slice(0, start).split("\n").length - 1;
            const last =
              comparisonTexts.original
                .slice(0, start + original.length - 1)
                .split("\n").length - 1;
            const mapped = data.original_map.slice(first, last + 1);
            range = {
              original_start: first,
              original_end: last + 1,
              revised_start: Math.min(...mapped),
              revised_end: Math.max(...mapped) + 1,
            };
          }
          return {
            original,
            revised: issue.redline?.suggested_text || original,
            range,
          };
        });
      const focusFirst = pendingInitialRiskFocus && issues.length > 0;
      if (issues.length) pendingInitialRiskFocus = false;
      for (const [title, side] of [
        ["原始合同文档", "original"],
        ["合同原件预览", "revised"],
      ])
        document
          .querySelector(`iframe[title="${title}"]`)
          ?.contentWindow?.postMessage(
            {
              type: "lexis-mark-differences",
              side,
              changes: data.changes,
              charRanges: data[side + "_chars"],
              text: comparisonTexts[side],
              issues,
              focusFirst,
            },
            location.origin,
          );
    } catch (error) {
      showToast(error.message);
    }
  };
  const handleMessage = async (event) => {
    const frame = document.querySelector('iframe[title="合同原件预览"]');
    const originalFrame = document.querySelector(
      'iframe[title="原始合同文档"]',
    );
    const isOriginal = event.source === originalFrame?.contentWindow;
    if (
      event.origin !== location.origin ||
      (!isOriginal && event.source !== frame?.contentWindow)
    )
      return;
    if (
      event.data?.type === "lexis-document-draft" &&
      !isOriginal &&
      event.data.source === workspace.conditions.source_id
    ) {
      documentDraft.value = event.data.editing
        ? { source: event.data.source, text: event.data.text }
        : null;
      if (documentCompare.value) {
        comparisonTexts.revised = event.data.text;
        scheduleDifferences();
      }
      return;
    }
    if (event.data?.type === "lexis-document-scroll" && documentCompare.value) {
      const target = isOriginal ? frame : originalFrame;
      const map = isOriginal
        ? comparisonData?.original_map
        : comparisonData?.revised_map;
      target?.contentWindow?.postMessage(
        {
          type: "lexis-sync-scroll",
          ratio: event.data.ratio,
          index: map?.[event.data.index],
          fraction: event.data.fraction,
        },
        location.origin,
      );
      return;
    }
    if (event.data?.type === "lexis-document-ready" && documentCompare.value) {
      event.source?.postMessage(
        {
          type: "lexis-set-zoom",
          scale: summaryOpen.value && opinionsOpen.value ? 0.8 : 1,
        },
        location.origin,
      );
      if (isOriginal && event.data.source === reviewBaseline.value.sourceId)
        comparisonTexts.original = event.data.text;
      else if (
        !isOriginal &&
        event.data.source === workspace.conditions.source_id
      )
        comparisonTexts.revised = event.data.text;
      comparisonSignature = "";
      refreshDocumentDifferences();
    }
    if (isOriginal) return;
    if (
      event.data?.type === "lexis-document-ready" &&
      event.data.source === workspace.conditions.source_id
    )
      documentDraft.value = null;
    if (
      event.data?.type === "lexis-document-ready" &&
      documentCompare.value &&
      !resultStale.value &&
      event.data.run === workspace.run?.id
    )
      previewText.value = event.data.text;
    if (
      event.data?.type === "lexis-document-ready" &&
      pendingEditLocation?.source === event.data.source &&
      workspace.conditions.source_id === event.data.source
    ) {
      frame.contentWindow.postMessage(
        { type: "lexis-locate-edit", ...pendingEditLocation },
        location.origin,
      );
      pendingEditLocation = null;
    }
    if (event.data?.type === "lexis-save-document") {
      try {
        if (workspace.historical || workspace.loading || isReviewing.value)
          throw new Error("当前版本不能编辑");
        if (event.data.source !== workspace.conditions.source_id)
          throw new Error("文档版本已变化，请重新打开编辑器");
        await saveFormattedText(event.data.text);
        showToast("文档已保留排版保存，请重新审查");
      } catch (error) {
        frame.contentWindow.postMessage(
          { type: "lexis-save-error", message: error.message },
          location.origin,
        );
      }
    }
  };
  window.addEventListener("message", handleMessage);
  const closeMenus = (event) => {
    document.querySelectorAll("details.wb-menu[open]").forEach((menu) => {
      if (!menu.contains(event.target)) menu.open = false;
    });
  };
  document.addEventListener("click", closeMenus);
  const handleKeydown = (event) => {
    if (event.key === "Escape")
      document
        .querySelectorAll("details.wb-menu[open]")
        .forEach((menu) => (menu.open = false));
  };
  document.addEventListener("keydown", handleKeydown);
  onMounted(() => {
    if (workspace.taskId)
      workspace.load().then(() => {
        reviewTrace.value =
          workspace.run?.audit_trace || reviewResult.value?.audit_trace || [];
        if (resultStale.value && workspace.task?.source_matches)
          viewMode.value = "original";
        else if (
          workspace.conditions.source_id &&
          (workspace.historical || workspace.task?.source_matches !== false)
        )
          viewMode.value = "original";
        if (reviewResult.value) {
          // Restore the comparison from the durable review snapshot, not the
          // latest edited source or transient in-memory UI flags.
          const snapshot = workspace.run?.input;
          if (snapshot) {
            reviewBaseline.value = {
              sourceId: snapshot.source_id || null,
              text: snapshot.text || "",
            };
            documentCompare.value = true;
            revisionScope.value = "all";
            summaryOpen.value = true;
            opinionsOpen.value = true;
            comparisonTexts.original = reviewBaseline.value.text;
            comparisonTexts.revised = null;
            comparisonData = null;
            comparisonSignature = "";
            comparisonGeneration++;
            previewText.value = null;
            pendingInitialRiskFocus = true;
          }
          reviewProgress.value = 100;
          Object.keys(nodeStates.value).forEach(
            (key) => (nodeStates.value[key] = "completed"),
          );
        }
      });
    else {
      workspace.load().then(fetchSamples);
    }
  });

  const saveBeforeNavigation = async () => {
    if (!workspace.taskId && !contractText.value.trim()) return true;
    if (isReviewing.value) {
      showToast("审查正在进行，请等待完成或先取消审查");
      return false;
    }
    try {
      await commitInlineDraft();
      await workspace.flush();
    } catch (error) {
      showToast("保存未完成：" + error.message);
      return false;
    }
  };
  onBeforeRouteLeave(saveBeforeNavigation);
  onBeforeRouteUpdate((to, from) => {
    if (
      String(to.query.task || "") === String(workspace.taskId || "") &&
      to.query.run === from.query.run
    )
      return true;
    return saveBeforeNavigation();
  });
  onScopeDispose(() => {
    controller?.abort();
    clearTimeout(differenceTimer);
    comparisonGeneration++;
    window.removeEventListener("message", handleMessage);
    document.removeEventListener("click", closeMenus);
    document.removeEventListener("keydown", handleKeydown);
  });

  return {
    summaryOpen,
    toggleSummary,
    toggleOpinions,
    opinionsOpen,
    openOpinions,
    closeOpinions,
    documentCompare,
    reviewBaseline,
    revisionScope,
    workspace,
    reviewAcceptedDraft,
    focusedIssueId,
    clauseEdit,
    openClauseEditor,
    saveClauseEditor,
    issueSearch,
    handlingFilter,
    reviewError,
    reviewedAt,
    resultStale,
    saveStatus,
    severityLabel,
    documentSaving,
    saveDocument,
    exportDocument,
    showEditor,
    editText,
    editTitle,
    editType,
    openEditor,
    saveEditor,
    cancelReview,
    exportContract,
    contractTitle,
    contractType,
    partyRole,
    contractText,
    selectedModel,
    selectedSampleKey,
    isReviewing,
    viewMode,
    focusedClauseId,
    severityFilter,
    appliedIssueIds,
    showModelModal,
    showReportModal,
    isTestingModel,
    testResult,
    toastMessage,
    latestLogMessage,
    reviewTrace,
    publicAnalysis,
    modelConfig,
    sampleContracts,
    pipelineNodes,
    nodeStates,
    reviewResult,
    currentTaxSettlement,
    reviewSource,
    formattedLines,
    filteredIssues,
    finalizedContractText,
    loadSample,
    clearText,
    startReview,
    highlightInContract,
    selectIssue,
    applyRedline,
    copyText,
    openModelModal,
    saveModelConfig,
    testModelConnection,
    reviewProgress,
    getScoreColor,
    resetToDefault,
  };
}
