# EoH (Evolution of Heuristic)

## 配置参数

### 核心参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `template_program_path` | `str` | 必填 | 模板程序文件路径 |
| `task_description_path` | `str` | 必填 | 任务描述文件路径 |
| `language` | `str` | `"python"` | 编程语言 |
| `pop_size` | `int` | `10` | 种群大小 |
| `selection_num` | `int` | `2` | 选择数量 |
| `use_e2_operator` | `bool` | `true` | 使用进化算子 |
| `use_m1_operator` | `bool` | `true` | 使用修改算子1 |
| `use_m2_operator` | `bool` | `true` | 使用修改算子2 |
| `num_samplers` | `int` | `4` | 并行采样线程数 |
| `num_evaluators` | `int` | `4` | 并行评估线程数 |
| `max_samples` | `int` | `1000` | 最大采样数 |
| `llm_max_tokens` | `int` | `1024` | LLM 生成的最大 token 数 |
| `llm_timeout_seconds` | `int` | `120` | LLM 调用超时时间 |
| `init_samples_ratio` | `float` | `2.0` | 初始样本比例 |
| `db_save_frequency` | `int` | `100` | 数据库保存频率 |

### 算子说明

- **E2 算子 (Evolution)**: 基于父代进行完整的进化
- **M1 算子 (Modification 1)**: 对现有实现进行小幅度修改
- **M2 算子 (Modification 2)**: 对"想法"进行改进后重新实现

## 伪代码流程

```
初始化:
    1. 加载模板程序
    2. 评估模板程序
    3. 使用初始样本填充种群

主循环:
    对于每个采样线程:
        当未达到 max_samples 时:
            1. 选择父代（基于适应度）
            2. 随机选择变异算子 (E2/M1/M2)
            3. 构建提示词（包含想法和/或实现）
            4. 调用 LLM 生成
            5. 评估生成程序
            6. 更新种群（选择+淘汰）
            7. 记录日志
```

## 使用示例

### 配置文件 `eoh.yaml`

```yaml
method:
  template_program_path: "templates/binary_search.py"
  task_description_path: "tasks/binary_search.txt"
  language: "python"
  pop_size: 10
  selection_num: 2
  use_e2_operator: true
  use_m1_operator: true
  use_m2_operator: true
  num_samplers: 4
  num_evaluators: 4
  max_samples: 500
  llm_max_tokens: 2048
  init_samples_ratio: 2.0

llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4"
    api_key: "your-api-key"

evaluator:
  class_path: "my_evaluator.BinarySearchEvaluator"
  kwargs: {}

logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/eoh_binary_search"
```

### 运行

```bash
python algodisco/methods/eoh/main_eoh.py --config eoh.yaml
```

## API 参考

### EoHSearch 类

```python
class EoHSearch(IterativeSearchBase):
    def __init__(
        self,
        config: EoHConfig,
        evaluator,
        llm: LanguageModel = None,
        logger: Optional[AlgoSearchLoggerBase] = None,
        prompt_constructor: EoHPromptAdapter = EoHPromptAdapter(),
        *,
        tool_mode=False,
    ):
```

#### 参数

- `config` (`EoHConfig`): 搜索配置
- `evaluator` (`Evaluator`): 评估器实例
- `llm` (`LanguageModel`, 可选): LLM 提供商
- `logger` (`AlgoSearchLoggerBase`, 可选): 日志器
- `prompt_constructor` (`EoHPromptAdapter`, 可选): 提示词构造器
- `tool_mode` (`bool`): 工具模式标志

### EoHConfig 数据类

```python
@dataclass
class EoHConfig:
    template_program: str
    task_description: str = ""
    language: str = "python"
    pop_size: int = 10
    selection_num: int = 2
    use_e2_operator: bool = True
    use_m1_operator: bool = True
    use_m2_operator: bool = True
    num_samplers: int = 4
    num_evaluators: int = 4
    max_samples: Optional[int] = 1000
    llm_max_tokens: int = 1024
    llm_timeout_seconds: int = 120
    db_save_frequency: int = 100
    init_samples_ratio: float = 2.0
    keep_metadata_keys: List[str] = field(default_factory=list)
```

## 相关文档

- [搜索方法总览](index.md)
- [FunSearch](funsearch.md)
- [OpenEvolve](openevolve.md)
