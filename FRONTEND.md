# Vue 单页前端

前端使用 Vue 3、Vue Router 和 Vite。所有业务页面和审查工作台属于同一个应用，
站内切换使用客户端路由；后端负责 API、文档预览、下载和单页应用的历史路由回退。

## 启动

正常使用仍运行：

```powershell
.venv/Scripts/python.exe run.py
```

访问 http://127.0.0.1:8001。首次启动或前端源码更新后，启动器会安装缺失的前端依赖并构建；
需要安装 Node.js（兼容当前 Vite 的版本）和 npm。构建产物位于 `frontend/dist/`，不提交到 Git。
运行中的后端不会自动重新构建前端；修改后执行 `npm run build` 再刷新，或使用开发服务器。

前端开发使用两个终端：

```powershell
# 终端一，仓库根目录
.venv/Scripts/python.exe run.py

# 终端二
cd frontend
npm ci
npm run dev
```

开发页面为 http://127.0.0.1:5173，支持热更新；API 和文档静态资源代理到 8001。
手动构建：在 `frontend/` 执行 `npm run build`。

## 目录

```text
frontend/src/
  App.vue                    根路由出口；缓存业务布局，工作台退出时释放资源
  router/index.js            路由、历史模式、按需加载、页面标题
  layouts/PortalLayout.vue   公共顶部栏、侧栏和业务页面出口
  views/                     审查、记录、分类、清单、起草、工作台等页面
  components/portal/         上传、清单选择、配置弹窗、起草步骤
  components/workbench/      文档、概览、意见、审查进度、编辑器等
  composables/               页面生命周期、工作台审查流程、持久化适配
  stores/portal.js           跨页面模型配置、任务摘要和消息
  portal/pages.js            业务导航、状态模块、操作模块及数据依赖
  portal/state/              按业务维护的响应式状态
  portal/features/           按业务维护的操作和初始化
  portal/services/           文件提取和参考资料校验
  styles/                    全局业务样式、工作台范围内的样式
```

页面使用 `.vue` 单文件组件，逻辑通过 Composition API 组合。
组件显式接收本页 `context`，在同一份响应式状态上操作，避免复制审查版本或采纳状态。
文件输入的 `$refs` 与操作按钮放在同一个子组件中。

## 路由与状态

- 业务链接使用 `RouterLink`，操作完成后的导航使用 `router.push/replace`。
- 下载和独立原件预览保持普通文件请求。
- 业务页面使用 `KeepAlive` 保留输入、筛选和滚动位置；返回时刷新所需的业务数据。
- 起草页面离开时保存有效且修改过的草稿；保存失败会留在当前页面显示错误。
- 离开工作台前提交正文编辑和处理状态；失败时保留编辑器。
- 审查进行中可先完成或取消审查，再切换页面。
- 切换任务或历史版本会创建独立工作台会话；首次保存新任务编号时保留当前编辑器。
- 工作台退出时取消旧请求、清理自动保存定时器和浏览器事件监听。

## 扩展

1. 在 `views/` 添加页面，复杂区块放入 `components/`。
2. 业务页面在 `portal/pages.js` 声明导航、数据和模块，在 `router/index.js` 注册懒加载入口。
3. 页面状态和操作分别放入 `portal/state/`、`portal/features/`，或编写独立 composable。
4. API 路径沿用相对地址 `/api/...`，不要绑定具体域名或端口。
5. 导航使用 Vue Router，避免 `location.href` 和手工 `history.pushState`。
6. 新业务前端路由由后端历史回退自动支持；API 和资源不存在时继续返回 404。

`backend/ui.py` 只提供构建后的入口 HTML；`backend/frontend_build.py` 管理启动时构建。
`backend/static/document-preview.html` 继续独立承担 Word/PDF 预览和版式编辑。

## 验证

```powershell
cd frontend
npm ci
npm run build
cd ..
.venv/Scripts/python.exe -m pytest -q
```

浏览器回归覆盖无刷新导航、前进后退、表单保留、草稿保存恢复、工作台往返，
以及原有条款编辑、修订采纳、文档预览和导出。
