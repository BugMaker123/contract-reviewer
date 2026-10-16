<script>
export default {
  props: {
    context: { type: Object, required: true },
    issue: { type: Object, required: true },
  },
  setup: (props) => props.context,
};
</script>
<template>
  <section
    class="revision-actions"
    @click.stop
    :aria-label="issue.clause_title + '修订操作'"
  >
    <div class="revision-author">
      <span>AI</span><strong>LexisGraph 修订建议</strong
      ><small v-if="workspace.run?.revision_history?.[issue.id]?.length"
        >第
        {{ workspace.run.revision_history[issue.id].at(-1).version }} 版</small
      >
    </div>
    <div v-if="issue.redline" class="revision-clause-preview">
      <small class="compact-suggestion-label">建议修订条款：</small
      ><del>{{ issue.redline.original_text || "（新增条款）" }}</del
      ><ins>{{ issue.redline.suggested_text || "（删除此条款）" }}</ins>
    </div>
    <p v-else class="revision-empty">
      此条意见尚无可替换文本，可先让 AI 生成修订建议。
    </p>
    <p v-if="issue.revision_explanation" class="revision-explanation">
      {{ issue.revision_explanation }}
    </p>
    <p v-if="revisionWarnings[issue.id]" class="revision-warning">
      {{ revisionWarnings[issue.id] }}
    </p>
    <div class="revision-primary-actions" role="group" aria-label="修订处理">
      <button
        class="revision-ai-button"
        @click="setReviewDecision(issue, 'applied')"
        :disabled="
          revisionReadOnly ||
          !issue.redline ||
          appliedIssueIds.includes(issue.id)
        "
      >
        采纳
      </button>
      <button
        @click="setReviewDecision(issue, 'rejected')"
        :disabled="
          revisionReadOnly || workspace.decisions[issue.id] === 'rejected'
        "
      >
        拒绝
      </button>
      <button @click="generateRevision(issue)" :disabled="revisionReadOnly">
        重新生成
      </button>
    </div>
    <p
      v-if="revisionBusy && activeRevision?.id === issue.id"
      class="revision-explanation"
      role="status"
    >
      正在处理这条修订…
    </p>
    <details
      class="revision-generation-options"
      :open="revisionMode === 'compare' || !!revisionInstructions[issue.id]"
    >
      <summary>补充生成要求</summary>
      <label class="revision-instruction"
        ><span>不满意？补充调整要求后重新生成</span
        ><textarea
          v-model="revisionInstructions[issue.id]"
          :disabled="revisionReadOnly"
          maxlength="3000"
          rows="2"
          placeholder="例如：保留原付款节点，措辞更温和，明确验收期限…"
          :aria-label="issue.clause_title + 'AI调整要求'"
        ></textarea>
      </label>
    </details>
    <details class="revision-more-actions">
      <summary>更多操作</summary>


      <div class="revision-secondary-actions">
        <button
          v-if="appliedIssueIds.includes(issue.id)"
          @click="setReviewDecision(issue, 'pending')"
          :disabled="revisionReadOnly"
        >
          撤销采纳
        </button>
        <button
          v-else-if="workspace.decisions[issue.id] === 'rejected'"
          @click="setReviewDecision(issue, 'pending')"
          :disabled="revisionReadOnly"
        >
          撤销拒绝
        </button>
        <button @click="beginRevisionEdit(issue)" :disabled="revisionReadOnly">
          手动调整修订
        </button>
        <button
          v-if="issue.redline"
          @click="copyText(issue.redline.suggested_text)"
        >
          复制建议
        </button>
      </div>
    </details>
    <div v-if="editingRevisionId === issue.id" class="revision-manual-editor">
      <label
        >调整后的完整条款<textarea
          v-model="revisionEdits[issue.id]"
          rows="6"
          maxlength="20000"
          :aria-label="issue.clause_title + '修订文本'"
          :disabled="revisionReadOnly"
        ></textarea>
      </label>
      <p>保存为待采纳修订，原始文档保持留档。</p>
      <div>
        <button
          class="revision-ai-button"
          @click="saveRevisionEdit(issue)"
          :disabled="revisionReadOnly || !revisionEdits[issue.id]?.trim()"
        >
          保存修订建议</button
        ><button @click="editingRevisionId = null" :disabled="revisionBusy">
          取消调整
        </button>
      </div>
    </div>
    <p v-if="revisionErrors[issue.id]" role="alert" class="revision-error">
      {{ revisionErrors[issue.id] }}
    </p>
    <details
      v-if="workspace.run?.revision_history?.[issue.id]?.length"
      class="revision-history"
    >
      <summary>
        建议版本 · {{ workspace.run.revision_history[issue.id].length }} 版
      </summary>
      <article
        v-for="version in [
          ...workspace.run.revision_history[issue.id],
        ].reverse()"
        :key="version.version"
      >
        <header>
          <strong
            >第 {{ version.version }} 版 ·
            {{
              {
                initial: "首次建议",
                ai: "AI 生成",
                manual: "人工调整",
                restore: "恢复版本",
              }[version.source]
            }}</strong
          ><button
            @click="restoreRevision(issue, version.version)"
            :disabled="
              revisionReadOnly ||
              version.redline.suggested_text === issue.redline?.suggested_text
            "
          >
            恢复此版
          </button>
        </header>
        <p>{{ version.redline.suggested_text || "删除此条款" }}</p>
        <small v-if="version.instruction"
          >调整要求：{{ version.instruction }}</small
        >
      </article>
    </details>
  </section>
</template>
