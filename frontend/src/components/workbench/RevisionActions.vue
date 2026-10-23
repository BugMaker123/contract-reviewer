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
      <span>{{ issue.source === "manual" ? "人工" : "AI" }}</span><strong>{{ issue.source === "manual" ? "人工补充意见" : "LexisGraph 修订建议" }}</strong
      ><small v-if="workspace.run?.revision_history?.[issue.id]?.length"
        >第
        {{ workspace.run.revision_history[issue.id].at(-1).version }} 版</small
      >
    </div>
    <div v-if="issue.redline" class="revision-clause-preview">
      <div class="revision-preview-header flex items-center justify-between mb-2">
        <small class="compact-suggestion-label font-semibold text-slate-700">AI 建议修订条款：</small>
        <span class="text-[11px] font-mono px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200/60 font-medium">Redline 差异对比</span>
      </div>
      <div class="revision-diff-block revision-diff-original">
        <span class="diff-tag diff-tag-del">原条款</span>
        <del>{{ issue.redline.original_text || "（新增条款）" }}</del>
      </div>
      <div class="revision-diff-arrow flex items-center justify-center py-1 text-slate-400">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 5v14M19 12l-7 7-7-7"/></svg>
      </div>
      <div class="revision-diff-block revision-diff-suggested">
        <span class="diff-tag diff-tag-ins">AI 建议合规修订</span>
        <ins>{{ issue.redline.suggested_text || "（删除此条款）" }}</ins>
      </div>
    </div>
    <p v-else class="revision-empty">
      此项尚未生成条款修订。请先确认处理位置，再生成建议或手动填写修订。
    </p>
    <div v-if="needsRevisionTarget(issue)" class="revision-target-editor">
      <strong>指定这条意见的处理位置</strong>
      <p>该意见没有唯一对应的原文。每次处理一处条款；涉及多个问题时，可分别添加人工意见。</p>
      <label>处理方式<select v-model="revisionTarget(issue).change_type" :disabled="revisionReadOnly" @change="revisionTarget(issue).original_text=''">
        <option value="replace">修改现有条款</option><option value="insert">新增缺失条款到文末</option>
      </select></label>
      <template v-if="revisionTarget(issue).change_type==='replace'">
        <label>从合同条款中选择<select v-model="revisionTarget(issue).original_text" :disabled="revisionReadOnly">
          <option value="">请选择待修改的条款</option><option v-for="segment in workspace.run?.result?.segments||[]" :key="segment.id" :value="segment.content">{{segment.title||segment.clause_title||segment.id}} · {{segment.content?.slice(0,80)}}</option>
        </select></label>
        <label>待修改的完整原文<textarea v-model="revisionTarget(issue).original_text" :disabled="revisionReadOnly" rows="4" maxlength="20000" placeholder="也可从正文复制一处完整且唯一的条款到这里；不能填写风险说明或条款编号摘要。"/></label>
      </template>
      <p v-else>生成并采纳后，会在合同文末新增条款。请确认合同确实缺少该约定。</p>
    </div>
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
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg><span>采纳</span>
      </button>
      <button class="revision-reject-button"
        @click="setReviewDecision(issue, 'rejected')"
        :disabled="
          revisionReadOnly || workspace.decisions[issue.id] === 'rejected'
        "
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="m7 7 10 10M17 7 7 17"/></svg><span>拒绝</span>
      </button>
      <button class="revision-undo-button" @click="setReviewDecision(issue, 'pending')"
        :disabled="revisionReadOnly || (!appliedIssueIds.includes(issue.id) && (!workspace.decisions[issue.id] || workspace.decisions[issue.id] === 'pending'))"
        :title="appliedIssueIds.includes(issue.id) ? '撤销采纳，恢复待处理' : workspace.decisions[issue.id] === 'rejected' ? '撤销拒绝，恢复待处理' : '恢复为待处理状态'">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 5 4 10l5 5M4 10h9a6 6 0 0 1 0 12" transform="translate(0 -2)"/></svg><span>撤销操作</span>
      </button>
    </div>
    <p
      v-if="revisionBusy && activeRevision?.id === issue.id"
      class="revision-explanation"
      role="status"
    >
      正在处理这条修订…
    </p>
    <details class="revision-support-tools" :open="!!revisionInstructions[issue.id] || editingRevisionId === issue.id">
      <summary>调整修订<span>补充要求、手动修改与复制</span></summary>
      <div class="revision-support-body">
        <label class="revision-instruction"><span>补充调整要求</span>
          <textarea v-model="revisionInstructions[issue.id]" :disabled="revisionReadOnly" maxlength="3000" rows="2"
            placeholder="例如：保留付款节点，措辞更温和…" :aria-label="issue.clause_title + 'AI调整要求'"></textarea>
        </label>
        <div class="revision-support-generate"><small>重新生成会保留旧建议版本。</small><button @click="generateRevision(issue)" :disabled="revisionReadOnly">按要求重新生成</button></div>
        <div class="revision-secondary-actions">
          <button @click="beginRevisionEdit(issue)" :disabled="revisionReadOnly">手动调整修订</button>
          <button @click="openClauseEditor(issue)" :disabled="revisionReadOnly || documentSaving">编辑正文</button>
          <button v-if="issue.redline" @click="copyText(issue.redline.suggested_text)">复制建议</button>
        </div>
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

<style scoped>
.revision-target-editor{margin:12px 0;padding:12px;border:1px solid #dbe5f4;background:#f8faff;border-radius:8px}.revision-target-editor>strong{font-size:12px;color:#334155}.revision-target-editor p{font-size:11px;line-height:1.8;color:#64748b;margin:7px 0}.revision-target-editor label{display:block;font-size:11px;color:#475569;margin-top:10px}.revision-target-editor select,.revision-target-editor textarea{display:block;box-sizing:border-box;width:100%;min-width:0;margin-top:5px;border:1px solid #dce3ed;border-radius:5px;padding:8px;background:#fff;font:inherit;color:#334155}.revision-target-editor textarea{resize:vertical;line-height:1.7}
</style>
