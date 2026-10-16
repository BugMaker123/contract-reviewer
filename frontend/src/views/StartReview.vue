<script>
import { usePortalPage } from "../composables/usePortalPage.js";
import PageFrame from "../components/PageFrame.vue";
import ContractSource from "../components/portal/ContractSource.vue";
import ChecklistConfig from "../components/portal/ChecklistConfig.vue";
import ChecklistSelection from "../components/portal/ChecklistSelection.vue";
import ComparisonReference from "../components/portal/ComparisonReference.vue";
import ReviewBackground from "../components/portal/ReviewBackground.vue";
export default {
  components: {
    PageFrame,
    ContractSource,
    ChecklistConfig,
    ChecklistSelection,
    ComparisonReference,
    ReviewBackground,
  },
  setup() {
    const context = usePortalPage("start");
    return { ...context, context };
  },
};
</script>
<template>
  <PageFrame :context="context">
    <section class="max-w-4xl mx-auto space-y-5">
      <div class="text-center mb-7">
        <h1 class="text-2xl font-bold text-slate-900">新建合同审查</h1>
        <p class="text-xs text-slate-500 mt-3">
          准备合同与审查条件，进入工作台逐项核对
        </p>
      </div>
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <button
          v-for="mode in modes"
          @click="form.mode = mode.id"
          class="mode-button"
          :class="{ active: form.mode === mode.id }"
        >
          <span
            class="block font-semibold text-xs"
            :class="form.mode === mode.id ? 'text-blue-700' : 'text-slate-800'"
            >{{ mode.name }}</span
          ><span class="block text-[11px] text-slate-500 mt-1.5">{{
            mode.description
          }}</span>
        </button>
      </div>
      <div class="card overflow-hidden">
        <div class="px-6 pt-5 flex items-center gap-2">
          <button
            v-for="source in sources"
            @click="switchSource(source.id)"
            :disabled="importing"
            class="button"
            :class="{ soft: inputMethod === source.id }"
          >
            {{ source.name }}</button
          ><span class="ml-auto text-xs text-slate-400"
            >{{ form.text.length }} 字</span
          >
        </div>
        <ContractSource :context="context" />
        <div class="px-6 pb-5 grid grid-cols-1 md:grid-cols-2 gap-4">
          <label
            ><span class="label">合同名称</span
            ><input
              v-model="form.title"
              class="field"
              placeholder="填写便于识别的合同名称" /></label
          ><label
            ><span class="label">合同类型</span
            ><input
              v-model="form.type"
              class="field"
              placeholder="如：采购合同、服务协议" /></label
          ><label
            ><span class="label">我方立场</span
            ><select v-model="form.role" class="field">
              <option v-for="role in roles" :value="role.value">
                {{ role.label }}
              </option>
            </select></label
          ><label
            ><span class="label">审查尺度</span
            ><select v-model="form.scale" class="field">
              <option>中立</option>
              <option>强势</option>
              <option>弱势</option>
            </select></label
          >
        </div>
        <ChecklistConfig :context="context" />
        <ChecklistSelection :context="context" />
        <ComparisonReference :context="context" />
        <ReviewBackground :context="context" />
      </div>
      <div class="text-center">
        <button
          @click="createTask"
          :disabled="
            busy ||
            importing ||
            !form.text.trim() ||
            !form.title.trim() ||
            (form.mode === 'checklist' &&
              (!form.checklist_id || form.checklist_item_ids?.length === 0)) ||
            (form.mode === 'compare' && !form.reference_text.trim())
          "
          class="button primary px-8 py-3"
        >
          {{ busy ? "正在保存…" : "进入工作台核对合同" }}
        </button>
      </div>
    </section>
  </PageFrame>
</template>
