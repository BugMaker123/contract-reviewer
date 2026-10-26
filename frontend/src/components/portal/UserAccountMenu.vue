<script setup>
import { ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { auth, logout } from '../../services/auth.js';
import ReviewIcon from './ReviewIcon.vue';
const emit=defineEmits(['help']);
const menuOpen=ref(false), route=useRoute();
watch(()=>route.path,()=>menuOpen.value=false);
</script>
<template>
    <div v-if="auth.web" class="header-account" @keydown.esc="menuOpen=false" @focusout="!$event.currentTarget.contains($event.relatedTarget) && (menuOpen=false)">
      <div v-if="menuOpen" class="header-account-menu" id="header-account-menu">
        <div class="account-menu-caption">我的账号 <small>{{ auth.user?.username }}</small></div>
        <button @click="emit('help'); menuOpen=false"><ReviewIcon name="info"/>操作手册</button>
        <RouterLink to="/change-password"><ReviewIcon name="shield"/>修改密码</RouterLink>
        <button class="account-logout" @click="logout"><ReviewIcon name="arrow"/>退出登录</button>
      </div>
      <button class="header-account-trigger" :aria-expanded="menuOpen" aria-controls="header-account-menu" aria-label="用户菜单" @click="menuOpen=!menuOpen">
        <span class="header-avatar">{{ (auth.user?.name || '用').slice(0,1) }}<i></i></span>
        <span class="header-account-copy"><strong>{{ auth.user?.name || '当前用户' }}</strong><small>{{ auth.user?.username || '个人账号' }}</small></span>
        <span class="header-account-chevron" aria-hidden="true">⌄</span>
      </button>
    </div>
</template>
<style scoped>
.header-account{position:relative;margin-top:auto;padding-top:22px;flex-shrink:0}.header-account-trigger{display:flex;align-items:center;gap:11px;width:100%;padding:14px 9px 0;border:0;border-top:1px solid #ffffff12;background:none;color:#e5ecf7;text-align:left;cursor:pointer}.header-avatar{position:relative;display:grid;place-items:center;flex-shrink:0;width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,#6688bf,#365681);border:2px solid #ffffff25;font-size:15px;font-weight:600}.header-avatar i{position:absolute;bottom:-1px;right:-1px;width:10px;height:10px;border-radius:50%;background:#54c69e;border:2px solid #17243a}.header-account-copy{display:grid;gap:5px;min-width:0;flex:1}.header-account-copy strong{font-size:12px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.header-account-copy small{font-size:10px;color:#8094b2}.header-account-chevron{color:#8c9fba}.header-account-menu{position:absolute;bottom:70px;left:0;right:0;padding:7px;background:#fff;border:1px solid #e1e8f2;border-radius:12px;box-shadow:0 12px 35px #07172e35;color:#415779}.account-menu-caption{display:grid;gap:5px;padding:11px 10px 13px;font-size:12px;font-weight:600;border-bottom:1px solid #edf1f6;margin-bottom:5px}.account-menu-caption small{color:#94a3b8;font-size:11px;font-weight:400}.header-account-menu button,.header-account-menu a{display:flex;align-items:center;gap:10px;width:100%;padding:11px 10px;border:0;border-radius:7px;background:none;color:#536782;font-size:12px;text-align:left;text-decoration:none;cursor:pointer}.header-account-menu button:hover,.header-account-menu a:hover{background:#f0f5fd;color:#356fc5}.header-account-menu .account-logout{color:#c56969;border-top:1px solid #edf1f6;border-radius:0;margin-top:4px}.header-account-trigger:focus-visible{outline:2px solid #729ce0;outline-offset:3px}.header-account{margin:0;padding:0;position:relative}.header-account-trigger{border:0;padding:5px 8px;gap:10px;color:#32465f;border-radius:9px}.header-account-trigger:hover{background:#f5f7fb}.header-avatar{width:34px;height:34px;font-size:13px;border:1px solid #e0e8f6;background:linear-gradient(135deg,#e5edfc,#cbdcf5);color:#4e72a9}.header-avatar i{border-color:#fff;width:9px;height:9px}.header-account-copy{gap:3px}.header-account-copy strong{font-size:12px}.header-account-copy small{color:#97a4b6;font-size:10px}.header-account-menu{top:54px;bottom:auto;left:auto;right:0;width:208px;z-index:80;box-shadow:0 8px 30px #223b601a}.header-account-chevron{font-size:15px;padding:0 3px;color:#8a9aaf}@media(max-width:650px){.header-account-copy,.header-account-chevron{display:none}.header-account-trigger{padding:4px}.header-account-menu{top:48px}}
</style>
