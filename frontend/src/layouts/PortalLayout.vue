<script>
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { usePortalShell } from "../stores/portal.js";
import ModelSettings from "../components/portal/ModelSettings.vue";
import Help from "../components/portal/Help.vue";
import ReviewIcon from "../components/portal/ReviewIcon.vue";

export default {
  name: "PortalLayout",
  components: { ModelSettings, Help, ReviewIcon },
  setup() {
    const shell = usePortalShell();
    const route = useRoute();
    const iconMap = {
      start: 'home',
      drafting: 'drafting',
      records: 'records',
      validations: 'validations',
      categories: 'categories',
      checklists: 'checklists',
      templates: 'templates',
    };
    const navigationGroups = computed(() => [
      {name:'', keys:['start']},
      {name:'审查管理', keys:['categories','checklists','records']},
      {name:'模板管理', keys:['templates','validations']},
      {name:'', keys:['drafting']},
    ].map(group => ({...group, items:group.keys.map(key => {
      const item = shell.navigation.find(item => item.key === key);
      return {...item, name:({checklists:'审查清单维护',validations:'合同模板核验记录'})[key] || item.name};
    })})));
    const recentError = ref('');
    const refreshRecent = async () => { try { await shell.loadRecords(); recentError.value = ''; } catch { recentError.value = '最近工作读取失败'; } };
    watch(() => route.path, refreshRecent, {immediate:true});
    const recentAction = status => ({completed:'查看审核结果',pending_review:'继续复核',running:'查看审查进度',draft:'继续审查',failed:'重新处理',interrupted:'恢复处理'})[status] || '打开任务';
    return { ...shell, shell, navigationGroups, iconMap, recentAction, recentError, refreshRecent, page: computed(() => route.meta.page) };
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
      <RouterLink to="/" class="portal-brand flex items-center gap-3"
        ><span
          class="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold"
          ><ReviewIcon name="scale" class="w-5 h-5 text-white" aria-hidden="true" /></span
        ><strong class="text-base text-slate-900">LexisGraph</strong>
      </RouterLink>
        <RouterLink v-if="['template-review', 'templates'].includes($route.name)" to="/" class="app-home-link"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m12 5-7 7 7 7M5 12h14"/></svg>返回主页</RouterLink>
      </div>
      <div class="flex gap-3 items-center">
        <button v-if="$route.name!=='template-review'" @click="showHelp = true" class="portal-help-button"><span aria-hidden="true">?</span>操作手册</button>
        <button v-if="$route.name!=='template-review'" @click="showModel = true" class="button">⚙ 模型配置</button>
      </div>
    </header>

    <div class="flex flex-1 overflow-hidden">
      <aside v-if="$route.name!=='template-review'"
        class="portal-sidebar bg-white border-r border-slate-200 p-4 flex flex-col shrink-0"
      >
        <nav class="portal-navigation" aria-label="功能导航">
          <section v-for="group in navigationGroups" :key="group.name" class="portal-nav-group" :aria-label="group.name || '主入口'">
            <h2 v-if="group.name" class="portal-nav-label">{{group.name}}</h2>
            <RouterLink v-for="item in group.items" :key="item.key" :to="item.href" class="nav-link" :class="{active:page===item.key}">
              <ReviewIcon :name="iconMap[item.key] || 'document'" class="nav-icon" aria-hidden="true" />{{item.name}}
            </RouterLink>
          </section>
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
