# 安装指南

本页说明如何为 AlgoDisco 搭建一个适合本地开发和实验的运行环境。

## 前置要求

开始前请确认你已经具备：

- Python 3.11 或更高版本
- `git`
- 至少一个 LLM 提供方的可用凭证，例如 OpenAI 或 Anthropic 的 API Key

## 克隆仓库

```bash
git clone https://github.com/RayZhhh/algodisco.git
cd algodisco
```

## 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## 安装 AlgoDisco

基础安装方式：

```bash
pip install -e .
```

按需安装可选扩展：

```bash
pip install -e ".[claude]"
pip install -e ".[vllm]"
pip install -e ".[sglang]"
pip install -e ".[wandb]"
pip install -e ".[swanlab]"
pip install -e ".[ray]"
pip install -e ".[dev]"
```

如果你准备在同一个环境里使用多个扩展，可以合并安装：

```bash
pip install -e ".[claude,wandb,ray,dev]"
```

## 配置凭证

最推荐的做法是通过环境变量提供密钥：

```bash
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
```

如果你使用兼容网关或代理，也可以设置对应的基础地址：

```bash
export OPENAI_BASE_URL="https://api.openai.com/v1"
export ANTHROPIC_BASE_URL="https://api.anthropic.com"
```

## 验证安装

执行一次最小导入测试：

```bash
python -c "import algodisco; print('AlgoDisco import successful')"
```

如果这条命令可以正常输出，说明包已经正确安装，可以继续运行示例。

## 常见说明

- 开发阶段建议使用可编辑安装，即 `pip install -e .`。
- `vllm`、`sglang`、`wandb`、`swanlab`、`ray` 都是可选依赖，不需要一次性全部安装。
- 仓库里的大多数示例默认你在项目根目录执行命令。

## 下一步

- 继续阅读 [快速开始](quickstart.md)，先跑通一个官方示例。
- 如果你准备接入自己的任务，请接着看 [配置指南](configuration.md)。
