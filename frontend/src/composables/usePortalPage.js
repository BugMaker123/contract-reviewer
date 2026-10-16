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
    tasks: shell.tasks,
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
      if (key === "draft" && context.draft.id && !route.query.id)
        await router.replace("/draft?id=" + context.draft.id);
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
      if (key === "draft" && route.query.id === context.draft.id) return;
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
    if (
      key === "draft" &&
      context.draft.title.trim() &&
      context.draft.background.trim() &&
      context.hasDraftChanges()
    ) {
      try {
        await context.persistDraft(false);
      } catch (error) {
        context.error.value = error.message;
        return false;
      }
    }
    context.scrollTop = document.querySelector(".portal-main")?.scrollTop || 0;
    active = false;
  });
  return context;
}
