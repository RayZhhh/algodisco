# LLM 提供商

algodisco 支持多种 LLM 提供商，包括云端 API 和本地推理服务器。

## 支持的提供商

| 提供商 | 描述 | 核心类 |
|--------|------|--------|
| [OpenAI](openai.md) | OpenAI API 兼容接口 | `OpenAIAPI` |
| [Claude](claude.md) | Anthropic Claude API | `ClaudeAPI` |
| [vLLM](vllm.md) | vLLM 本地推理服务器 | `VLLMServer` |
| [SGLang](sglang.md) | SGLang 本地推理服务器 | `SGLangServer` |

## 选择指南

### 使用 OpenAI

- 需要使用 OpenAI API 或兼容服务
- 简单快速集成
- 需要 API 密钥

### 使用 Claude

- 需要使用 Anthropic Claude 模型
- 需要 API 密钥

### 使用 vLLM

- 本地部署大语言模型
- 需要 GPU 资源
- 支持 LoRA 适配器

### 使用 SGLang

- 本地部署大语言模型
- 需要 GPU 资源
- 高吞吐量需求

## 配置示例

```yaml
llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4"
    api_key: "your-api-key"
```

详细参数请参考各提供商的专门文档。
