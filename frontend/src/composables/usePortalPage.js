import { onMounted, onActivated, watch, nextTick } from "vue";
import { onBeforeRouteLeave, useRoute, useRouter } from "vue-router";
import { createContext } from "../portal/core/context.js";
import { getPageModules } from "../portal/modules.js";
import { usePortalShell } from "../stores/portal.js";

export function usePortalPage(key) {
  const { page, states, features } = getPageModules(key);
  const shell = usePortalShell();
  const router = useRouter();
  const route = useRoute();
  const context = createContext(key, page.data);
  let actionNavigation = false;
  Object.assign(context, {
    refreshRecent: shell.loadRecords,
    model: shell.model,
    toast: shell.toast,
    notify: shell.notify,
    navigate: async (path) => {
      actionNavigation = true;
      try {
        return await router.push(path);
      } finally {
        actionNavigation = false;
      }
    },
    replaceRoute: (path) => router.replace(path),
  });
  for (const state of states) Object.assign(context, state.setup(context));
  for (const feature of features)
    Object.assign(context, feature.setup(context));

  let initialized = false;
  let active = false;
  const initialize = async () => {
    try {
      await context.loadRecords();
      await context.initialize?.();
      initialized = true;
    } catch (error) {
      context.error.value = error.message;
    } finally {
      context.loading.value = false;
    }
  };
  onMounted(initialize);
  onActivated(async () => {
    active = true;
    if (initialized) {
      try {
        await context.loadRecords();
      } catch (error) {
        context.error.value = error.message;
      }
    }
    await nextTick();
    document.querySelector(".portal-main")?.scrollTo(0, context.scrollTop || 0);
  });
  watch(
    () => route.query,
    async () => {
      if (route.meta.page !== key || !initialized) return;
      try {
        await context.initialize?.();
      } catch (error) {
        context.error.value = error.message;
      }
    },
  );
  onBeforeRouteLeave(async () => {
    if (!active) return true;
    if (!actionNavigation && (context.busy.value || context.importing.value)) {
      context.notify("正在处理，请稍后再切换页面");
      return false;
    }
    context.scrollTop = document.querySelector(".portal-main")?.scrollTop || 0;
    if(context.draftSave && !actionNavigation){try{await context.draftSave.save();}catch(e){context.error.value=e.message;context.notify('草稿尚未保存，请重试后再离开');return false;}}
    active = false;
  });
  return context;
}
