# AlgoDisco 文档

AlgoDisco 是一个由大语言模型驱动的算法发现与优化框架。它将“候选程序生成、程序评测、搜索策略、结果记录”组织成一套可复现实验流程，用于探索和改进算法实现。

## 这套文档适合谁

这套文档主要面向：

- 需要快速验证算法搜索思路的研究人员
- 评估 LLM 程序优化能力的工程团队
- 希望为 AlgoDisco 增加新方法、新评测器或新模型后端的贡献者

## AlgoDisco 能做什么

当前仓库内置了以下搜索方法：

- FunSearch
- OpenEvolve
- EoH
- (1+1)-EPS
- RandSample
- BehaveSim

已支持的 LLM 后端包括：

- OpenAI
- Claude
- vLLM
- SGLang

整个框架由几类核心组件组成：

- 搜索方法：决定如何生成、选择和演化候选程序
- 评测器：负责执行候选程序并给出分数
- LLM 后端：负责生成候选实现
- 日志器：负责保存实验结果与过程产物

## 推荐使用流程

对于大多数用户，建议按下面的顺序开始：

1. 完成环境安装和可选依赖安装。
2. 先跑通仓库自带示例配置。
3. 查看日志目录和最佳候选程序。
4. 再替换为你自己的模板程序、任务描述和评测器。

## 文档导航

- [安装指南](getting-started/installation.md)：环境准备、依赖安装、API Key 配置
- [快速开始](getting-started/quickstart.md)：运行内置的在线装箱示例
- [配置指南](getting-started/configuration.md)：理解 YAML 结构和路径解析规则
- [搜索方法](user-guide/search-methods/index.md)：不同方法的特点与适用场景
- [LLM 提供方](user-guide/llm-providers/index.md)：不同模型后端的配置方式
- [Sandbox](user-guide/sandbox.md)：安全执行相关说明
- [API 参考](api/base-classes.md)：核心抽象与基础类

## 典型运行流程

```text
YAML 配置
    |
    +--> method
    +--> llm
    +--> evaluator
    +--> logger
              |
              v
搜索循环：构造提示词 -> 生成候选 -> 评测打分 -> 注册结果 -> 重复
```

## 从哪里开始最合适

如果你是第一次接触项目，先看 [安装指南](getting-started/installation.md)，然后按 [快速开始](getting-started/quickstart.md) 跑通一次示例。如果你已经理解整体框架，想直接接入自己的任务，建议从 [配置指南](getting-started/configuration.md) 和开发者文档开始。
