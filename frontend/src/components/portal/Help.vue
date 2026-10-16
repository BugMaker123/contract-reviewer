<script>
export default {
  props: { context: { type: Object, required: true } },
  setup: (props) => props.context,
};
</script>

<template>
  <div v-if="showHelp" class="modal">
    <div class="modal-panel max-w-lg p-6 space-y-4">
      <div class="flex justify-between">
        <h2 class="font-bold">内部操作说明</h2>
        <button @click="showHelp = false" aria-label="关闭操作说明">✕</button>
      </div>
      <ol class="text-xs text-slate-600 leading-loose list-decimal pl-5">
        <li>导入真实合同，核对正文和审查条件，再进入工作台发起审查。</li>
        <li>企业清单需核对并发布后才能使用；任务会保留选用的清单版本。</li>
        <li>逐项采纳、撤销、不采纳或标为待复核。重新审查形成独立版本。</li>
        <li>起草先确认交易信息和大纲，缺失信息请补全后交付。</li>
        <li>
          合同与记录保存在本机服务。归档可恢复；Word 导出请核对内容与排版。
        </li>
      </ol>
    </div>
  </div>
</template>
