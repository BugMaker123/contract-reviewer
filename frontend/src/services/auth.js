import { reactive } from 'vue';

export const auth = reactive({ web: false, user: null, ready: false });
export const can = (permission) => !auth.web || Boolean(auth.user?.permissions?.includes(permission));
export const homeForUser = () => [['review.view','/'],['drafting.view','/drafting'],['validation.view','/validation-records'],['templates.view','/templates'],['checklists.view','/checklists'],['catalog.view','/categories'],['users.manage','/admin/users'],['roles.manage','/admin/roles'],['models.manage','/admin/model']].find(([permission])=>can(permission))?.[1] || '/access-denied';
const originalFetch = window.fetch.bind(window);

window.fetch = async (input, options = {}) => {
  const url = new URL(typeof input === 'string' ? input : input.url, location.origin);
  if (url.origin === location.origin && url.pathname.startsWith('/api/')) {
    const method = (options.method || input.method || 'GET').toUpperCase();
    const headers = new Headers(options.headers || input.headers);
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
      const cookie = document.cookie.split('; ').find(item => item.startsWith('lexis_csrf='));
      if (cookie) headers.set('X-CSRF-Token', decodeURIComponent(cookie.slice(11)));
    }
    options = { ...options, headers, credentials: 'same-origin' };
  }
  const response = await originalFetch(input, options);
  if (auth.web && response.status === 401 && !url.pathname.endsWith('/login')) {
    auth.user = null;
    if (location.pathname !== '/login') location.assign('/login?return=' + encodeURIComponent(location.pathname + location.search));
  }
  return response;
};

export async function api(path, method = 'GET', body) {
  const response = await fetch(path, { method, headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '操作失败，请检查输入并重试');
  return data;
}

export const authReady = (async () => {
  const config = await api('/api/client-config');
  auth.web = config.web_mode;
  if (auth.web) {
    const response = await originalFetch('/api/auth/me');
    if (response.ok) auth.user = await response.json();
  }
  auth.ready = true;
})();

export async function logout() {
  await api('/api/auth/logout', 'POST');
  auth.user = null;
  location.assign('/login');
}
