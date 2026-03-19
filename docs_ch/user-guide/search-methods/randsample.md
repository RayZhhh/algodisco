# RandSample

## 配置参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `template_program_path` | `str` | 必填 | 模板程序文件路径 |
| `task_description_path` | `str` | 必填 | 任务描述文件路径 |
| `language` | `str` | `"python"` | 编程语言 |
| `num_samplers` | `int` | `1` | 并行采样线程数 |
| `num_evaluators` | `int` | `4` | 并行评估线程数 |
| `max_samples` | `int` | `1000` | 最大采样数 |
| `llm_max_tokens` | `int` | `1024` | LLM 生成的最大 token 数 |
| `llm_timeout_seconds` | `int` | `120` | LLM 调用超时时间 |

## 使用示例

```yaml
method:
  template_program_path: "templates/max_value.py"
  task_description_path: "tasks/max_value.txt"
  language: "python"
  num_samplers: 1
  num_evaluators: 4
  max_samples: 1000

llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-3.5-turbo"

evaluator:
  class_path: "my_evaluator.MaxValueEvaluator"
  kwargs: {}

logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/randsample"
```

运行:
```bash
python algodisco/methods/randsample/main_randsample.py --config config.yaml
```

## API 参考

### RandSample 类

```python
class RandSample(IterativeSearchBase):
    def __init__(
        self,
        config: RandSampleConfig,
        evaluator,
        llm: LanguageModel = None,
        logger: Optional[AlgoSearchLoggerBase] = None,
        prompt_constructor: PromptAdapter = PromptAdapter(),
        *,
        tool_mode=False,
    ):
```

## 相关文档

- [搜索方法总览](index.md)
- [FunSearch](funsearch.md)
