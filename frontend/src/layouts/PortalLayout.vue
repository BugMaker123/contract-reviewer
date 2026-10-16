<script>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { usePortalShell } from "../stores/portal.js";
import ModelSettings from "../components/portal/ModelSettings.vue";
import Help from "../components/portal/Help.vue";
export default {
  name: "PortalLayout",
  components: { ModelSettings, Help },
  setup() {
    const shell = usePortalShell();
    const route = useRoute();
    return { ...shell, shell, page: computed(() => route.meta.page) };
  },
};
</script>
<template>
  <div
    class="h-screen flex flex-col overflow-hidden bg-slate-50 text-slate-800 antialiased"
  >
    <header
      class="portal-header h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shrink-0"
    >
      <RouterLink to="/" class="flex items-center gap-3"
        ><span
          class="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold"
          >⚖</span
        ><strong class="text-base text-slate-900">LexisGraph</strong>
      </RouterLink>
      <div class="flex gap-3 items-center">
        <button @click="showModel = true" class="button">⚙ 模型配置</button>
      </div>
    </header>

    <div class="flex flex-1 overflow-hidden">
      <aside
        class="portal-sidebar w-56 bg-white border-r border-slate-200 p-4 flex flex-col shrink-0"
      >
        <nav class="space-y-1">
          <RouterLink
            v-for="item in navigation"
            :to="item.href"
            class="nav-link"
            :class="{ active: page === item.key }"
            ><span aria-hidden="true" class="w-5 text-center">{{
              item.icon
            }}</span
            >{{ item.name }}</RouterLink
          >
        </nav>
        <div class="mt-6 card p-3 bg-slate-50" v-if="recentTasks.length">
          <div class="text-xs font-semibold mb-2 text-slate-700">最近工作</div>
          <RouterLink
            :to="'/workbench?task=' + recentTasks[0].id"
            class="text-xs text-slate-700 break-words leading-relaxed block"
            >{{ recentTasks[0].title }}</RouterLink
          >
          <div class="mt-2 text-[11px] text-slate-400">
            {{ statusName(recentTasks[0].status) }}
          </div>
          <RouterLink
            :to="'/workbench?task=' + recentTasks[0].id"
            class="block mt-3 text-xs font-semibold text-blue-600"
            >继续处理 →</RouterLink
          >
        </div>
        <div
          class="mt-auto pt-6 text-[11px] text-slate-400 border-t border-slate-100"
        >
          <button @click="showHelp = true" class="text-slate-500 mb-3">
            操作说明
          </button>
        </div>
      </aside>

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
