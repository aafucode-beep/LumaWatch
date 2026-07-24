"""SQLite FTS5 全文检索维护。

使用外部内容表方式：company_fts 与 company 表通过触发器保持同步。
非 SQLite 数据库时降级为 LIKE 查询（在 search 路由中处理）。
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import settings

IS_SQLITE = settings.database_url.startswith("sqlite")


def init_fts(db: Session) -> None:
    if not IS_SQLITE:
        return
    db.execute(
        text(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS company_fts USING fts5(
                name, name_cn, summary, history, philosophy,
                content='company', content_rowid='id',
                tokenize='unicode61'
            );
            """
        )
    )
    # 触发器：插入 / 更新 / 删除时同步 FTS
    db.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS company_ai AFTER INSERT ON company BEGIN
              INSERT INTO company_fts(rowid, name, name_cn, summary, history, philosophy)
              VALUES (new.id, new.name, new.name_cn, new.summary, new.history, new.philosophy);
            END;
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS company_ad AFTER DELETE ON company BEGIN
              INSERT INTO company_fts(company_fts, rowid, name, name_cn, summary, history, philosophy)
              VALUES ('delete', old.id, old.name, old.name_cn, old.summary, old.history, old.philosophy);
            END;
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS company_au AFTER UPDATE ON company BEGIN
              INSERT INTO company_fts(company_fts, rowid, name, name_cn, summary, history, philosophy)
              VALUES ('delete', old.id, old.name, old.name_cn, old.summary, old.history, old.philosophy);
              INSERT INTO company_fts(rowid, name, name_cn, summary, history, philosophy)
              VALUES (new.id, new.name, new.name_cn, new.summary, new.history, new.philosophy);
            END;
            """
        )
    )
    db.commit()


def search_company_ids(db: Session, query: str) -> list[int]:
    """返回匹配的 company id 列表（按相关度）。"""
    q = (query or "").strip()
    if not q:
        return []
    if IS_SQLITE:
        # FTS5 前缀匹配
        match_expr = " ".join(f'"{tok}"*' for tok in q.split() if tok)
        rows = db.execute(
            text(
                "SELECT rowid FROM company_fts WHERE company_fts MATCH :m ORDER BY rank"
            ),
            {"m": match_expr},
        ).fetchall()
        return [r[0] for r in rows]
    # 非 SQLite：LIKE 兜底
    like = f"%{q}%"
    rows = db.execute(
        text(
            "SELECT id FROM company WHERE name LIKE :l OR name_cn LIKE :l "
            "OR summary LIKE :l OR history LIKE :l OR philosophy LIKE :l"
        ),
        {"l": like},
    ).fetchall()
    return [r[0] for r in rows]
