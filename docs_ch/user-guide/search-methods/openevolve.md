# OpenEvolve

## 配置参数

### 核心参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `template_program_path` | `str` | 必填 | 模板程序文件路径 |
| `task_description_path` | `str` | 必填 | 任务描述文件路径 |
| `language` | `str` | `"python"` | 编程语言 |
| `diff_based_evolution` | `bool` | `false` | 是否使用差分进化 |
| `num_top_programs` | `int` | `1` | 选择的最优程序数量 |
| `num_diverse_programs` | `int` | `1` | 选择的多样程序数量 |
| `include_artifacts` | `bool` | `false` | 是否包含中间产物 |
| `num_samplers` | `int` | `4` | 并行采样线程数 |
| `num_evaluators` | `int` | `4` | 并行评估线程数 |
| `exploration_ratio` | `float` | `0.2` | 探索比例 |
| `exploitation_ratio` | `float` | `0.7` | 利用比例 |
| `elite_selection_ratio` | `float` | `0.1` | 精英选择比例 |
| `samples_per_prompt` | `int` | `1` | 每个提示词生成的样本数 |
| `max_samples` | `int` | `1000` | 最大采样数 |
| `llm_max_tokens` | `int` | `1024` | LLM 生成的最大 token 数 |
| `llm_timeout_seconds` | `int` | `120` | LLM 调用超时时间 |

### 数据库参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `db_num_islands` | `int` | `10` | 岛屿数量 |
| `db_reset_period` | `int` | `14400` | 岛屿重置周期（秒） |
| `db_save_frequency` | `int` | `100` | 数据库保存频率 |
| `feature_dimensions` | `List[str]` | `["complexity", "diversity"]` | 特征维度 |
| `feature_bins` | `int` | `10` | 特征分箱数 |
| `diversity_reference_size` | `int` | `20` | 多样性参考大小 |
| `archive_size` | `int` | `100` | 档案库大小 |
| `migration_interval` | `int` | `50` | 迁移间隔 |
| `migration_rate` | `float` | `0.1` | 迁移率 |

## 伪代码流程

```
初始化:
    1. 加载模板程序
    2. 评估模板程序
    3. 初始化多样性驱动的数据库

主循环:
    对于每个采样线程:
        当未达到 max_samples 时:
            1. 决定探索/利用/精英策略
            2. 从数据库选择父代程序
            3. 构建提示词
            4. 调用 LLM 生成
            5. 评估生成程序
            6. 注册到数据库（基于多样性）
            7. 定期迁移程序到其他岛屿
```

## 使用示例

### 配置文件 `openevolve.yaml`

```yaml
method:
  template_program_path: "templates/sort.py"
  task_description_path: "tasks/sort.txt"
  language: "python"
  diff_based_evolution: false
  num_top_programs: 1
  num_diverse_programs: 1
  exploration_ratio: 0.2
  exploitation_ratio: 0.7
  elite_selection_ratio: 0.1
  num_samplers: 4
  num_evaluators: 4
  max_samples: 1000
  db_num_islands: 10
  archive_size: 100
  migration_interval: 50
  migration_rate: 0.1

llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4"
    api_key: "your-api-key"

evaluator:
  class_path: "my_evaluator.SortEvaluator"
  kwargs: {}

logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/openevolve_sort"
```

### 运行

```bash
python algodisco/methods/openevolve/main_openevolve.py --config openevolve.yaml
```

## API 参考

### OpenEvolve 类

```python
class OpenEvolve(IterativeSearchBase):
    def __init__(
        self,
        config: OpenEvolveConfig,
        evaluator,
        llm: LanguageModel = None,
        logger: Optional[AlgoSearchLoggerBase] = None,
        prompt_constructor: PromptConstructor = None,
        *,
        tool_mode=False,
    ):
```

#### 参数

- `config` (`OpenEvolveConfig`): 搜索配置
- `evaluator` (`Evaluator`): 评估器实例
- `llm` (`LanguageModel`, 可选): LLM 提供商
- `logger` (`AlgoSearchLoggerBase`, 可选): 日志器
- `prompt_constructor` (`PromptConstructor`, 可选): 提示词构造器
- `tool_mode` (`bool`): 工具模式标志

### OpenEvolveConfig 数据类

```python
@dataclass
class OpenEvolveConfig:
    template_program: str
    task_description: str = ""
    language: str = "python"
    diff_based_evolution: bool = False
    num_top_programs: int = 1
    num_diverse_programs: int = 1
    include_artifacts: bool = False
    num_samplers: int = 4
    num_evaluators: int = 4
    exploration_ratio: float = 0.2
    exploitation_ratio: float = 0.7
    elite_selection_ratio: float = 0.1
    samples_per_prompt: int = 1
    max_samples: Optional[int] = 1000
    llm_max_tokens: int = 1024
    llm_timeout_seconds: int = 120
    db_num_islands: int = 10
    db_reset_period: int = 4 * 60 * 60
    db_save_frequency: int = 100
```

## 相关文档

- [搜索方法总览](index.md)
- [FunSearch](funsearch.md)
- [EoH](eoh.md)
