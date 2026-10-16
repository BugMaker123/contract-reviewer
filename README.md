# LexisGraph 内部合同工作系统

保留蓝白灰视觉风格与三栏审查工作台，提供长期审查记录、企业审查清单、合同对比、Word 交付及分阶段起草。

## 启动

前端已迁移为 Vue 3 单页应用。请先安装 Node.js 和 npm；启动器会按需安装前端依赖并构建。

```powershell
uv venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
.venv/Scripts/python.exe run.py
```

访问 http://127.0.0.1:8001。当前默认是仅本机可访问的单个内部实例，尚未接入组织账号、权限和审批流。

## 功能

- 主页支持上传 DOCX、文字型 PDF、TXT 或粘贴正文，设置立场、审查尺度、交易背景及重点要求。
- 快速审查执行基础规则；深度审查结合配置的模型与参考资料。结果会标明模型来源、规则回退和覆盖范围。
- 企业清单支持文件提取草稿、人工编辑、发布和版本固定；核验结果区分通过、未通过、待确认及不适用。
- 对比审查识别新增、删除和修改；可用模型进一步评估变化，无模型时明确保留待人工评估。
- Workbench 支持定位、采纳/撤销、人工备注、处理状态、条款编辑、单条追问和历史版本查看。
- Word 可导出当前稿、含修订痕迹的稿件、全部建议稿及不同范围的意见书；保留匹配的原 DOCX 版式，其他来源按统一版式重排。
- 起草按背景、交易信息、大纲和正文分阶段保存；支持参考模板、资料、定向改写提案、历史草稿和送审。

生成、语义检查和追问需要可用模型。配置可在页面填写，或由服务端的 DEEPSEEK_API_KEY / OPENAI_API_KEY 环境变量提供。浏览器配置不写入案件数据库。

数据保存在 `data/lexis.db`，原始文件保存在 `data/sources/`；备份时应一起备份。任务可归档和恢复。服务重启时未完成的审查标记中断，旧结果保留。

详细步骤见 [内部系统使用说明](docs/内部系统使用说明.md)，设计取舍见 [功能对照与实施方案](docs/参考网站功能对照与实施方案.md)。

## 开发与验证

```powershell
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt
.venv/Scripts/python.exe -m pytest -q
npx --yes tailwindcss@3.4.17 -i ./backend/static/styles.input.css -o ./backend/static/vendor/tailwind.css --minify
```

Vue 和路由通过 Vite 打包后由本机服务提供，运行时无需外部 CDN。前端开发和扩展见 [前端架构说明](FRONTEND.md)。后端热重载仅监控 `backend/`，避免测试和临时转换工具触发服务重启。

## 主要文件

- `backend/main.py`：服务入口、文件提取与兼容审查接口。
- `backend/store.py`：SQLite 存储、版本冲突和运行恢复。
- `backend/workspace_api.py`：任务、清单、起草和交付接口。
- `backend/workspace_review.py`：审查模式、逐项核验与差异分析。
- `backend/word_export.py`：Word 版式保留、修订标记和批注。
- `frontend/src/views/`、`layouts/` 与 `components/`：Vue 页面、公共布局及业务组件。
- `frontend/src/composables/`：工作台流程、页面生命周期与持久化适配。
- `frontend/src/router/`：无刷新路由及页面懒加载。
