# 基础类 API

## AlgoProto

算法表示的基类。

```python
from algodisco.base.algo import AlgoProto
```

### 类定义

```python
class AlgoProto:
    def __init__(
        self,
        algo_id: str = "",
        program: str = "",
        language: str = "",
        score: Any = None,
    ):
```

### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `algo_id` | `str` | 唯一标识符 (UUID) |
| `program` | `str` | 程序源代码 |
| `language` | `str` | 编程语言 |
| `score` | `Any` | 评估分数 |
| `metadata` | `dict` | 附加元数据 |

### 方法

#### from_dict()

```python
@classmethod
def from_dict(cls, data: Dict) -> "AlgoProto":
    """从字典创建 AlgoProto"""
```

#### from_program_str()

```python
@classmethod
def from_program_str(cls, program: str) -> "AlgoProto":
    """从程序字符串创建 AlgoProto"""
```

#### to_dict()

```python
def to_dict(self) -> Dict:
    """转换为字典"""
```

#### get_markdown_code_block()

```python
def get_markdown_code_block(self) -> str:
    """获取 Markdown 代码块格式"""
```

#### update()

```python
def update(self, data: Dict) -> None:
    """从字典更新属性"""
```

#### keep_metadata_keys()

```python
def keep_metadata_keys(self, keys: str | List[str]):
    """保留指定的元数据键，删除其他"""
```

---

## IterativeSearchBase

迭代搜索方法的抽象基类。

```python
from algodisco.base.search_method import IterativeSearchBase
```

### 类定义

```python
class IterativeSearchBase(abc.ABC):
```

### 抽象方法

#### initialize()

```python
@abc.abstractmethod
def initialize(self) -> None:
    """初始化搜索过程"""
```

#### select_and_create_prompt()

```python
@abc.abstractmethod
def select_and_create_prompt(self) -> Optional[AlgoProto]:
    """选择父代并构建提示词"""
```

#### generate()

```python
@abc.abstractmethod
def generate(self, selection: AlgoProto) -> Union[AlgoProto, List[AlgoProto]]:
    """生成新候选算法"""
```

#### extract_algo_from_response()

```python
@abc.abstractmethod
def extract_algo_from_response(self, candidate: AlgoProto) -> AlgoProto:
    """从 LLM 响应提取算法"""
```

#### evaluate()

```python
@abc.abstractmethod
def evaluate(
    self, candidates: Union[AlgoProto, List[AlgoProto]]
) -> Union[AlgoProto, List[AlgoProto]]:
    """评估候选算法"""
```

#### register()

```python
@abc.abstractmethod
def register(self, results: Union[AlgoProto, List[AlgoProto]]) -> None:
    """注册评估结果"""
```

#### is_stopped()

```python
@abc.abstractmethod
def is_stopped(self) -> bool:
    """检查是否满足终止条件"""
```

---

## Evaluator

评估器的抽象基类。

```python
from algodisco.base.evaluator import Evaluator, EvalResult
```

### 类定义

```python
class Evaluator(ABC, Generic[T]):
    @abstractmethod
    def evaluate_program(self, program_str: str) -> T:
        pass
```

### EvalResult 类型

```python
class EvalResult(TypedDict):
    score: float
    execution_time: Optional[float]
    error_msg: Optional[str]
```

---

## LanguageModel

语言模型的抽象基类。

```python
from algodisco.base.llm import LanguageModel
```

### 类定义

```python
class LanguageModel:
```

### 方法

#### chat_completion()

```python
def chat_completion(
    self,
    message: str | List[ChatCompletionMessageParam],
    max_tokens: int,
    timeout_seconds: float,
    *args,
    **kwargs,
):
    """发送聊天完成请求"""
```

#### embedding()

```python
def embedding(
    self,
    text: str | List[str],
    dimensions: Optional[int] = None,
    timeout_seconds: Optional[float] = None,
    **kwargs,
) -> List[float] | List[List[float]]:
    """生成文本嵌入"""
```

#### close()

```python
def close(self):
    """释放资源"""
```

#### reload()

```python
def reload(self):
    """重新加载模型"""
```

---

## AlgoSearchLoggerBase

日志器的抽象基类。

```python
from algodisco.base.logger import AlgoSearchLoggerBase
```

### 类定义

```python
class AlgoSearchLoggerBase(ABC):
```

### 方法

#### log_dict()

```python
async def log_dict(self, log_item: Dict, item_name: str):
    """异步记录日志"""
```

#### log_dict_sync()

```python
def log_dict_sync(self, log_item: Dict, item_name: str):
    """同步记录日志"""
```

#### finish()

```python
async def finish(self):
    """完成日志记录"""
```

#### finish_sync()

```python
def finish_sync(self):
    """同步完成日志记录"""
```

#### set_log_item_flush_frequency()

```python
def set_log_item_flush_frequency(self, *args, **kwargs):
    """设置日志刷新频率"""
```
