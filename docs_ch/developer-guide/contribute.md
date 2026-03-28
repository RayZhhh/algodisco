# 贡献指南

欢迎为 AlgoDisco 提交改进。本页说明最基本的开发环境准备方式，以及建议的贡献流程。

## 开发环境准备

```bash
git clone https://github.com/RayZhhh/algodisco.git
cd algodisco

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

如果你的改动依赖特定能力，再按需安装扩展：

```bash
pip install -e ".[claude]"
pip install -e ".[wandb]"
pip install -e ".[ray]"
```

## 仓库结构

```text
algodisco/
├── algodisco/               # 核心代码包
│   ├── base/                # 基础抽象
│   ├── common/              # 配置加载与公共工具
│   ├── methods/             # 搜索方法实现
│   ├── providers/           # LLM 与日志提供方
│   └── toolkit/             # sandbox、解析等工具
├── docs_en/                 # 英文文档
├── docs_ch/                 # 中文文档
├── examples/                # 可运行示例与配置
└── tutorial/                # Notebook 教程
```

## 常见贡献类型

### 新增搜索方法

通常需要完成：

1. 在 `algodisco/methods/` 下新增模块。
2. 定义该方法对应的配置 dataclass。
3. 实现搜索循环与结果注册逻辑。
4. 添加可执行入口模块。
5. 补充示例配置和文档说明。

### 新增 LLM 提供方

通常需要完成：

1. 在 `algodisco/providers/llm/` 下新增 provider。
2. 实现 `LanguageModel` 接口要求的方法。
3. 说明构造参数、环境变量和依赖要求。

### 新增或扩展 Evaluator

评测器必须继承 `algodisco.base.evaluator.Evaluator`，并返回至少包含 `score` 的结果字典。

## 质量要求

提交 PR 之前，请至少确认：

- 改动范围聚焦，不要把无关修改混在一起
- 行为变更时补充或更新测试
- 用户可见的改动要同步更新文档
- 不要引入占位仓库地址、虚假命令或未经验证的示例

## Pull Request 建议流程

1. Fork 仓库并创建功能分支。
2. 在本地完成实现与验证。
3. 如果改动影响使用方式，同步更新文档、配置或示例。
4. 提交 Pull Request，并简洁说明问题和修复内容。

## 问题反馈

Bug、回归问题和新需求建议统一通过 GitHub Issues 提交。
