# BehaveSim

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
| `inter_island_selection_p` | `float` | `0.5` | 岛屿间选择概率 |
| `enable_database_reclustering` | `bool` | `true` | 启用动态重聚类 |
| `recluster_threshold` | `int` | `100` | 重聚类阈值 |

### 数据库配置

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `n_islands` | `int` | `10` | 岛屿数量 |
| `island_capacity` | `int` | `100` | 岛屿容量 |
| `selection_exploitation_intensity` | `float` | `1.0` | 选择利用强度 |
| `ast_dfg_weight` | `float` | `1.0` | AST/DFG 权重 |
| `embedding_weight` | `float` | `1.0` | 嵌入权重 |
| `behavioral_weight` | `float` | `1.0` | 行为权重 |

### 嵌入 LLM 配置

BehaveSim 需要单独的嵌入模型：

```yaml
emb_llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "text-embedding-3-small"
    api_key: "your-api-key"
```

## 使用示例

```yaml
method:
  template_program_path: "templates/sort.py"
  task_description_path: "tasks/sort.txt"
  language: "python"
  num_samplers: 4
  num_evaluators: 4
  examples_per_prompt: 2
  samples_per_prompt: 4
  max_samples: 500
  inter_island_selection_p: 0.5
  enable_database_reclustering: true
  recluster_threshold: 100
  database_config:
    n_islands: 10
    island_capacity: 100
    selection_exploitation_intensity: 1.0
    ast_dfg_weight: 1.0
    embedding_weight: 1.0
    behavioral_weight: 1.0

llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4"

emb_llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "text-embedding-3-small"
    api_key: "your-api-key"

evaluator:
  class_path: "my_evaluator.SortEvaluator"
  kwargs: {}

logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/behavesim"
```

运行:
```bash
python algodisco/methods/funsearch_behavesim/main_behavesim_search.py --config config.yaml
```

## API 参考

### BehaveSim 类

```python
class BehaveSim(IterativeSearchBase):
    def __init__(
        self,
        config: BehaveSimConfig,
        evaluator,
        llm: LanguageModel = None,
        emb_llm: LanguageModel = None,
        logger: Optional[AlgoSearchLoggerBase] = None,
        prompt_constructor: PromptAdapter = PromptAdapter(),
        *,
        tool_mode=False,
    ):
```

#### 参数

- `config` (`BehaveSimConfig`): 搜索配置
- `evaluator` (`Evaluator`): 评估器实例
- `llm` (`LanguageModel`): 主 LLM 提供商
- `emb_llm` (`LanguageModel`): 嵌入 LLM 提供商
- `logger` (`AlgoSearchLoggerBase`, 可选): 日志器

## 相关文档

- [搜索方法总览](index.md)
- [FunSearch](funsearch.md)
- [LLM 提供商](../llm-providers/index.md)
