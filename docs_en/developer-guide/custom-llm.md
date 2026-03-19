# 自定义 LLM 提供商

本指南介绍如何为 algodisco 创建自定义 LLM 提供商。

## 基本结构

LLM 提供商需要继承 `LanguageModel` 基类：

```python
from algodisco.base.llm import LanguageModel


class MyLLM(LanguageModel):
    def __init__(self, model: str, **kwargs):
        self._model = model
        # 初始化连接

    def chat_completion(self, message, max_tokens, timeout_seconds, *args, **kwargs):
        # 实现聊天完成
        pass

    def embedding(self, text, dimensions=None, timeout_seconds=None, **kwargs):
        # 实现嵌入生成
        pass

    def close(self):
        # 清理资源
        pass
```

## 完整示例

```python
from algodisco.base.llm import LanguageModel
from typing import List, Optional


class MyLLM(LanguageModel):
    """自定义 LLM 提供商示例"""

    def __init__(
            self,
            model: str,
            api_url: str,
            api_key: str = None,
            **kwargs
    ):
        super().__init__()
        self._model = model
        self._api_url = api_url
        self._api_key = api_key
        self._session = None

    def _get_session(self):
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({"Authorization": f"Bearer {self._api_key}"})
        return self._session

    def chat_completion(
            self,
            message: str | List[dict],
            max_tokens: int = 1024,
            timeout_seconds: float = 120,
            *args,
            **kwargs
    ) -> str:
        """发送聊天完成请求"""
        import requests

        # 格式化消息
        if isinstance(message, str):
            messages = [{"role": "user", "content": message}]
        else:
            messages = message

        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        payload.update(kwargs)

        response = requests.post(
            f"{self._api_url}/chat/completions",
            json=payload,
            timeout=timeout_seconds,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"]

    def embedding(
            self,
            text: str | List[str],
            dimensions: Optional[int] = None,
            timeout_seconds: Optional[float] = None,
            **kwargs
    ) -> List[float] | List[List[float]]:
        """生成文本嵌入"""
        import requests

        is_single = isinstance(text, str)
        if is_single:
            text = [text]

        payload = {
            "input": text,
            "model": self._model,
        }
        if dimensions:
            payload["dimensions"] = dimensions

        response = requests.post(
            f"{self._api_url}/embeddings",
            json=payload,
            timeout=timeout_seconds,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        result = response.json()
        embeddings = [item["embedding"] for item in result["data"]]

        return embeddings[0] if is_single else embeddings

    def close(self):
        """关闭连接"""
        if self._session:
            self._session.close()
            self._session = None

    def reload(self):
        """重新加载"""
        self.close()
        self._session = None
```

## 使用自定义 LLM

在配置文件中指定：

```yaml
llm:
  class_path: "my_llm.MyLLM"
  kwargs:
    model: "my-model"
    api_url: "http://localhost:8000/v1"
    api_key: "optional-key"
```

## 接口要求

### chat_completion()

必须支持以下参数签名：

```python
def chat_completion(
    self,
    message: str | List[ChatCompletionMessageParam],
    max_tokens: int,
    timeout_seconds: float,
    *args,
    **kwargs,
) -> str:
    """返回生成的文本内容"""
```

### embedding()

```python
def embedding(
    self,
    text: str | List[str],
    dimensions: Optional[int] = None,
    timeout_seconds: Optional[float] = None,
    **kwargs,
) -> List[float] | List[List[float]]:
    """返回嵌入向量"""
```

### close() 和 reload()

```python
def close(self):
    """释放资源"""

def reload(self):
    """重新加载/重置连接"""
```

## 相关文档

- [LanguageModel API](../api/base-classes.md)
- [LLM 提供商](../user-guide/llm-providers/index.md)
