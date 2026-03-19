# (1+1)-EPS

## 配置参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `template_program_path` | `str` | 必填 | 模板程序文件路径 |
| `task_description_path` | `str` | 必填 | 任务描述文件路径 |
| `language` | `str` | `"python"` | 编程语言 |
| `num_samplers` | `int` | `4` | 并行采样线程数 |
| `num_evaluators` | `int` | `4` | 并行评估线程数 |
| `samples_per_prompt` | `int` | `4` | 每个提示词生成的样本数 |
| `max_samples` | `int` | `1000` | 最大采样数 |
| `llm_max_tokens` | `int` | `1024` | LLM 生成的最大 token 数 |
| `llm_timeout_seconds` | `int` | `120` | LLM 调用超时时间 |

## 使用示例

```yaml
method:
  template_program_path: "templates/max_value.py"
  task_description_path: "tasks/max_value.txt"
  language: "python"
  num_samplers: 4
  num_evaluators: 4
  samples_per_prompt: 4
  max_samples: 500

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
    logdir: "logs/one_plus_one_eps"
```

运行:
```bash
python algodisco/methods/one_plus_one_eps/main_one_plus_one_eps.py --config config.yaml
```

## API 参考

### OnePlusOneEPS 类

```python
class OnePlusOneEPS(IterativeSearchBase):
    def __init__(
        self,
        config: OnePlusOneEPSConfig,
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
