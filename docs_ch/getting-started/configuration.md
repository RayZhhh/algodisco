# 配置指南

AlgoDisco 通过 YAML 文件描述一次完整实验。一个配置文件会同时定义搜索方法、LLM 后端、评测器和日志器。

## 配置结构

一个典型配置文件包含以下顶层字段：

```yaml
method:
  ...
llm:
  ...
evaluator:
  ...
logger:
  ...
```

各部分职责如下：

- `method`：搜索策略、模板输入、采样预算等方法级配置
- `llm`：候选程序生成所使用的模型后端
- `evaluator`：负责执行程序并计算分数的组件
- `logger`：负责保存实验结果、日志和中间产物的组件

## 组件是如何加载的

`llm`、`evaluator` 和 `logger` 三个部分遵循相同结构：

```yaml
llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4o-mini"
```

`class_path` 支持两种写法：

- Python 导入路径，例如 `algodisco.providers.llm.openai_api.OpenAIAPI`
- 文件路径加类名，例如 `examples/online_bin_packing/evaluator.py:OnlineBinPackingEvaluator`

`kwargs` 会原样传给构造函数。

## 路径解析规则

当前实现中，配置里的相对路径是相对于仓库根目录解析的，而不是相对于 YAML 文件所在目录。

这条规则尤其影响以下字段：

- `method.template_program_path`
- `method.task_description_path`
- `method.template_dir`
- `logger.kwargs.logdir`

如果你调整了配置文件位置，这一点必须注意。

## 常用的 Method 字段

大多数搜索方法都共享一组基础字段：

| 字段 | 类型 | 作用 |
| --- | --- | --- |
| `template_program_path` | `str` | 初始模板程序路径 |
| `task_description_path` | `str` | 任务描述文件路径 |
| `language` | `str` | 生成程序所使用的语言 |
| `num_samplers` | `int` 或 `"auto"` | 并发采样线程数 |
| `num_evaluators` | `int` 或 `"auto"` | 并发评测线程数 |
| `max_samples` | `int` | 最多生成多少个候选 |
| `llm_max_tokens` | `int \| null` | 单次模型响应的 token 上限 |
| `llm_timeout_seconds` | `int` | 单次模型调用超时 |
| `debug_mode` | `bool` | 是否开启更详细的调试行为 |
| `debug_mode_crash` | `bool` | 出错时是否立刻中断而不是继续运行 |

不同方法还会附加自己的专属字段。例如：

- FunSearch 会使用 `db_num_islands` 等归档与岛模型参数。
- OpenEvolve 会增加 `diff_based_evolution`、`feature_dimensions`、`archive_size` 等演化与归档相关配置。
- BehaveSim 会额外引入 `emb_llm` 配置块，用于相似度相关能力。

## 一个最小可用示例

下面是一个足够实用的起步配置：

```yaml
method:
  template_program_path: "examples/online_bin_packing/template_algo.txt"
  task_description_path: "examples/online_bin_packing/task_description.txt"
  language: "python"
  num_samplers: auto
  num_evaluators: auto
  max_samples: 100
  llm_max_tokens: 1024
  llm_timeout_seconds: 120

llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4o-mini"
    api_key: null
    base_url: "https://api.openai.com/v1"

evaluator:
  class_path: "examples/online_bin_packing/evaluator.py:OnlineBinPackingEvaluator"
  kwargs: {}

logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/my_first_run"
```

## LLM 配置块

`llm` 用来指定模型后端以及对应构造参数。

仓库中已经包含以下后端实现：

- `algodisco.providers.llm.openai_api.OpenAIAPI`
- `algodisco.providers.llm.claude_api.ClaudeAPI`
- `algodisco.providers.llm.vllm_server.VLLMServer`
- `algodisco.providers.llm.sglang_server.SGLangServer`

API Key 一类敏感信息建议通过环境变量提供，不要直接写进可提交的配置文件。

## Evaluator 配置块

评测器的职责是把“生成出来的程序”转换成“可以比较的数值分数”。

它必须满足：

- 继承 `algodisco.base.evaluator.Evaluator`
- 实现 `evaluate_program(self, program_str: str)`
- 返回至少包含 `score` 字段的字典

示例：

```yaml
evaluator:
  class_path: "path/to/evaluator.py:YourEvaluator"
  kwargs: {}
```

## Logger 配置块

默认日志器会把实验产物保存在本地：

```yaml
logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/my_experiment"
```

仓库里还提供了可选日志器：

- `algodisco.providers.logger.wandb_logger.BaseWandbLogger`
- `algodisco.providers.logger.swanlab_logger.BaseSwanLabLogger`

## 推荐实践

- 不要从零手写配置，优先复制仓库里的示例配置再修改。
- 在当前实现下，尽量统一使用“相对于仓库根目录”的路径写法。
- API Key 放环境变量，不要提交到版本库。
- 每次实验使用独立的 `logdir`，避免结果互相覆盖。

## 下一步

- 如果你想先跑一个可用实验，继续看 [快速开始](quickstart.md)。
- 如果你需要调优策略参数，请阅读 [搜索方法](../user-guide/search-methods/index.md) 下的具体页面。
- 如果你准备扩展框架，请继续阅读开发者文档。
