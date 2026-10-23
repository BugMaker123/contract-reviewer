<script>
import { computed, watch } from "vue";
import { useRoute } from "vue-router";
import { usePortalShell } from "../stores/portal.js";
import ModelSettings from "../components/portal/ModelSettings.vue";
import Help from "../components/portal/Help.vue";
import WorkspaceSidebar from "../components/portal/WorkspaceSidebar.vue";

export default {
  name: "PortalLayout",
  components: { ModelSettings, Help, WorkspaceSidebar },
  setup() {
    const shell = usePortalShell();
    const route = useRoute();
    watch(() => route.path, () => shell.loadRecords().catch(() => shell.notify('最近工作读取失败，请稍后重试')), { immediate: true });
    return { ...shell, shell, page: computed(() => route.meta.page) };
  },
};
</script>
<template>
  <div
    class="portal-shell h-screen flex flex-col overflow-hidden bg-slate-50 text-slate-800 antialiased"
    :class="{'portal-review-shell': $route.name==='template-review'}"
  >
    <header
      class="portal-header h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shrink-0"
    >
      <div class="portal-header-leading">
        <div class="prototype-breadcrumb">合同工作 <span>/</span> <strong>{{ $route.meta.title || '工作台' }}</strong></div>
      </div>
      <div class="flex gap-3 items-center">
        <button v-if="$route.name!=='template-review'" @click="showHelp = true" class="portal-help-button"><span aria-hidden="true">?</span>操作手册</button>
        <button v-if="$route.name!=='template-review'" @click="showModel = true" class="button">⚙ 模型配置</button>
      </div>
    </header>

    <div class="flex flex-1 overflow-hidden">
      <WorkspaceSidebar :active="page" />

      <main class="portal-main flex-1 overflow-y-auto p-8">
        <RouterView v-slot="{ Component, route }"
          ><KeepAlive :max="8"
            ><component :is="Component" :key="route.path" /></KeepAlive
        ></RouterView>
      </main>
    </div>
    <ModelSettings :context="shell" /><Help :context="shell" />
    <div
      v-if="toast"
      role="status"
      class="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-slate-900 text-white rounded-lg px-4 py-2 text-xs shadow-lg"
    >
      {{ toast }}
    </div>
  </div>
</template>
