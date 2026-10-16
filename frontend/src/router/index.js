import { createRouter, createWebHistory } from "vue-router";
import { pages } from "../portal/pages.js";
import { loadPageModules } from "../portal/modules.js";

const views = {
  start: () => import("../views/StartReview.vue"),
  records: () => import("../views/ReviewRecords.vue"),
  categories: () => import("../views/BusinessCategories.vue"),
  checklists: () => import("../views/Checklists.vue"),
  draft: () => import("../views/ContractDraft.vue"),
  drafts: () => import("../views/DraftRecords.vue"),
};

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      component: () => import("../layouts/PortalLayout.vue"),
      children: Object.entries(pages).map(([path, page]) => ({
        path,
        name: page.key,
        meta: { page: page.key, title: page.name },
        component: async () => {
          const [, view] = await Promise.all([
            loadPageModules(page.key),
            views[page.key](),
          ]);
          return view;
        },
      })),
    },
    {
      path: "/workbench",
      alias: "/workbench.html",
      name: "workbench",
      meta: { title: "合同审查工作台" },
      component: () => import("../views/Workbench.vue"),
    },
    {
      path: "/:pathMatch(.*)*",
      component: () => import("../views/NotFound.vue"),
      meta: { title: "页面不存在" },
    },
  ],
});

router.afterEach((to, _from, failure) => {
  if (!failure)
    document.title = `${to.meta.title || "合同工作系统"} · LexisGraph`;
});
