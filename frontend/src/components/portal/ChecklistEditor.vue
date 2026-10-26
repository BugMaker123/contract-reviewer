<script>
import { ref, watch } from 'vue';
export default {
  props: {context:{type:Object,required:true}},
  setup(props) {
    const batchOpen = ref(false), batchText = ref('');
    watch(() => props.context.checklistEditor.value, () => {batchOpen.value = false; batchText.value = '';});
    const addBatch = () => {
      props.context.modalError.value = '';
      try {
        const result = props.context.appendChecklistRequirements(batchText.value);
        batchText.value = ''; batchOpen.value = false;
        props.context.notify(`已添加 ${result.added} 条要求${result.duplicates ? '，重复内容已跳过' : ''}`);
      } catch (err) { props.context.modalError.value = err.message; }
    };
    return {...props.context,batchOpen,batchText,addBatch};
  },
};
</script>
<template>
  <div v-if="checklistEditor" class="modal">
    <section class="modal-panel checklist-editor" role="dialog" aria-modal="true" :aria-label="checklistEditor.id ? '编辑审查清单' : '创建审查清单'">
      <header class="checklist-editor-heading"><div><h2>{{ checklistEditor.id ? '编辑审查清单' : '创建审查清单' }}</h2><p>写下常用审查要求，下次选中清单即可使用。</p></div><button :disabled="busy || importing" @click="checklistEditor = null" aria-label="关闭清单编辑器">关闭</button></header>
      <div class="checklist-editor-body">
        <p v-if="modalError" role="alert" class="checklist-editor-error">{{ modalError }}</p>
        <fieldset :disabled="busy || importing">
          <div class="checklist-basic-fields">
            <label><span class="label">清单名称 <em>*</em></span><input v-model="checklistEditor.name" class="field" maxlength="200" placeholder="如：采购合同审查要求" /></label>
            <label><span class="label">业务分类（选填）</span><select v-model="checklistEditor.category_id" class="field"><option :value="null">暂不分类</option><option v-for="row in categories" :key="row.id" :value="row.id">{{ row.name }}</option></select></label>
          </div>
          <details class="checklist-supplement"><summary>补充适用范围与说明（选填）</summary><div class="checklist-basic-fields"><label><span class="label">适用合同类型</span><input v-model="checklistEditor.contract_type" class="field" /></label><label><span class="label">说明</span><input v-model="checklistEditor.description" class="field" maxlength="3000" placeholder="适用范围或特殊要求" /></label></div></details>
          <div class="checklist-requirements-heading"><h3>审查要求 <span>{{ checklistEditor.items.length }} / 100</span></h3><div><button type="button" class="button" @click="batchOpen = !batchOpen">批量粘贴</button><button type="button" class="button" @click="$refs.checklistInput.click()">从文件导入</button><input type="file" ref="checklistInput" class="hidden" accept=".docx,.pdf,.txt" @change="importDocument($event,'checklist')" /></div></div>
          <div v-if="batchOpen" class="checklist-batch"><label class="label" for="checklist-batch-input">每行一条要求，添加到现有清单末尾</label><textarea id="checklist-batch-input" v-model="batchText" class="field" rows="5" placeholder="例如：付款前必须完成验收
违约责任应约定赔偿上限
明确约定交付时间" /><div><button type="button" class="button" @click="batchOpen = false">收起</button><button type="button" class="button primary" @click="addBatch">添加这些要求</button></div></div>
          <article v-for="(item,index) in checklistEditor.items" :key="item.id" class="checklist-requirement-row">
            <div class="checklist-requirement-main"><span class="checklist-item-number">{{ index + 1 }}</span><textarea v-model="item.requirement" class="field" rows="2" maxlength="3000" placeholder="写清楚需要核对的要求，如：付款前必须完成验收" aria-label="检查项要求" /><button type="button" @click="checklistEditor.items.splice(index,1)" :aria-label="'移除第' + (index + 1) + '条要求'">移除</button></div>
            <details class="checklist-item-advanced"><summary>高级设置<span v-if="item.operator !== 'semantic'"> · 已配置文字匹配</span><span v-if="item.severity === 'critical'"> · 重大风险</span></summary>
              <div class="checklist-advanced-fields">
                <label><span class="label">检查项标题（可不填）</span><input v-model="item.title" class="field" maxlength="200" aria-label="检查项标题" placeholder="默认从要求中生成" /></label>
                <label><span class="label">未通过风险等级</span><select v-model="item.severity" class="field"><option value="warning">一般风险</option><option value="critical">重大风险</option><option value="info">优化建议</option></select></label>
                <label><span class="label">核验方式</span><select v-model="item.operator" class="field"><option value="semantic">按要求理解并判断</option><option value="contains_all">必须包含全部文字</option><option value="contains_any">至少包含一项文字</option><option value="forbidden">不得包含这些文字</option></select></label>
                <label v-if="item.operator !== 'semantic'"><span class="label">匹配文字（逗号分隔）</span><input v-model="item.keywordText" class="field" placeholder="如：付款,验收" /></label>
                <label class="checklist-suggestion"><span class="label">未通过时的处理建议（选填）</span><input v-model="item.suggestion" class="field" maxlength="5000" /></label>
              </div>
            </details>
          </article>
          <button type="button" class="checklist-add-requirement" @click="addChecklistItem" :disabled="checklistEditor.items.length >= 100">＋ 添加一条要求</button>
        </fieldset>
      </div>
      <footer class="checklist-editor-footer"><span>{{ checklistEditor.id ? '保存后生成新版本，已有审查记录不受影响。' : '默认按要求进行审查，无需逐项配置规则。' }}</span><div><button @click="saveChecklist(false)" :disabled="busy || importing" class="button">存为草稿</button><button v-can="'checklists.publish'" @click="saveChecklist(true)" :disabled="busy || importing" class="button primary">{{ busy ? '正在保存…' : '保存并启用' }}</button></div></footer>
    </section>
  </div>
</template>
