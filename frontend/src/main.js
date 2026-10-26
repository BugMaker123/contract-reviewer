import { createApp } from "vue";
import App from "./App.vue";
import { router } from "./router/index.js";
import "./styles/portal.css";
import { can } from './services/auth.js';

const app = createApp(App);
app.directive('can', {
  mounted(el, binding) { if(!can(binding.value)) el.style.setProperty('display','none','important'); },
  updated(el, binding) { if(!can(binding.value)) el.style.setProperty('display','none','important'); },
});
app.use(router);
router
  .isReady()
  .then(() => app.mount("#app"))
  .catch((error) => {
    const target = document.getElementById("app");
    target.textContent = `页面加载失败，请刷新重试：${error.message}`;
    target.setAttribute("role", "alert");
  });
