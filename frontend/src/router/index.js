import { createRouter, createWebHistory } from "vue-router";
import { pages } from "../portal/pages.js";
import { loadPageModules } from "../portal/modules.js";

const views = {
  drafting: () => import("../views/ContractDraftList.vue"),
  templates: () => import("../views/ContractTemplates.vue"),
  start: () => import("../views/StartReview.vue"),
  records: () => import("../views/ReviewRecords.vue"),
  validations: () => import("../views/ValidationRecords.vue"),
  categories: () => import("../views/BusinessCategories.vue"),
  checklists: () => import("../views/Checklists.vue"),
  "template-groups": () => import("../views/TemplateGroups.vue"),
};

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      component: () => import("../layouts/PortalLayout.vue"),
      children: [...Object.entries(pages).map(([path, page]) => ({
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
      {path:'/reviews/new',name:'review-new',meta:{page:'start',title:'新建合同审查'},component:()=>import('../views/StartReview.vue')},
      {path:'/template-checks/new',name:'template-check-new',meta:{page:'start',title:'新建模板核验'},component:()=>import('../views/StartReview.vue')},
      {path:'/validation-records/:id',name:'validation-record-detail',meta:{page:'validations',title:'模板核验报告'},component:()=>import('../views/ValidationRecords.vue')},
      {path:'/drafting/new',name:'drafting-new',meta:{page:'drafting',title:'新建合同起草'},component:()=>import('../views/ContractDrafting.vue')},
      {path:'/drafting/:id/edit',name:'drafting-edit',meta:{page:'drafting',title:'编辑合同草稿'},component:()=>import('../views/ContractDrafting.vue')},
      {path: '/templates/:id/review', name: 'template-review', meta: {page: 'templates', title: '模板规则配置'}, component: () => import('../views/TemplateReview.vue')}],
    },
    {
      path: "/workbench",
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

router.beforeEach((to) => {
  if (to.path === '/records' && to.query.tab === 'templates') {
    const {tab, ...query} = to.query;
    return {path:'/validation-records',query,replace:true};
  }
});

router.afterEach((to, _from, failure) => {
  if (!failure)
    document.title = `${to.meta.title || "合同工作系统"} · LexisGraph`;
});
