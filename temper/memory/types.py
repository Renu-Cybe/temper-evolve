"""记忆类型定义"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Any
import json


class MemoryType(Enum):
    """记忆类型"""
    MESSAGE = "message"           # 对话消息
    FACT = "fact"                 # 关键事实
    CODE = "code"                 # 代码片段
    ERROR = "error"               # 错误记录
    DECISION = "decision"         # 决策记录
    SUMMARY = "summary"           # 会话摘要
    PROJECT = "project"           # 项目上下文


@dataclass
class Memory:
    """单个记忆单元"""
    id: str
    type: MemoryType
    content: str
    timestamp: datetime
    session_id: Optional[str] = None
    project: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 1.0  # 0.0-2.0, 重要性评分
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "project": self.project,
            "metadata": self.metadata,
            "importance": self.importance
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Memory":
        return cls(
            id=data["id"],
            type=MemoryType(data["type"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            session_id=data.get("session_id"),
            project=data.get("project"),
            metadata=data.get("metadata", {}),
            importance=data.get("importance", 1.0)
        )


@dataclass
class Session:
    """会话记录"""
    id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    project: Optional[str] = None
    messages: List[Memory] = field(default_factory=list)
    summary: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "project": self.project,
            "messages": [m.to_dict() for m in self.messages],
            "summary": self.summary
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Session":
        return cls(
            id=data["id"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            project=data.get("project"),
            messages=[Memory.from_dict(m) for m in data.get("messages", [])],
            summary=data.get("summary")
        )


@dataclass
class ProjectContext:
    """项目上下文"""
    name: str
    path: str
    description: Optional[str] = None
    tech_stack: List[str] = field(default_factory=list)
    key_files: List[str] = field(default_factory=list)
    conventions: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "path": self.path,
            "description": self.description,
            "tech_stack": self.tech_stack,
            "key_files": self.key_files,
            "conventions": self.conventions,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ProjectContext":
        return cls(
            name=data["name"],
            path=data["path"],
            description=data.get("description"),
            tech_stack=data.get("tech_stack", []),
            key_files=data.get("key_files", []),
            conventions=data.get("conventions", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"])
        )
