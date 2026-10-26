# 集中部署与数据切换

后端只运行 **一个进程**。沿用进程内审查队列；禁止增加 Uvicorn workers。

## 准备

服务器准备 Python、MySQL 8.0、Nginx。发布前安装 requirements.txt 依赖并在 frontend 执行 `npm ci && npm run build`，启动不下载资源。复制 `.env.web.example` 为 `.env.web`，填写数据库账号、固定数据目录、正式域名和 Origin。生产 Cookie 必须保留 `LEXIS_COOKIE_SECURE=1`。

数据库账号仅授权独立应用库。密码中的特殊字符需 URL 编码。模型地址必须在 `LEXIS_MODEL_ALLOWED_ORIGINS` 中预置；管理员通过模型配置页填写统一地址、模型名和密钥。

初始化 SQL 位于 [`deploy/sql/init.sql`](../deploy/sql/init.sql)，包含业务存储、审查事件、账号、角色权限、会话、操作日志、模型配置及配置历史表。先创建独立 MySQL 8.0 数据库，再指定目标库导入：

```sh
mysql --default-character-set=utf8mb4 -u APP_USER -p APP_DATABASE < deploy/sql/init.sql
```

脚本可重复执行补建缺失表，不清空数据；已有表的结构升级仍以应用迁移程序为准。脚本不内置账号密码或模型密钥，导入后仍需执行下面的管理员初始化命令，由该命令创建默认角色和权限。已有账号的库不要再次执行 `web_admin init`。

生成模型加密主密钥：

```sh
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

主密钥放服务器安全配置，与数据库备份分开保管；丢失后无法解密原模型密钥。初始化账号使用交互输入独立密码：

```sh
python -m backend.web_admin --env .env.web init --username admin
```

命令输出的 admin_id 用作旧记录归属人。首次登录必须改密。

## 旧数据切换

停止旧服务，备份 SQLite 与 sources 目录。先核对重复分类与失效引用。迁移程序不会改写旧数据；目标库与目标 sources 必须为空（账号、角色等初始化表可以存在）。

```sh
# 默认读取 .env.web，可通过 --env 指定其他文件
python -m backend.migrate_data --sqlite /backup/lexis.db --sources /backup/sources --target-sources /srv/contract-reviewer/data/sources --owner ADMIN_ID
```

该命令读取 `LEXIS_DATABASE_URL`。保留所有 kind（包括 draft 与 contract_draft）、ID、revision 和审查事件；复制并校验全部已登记原件哈希；检查 parent 和 event 引用、迁移行数。迁移输出应另存为验收记录。无法区分的历史个人数据先归指定管理员，已发布模板和清单按公共规则提供。浏览器草稿由原使用者在切换前保存或导出。

迁移完成执行 `python -m backend.web_admin verify`。抽查旧合同、历史修订、核验报告、模板和 Word 导出，再停止旧系统写入。新系统有新数据后应先备份修复，不直接切回旧 SQLite。

## Nginx 与服务

使用 `deploy/nginx.conf.example` 和 `deploy/contract-reviewer.service`，替换路径、域名、证书与服务账号。文件目录不配置任何静态 location。前端 `/assets/` 与固定公共 `/static/` 由应用提供；业务原件始终经 API 鉴权。HTTPS 反向代理需关闭 SSE 缓冲。启动：`python run_web.py`。

本地 HTTP 联调可显式设 `LEXIS_COOKIE_SECURE=0`，并将本地准确 Origin 加入允许列表。正式机房使用 HTTPS、安全 Cookie 和准确域名。

## 备份与恢复

停止服务后执行一致性备份，完成再启动；每天备份一次，升级前额外备份。备份目录放应用服务器之外。以下工具备份 MySQL 全部表与文件，包含账号会话、角色权限和加密后的模型配置，逐文件记录 SHA-256；不包含模型加密主密钥。

```sh
python -m backend.web_admin backup --directory /offhost/backup/2026-10-26
python -m backend.web_admin --env .env.restore restore --directory /offhost/backup/2026-10-26
python -m backend.web_admin --env .env.restore verify
```

恢复目标必须是空库和空文件目录；环境文件指定新库、新目录与原加密主密钥。恢复演练必须登录、打开合同原件并导出 Word，不能只核对行数。

## 验收

双账号验证记录、原件、导出和 source_id 引用隔离；取消权限后手工请求 API 应拒绝；停用和重置密码使旧会话失效。浏览器清缓存后从带 ID 链接恢复，检查自动保存失败与 revision 冲突时保留输入。

使用模型模拟器验证多账号同时审查排队、查询、自动保存和导出。关闭页面后任务继续，重启后运行中与排队任务显示中断；已落库结果仍可读，人工重试。机房上线前另使用批准模型与实际法务人数进行容量验收。日志不得记录合同正文、密码和模型密钥。
