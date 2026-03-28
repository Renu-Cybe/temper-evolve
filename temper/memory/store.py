"""记忆存储层 - 负责数据的持久化"""
import json
import os
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import uuid

from .types import Memory, MemoryType, Session, ProjectContext


class MemoryStore:
    """记忆存储管理器"""
    
    def __init__(self, base_path: Optional[str] = None):
        if base_path is None:
            base_path = os.path.expanduser("~/.temper/memory")
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化目录结构
        (self.base_path / "sessions").mkdir(exist_ok=True)
        (self.base_path / "projects").mkdir(exist_ok=True)
        (self.base_path / "vector").mkdir(exist_ok=True)
        
        # 初始化向量数据库
        self._init_vector_db()
        
        # 当前会话
        self._current_session: Optional[Session] = None
    
    def _init_vector_db(self):
        """初始化 SQLite 向量存储"""
        db_path = self.base_path / "vector" / "embeddings.db"
        self.conn = sqlite3.connect(str(db_path))
        cursor = self.conn.cursor()
        
        # 创建记忆表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT,
                content TEXT,
                timestamp TEXT,
                session_id TEXT,
                project TEXT,
                metadata TEXT,
                importance REAL,
                embedding BLOB
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_session ON memories(session_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_project ON memories(project)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_type ON memories(type)
        ''')
        
        self.conn.commit()
    
    # ========== 会话管理 ==========
    
    def create_session(self, project: Optional[str] = None) -> Session:
        """创建新会话"""
        session = Session(
            id=str(uuid.uuid4())[:8],
            start_time=datetime.now(),
            project=project
        )
        self._current_session = session
        return session
    
    def get_current_session(self) -> Optional[Session]:
        """获取当前会话"""
        return self._current_session
    
    def end_session(self, summary: Optional[str] = None):
        """结束当前会话"""
        if self._current_session:
            self._current_session.end_time = datetime.now()
            if summary:
                self._current_session.summary = summary
            self.save_session(self._current_session)
            self._current_session = None
    
    def save_session(self, session: Session):
        """保存会话到文件"""
        path = self.base_path / "sessions" / f"{session.id}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load_session(self, session_id: str) -> Optional[Session]:
        """加载会话"""
        path = self.base_path / "sessions" / f"{session_id}.json"
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return Session.from_dict(json.load(f))
        return None
    
    def list_sessions(self, project: Optional[str] = None, 
                     limit: int = 10) -> List[Session]:
        """列出历史会话"""
        sessions = []
        sessions_dir = self.base_path / "sessions"
        
        for file in sorted(sessions_dir.glob("*.json"), 
                          key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    session = Session.from_dict(json.load(f))
                    if project is None or session.project == project:
                        sessions.append(session)
                        if len(sessions) >= limit:
                            break
            except Exception:
                continue
        
        return sessions
    
    # ========== 记忆存储 ==========
    
    def save_memory(self, memory: Memory) -> str:
        """保存记忆到数据库"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO memories 
            (id, type, content, timestamp, session_id, project, metadata, importance, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            memory.id,
            memory.type.value,
            memory.content,
            memory.timestamp.isoformat(),
            memory.session_id,
            memory.project,
            json.dumps(memory.metadata),
            memory.importance,
            None  # embedding 待实现
        ))
        self.conn.commit()
        
        # 同时添加到当前会话
        if self._current_session and memory.session_id == self._current_session.id:
            self._current_session.messages.append(memory)
        
        return memory.id
    
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """获取单个记忆"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        )
        row = cursor.fetchone()
        if row:
            return self._row_to_memory(row)
        return None
    
    def search_memories(self, 
                       query: Optional[str] = None,
                       memory_type: Optional[MemoryType] = None,
                       project: Optional[str] = None,
                       session_id: Optional[str] = None,
                       since: Optional[datetime] = None,
                       limit: int = 50) -> List[Memory]:
        """搜索记忆"""
        cursor = self.conn.cursor()
        
        conditions = []
        params = []
        
        if memory_type:
            conditions.append("type = ?")
            params.append(memory_type.value)
        if project:
            conditions.append("project = ?")
            params.append(project)
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        if since:
            conditions.append("timestamp > ?")
            params.append(since.isoformat())
        if query:
            conditions.append("content LIKE ?")
            params.append(f"%{query}%")
        
        sql = "SELECT * FROM memories"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        return [self._row_to_memory(row) for row in cursor.fetchall()]
    
    def _row_to_memory(self, row) -> Memory:
        """数据库行转 Memory 对象"""
        return Memory(
            id=row[0],
            type=MemoryType(row[1]),
            content=row[2],
            timestamp=datetime.fromisoformat(row[3]),
            session_id=row[4],
            project=row[5],
            metadata=json.loads(row[6]) if row[6] else {},
            importance=row[7]
        )
    
    # ========== 项目上下文 ==========
    
    def save_project_context(self, context: ProjectContext):
        """保存项目上下文"""
        project_dir = self.base_path / "projects" / context.name
        project_dir.mkdir(exist_ok=True)
        
        path = project_dir / "context.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(context.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load_project_context(self, project_name: str) -> Optional[ProjectContext]:
        """加载项目上下文"""
        path = self.base_path / "projects" / project_name / "context.json"
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return ProjectContext.from_dict(json.load(f))
        return None
    
    def list_projects(self) -> List[str]:
        """列出所有项目"""
        projects_dir = self.base_path / "projects"
        return [d.name for d in projects_dir.iterdir() if d.is_dir()]
    
    # ========== 统计与维护 ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM memories")
        total_memories = cursor.fetchone()[0]
        
        cursor.execute("SELECT type, COUNT(*) FROM memories GROUP BY type")
        type_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        sessions = len(list((self.base_path / "sessions").glob("*.json")))
        projects = len(self.list_projects())
        
        return {
            "total_memories": total_memories,
            "by_type": type_counts,
            "total_sessions": sessions,
            "total_projects": projects,
            "storage_path": str(self.base_path)
        }
    
    def cleanup_old_memories(self, days: int = 30):
        """清理旧记忆"""
        cutoff = datetime.now() - timedelta(days=days)
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM memories WHERE timestamp < ? AND importance < 1.0",
            (cutoff.isoformat(),)
        )
        self.conn.commit()
        return cursor.rowcount
    
    def close(self):
        """关闭数据库连接"""
        self.conn.close()
