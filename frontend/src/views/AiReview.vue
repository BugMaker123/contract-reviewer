<script>
import { computed, watch } from "vue";
import { usePortalPage } from "../composables/usePortalPage.js";
import PageFrame from "../components/PageFrame.vue";
import ContractSource from "../components/portal/ContractSource.vue";
import ChecklistConfig from "../components/portal/ChecklistConfig.vue";
import ChecklistSelection from "../components/portal/ChecklistSelection.vue";
import ReviewBackground from "../components/portal/ReviewBackground.vue";
export default {
  components: {
    PageFrame,
    ContractSource,
    ChecklistConfig,
    ChecklistSelection,
    ReviewBackground,
  },
  props: { importedContract: Object },
  emits: ["processing"],
  setup(props, { emit }) {
    const context = usePortalPage("start");
    watch([() => props.importedContract, context.loading], ([value, loading]) => {
      if (value && !loading) { Object.assign(context.form, {text:value.text, source_id:value.source_id, title:value.filename.replace(/\.docx$/i,'')}); context.inputMethod.value='file'; }
    }, {immediate:true});
    watch([context.busy, context.importing], ([busy, importing]) => emit('processing', busy || importing), {immediate:true});
    const addFocus = (focus) => {
      const values = context.form.focus.split('；').filter(Boolean);
      context.form.focus = (values.includes(focus) ? values.filter(value => value !== focus) : [...values, focus]).join('；');
    };
    const readiness = computed(() => {
      const { form, selectedList, importing, busy } = context;
      if (importing.value) return "正在提取合同正文，请稍候";
      if (busy.value) return "正在创建审查任务";
      if (!form.text.trim()) return "请先上传合同或粘贴正文";
      if (!form.title.trim()) return "请填写合同名称";
      if (form.mode === "checklist" && !selectedList.value) return "请选择已发布的审查清单";
      if (form.mode === "checklist" && !(form.checklist_item_ids ?? selectedList.value.items).length) return "请至少勾选一项审查要点";
      if (form.references.some(ref => ref.kind === 'policy' && !ref.confirmed)) return "请先核对并确认公司制度要求";
      return "";
    });
    return { ...context, context, readiness, addFocus };
  },
};
</script>
<template>
  <PageFrame :context="context">
    <section class="review-start">
      <section class="review-settings card review-conditions-first">
        <div class="review-section-heading">
          <div>
            <h2>审查条件</h2>
          </div>
        </div>
        <div class="review-condition-fields">
          <label><span class="label">审查角色（我方立场）</span><select v-model="form.role" class="field">
              <option v-for="role in roles" :key="role.value" :value="role.value">{{role.label}}</option>
            </select></label>
          <label><span class="label">谈判尺度</span><select v-model="form.scale" class="field">
              <option>中立</option>
              <option>强势</option>
              <option>弱势</option>
            </select></label>
          <label><span class="label">审查要求来源</span><select v-model="form.mode" class="field">
              <option value="deep">自定义审查要求（Prompt）</option>
              <option value="checklist">业务分类与审查标准</option>
            </select></label>
        </div>
        <div class="review-setup-body">
          <div class="review-contract-panel">
            <div class="review-contract-heading"><span class="label">合同文档</span><span class="pill"
                :class="form.text.trim() ? 'green' : 'amber'">{{ form.text.trim() ? '已添加' : '待添加' }}</span></div>
            <label class="block review-contract-name">
              <!-- <span class="label">合同名称 <em>*</em></span> -->
              <input
                v-model="form.title" class="field" placeholder="填写便于识别的合同名称(支持从文件名自动提取)" /></label>
            <div class="review-source-tabs">
              <button v-for="source in sources" :key="source.id" @click="switchSource(source.id)" :disabled="importing"
                class="button" :class="{ soft: inputMethod === source.id }" :aria-pressed="inputMethod === source.id">{{
                  source.name }}</button>
              <span>{{ form.text.length.toLocaleString() }} 字</span>
            </div>
            <div class="review-document">
              <ContractSource :context="context" />
            </div>
          </div>
          <div class="review-requirement-panel">
            <template v-if="form.mode === 'checklist'">
              <ChecklistConfig :context="context" />
              <ChecklistSelection :context="context" />
            </template>
            <div v-else class="review-prompt-field"><div class="ai-focus-pills"><button v-for="focus in ['付款与验收','违约责任','知识产权','合同解除','争议解决']" :key="focus" type="button" :aria-pressed="form.focus.split('；').includes(focus)" @click="addFocus(focus)">{{focus}}</button></div>
              <label class="block"><span class="label">自定义审查要求（Prompt）</span><textarea v-model="form.focus"
                  class="field" rows="5"
                  placeholder="例如：重点审查付款与验收条款；指出单方解除权及责任不对等的风险；修改建议应保留合理的协商空间。"></textarea></label>
              <p>可填写关注重点、不可接受的条件和修改偏好；留空按通用标准审查，重点要求不替代全文风险审查。</p>
            </div>

          </div>
        </div>
        <ReviewBackground :context="context" :expanded="false" hide-focus />
      </section>
      <footer class="review-submit">
        <button @click="createTask" :disabled="!!readiness" class="button primary">{{ busy ? '正在保存…' : '进入工作台核对合同' }}
</button>
        <div><strong>{{ error ? '创建任务失败' : readiness ? '完成准备后，开始合同审查' : '准备就绪，可以进入审查工作台' }}</strong>
          <p :role="error ? 'alert' : 'status'" :class="{ 'review-submit-error': error }">{{ error || readiness ||
            '合同正文及审查条件已准备' }}</p>
        </div>
      </footer>
    </section>
  </PageFrame>
</template>

<style scoped>
.ai-intro{color:#64748b;font-size:13px;line-height:1.8;margin:8px 24px 25px}.review-settings{border-radius:18px;box-shadow:0 4px 16px #0f172a06}.ai-focus-pills{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}.ai-focus-pills button{padding:5px 10px;border-radius:20px;font-size:12px;background:#f1f5f9;color:#64748b}.ai-focus-pills button[aria-pressed=true]{background:#eff6ff;color:#2563eb}
</style>
