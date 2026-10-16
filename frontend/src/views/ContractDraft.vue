<script>
import { usePortalPage } from "../composables/usePortalPage.js";
import PageFrame from "../components/PageFrame.vue";
import DraftStep1 from "../components/portal/DraftStep1.vue";
import DraftStep2 from "../components/portal/DraftStep2.vue";
import DraftStep3 from "../components/portal/DraftStep3.vue";
import DraftStep4 from "../components/portal/DraftStep4.vue";
import DraftVersion from "../components/portal/DraftVersion.vue";
export default {
  components: {
    PageFrame,
    DraftStep1,
    DraftStep2,
    DraftStep3,
    DraftStep4,
    DraftVersion,
  },
  setup() {
    const context = usePortalPage("draft");
    return { ...context, context };
  },
};
</script>
<template>
  <PageFrame :context="context">
    <section class="max-w-5xl mx-auto space-y-5">
      <div class="flex justify-between items-center gap-3">
        <div>
          <h1 class="text-xl font-bold">合同起草</h1>
          <p class="text-xs text-slate-500 mt-2">
            确认交易信息和条款大纲，再生成可编辑的合同草稿
          </p>
        </div>
        <div class="flex gap-2">
          <button
            @click="saveDraft"
            :disabled="busy || !draft.title.trim() || !draft.background.trim()"
            class="button"
          >
            保存草稿</button
          ><a
            v-if="draft.id && draft.text.trim()"
            :href="'/api/drafts/' + draft.id + '/export'"
            class="button soft"
            >导出 Word</a
          ><button
            v-if="draft.text.trim()"
            @click="sendDraftToReview"
            :disabled="busy"
            class="button primary"
          >
            送入审查 →
          </button>
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="(step, index) in draftSteps"
          @click="draftStep = index"
          class="button"
          :class="{ soft: draftStep === index }"
        >
          {{ index + 1 }}. {{ step }}</button
        ><span class="ml-auto self-center text-xs text-slate-400">{{
          draft.id ? "已有存档，修改后请保存" : "尚未保存"
        }}</span>
      </div>
      <fieldset :disabled="busy" class="card p-6 space-y-5">
        <label class="block"
          ><span class="label">合同名称</span
          ><input
            v-model="draft.title"
            class="field"
            placeholder="填写草稿名称"
        /></label>
        <DraftStep1 v-if="draftStep === 0" :context="context" />
        <DraftStep2 v-if="draftStep === 1" :context="context" />
        <DraftStep3 v-if="draftStep === 2" :context="context" />
        <DraftStep4 v-if="draftStep === 3" :context="context" />
      </fieldset>
      <details v-if="draftVersions.length" class="card p-4">
        <summary class="text-xs font-semibold text-slate-600 cursor-pointer">
          历史草稿版本（{{ draftVersions.length }}）
        </summary>
        <div
          v-for="version in draftVersions"
          class="flex justify-between py-3 border-b border-slate-100 text-xs"
        >
          <span
            >{{ dateTime(version.created_at) }} ·
            {{ statusName(version.status) }}</span
          ><button @click="previewDraftVersion = version" class="text-blue-600">
            查看
          </button>
        </div>
      </details>
    </section>
    <DraftVersion :context="context" />
  </PageFrame>
</template>
