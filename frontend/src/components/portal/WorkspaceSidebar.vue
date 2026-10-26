<script setup>
import ReviewIcon from './ReviewIcon.vue';

const props = defineProps({ active: { type: String, default: '' }, beforeNavigate: { type: Function, default: null } });
const groups = [
  { title: '合同工作', items: [
    { key: 'start', label: '开始', href: '/', icon: 'home' },
    { key: 'records', label: '审查记录', href: '/records', icon: 'records' },
    { key: 'validations', label: '模板核验记录', href: '/validation-records', icon: 'validations' },
    { key: 'drafting', label: '合同起草', href: '/drafting', icon: 'drafting' },
    { key: 'chat', label: '知识库对话', href: '/chat', icon: 'records' },
  ] },
  { title: '标准与资料', items: [
    { key: 'templates', label: '合同模板', href: '/templates', icon: 'templates' },
    { key: 'template-groups', label: '模板分组', href: '/template-groups', icon: 'categories' },
    { key: 'categories', label: '业务分类', href: '/categories', icon: 'categories' },
    { key: 'checklists', label: '审查清单', href: '/checklists', icon: 'checklists' },
    { key: 'knowledge', label: '知识库与图谱', href: '/knowledge', icon: 'categories' },
  ] },
];
function navigate(event, href) {
  if (!props.beforeNavigate || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button) return;
  event.preventDefault();
  props.beforeNavigate(href);
}
</script>

<template>
  <aside class="portal-sidebar workspace-sidebar">
    <RouterLink to="/" class="prototype-side-brand" aria-label="返回开始" title="返回开始" @click="navigate($event, '/')"><span class="prototype-side-mark" aria-hidden="true">◇</span><strong>LexisGraph</strong></RouterLink>
    <p class="prototype-side-label">工作空间</p>
    <nav class="portal-navigation" aria-label="功能导航">
      <section v-for="group in groups" :key="group.title" class="portal-nav-group" :aria-label="group.title">
        <h2 class="portal-nav-label">{{ group.title }}</h2>
        <RouterLink v-for="item in group.items" :key="item.key" :to="item.href" class="nav-link" :class="{ active: active === item.key }" :aria-label="item.label" :title="item.label" @click="navigate($event, item.href)">
          <ReviewIcon :name="item.icon" class="nav-icon" aria-hidden="true" /><span>{{ item.label }}</span>
        </RouterLink>
      </section>
    </nav>
  </aside>
</template>
