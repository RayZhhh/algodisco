# 程序解析器 (Program Parser)

## 概述

程序解析器是 algodisco 工具包的一部分，使用 tree-sitter 进行语言感知的代码解析。该模块支持多语言解析，具有 100% 的往返保真度。

## 安装

```bash
pip install tree-sitter
```

## 核心类

### CodeParser

```python
from algodisco.toolkit.program_parser import CodeParser
```

#### 初始化

```python
parser = CodeParser(language: str)
```

支持的编程语言：
- `python`
- `javascript`
- `java`
- `cpp`
- `go`

#### 使用方法

```python
# 创建解析器
parser = CodeParser("python")

# 解析源代码
program = parser.parse(source_code)

# 访问函数
for func in program.functions:
    print(f"Function: {func.name}")
    print(f"Body: {func.body}")

# 访问类
for cls in program.classes:
    print(f"Class: {cls.name}")

# 重建源代码（100% 保真度）
reconstructed = str(program)
```

## 数据类

### Function

表示函数或方法定义。

```python
@dataclass
class Function:
    name: str                    # 函数名
    pre_name: str               # 函数名前的文本（如 "async def "）
    post_name: str              # 函数名后的文本（如 "(args):\n"）
    body: str                   # 函数体代码
    footer: str                 # 尾部字符（如闭合括号、分号）
    docstring: Optional[str]   # 文档字符串
    is_async: bool             # 是否为异步函数
    decorators_or_annotations: List[str]  # 装饰器或注解
    indent: str                # 缩进
```

### Class

表示类定义。

```python
@dataclass
class Class:
    name: str
    pre_name: str
    post_name: str
    footer: str
    body: List[Union[CodeBlock, Function]]  # 类体
```

### CodeBlock

表示非函数或类的代码块，用于保留注释、空格和导入语句。

```python
@dataclass
class CodeBlock:
    code: str       # 代码内容
    indent: str     # 缩进
```

### Program

表示完整的程序。

```python
@dataclass
class Program:
    code: str                           # 原始代码
    language: str                       # 编程语言
    imports: List[str]                 # 导入语句
    functions: List[Function]          # 函数列表
    classes: List[Class]                # 类列表
    code_blocks: List[CodeBlock]       # 代码块列表
```

## API 参考

### CodeParser 类

```python
class CodeParser:
    def __init__(self, language: str):
        """初始化解析器

        Args:
            language: 编程语言 ("python", "javascript", "java", "cpp", "go")
        """

    def parse(self, source_code: str) -> Program:
        """解析源代码

        Args:
            source_code: 源代码字符串

        Returns:
            Program 对象
        """

    def has_syntax_error(self, source_code: str) -> bool:
        """检查源代码是否有语法错误

        Args:
            source_code: 源代码字符串

        Returns:
            是否有语法错误
        """
```

### 辅助函数

```python
from algodisco.toolkit.program_parser import has_syntax_error

# 检查语法错误
if has_syntax_error(code):
    print("Code has syntax error")
```

## 使用示例

### 解析 Python 代码

```python
from algodisco.toolkit.program_parser import CodeParser

source_code = """
import os
from typing import List

def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b

class Calculator:
    def __init__(self):
        self.result = 0

    def add(self, x):
        self.result += x
        return self.result
"""

parser = CodeParser("python")
program = parser.parse(source_code)

# 访问导入
print("Imports:", program.imports)

# 访问函数
for func in program.functions:
    print(f"Function: {func.name}")
    print(f"  Async: {func.is_async}")
    print(f"  Docstring: {func.docstring}")

# 访问类
for cls in program.classes:
    print(f"Class: {cls.name}")
    for method in cls.body:
        if hasattr(method, 'name'):
            print(f"  Method: {method.name}")

# 重建源代码
print(str(program))
```

### 解析 JavaScript 代码

```python
from algodisco.toolkit.program_parser import CodeParser

js_code = """
function greet(name) {
    return `Hello, ${name}!`;
}

class Person {
    constructor(name) {
        this.name = name;
    }

    introduce() {
        return greet(this.name);
    }
}
"""

parser = CodeParser("javascript")
program = parser.parse(js_code)

for func in program.functions:
    print(f"Function: {func.name}")
```

## 语法错误检查

```python
from algodisco.toolkit.program_parser import has_syntax_error

# 检查代码是否有语法错误
valid_code = "def add(a, b): return a + b"
invalid_code = "def add(a, b) return a + b"

print(has_syntax_error(valid_code))  # False
print(has_syntax_error(invalid_code))  # True
```

## 最佳实践

1. **选择正确的语言**: 初始化时指定正确的语言
2. **处理语法错误**: 使用 `has_syntax_error()` 检查后再解析
3. **保留空白字符**: 代码块会自动保留注释和空格

## 相关文档

- [沙箱执行](sandbox.md)
- [评估器](evaluator.md)
