"""Versioned, additive schema migrations shared by install and migration CLI."""
from sqlalchemy import text

MIGRATIONS = [(1, [
    '''CREATE TABLE objects (
        id VARCHAR(64) PRIMARY KEY, kind VARCHAR(64) NOT NULL, parent VARCHAR(64),
        data JSON NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
        created VARCHAR(40) NOT NULL, updated VARCHAR(40) NOT NULL,
        owner_user_id VARCHAR(64), created_by VARCHAR(64), updated_by VARCHAR(64),
        INDEX objects_kind_parent(kind,parent), INDEX objects_kind_updated(kind,updated,id),
        INDEX objects_owner_updated(owner_user_id,updated)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin''',
    '''CREATE TABLE review_events (
        id BIGINT PRIMARY KEY AUTO_INCREMENT, run_id VARCHAR(64) NOT NULL,
        data JSON NOT NULL, INDEX review_events_run(run_id,id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin''',
    'CREATE TABLE repository_lock (id INTEGER PRIMARY KEY) ENGINE=InnoDB',
    'INSERT INTO repository_lock(id) VALUES(1)',
])]


def migrate(engine):
    # MySQL DDL commits implicitly. Each statement is restartable by checking
    # table existence; a completed version is recorded only after all steps.
    with engine.connect() as db:
        locked = db.execute(text("SELECT GET_LOCK('lexis_schema_migration',30)")).scalar()
        if locked != 1:
            raise RuntimeError('Cannot acquire schema migration lock')
        try:
            db.execute(text('CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY) ENGINE=InnoDB'))
            db.commit()
            versions = set(db.execute(text('SELECT version FROM schema_migrations')).scalars())
            for version, statements in MIGRATIONS:
                if version in versions:
                    continue
                for statement in statements:
                    if statement.startswith('CREATE TABLE '):
                        statement = statement.replace('CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS ', 1)
                    elif statement.startswith('INSERT INTO repository_lock'):
                        statement += ' ON DUPLICATE KEY UPDATE id=id'
                    db.execute(text(statement))
                    db.commit()
                db.execute(text('INSERT INTO schema_migrations(version) VALUES(:version)'), {'version': version})
                db.commit()
            if 2 not in versions:
                from .security import metadata
                metadata.create_all(db)
                db.execute(text('INSERT INTO schema_migrations(version) VALUES(2)'))
                db.commit()
        finally:
            db.execute(text("SELECT RELEASE_LOCK('lexis_schema_migration')"))
            db.commit()
