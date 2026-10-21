<script setup>
import { computed } from 'vue';
const props=defineProps({context:{type:Object,required:true}});
const workspace=props.context.workspace;
const label=status=>({pass:'符合',fail:'不符合',needs_review:'待确认',not_applicable:'不适用'})[status]||status;
const groups=computed(()=>[
  {name:'当前采纳稿要求核验',items:workspace.run?.current_verification?.findings||[],current:true},
  {name:'全部建议稿要求核验',items:workspace.run?.result?.proposed_requirement_findings||[],current:false},
]);
</script>
<template>
  <div class="requirement-checks">
    <div class="requirement-check-actions">
      <button :disabled="workspace.historical||workspace.verifying||context.resultStale.value||context.isReviewing.value" @click="workspace.verifyCurrent()">{{workspace.verifying?'正在核验当前稿…':'核验当前稿'}}</button>
      <span :class="{valid:workspace.run?.current_verification_valid}">{{workspace.run?.current_verification_valid?'当前稿核验有效':'当前稿未核验或已失效'}}</span>
    </div>
    <p class="requirement-check-hint">采纳或撤销修改后，在此核验当前稿，再完成审核。</p>
    <details :open="workspace.showCompletionChecks" @toggle="workspace.showCompletionChecks=$event.target.open">
      <summary>核验结果与人工确认</summary>
      <details v-for="group in groups" :key="group.name" :open="group.current">
        <summary>{{group.name}} · {{group.items.length}} 项</summary>
        <p v-if="!group.current">基于全部建议组合，不代表当前采纳稿。</p>
        <p v-if="!group.items.length">{{group.current?'请点击上方“核验当前稿”。':'本版本没有核验结果。'}}</p>
        <article v-for="item in group.items" :key="item.id">
          <strong>{{label(item.status)}} · {{item.text}}</strong>
          <p>{{item.source}} · {{item.priority==='required'?'硬性要求':'优先偏好'}}</p>
          <p>{{item.explanation}}</p><blockquote v-if="item.evidence">{{item.evidence}}</blockquote>
          <p v-if="item.conflict_with?.length" class="conflict">冲突要求：{{item.conflict_with.join('、')}}，请修改条件并重新审查。</p>
          <label v-if="group.current&&!['pass','not_applicable'].includes(item.status)&&!item.conflict_with?.length">人工确认理由（5至3000字）<textarea v-model="workspace.confirmations[item.id]" :disabled="workspace.historical||workspace.task?.status==='completed'||!workspace.run?.current_verification_valid" maxlength="3000" placeholder="说明处理方式、确认依据或接受风险的理由"/></label>
        </article>
      </details>
    </details>
  </div>
</template>
<style scoped>
.requirement-checks{margin-top:16px;padding-top:14px;border-top:1px solid #e5edf8;font-size:11px;color:#64748b;line-height:1.8}.requirement-check-actions{display:flex;align-items:center;flex-wrap:wrap;gap:10px}.requirement-check-actions button{padding:6px 11px;border:1px solid #c5d8ff;border-radius:6px;background:#eff6ff;color:#2563eb;font-size:12px;font-weight:500}.requirement-check-actions button:disabled{opacity:.5;cursor:not-allowed}.requirement-check-actions .valid{color:#059669}.requirement-check-hint{margin:8px 0 12px;font-size:11px;color:#94a3b8}.requirement-checks summary{cursor:pointer;padding:8px 0;color:#475569;font-weight:500}.requirement-checks details details{margin-left:10px;border-top:1px solid #edf1f7}.requirement-checks article{padding:12px 0;border-top:1px solid #edf1f7}.requirement-checks article strong{color:#334155;font-weight:600}.requirement-checks p{margin-top:6px;overflow-wrap:anywhere}.requirement-checks blockquote{margin:8px 0;padding:8px 10px;background:#f8fafc;border-left:2px solid #cbd5e1;white-space:pre-wrap}.requirement-checks label{display:block;margin-top:10px;color:#475569}.requirement-checks textarea{display:block;width:100%;min-height:80px;margin-top:6px;padding:8px;border:1px solid #dce3ed;border-radius:6px;background:#fff;font:inherit;color:#334155;resize:vertical}.requirement-checks .conflict{color:#b45309}
</style>
