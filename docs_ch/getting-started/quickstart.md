# 快速开始

这份指南给出一条最稳妥的上手路径：直接运行仓库内置的在线装箱示例，并使用 FunSearch 作为搜索方法。

## 你将运行什么

这个示例由以下几个部分组成：

- `examples/online_bin_packing/template_algo.txt`：待优化的模板程序
- `examples/online_bin_packing/task_description.txt`：任务描述
- `examples/online_bin_packing/evaluator.py`：评测器实现
- `examples/online_bin_packing/configs/funsearch.yaml`：可直接运行的配置文件

## 第一步：完成安装

请先按照 [安装指南](installation.md) 配好环境。最少需要执行：

```bash
pip install -e .
export OPENAI_API_KEY="your-openai-key"
```

## 第二步：检查示例配置

打开下面这个配置文件：

```bash
examples/online_bin_packing/configs/funsearch.yaml
```

最重要的几个字段是：

- `method.template_program_path`：算法模板文件
- `method.task_description_path`：会注入提示词的任务描述
- `llm.class_path`：要实例化的模型后端
- `evaluator.class_path`：负责打分的评测器
- `logger.kwargs.logdir`：实验输出目录

你可以保持 `api_key: null`，改用环境变量 `OPENAI_API_KEY`；也可以在本地调试时直接把 key 写进配置文件。

## 第三步：运行 FunSearch

在仓库根目录执行：

```bash
python -m algodisco.methods.funsearch.main_funsearch --config examples/online_bin_packing/configs/funsearch.yaml
```

程序启动后会持续生成候选程序、执行评测并写入日志。默认输出目录是：

```text
logs/online_bin_packing_funsearch
```

## 第四步：查看输出

运行开始后，你可以重点关注日志目录中的内容，通常会包括：

- 序列化的实验产物
- 每个候选程序的分数与元数据
- 采样耗时、执行耗时、错误信息等调试信息

## 如何切换到其他搜索方法

同一个在线装箱示例已经提供了多种方法对应的配置。只需要替换模块和配置文件：

| 方法 | 命令 |
| --- | --- |
| FunSearch | `python -m algodisco.methods.funsearch.main_funsearch --config examples/online_bin_packing/configs/funsearch.yaml` |
| OpenEvolve | `python -m algodisco.methods.openevolve.main_openevolve --config examples/online_bin_packing/configs/openevolve.yaml` |
| EoH | `python -m algodisco.methods.eoh.main_eoh --config examples/online_bin_packing/configs/eoh.yaml` |
| (1+1)-EPS | `python -m algodisco.methods.one_plus_one_eps.main_one_plus_one_eps --config examples/online_bin_packing/configs/one_plus_one_eps.yaml` |
| RandSample | `python -m algodisco.methods.randsample.main_randsample --config examples/online_bin_packing/configs/randsample.yaml` |

## 如何改成自己的任务

在示例跑通后，复制一份配置文件，并替换以下内容：

- `template_program_path`：改成你的模板程序
- `task_description_path`：改成你的任务描述
- `evaluator.class_path`：改成你的评测器实现
- `logger.kwargs.logdir`：改成新的实验输出目录

你的评测器必须继承 `algodisco.base.evaluator.Evaluator`，并实现 `evaluate_program(program_str: str)`。

## 常见失败原因

- 没有设置 API Key，导致模型调用在采样前就失败
- 不在仓库根目录执行命令，导致示例中的相对路径找不到文件
- `class_path` 写错，动态导入阶段直接报错

## 下一步

- 继续阅读 [配置指南](configuration.md)，理解 YAML 配置是如何被加载的。
- 查看 [搜索方法](../user-guide/search-methods/index.md)，选择更适合你任务的方法。
- 如果你要扩展框架，请继续阅读开发者文档。
