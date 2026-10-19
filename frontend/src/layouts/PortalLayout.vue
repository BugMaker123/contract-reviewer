<script>
import { computed, ref, watch } from "vue";
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
    const recentError = ref('');
    const refreshRecent = async () => { try { await shell.loadRecords(); recentError.value = ''; } catch { recentError.value = '最近工作读取失败'; } };
    watch(() => route.path, refreshRecent, {immediate:true});
    const recentAction = status => ({completed:'查看审核结果',pending_review:'继续复核',running:'查看审查进度',draft:'继续审查',failed:'重新处理',interrupted:'恢复处理'})[status] || '打开任务';
    return { ...shell, shell, recentAction, recentError, refreshRecent, page: computed(() => route.meta.page) };
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
      <div class="portal-header-leading">
      <RouterLink to="/" class="portal-brand flex items-center gap-3"
        ><span
          class="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold"
          >⚖</span
        ><strong class="text-base text-slate-900">LexisGraph</strong>
      </RouterLink>
      <h1 v-if="page === 'start'" class="portal-page-title">新建合同审查</h1>
      </div>
      <div class="flex gap-3 items-center">
        <button @click="showModel = true" class="button">⚙ 模型配置</button>
      </div>
    </header>

    <div class="flex flex-1 overflow-hidden">
      <aside
        class="portal-sidebar bg-white border-r border-slate-200 p-4 flex flex-col shrink-0"
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
        <section class="mt-6 card p-4 bg-slate-50 recent-work">
          <div class="text-sm font-semibold mb-2 text-slate-700">最近工作</div>
          <p v-if="recentError" class="text-xs text-amber-700">{{ recentError }} <button @click="refreshRecent">重试</button></p>
          <p v-else-if="!recentTasks.length" class="text-xs text-slate-400">暂无工作记录</p>
          <article v-for="task in recentTasks" :key="task.id" class="recent-work-item">
            <RouterLink :to="'/workbench?task=' + task.id" class="text-sm text-slate-700 break-words leading-relaxed block">{{ task.title }}</RouterLink>
            <div class="mt-2 text-xs text-slate-500">{{ statusName(task.status) }}</div>
            <RouterLink :to="'/workbench?task=' + task.id" class="block mt-2 text-xs font-semibold text-blue-600">{{ recentAction(task.status) }} →</RouterLink>
          </article>
        </section>
        <div
          class="mt-auto pt-6 text-xs text-slate-500 border-t border-slate-100"
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
