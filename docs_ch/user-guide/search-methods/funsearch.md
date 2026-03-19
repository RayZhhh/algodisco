# FunSearch

## 配置参数

### 核心参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `template_program_path` | `str` | 必填 | 模板程序文件路径 |
| `task_description_path` | `str` | 必填 | 任务描述文件路径 |
| `language` | `str` | `"python"` | 编程语言 |
| `num_samplers` | `int` | `4` | 并行采样线程数 |
| `num_evaluators` | `int` | `4` | 并行评估线程数 |
| `examples_per_prompt` | `int` | `2` | 提示词中的示例数量 |
| `samples_per_prompt` | `int` | `4` | 每个提示词生成的样本数 |
| `max_samples` | `int` | `1000` | 最大采样数 |
| `llm_max_tokens` | `int` | `1024` | LLM 生成的最大 token 数 |
| `llm_timeout_seconds` | `int` | `120` | LLM 调用超时时间 |

### 数据库参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `db_num_islands` | `int` | `10` | 岛屿数量 |
| `db_max_island_capacity` | `int` | `null` | 每个岛屿的最大容量 |
| `db_reset_period` | `int` | `14400` | 岛屿重置周期（秒） |
| `db_cluster_sampling_temperature_init` | `float` | `0.1` | 初始采样温度 |
| `db_cluster_sampling_temperature_period` | `int` | `30000` | 温度调整周期 |
| `db_save_frequency` | `int` | `100` | 数据库保存频率 |

### 调试参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `debug_mode` | `bool` | `false` | 启用调试模式 |
| `debug_mode_crash` | `bool` | `false` | 调试模式下遇错即停 |
| `keep_metadata_keys` | `List[str]` | 见下方 | 保留的元数据键 |

默认 `keep_metadata_keys`:
```python
["sample_time", "eval_time", "execution_time", "error_msg", "prompt", "response_text"]
```

## 伪代码流程

```
初始化:
    1. 加载模板程序
    2. 评估模板程序获得基线分数
    3. 初始化 N 个岛屿数据库

主循环 (并行执行):
    对于每个采样线程:
        当未达到 max_samples 时:
            1. 随机选择一个岛屿
            2. 从该岛屿选择高分程序作为父代
            3. 构建提示词（包含任务描述和示例）
            4. 调用 LLM 生成新程序
            5. 从响应中提取代码
            6. 评估生成程序
            7. 如果评分提高，注册到岛屿
            8. 记录日志
            9. 定期保存数据库快照

终止条件:
    - 达到 max_samples
    - 手动停止
```

## 使用示例

### 1. 准备配置文件 `funsearch.yaml`

```yaml
method:
  template_program_path: "templates/max_value.py"
  task_description_path: "tasks/max_value.txt"
  language: "python"
  num_samplers: 4
  num_evaluators: 4
  examples_per_prompt: 2
  samples_per_prompt: 4
  max_samples: 500
  llm_max_tokens: 1024
  llm_timeout_seconds: 120
  db_num_islands: 10
  db_max_island_capacity: 50
  db_reset_period: 7200
  db_save_frequency: 50

llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4-turbo-preview"
    api_key: "your-api-key"

evaluator:
  class_path: "my_evaluator.MaxValueEvaluator"
  kwargs: {}

logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/funsearch_max_value"
```

### 2. 运行搜索

```bash
python algodisco/methods/funsearch/main_funsearch.py --config funsearch.yaml
```

## API 参考

### FunSearch 类

```python
class FunSearch(IterativeSearchBase):
    def __init__(
        self,
        config: FunSearchConfig,
        evaluator,
        llm: LanguageModel = None,
        logger: Optional[AlgoSearchLoggerBase] = None,
        prompt_constructor: PromptAdapter = PromptAdapter(),
        *,
        tool_mode=False,
    ):
```

#### 参数

- `config` (`FunSearchConfig`): 搜索配置
- `evaluator` (`Evaluator`): 评估器实例
- `llm` (`LanguageModel`, 可选): LLM 提供商
- `logger` (`AlgoSearchLoggerBase`, 可选): 日志器
- `prompt_constructor` (`PromptAdapter`, 可选): 提示词构造器
- `tool_mode` (`bool`): 工具模式标志

#### 方法

##### run()

```python
def run(self) -> None:
    """启动搜索过程"""
```

启动 FunSearch 进化搜索主循环。

##### initialize()

```python
def initialize(self) -> None:
    """初始化搜索过程"""
```

评估模板程序并初始化岛屿数据库。

##### is_stopped()

```python
def is_stopped(self) -> bool:
    """检查是否满足终止条件"""
```

返回 `True` 如果达到 `max_samples` 或收到停止信号。

### FunSearchConfig 数据类

```python
@dataclass
class FunSearchConfig:
    template_program: str
    task_description: str = ""
    language: str = "python"
    num_samplers: int = 4
    num_evaluators: int = 4
    examples_per_prompt: int = 2
    samples_per_prompt: int = 4
    max_samples: Optional[int] = 1000
    llm_max_tokens: Optional[int] = None
    llm_timeout_seconds: int = 120
    db_num_islands: int = 10
    db_max_island_capacity: Optional[int] = None
    db_reset_period: int = 4 * 60 * 60
    db_cluster_sampling_temperature_init: float = 0.1
    db_cluster_sampling_temperature_period: int = 30_000
    db_save_frequency: Optional[int] = 100
    keep_metadata_keys: List[str] = field(default_factory=list)
```

## 相关文档

- [快速开始](../../getting-started/quickstart.md)
- [配置指南](../../getting-started/configuration.md)
- [LLM 提供商](../llm-providers/index.md)
