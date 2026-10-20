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
      </div>
      <div class="flex gap-3 items-center">
        <button @click="showHelp = true" class="portal-help-button"><span aria-hidden="true">?</span>操作手册</button>
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
        <section v-if="false" class="recent-work" aria-labelledby="recent-work-title">
          <div class="recent-work-heading"><h2 id="recent-work-title">最近工作</h2><RouterLink to="/records">全部记录</RouterLink></div>
          <p v-if="recentError" class="recent-work-empty">{{ recentError }} <button @click="refreshRecent">重试</button></p>
          <p v-else-if="!recentTasks.length" class="recent-work-empty">暂无工作记录</p>
          <article v-for="task in recentTasks" :key="task.id" class="recent-work-item">
            <div class="recent-work-document">
              <RouterLink :to="'/workbench?task=' + task.id" class="recent-work-title" :title="task.title">{{ task.title }}</RouterLink>
            </div>
            <div class="recent-work-meta">
              <span class="recent-work-status">{{ statusName(task.status) }}</span>
              <RouterLink :to="'/workbench?task=' + task.id" class="recent-work-action">{{ recentAction(task.status) }}</RouterLink>
            </div>
          </article>
        </section>
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
