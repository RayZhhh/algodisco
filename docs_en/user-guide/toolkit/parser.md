# Program Parser

## Overview

The Program Parser is part of the algodisco toolkit, providing language-aware code parsing using tree-sitter. It supports multi-language parsing with 100% round-trip fidelity.

## Installation

```bash
pip install tree-sitter
```

## Core Classes

### CodeParser

```python
from algodisco.toolkit.program_parser import CodeParser
```

#### Initialization

```python
parser = CodeParser(language: str)
```

Supported languages:
- `python`
- `javascript`
- `java`
- `cpp`
- `go`

#### Usage

```python
# Create parser
parser = CodeParser("python")

# Parse source code
program = parser.parse(source_code)

# Access functions
for func in program.functions:
    print(f"Function: {func.name}")
    print(f"Body: {func.body}")

# Access classes
for cls in program.classes:
    print(f"Class: {cls.name}")

# Reconstruct source (100% fidelity)
reconstructed = str(program)
```

## Data Classes

### Function

Represents a function or method definition.

```python
@dataclass
class Function:
    name: str                    # Function name
    pre_name: str               # Text before function name (e.g., "async def ")
    post_name: str              # Text between name and body (e.g., "(args):\n")
    body: str                   # Function body code
    footer: str                 # Trailing characters (e.g., closing braces, semicolons)
    docstring: Optional[str]   # Documentation string
    is_async: bool             # Whether it's an async function
    decorators_or_annotations: List[str]  # Decorators or annotations
    indent: str                # Indentation
```

### Class

Represents a class definition.

```python
@dataclass
class Class:
    name: str
    pre_name: str
    post_name: str
    footer: str
    body: List[Union[CodeBlock, Function]]  # Class body
```

### CodeBlock

Represents code chunks that aren't parsed functions or classes, preserving comments, whitespace, and imports.

```python
@dataclass
class CodeBlock:
    code: str       # Code content
    indent: str     # Indentation
```

### Program

Represents a complete program.

```python
@dataclass
class Program:
    code: str                           # Original code
    language: str                       # Programming language
    imports: List[str]                 # Import statements
    functions: List[Function]           # List of functions
    classes: List[Class]                # List of classes
    code_blocks: List[CodeBlock]       # List of code blocks
```

## API Reference

### CodeParser Class

```python
class CodeParser:
    def __init__(self, language: str):
        """Initialize parser

        Args:
            language: Programming language ("python", "javascript", "java", "cpp", "go")
        """

    def parse(self, source_code: str) -> Program:
        """Parse source code

        Args:
            source_code: Source code string

        Returns:
            Program object
        """

    def has_syntax_error(self, source_code: str) -> bool:
        """Check if source code has syntax errors

        Args:
            source_code: Source code string

        Returns:
            Whether there are syntax errors
        """
```

### Helper Functions

```python
from algodisco.toolkit.program_parser import has_syntax_error

# Check for syntax errors
if has_syntax_error(code):
    print("Code has syntax error")
```

## Usage Examples

### Parsing Python Code

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

# Access imports
print("Imports:", program.imports)

# Access functions
for func in program.functions:
    print(f"Function: {func.name}")
    print(f"  Async: {func.is_async}")
    print(f"  Docstring: {func.docstring}")

# Access classes
for cls in program.classes:
    print(f"Class: {cls.name}")
    for method in cls.body:
        if hasattr(method, 'name'):
            print(f"  Method: {method.name}")

# Reconstruct source code
print(str(program))
```

### Parsing JavaScript Code

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

## Syntax Error Checking

```python
from algodisco.toolkit.program_parser import has_syntax_error

# Check if code has syntax errors
valid_code = "def add(a, b): return a + b"
invalid_code = "def add(a, b) return a + b"

print(has_syntax_error(valid_code))  # False
print(has_syntax_error(invalid_code))  # True
```

## Best Practices

1. **Choose Correct Language**: Specify the correct language during initialization
2. **Handle Syntax Errors**: Use `has_syntax_error()` before parsing
3. **Preserve Whitespace**: Code blocks automatically preserve comments and whitespace

## Related Documents

- [Sandbox](sandbox.md)
- [Evaluator](evaluator.md)
