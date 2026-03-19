# SGLang

## 概述

SGLang 提供商允许 algodisco 与本地 SGLang 推理服务器交互。SGLang 是一个高吞吐量的 LLM 推理框架。

## 安装

```bash
pip install sglang
```

## 配置参数

### 初始化参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `model_path` | `str` | 是 | 模型路径或 Hugging Face 模型 ID |
| `port` | `int` | 是 | 服务端口 |
| `gpus` | `int` \| `list[int]` | 是 | GPU 编号 |
| `tokenizer_path` | `str` | 否 | tokenizer 路径 |
| `max_model_len` | `int` | 否 | 模型最大长度 |
| `host` | `str` | 否 | 主机地址 (默认: `0.0.0.0`) |
| `mem_util` | `float` | 否 | GPU 显存利用率 (默认: 0.85) |
| `deploy_timeout_seconds` | `int` | 否 | 部署超时 (默认: 600) |

## 使用示例

```yaml
llm:
  class_path: "algodisco.providers.llm.sglang_server.SGLangServer"
  kwargs:
    model_path: "meta-llama/Llama-2-70b-hf"
    port: 30000
    gpus: [0, 1]
    mem_util: 0.8
```

## API 参考

### SGLangServer 类

```python
class SGLangServer(LanguageModel):
    def __init__(
        self,
        model_path: str,
        port: int,
        gpus: int | list[int],
        tokenizer_path: Optional[str] = None,
        max_model_len: int = 16384,
        host: str = "0.0.0.0",
        mem_util: float = 0.85,
        deploy_timeout_seconds: int = 600,
    ):
```

#### 方法

##### chat_completion()

```python
def chat_completion(
    self,
    message: str | List[ChatCompletionMessageParam],
    max_tokens: Optional[int] = None,
    timeout_seconds: Optional[int] = None,
    temperature: float = 0.9,
    top_p: float = 0.9,
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
) -> List[float] | List[List[float]]:
    """生成文本嵌入"""
```

##### close()

```python
def close(self) -> None:
    """关闭 SGLang 服务器"""
```

## 相关文档

- [LLM 提供商总览](index.md)
- [OpenAI](openai.md)
- [vLLM](vllm.md)
