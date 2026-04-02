"""
代码生成器

基于模板生成代码
"""

from typing import Dict, List, Any, Optional
from string import Template
from pathlib import Path
from dataclasses import dataclass


@dataclass
class CodeTemplate:
    """代码模板
    
    Attributes:
        name: 模板名称
        template: 模板字符串
        description: 描述
        parameters: 参数定义
        output_extension: 输出文件扩展名
    """
    name: str
    template: str
    description: str = ""
    parameters: Dict[str, Any] = None
    output_extension: str = ".py"
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
    
    def render(self, **kwargs) -> str:
        """渲染模板
        
        Args:
            **kwargs: 模板变量
            
        Returns:
            渲染后的代码
        """
        t = Template(self.template)
        return t.safe_substitute(**kwargs)
    
    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        """验证参数
        
        Args:
            params: 参数字典
            
        Returns:
            缺失的参数列表
        """
        required = set(self.parameters.get('required', []))
        provided = set(params.keys())
        return list(required - provided)


class CodeGenerator:
    """代码生成器
    
    基于模板生成代码
    
    使用示例：
        generator = CodeGenerator("templates")
        
        # 注册模板
        generator.register_template(CodeTemplate(
            name="class_template",
            template="""
class ${class_name}:
    def __init__(self):
        self.name = "${class_name}"
    
    def ${method_name}(self):
        ${method_body}
"""
        ))
        
        # 生成代码
        code = generator.generate(
            template_name="class_template",
            output_path="generated/my_class.py",
            parameters={
                'class_name': 'MyClass',
                'method_name': 'do_something',
                'method_body': 'pass'
            },
            confirmed=True
        )
    """
    
    def __init__(self, template_dir: str = "templates"):
        self._template_dir = Path(template_dir)
        self._templates: Dict[str, CodeTemplate] = {}
        self._load_templates()
    
    def _load_templates(self) -> None:
        """加载模板文件"""
        if not self._template_dir.exists():
            return
        
        for template_file in self._template_dir.glob("*.tpl"):
            name = template_file.stem
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 尝试解析元数据（JSON 头部）
                metadata = {}
                if content.startswith('/*'):
                    end = content.find('*/')
                    if end > 0:
                        import json
                        try:
                            metadata = json.loads(content[2:end].strip())
                            content = content[end+2:].strip()
                        except json.JSONDecodeError:
                            pass
                
                self._templates[name] = CodeTemplate(
                    name=name,
                    template=content,
                    description=metadata.get('description', ''),
                    parameters=metadata.get('parameters', {}),
                    output_extension=metadata.get('output_extension', '.py')
                )
            except Exception as e:
                print(f"Failed to load template {name}: {e}")
    
    def register_template(self, template: CodeTemplate) -> None:
        """注册模板"""
        self._templates[template.name] = template
    
    def unregister_template(self, name: str) -> bool:
        """注销模板"""
        if name in self._templates:
            del self._templates[name]
            return True
        return False
    
    def get_template(self, name: str) -> Optional[CodeTemplate]:
        """获取模板"""
        return self._templates.get(name)
    
    def list_templates(self) -> List[str]:
        """列出可用模板"""
        return list(self._templates.keys())
    
    def generate(self, 
                 template_name: str, 
                 parameters: Dict[str, Any],
                 output_path: str = None,
                 confirmed: bool = False) -> Optional[str]:
        """生成代码
        
        Args:
            template_name: 模板名称
            parameters: 模板参数
            output_path: 输出路径（可选）
            confirmed: 是否已确认写入文件
            
        Returns:
            生成的代码，失败返回 None
            
        Raises:
            ValueError: 模板不存在或参数缺失
        """
        template = self._templates.get(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        # 验证参数
        missing = template.validate_params(parameters)
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")
        
        # 渲染模板
        code = template.render(**parameters)
        
        # 如果需要写入文件
        if output_path and confirmed:
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)
            
            # 备份已存在的文件
            if output.exists():
                backup = output.with_suffix(output.suffix + '.bak')
                backup.write_text(output.read_text())
            
            with open(output, 'w', encoding='utf-8') as f:
                f.write(code)
        
        return code
    
    def preview(self, template_name: str, 
                parameters: Dict[str, Any]) -> Optional[str]:
        """预览生成的代码（不写入文件）
        
        Args:
            template_name: 模板名称
            parameters: 模板参数
            
        Returns:
            生成的代码预览
        """
        return self.generate(template_name, parameters, output_path=None)
    
    def create_template(self, 
                        name: str,
                        template_str: str,
                        description: str = "",
                        parameters: Dict[str, Any] = None,
                        save: bool = True) -> CodeTemplate:
        """创建新模板
        
        Args:
            name: 模板名称
            template_str: 模板字符串
            description: 描述
            parameters: 参数定义
            save: 是否保存到文件
            
        Returns:
            创建的模板
        """
        template = CodeTemplate(
            name=name,
            template=template_str,
            description=description,
            parameters=parameters or {}
        )
        
        self._templates[name] = template
        
        if save:
            self._save_template(template)
        
        return template
    
    def _save_template(self, template: CodeTemplate) -> bool:
        """保存模板到文件"""
        try:
            self._template_dir.mkdir(parents=True, exist_ok=True)
            
            template_file = self._template_dir / f"{template.name}.tpl"
            
            # 构建带元数据的模板文件
            import json
            metadata = {
                'description': template.description,
                'parameters': template.parameters,
                'output_extension': template.output_extension
            }
            
            content = f"/*{json.dumps(metadata)}*/\n{template.template}"
            
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        except Exception as e:
            print(f"Failed to save template: {e}")
            return False
    
    def get_builtin_templates(self) -> Dict[str, CodeTemplate]:
        """获取内置模板"""
        return {
            'function': CodeTemplate(
                name='function',
                template='''def ${function_name}(${parameters}):
    """
    ${description}
    """
    ${body}
''',
                description='Generate a function',
                parameters={
                    'required': ['function_name', 'body'],
                    'optional': ['parameters', 'description']
                }
            ),
            'class': CodeTemplate(
                name='class',
                template='''class ${class_name}${bases}:
    """
    ${description}
    """
    
    def __init__(self${init_params}):
        ${init_body}
''',
                description='Generate a class',
                parameters={
                    'required': ['class_name'],
                    'optional': ['bases', 'description', 'init_params', 'init_body']
                }
            ),
            'module': CodeTemplate(
                name='module',
                template='''"""
${module_name}

${description}
"""

${imports}

${body}
''',
                description='Generate a module',
                parameters={
                    'required': ['module_name'],
                    'optional': ['description', 'imports', 'body']
                }
            )
        }
    
    def install_builtin_templates(self) -> None:
        """安装内置模板"""
        for name, template in self.get_builtin_templates().items():
            if name not in self._templates:
                self._templates[name] = template
                self._save_template(template)
