import { pages } from "./pages.js";

const stateModules = import.meta.glob("./state/*.js");
const featureModules = import.meta.glob("./features/*.js");
const loaded = new Map();

export async function loadPageModules(key) {
  if (loaded.has(key)) return loaded.get(key);
  const page = Object.values(pages).find((page) => page.key === key);
  if (!page) throw new Error(`页面未注册：${key}`);
  const [states, features] = await Promise.all([
    Promise.all(
      page.states.map((name) => stateModules[`./state/${name}.js`]()),
    ),
    Promise.all(
      page.features.map((name) => featureModules[`./features/${name}.js`]()),
    ),
  ]);
  const modules = { page, states, features };
  loaded.set(key, modules);
  return modules;
}

export function getPageModules(key) {
  const modules = loaded.get(key);
  if (!modules) throw new Error(`页面模块尚未加载：${key}`);
  return modules;
}
