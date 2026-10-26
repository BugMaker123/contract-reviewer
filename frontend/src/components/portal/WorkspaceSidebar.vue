<script setup>
import ReviewIcon from './ReviewIcon.vue';
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { auth, can } from '../../services/auth.js';

const collapsed=ref({});
const route=useRoute();
watch(()=>route.path,()=>{const group=groups.value.find(group=>group.items.some(item=>item.href===route.path));if(group)collapsed.value[group.title]=false;});
const props = defineProps({ active: { type: String, default: '' }, beforeNavigate: { type: Function, default: null } });
const allGroups = [
  { title: '合同工作', items: [
    { key: 'start', label: '开始', href: '/', icon: 'home' },
    { key: 'review-new', label: '新建合同审查', href: '/reviews/new', icon: 'plus' },
    { key: 'template-check-new', label: '新建模板核验', href: '/template-checks/new', icon: 'validations' },
    { key: 'records', label: '审查记录', href: '/records', icon: 'records' },
    { key: 'validations', label: '模板核验记录', href: '/validation-records', icon: 'validations' },
    { key: 'drafting', label: '合同起草', href: '/drafting', icon: 'drafting' },
  ] },
  { title: '标准与资料', items: [
    { key: 'templates', label: '合同模板', href: '/templates', icon: 'templates' },
    { key: 'template-groups', label: '模板分组', href: '/template-groups', icon: 'categories' },
    { key: 'categories', label: '业务分类', href: '/categories', icon: 'categories' },
    { key: 'checklists', label: '审查清单', href: '/checklists', icon: 'checklists' },
  ] },
];
const activeKey=computed(()=>route.path==='/reviews/new'?'review-new':route.path==='/template-checks/new'?'template-check-new':props.active);
const permissionMap={'review-new':'review.create','template-check-new':'validation.execute',start:'review.view',records:'review.view',validations:'validation.view',drafting:'drafting.view',templates:'templates.view',checklists:'checklists.view',categories:'catalog.view','template-groups':'catalog.view',users:'users.manage',roles:'roles.manage',model:'models.manage'};
const groups=computed(()=>[...allGroups,...(auth.web?[{title:'系统管理',items:[{key:'users',label:'账号管理',href:'/admin/users',icon:'categories'},{key:'roles',label:'角色权限',href:'/admin/roles',icon:'checklists'},{key:'model',label:'模型配置',href:'/admin/model',icon:'categories'}]}]:[])].map(group=>({...group,items:group.items.filter(item=>can(permissionMap[item.key]))})).filter(group=>group.items.length));
function navigate(event, href) {
  if (!props.beforeNavigate || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button) return;
  event.preventDefault();
  props.beforeNavigate(href);
}
</script>

<template>
  <aside class="portal-sidebar workspace-sidebar">
    <RouterLink to="/" class="prototype-side-brand" aria-label="返回开始" title="返回开始" @click="navigate($event, '/')"><span class="prototype-side-mark" aria-hidden="true">◇</span><strong>LexisGraph</strong></RouterLink>
    <nav class="portal-navigation" aria-label="功能导航">
      <section v-for="group in groups" :key="group.title" class="portal-nav-group" :aria-label="group.title">
        <h2 class="portal-group-heading"><button type="button" :aria-expanded="!collapsed[group.title]" :aria-controls="'nav-group-'+group.title" @click="collapsed[group.title]=!collapsed[group.title]" :title="(collapsed[group.title]?'展开':'收起')+group.title"><span>{{ group.title }}</span><svg :class="{collapsed:collapsed[group.title]}" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg></button></h2>
        <div v-show="!collapsed[group.title]" :id="'nav-group-'+group.title" class="portal-group-items">
        <RouterLink v-for="item in group.items" :key="item.key" :to="item.href" class="nav-link" :class="{ active: activeKey === item.key }" :aria-label="item.label" :title="item.label" @click="navigate($event, item.href)">
          <ReviewIcon :name="item.icon" class="nav-icon" aria-hidden="true" /><span>{{ item.label }}</span>
        </RouterLink>
        </div>
      </section>
    </nav>

  </aside>
</template>

<style scoped>
.workspace-sidebar .portal-navigation{margin-top:30px}.portal-group-heading{margin:0 0 7px;padding:0}.portal-group-heading button{display:flex;align-items:center;justify-content:space-between;width:100%;padding:8px 13px;border:0;border-radius:6px;background:transparent;color:#a7b8ce;font-size:14px;font-weight:650;cursor:pointer;text-align:left;letter-spacing:.02em}.portal-group-heading button:hover{color:#eef3ff;background:#ffffff05}.portal-group-heading button:focus-visible{outline:2px solid #739ce4;outline-offset:-2px}.portal-group-heading svg{color:#7186a3;transition:transform .18s}.portal-group-heading svg.collapsed{transform:rotate(-90deg)}.portal-group-items{display:grid;gap:3px}@media(max-width:800px){.workspace-sidebar .portal-navigation{margin-top:22px}.portal-group-heading button{padding:8px 0;justify-content:center;font-size:11px;letter-spacing:0}.portal-group-heading svg{display:none}}
</style>
