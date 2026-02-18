from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Segment:
    """视频分段：每轮 AI 会话在同一场景中添加新分段"""
    id: int
    workspace: str
    segment_index: int
    input_text: str
    cumulative_code: str  # 累积的完整代码
    section_video_path: str  # 当前分段的视频路径
    created_at: str


class Database:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path.as_posix())

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace TEXT NOT NULL,
                    segment_index INTEGER NOT NULL,
                    input_text TEXT NOT NULL,
                    cumulative_code TEXT NOT NULL DEFAULT '',
                    section_video_path TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_segments_workspace ON segments(workspace)"
            )
            self._migrate_tables(conn)

    def _migrate_tables(self, conn: sqlite3.Connection) -> None:
        """从旧 history 表迁移到新 segments 表"""
        try:
            conn.execute("SELECT id FROM history LIMIT 1")
        except sqlite3.OperationalError:
            return
        try:
            rows = conn.execute(
                "SELECT workspace, input_text, manim_code, video_path, created_at FROM history ORDER BY id"
            ).fetchall()
            workspace_counts: dict[str, int] = {}
            for row in rows:
                workspace = row[0] or "default"
                idx = workspace_counts.get(workspace, 0)
                conn.execute(
                    "INSERT INTO segments (workspace, segment_index, input_text, cumulative_code, section_video_path, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (workspace, idx, row[1], row[2] or "", row[3] or "", row[4]),
                )
                workspace_counts[workspace] = idx + 1
            conn.execute("DROP TABLE history")
        except sqlite3.OperationalError:
            pass

    def create_segment(self, workspace: str, input_text: str) -> Segment:
        """创建新分段，自动分配 segment_index"""
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            # 获取下一个分段索引
            row = conn.execute(
                "SELECT COALESCE(MAX(segment_index), -1) + 1 FROM segments WHERE workspace = ?",
                (workspace,),
            ).fetchone()
            segment_index = row[0]
            
            # 插入新分段
            cursor = conn.execute(
                "INSERT INTO segments (workspace, segment_index, input_text, cumulative_code, section_video_path, created_at) "
                "VALUES (?, ?, ?, '', '', ?)",
                (workspace, segment_index, input_text, created_at),
            )
            segment_id = int(cursor.lastrowid)
        
        return Segment(
            id=segment_id,
            workspace=workspace,
            segment_index=segment_index,
            input_text=input_text,
            cumulative_code="",
            section_video_path="",
            created_at=created_at,
        )

    def update_segment_render(self, segment_id: int, cumulative_code: str, section_video_path: str) -> None:
        """更新分段的渲染结果"""
        with self._connect() as conn:
            conn.execute(
                "UPDATE segments SET cumulative_code = ?, section_video_path = ? WHERE id = ?",
                (cumulative_code, section_video_path, segment_id),
            )

    def list_segments(self, workspace: str, limit: int = 200) -> list[Segment]:
        """按 segment_index 降序列出分段（最新优先）"""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, workspace, segment_index, input_text, cumulative_code, section_video_path, created_at "
                "FROM segments WHERE workspace = ? ORDER BY segment_index DESC LIMIT ?",
                (workspace, limit),
            ).fetchall()
        return [self._row_to_segment(row) for row in rows]

    def list_segments_asc(self, workspace: str) -> list[Segment]:
        """按 segment_index 升序列出分段（用于连续播放）"""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, workspace, segment_index, input_text, cumulative_code, section_video_path, created_at "
                "FROM segments WHERE workspace = ? ORDER BY segment_index ASC",
                (workspace,),
            ).fetchall()
        return [self._row_to_segment(row) for row in rows]

    def get_latest_cumulative_code(self, workspace: str) -> str:
        """获取工作区最新的累积代码（用于继续添加分段）"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT cumulative_code FROM segments WHERE workspace = ? ORDER BY segment_index DESC LIMIT 1",
                (workspace,),
            ).fetchone()
        return row[0] if row and row[0] else ""

    def get_segment_count(self, workspace: str) -> int:
        """获取工作区分段数量"""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM segments WHERE workspace = ?",
                (workspace,),
            ).fetchone()
        return row[0] if row else 0

    def _row_to_segment(self, row: tuple) -> Segment:
        return Segment(
            id=int(row[0]),
            workspace=row[1],
            segment_index=int(row[2]),
            input_text=row[3],
            cumulative_code=row[4] or "",
            section_video_path=row[5] or "",
            created_at=row[6],
        )

    def get_setting(self, key: str, default: str = "") -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
            ).fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def bulk_set_settings(self, items: Iterable[tuple[str, str]]) -> None:
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                list(items),
            )

    def delete_workspace_data(self, workspace: str) -> None:
        """删除工作区的所有分段和设置"""
        with self._connect() as conn:
            conn.execute("DELETE FROM segments WHERE workspace = ?", (workspace,))
            conn.execute("DELETE FROM settings WHERE key LIKE ?", (f"%::{workspace}",))

    def delete_segment(self, segment_id: int) -> None:
        """删除指定的分段"""
        with self._connect() as conn:
            conn.execute("DELETE FROM segments WHERE id = ?", (segment_id,))
