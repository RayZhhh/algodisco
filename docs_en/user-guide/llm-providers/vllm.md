# vLLM

## 概述

vLLM 提供商允许 algodisco 与本地 vLLM 推理服务器交互。vLLM 是一个高效的 LLM 推理服务，支持多种模型和优化。

## 安装

```bash
pip install vllm
```

## 配置参数

### 初始化参数

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `model_path` | `str` | 是 | 模型路径或 Hugging Face 模型 ID |
| `port` | `int` | 是 | 服务端口 |
| `gpus` | `int` \| `list[int]` | 是 | GPU 编号 |
| `tokenizer_path` | `str` | 否 | tokenizer 路径 (默认同 model_path) |
| `max_model_len` | `int` | 否 | 模型最大长度 (默认: 16384) |
| `max_lora_rank` | `int` | 否 | LoRA 适配器最大 rank |
| `host` | `str` | 否 | 主机地址 (默认: `0.0.0.0`) |
| `mem_util` | `float` | 否 | GPU 显存利用率 (默认: 0.85) |
| `deploy_timeout_seconds` | `int` | 否 | 部署超时 (默认: 600) |
| `launch_vllm_in_init` | `bool` | 否 | 初始化时启动服务器 (默认: True) |
| `enforce_eager` | `bool` | 否 | 强制 eager 模式 |
| `vllm_log_level` | `str` | 否 | 日志级别 |
| `silent_mode` | `bool` | 否 | 静默模式 |

### 聊天完成参数

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `max_tokens` | `int` | None | 最大生成 token 数 |
| `timeout_seconds` | `int` | None | 超时时间 |
| `temperature` | `float` | 0.9 | 温度参数 |
| `top_p` | `float` | 0.9 | top-p 参数 |
| `lora_name` | `str` | None | LoRA 适配器名称 |

## 使用示例

### 基本使用

```yaml
llm:
  class_path: "algodisco.providers.llm.vllm_server.VLLMServer"
  kwargs:
    model_path: "meta-llama/Llama-2-70b-hf"
    port: 8000
    gpus: [0, 1]
    mem_util: 0.8
```

### 使用 LoRA 适配器

```python
from algodisco.providers.llm import VLLMServer

llm = VLLMServer(
    model_path="meta-llama/Llama-2-70b-hf",
    port=8000,
    gpus=[0],
    max_lora_rank=64,
    mem_util=0.8,
)

# 加载 LoRA
llm.load_lora_adapter("adapter_name", "/path/to/adapter")

# 使用 LoRA 生成
response = llm.chat_completion("Hello", lora_name="adapter_name")

# 卸载 LoRA
llm.unload_lora_adapter("adapter_name")

llm.close()
```

### 启用推理能力

```yaml
llm:
  class_path: "algodisco.providers.llm.vllm_server.VLLMServer"
  kwargs:
    model_path: "deepseek-ai/DeepSeek-R1"
    port: 8000
    gpus: [0]
    vllm_serve_args:
      - "--enable-reasoning"
    vllm_serve_kwargs:
      - "--reasoning-parser"
      - "deepseek-r1"
```

## API 参考

### VLLMServer 类

```python
class VLLMServer(LanguageModel):
    def __init__(
        self,
        model_path: str,
        port: int,
        gpus: int | list[int],
        tokenizer_path: Optional[str] = None,
        max_model_len: int = 16384,
        max_lora_rank: Optional[int] = None,
        host: str = "0.0.0.0",
        mem_util: float = 0.85,
        deploy_timeout_seconds: int = 600,
        *,
        launch_vllm_in_init: bool = True,
        enforce_eager: bool = False,
        vllm_log_level: str = "INFO",
        silent_mode: bool = False,
    ):
```

#### 方法

##### launch_vllm_server()

```python
def launch_vllm_server(
    self,
    detach: bool = False,
    skip_if_running: bool = False,
) -> None:
    """启动 vLLM 服务器"""
```

##### chat_completion()

```python
def chat_completion(
    self,
    message: str | List[ChatCompletionMessageParam],
    max_tokens: Optional[int] = None,
    timeout_seconds: Optional[int] = None,
    lora_name: Optional[str] = None,
    temperature: float = 0.9,
    top_p: float = 0.9,
    chat_template_kwargs: Optional[Dict[str, Any]] = None,
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
    lora_name: Optional[str] = None,
) -> List[float] | List[List[float]]:
    """生成文本嵌入"""
```

##### load_lora_adapter()

```python
def load_lora_adapter(
    self,
    lora_name: str,
    new_adapter_path: str,
    num_trails: int = 5,
) -> bool:
    """动态加载 LoRA 适配器"""
```

##### close()

```python
def close(self) -> None:
    """关闭 vLLM 服务器"""
```

## 相关文档

- [LLM 提供商总览](index.md)
- [OpenAI](openai.md)
- [SGLang](sglang.md)
