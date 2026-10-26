-- LexisGraph / MySQL 8.0 数据库初始化
-- 使用方式：mysql --default-character-set=utf8mb4 -u APP_USER -p APP_DATABASE < deploy/sql/init.sql
-- 请先创建独立数据库并在命令中指定；本脚本不创建或切换数据库。
-- 在停止应用的情况下执行。仅适用于新库或补建缺失表，不覆盖已有表结构和业务数据。
-- 表结构来源：backend/schema.py、backend/security.py。
-- 初始管理员、默认角色与权限由下列命令创建（交互输入独立密码）：
-- python -m backend.web_admin --env .env.web init --username admin
-- 不包含默认密码、模型密钥、业务示例或生产数据。
SET NAMES utf8mb4;


CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS objects (
        id VARCHAR(64) PRIMARY KEY, kind VARCHAR(64) NOT NULL, parent VARCHAR(64),
        data JSON NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
        created VARCHAR(40) NOT NULL, updated VARCHAR(40) NOT NULL,
        owner_user_id VARCHAR(64), created_by VARCHAR(64), updated_by VARCHAR(64),
        INDEX objects_kind_parent(kind,parent), INDEX objects_kind_updated(kind,updated,id),
        INDEX objects_owner_updated(owner_user_id,updated)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS review_events (
        id BIGINT PRIMARY KEY AUTO_INCREMENT, run_id VARCHAR(64) NOT NULL,
        data JSON NOT NULL, INDEX review_events_run(run_id,id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS repository_lock (id INTEGER PRIMARY KEY) ENGINE=InnoDB;

INSERT INTO repository_lock(id) VALUES(1) ON DUPLICATE KEY UPDATE id=id;

CREATE TABLE IF NOT EXISTS model_settings (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	data TEXT NOT NULL, 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS model_settings_history (
	id VARCHAR(64) NOT NULL, 
	data TEXT NOT NULL, 
	created VARCHAR(40) NOT NULL, 
	operator VARCHAR(200) NOT NULL, 
	action VARCHAR(30) NOT NULL, 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS operation_logs (
	id VARCHAR(64) NOT NULL, 
	user_id VARCHAR(64), 
	action VARCHAR(100) NOT NULL, 
	target VARCHAR(200), 
	created VARCHAR(40) NOT NULL, 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS role_permissions (
	role_id VARCHAR(64) NOT NULL, 
	permission VARCHAR(100) NOT NULL, 
	PRIMARY KEY (role_id, permission)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS roles (
	id VARCHAR(64) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description TEXT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS sessions (
	digest VARCHAR(64) NOT NULL, 
	user_id VARCHAR(64) NOT NULL, 
	csrf_digest VARCHAR(64) NOT NULL, 
	expires VARCHAR(40) NOT NULL, 
	PRIMARY KEY (digest),
	INDEX ix_sessions_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS user_roles (
	user_id VARCHAR(64) NOT NULL, 
	role_id VARCHAR(64) NOT NULL, 
	PRIMARY KEY (user_id, role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS users (
	id VARCHAR(64) NOT NULL, 
	username VARCHAR(100) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	password_hash TEXT NOT NULL, 
	active BOOL NOT NULL, 
	must_change_password BOOL NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

INSERT INTO schema_migrations(version) VALUES (1), (2) ON DUPLICATE KEY UPDATE version=version;
