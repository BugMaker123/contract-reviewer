<script setup>
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { auth, api } from '../services/auth.js';
const route = useRoute(), router = useRouter();
const username=ref(''), password=ref(''), nextPassword=ref(''), error=ref(''), busy=ref(false);
async function submit() {
  busy.value=true; error.value='';
  try {
    if (route.path === '/change-password') {
      await api('/api/auth/password','POST',{current_password:password.value,new_password:nextPassword.value});
      auth.user=null; password.value=''; nextPassword.value='';
      await router.replace('/login');
    } else {
      auth.user=await api('/api/auth/login','POST',{username:username.value,password:password.value});
      const target=String(route.query.return || '/');
      await router.replace(auth.user.must_change_password ? '/change-password' : target.startsWith('/') && !target.startsWith('//') ? target : '/');
    }
  } catch (e) { error.value=e.message; } finally { busy.value=false; }
}
</script>
<template>
  <main class="login-page"><form class="login-card" @submit.prevent="submit">
    <h1>{{ $route.path === '/change-password' ? '修改密码' : '合同工作系统' }}</h1>
    <p>{{ $route.path === '/change-password' ? '首次登录或密码重置后，请设置个人密码。修改后重新登录。' : '使用管理员分配的账号登录' }}</p>
    <label v-if="$route.path !== '/change-password'">账号<input v-model="username" required autocomplete="username" maxlength="100"></label>
    <label>{{ $route.path === '/change-password' ? '原密码' : '密码' }}<input v-model="password" required type="password" autocomplete="current-password" maxlength="200"></label>
    <label v-if="$route.path === '/change-password'">新密码（至少 12 个字符）<input v-model="nextPassword" required minlength="12" maxlength="200" type="password" autocomplete="new-password"></label>
    <p v-if="error" role="alert" class="text-red-600">{{ error }}</p><button class="button" :disabled="busy">{{ busy ? '处理中…' : $route.path === '/change-password' ? '修改并重新登录' : '登录' }}</button>
  </form></main>
</template>
<style scoped>
.login-page{min-height:100vh;display:grid;place-items:center;background:#f1f5f9}.login-card{width:min(420px,90vw);padding:36px;background:white;border:1px solid #e2e8f0;border-radius:16px;display:grid;gap:20px}.login-card h1{font-size:24px;font-weight:700}.login-card label{display:grid;gap:8px}.login-card input{padding:10px;border:1px solid #cbd5e1;border-radius:6px}.login-card p{font-size:14px;color:#64748b}
</style>
