"""
序列化器

提供多种序列化格式支持
"""

from typing import Any, Protocol
import json
import pickle
import base64


class Serializer(Protocol):
    """序列化器协议
    
    所有序列化器必须实现此协议
    """
    
    def serialize(self, obj: Any) -> bytes:
        """将对象序列化为字节"""
        ...
    
    def deserialize(self, data: bytes) -> Any:
        """将字节反序列化为对象"""
        ...
    
    @property
    def content_type(self) -> str:
        """返回内容类型标识"""
        ...
    
    @property
    def file_extension(self) -> str:
        """返回文件扩展名"""
        ...


class JSONSerializer:
    """JSON序列化器
    
    适用于简单数据结构，人类可读
    
    使用示例：
        serializer = JSONSerializer()
        data = serializer.serialize({'key': 'value'})
        obj = serializer.deserialize(data)
    """
    
    def __init__(self, indent: Optional[int] = None, 
                 ensure_ascii: bool = False,
                 default: callable = None):
        self._indent = indent
        self._ensure_ascii = ensure_ascii
        self._default = default or self._default_encoder
    
    def _default_encoder(self, obj: Any) -> Any:
        """默认编码器，处理常见类型"""
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        if hasattr(obj, 'isoformat'):  # datetime
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def serialize(self, obj: Any) -> bytes:
        """序列化为JSON字节"""
        return json.dumps(
            obj, 
            indent=self._indent,
            ensure_ascii=self._ensure_ascii,
            default=self._default
        ).encode('utf-8')
    
    def deserialize(self, data: bytes) -> Any:
        """从JSON字节反序列化"""
        return json.loads(data.decode('utf-8'))
    
    @property
    def content_type(self) -> str:
        return "application/json"
    
    @property
    def file_extension(self) -> str:
        return ".json"


class PickleSerializer:
    """Pickle序列化器
    
    适用于复杂Python对象，包括自定义类实例
    
    警告：只用于内部状态，不要用于用户输入的数据
    
    使用示例：
        serializer = PickleSerializer()
        data = serializer.serialize(complex_object)
        obj = serializer.deserialize(data)
    """
    
    def __init__(self, protocol: int = pickle.HIGHEST_PROTOCOL):
        self._protocol = protocol
    
    def serialize(self, obj: Any) -> bytes:
        """序列化为Pickle字节"""
        return pickle.dumps(obj, protocol=self._protocol)
    
    def deserialize(self, data: bytes) -> Any:
        """从Pickle字节反序列化"""
        return pickle.loads(data)
    
    @property
    def content_type(self) -> str:
        return "application/python-pickle"
    
    @property
    def file_extension(self) -> str:
        return ".pkl"


class Base64Serializer:
    """Base64包装序列化器
    
    将二进制序列化结果转为Base64文本，便于存储和传输
    
    使用示例：
        inner = PickleSerializer()
        serializer = Base64Serializer(inner)
        text = serializer.serialize(obj)  # 返回bytes，但内容是base64
    """
    
    def __init__(self, inner: Serializer):
        self._inner = inner
    
    def serialize(self, obj: Any) -> bytes:
        """序列化并Base64编码"""
        data = self._inner.serialize(obj)
        return base64.b64encode(data)
    
    def deserialize(self, data: bytes) -> Any:
        """Base64解码并反序列化"""
        decoded = base64.b64decode(data)
        return self._inner.deserialize(decoded)
    
    @property
    def content_type(self) -> str:
        return f"{self._inner.content_type};base64"
    
    @property
    def file_extension(self) -> str:
        return f"{self._inner.file_extension}.b64"


class CompressedSerializer:
    """压缩包装序列化器
    
    使用gzip压缩序列化结果
    
    使用示例：
        inner = JSONSerializer()
        serializer = CompressedSerializer(inner)
        compressed = serializer.serialize(large_object)
    """
    
    def __init__(self, inner: Serializer, level: int = 6):
        self._inner = inner
        self._level = level
    
    def serialize(self, obj: Any) -> bytes:
        """序列化并压缩"""
        import gzip
        data = self._inner.serialize(obj)
        return gzip.compress(data, compresslevel=self._level)
    
    def deserialize(self, data: bytes) -> Any:
        """解压并反序列化"""
        import gzip
        decompressed = gzip.decompress(data)
        return self._inner.deserialize(decompressed)
    
    @property
    def content_type(self) -> str:
        return f"{self._inner.content_type};gzip"
    
    @property
    def file_extension(self) -> str:
        return f"{self._inner.file_extension}.gz"


# 便捷函数
def get_serializer(format: str = 'json') -> Serializer:
    """根据格式获取序列化器
    
    Args:
        format: 格式名称 ('json', 'pickle', 'json_compressed', 'pickle_compressed')
        
    Returns:
        对应的序列化器实例
    """
    format = format.lower()
    
    if format == 'json':
        return JSONSerializer()
    elif format == 'pickle':
        return PickleSerializer()
    elif format == 'json_compressed':
        return CompressedSerializer(JSONSerializer())
    elif format == 'pickle_compressed':
        return CompressedSerializer(PickleSerializer())
    else:
        raise ValueError(f"Unknown format: {format}")
