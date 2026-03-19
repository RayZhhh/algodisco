# OpenAI

## 概述

OpenAI 提供商允许 algodisco 与 OpenAI API 以及任何 OpenAI 兼容的 API 服务交互。

## 安装

```bash
pip install openai
```

## 配置参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `model` | `str` | 是 | 模型名称 (如 `gpt-4`, `gpt-3.5-turbo`) |
| `api_key` | `str` | 否 | API 密钥 (或通过环境变量 `OPENAI_API_KEY`) |
| `base_url` | `str` | 否 | API 基础 URL (默认: `https://api.openai.com/v1`) |

## 使用示例

### 直接配置

```yaml
llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4-turbo-preview"
    api_key: "sk-..."
    base_url: "https://api.openai.com/v1"
```

### 使用环境变量

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

```yaml
llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4"
    api_key: null
    base_url: null
```

### 使用代理

```yaml
llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-4"
    api_key: "sk-..."
    base_url: "http://localhost:8080/v1"
```

## API 参考

### OpenAIAPI 类

```python
class OpenAIAPI(LanguageModel):
    def __init__(
        self,
        model: str,
        base_url: str = None,
        api_key: str = None,
        **openai_init_kwargs,
    ):
```

#### 初始化参数

- `model` (`str`): 模型名称
- `base_url` (`str`, 可选): API 基础 URL
- `api_key` (`str`, 可选): API 密钥
- `**openai_init_kwargs`: 其他传递给 OpenAI 客户端的参数

#### 方法

##### chat_completion()

```python
def chat_completion(
    self,
    message: str | List[ChatCompletionMessageParam],
    max_tokens: Optional[int] = None,
    timeout_seconds: Optional[float] = None,
    *args,
    **kwargs,
) -> str:
    """发送聊天完成请求"""
```

##### embedding()

```python
def embedding(
    self,
    text: str | List[str],
    dimensions: Optional[int] = None,
    timeout_seconds: Optional[float] = None,
    **kwargs,
) -> List[float] | List[List[float]]:
    """生成文本嵌入"""
```

## 相关文档

- [LLM 提供商总览](index.md)
- [Claude](claude.md)
- [vLLM](vllm.md)
