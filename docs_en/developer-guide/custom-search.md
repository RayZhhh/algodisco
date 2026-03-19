# 自定义搜索方法

本指南介绍如何为 algodisco 创建自定义搜索方法。

## 基本结构

搜索方法需要继承 `IterativeSearchBase` 基类：

```python
from algodisco.base.search_method import IterativeSearchBase
from algodisco.base.algo import AlgoProto
from typing import Optional, Union, List


class MySearchMethod(IterativeSearchBase):
    def __init__(self, config, evaluator, llm=None, logger=None):
        self._config = config
        self._evaluator = evaluator
        self._llm = llm
        self._logger = logger

    def initialize(self):
        """初始化搜索"""
        pass

    def select_and_create_prompt(self) -> Optional[AlgoProto]:
        """选择父代并构建提示词"""
        pass

    def generate(self, selection: AlgoProto) -> Union[AlgoProto, List[AlgoProto]]:
        """生成新候选"""
        pass

    def extract_algo_from_response(self, candidate: AlgoProto) -> AlgoProto:
        """从响应提取算法"""
        pass

    def evaluate(self, candidates) -> Union[AlgoProto, List[AlgoProto]]:
        """评估候选"""
        pass

    def register(self, results):
        """注册结果"""
        pass

    def is_stopped(self) -> bool:
        """检查终止条件"""
        return False
```

## 完整示例

```python
from algodisco.base.search_method import IterativeSearchBase
from algodisco.base.algo import AlgoProto
from algodisco.base.evaluator import Evaluator
from algodisco.base.llm import LanguageModel
from typing import Optional, Union, List
import copy


class SimpleSearch(IterativeSearchBase):
    """简单的随机搜索方法"""

    def __init__(self, config, evaluator, llm=None, logger=None):
        self._config = config
        self._evaluator = evaluator
        self._llm = llm
        self._logger = logger
        self._database = []
        self._best_score = None

    def initialize(self):
        # 评估模板
        template = AlgoProto(
            program=self._config.template_program,
            language=self._config.language
        )
        result = self._evaluator.evaluate_program(template.program)
        template.score = result["score"]
        self._database.append(template)
        self._best_score = template.score

    def select_and_create_prompt(self) -> Optional[AlgoProto]:
        # 随机选择父代
        if not self._database:
            return None
        import random
        parent = random.choice(self._database)

        # 创建新候选
        candidate = AlgoProto(language=self._config.language)
        candidate["prompt"] = self._build_prompt(parent)
        return candidate

    def generate(self, selection: AlgoProto) -> AlgoProto:
        # 调用 LLM 生成
        response = self._llm.chat_completion(
            selection["prompt"],
            self._config.llm_max_tokens,
            self._config.llm_timeout_seconds
        )
        selection["response_text"] = response
        return selection

    def extract_algo_from_response(self, candidate: AlgoProto) -> AlgoProto:
        # 从响应提取代码
        response = candidate.get("response_text", "")
        # 提取代码块
        code = self._extract_code(response)
        candidate.program = code
        return candidate

    def evaluate(self, candidates) -> Union[AlgoProto, List[AlgoProto]]:
        result = self._evaluator.evaluate_program(candidates.program)
        candidates.score = result.get("score")
        return candidates

    def register(self, results):
        if results.score and results.score > self._best_score:
            self._best_score = results.score
        self._database.append(results)

    def is_stopped(self) -> bool:
        return len(self._database) >= self._config.max_samples

    def _build_prompt(self, parent: AlgoProto) -> str:
        return f"{self._config.task_description}\n\nExample:\n{parent.program}"

    def _extract_code(self, response: str) -> str:
        # 简单的代码提取
        if "```" in response:
            start = response.find("```python")
            if start == -1:
                start = response.find("```")
            end = response.find("```", start + 3)
            return response[start + 3:end] if end > 0 else response
        return response
```

## 必需方法

| 方法 | 描述 |
|------|------|
| `initialize()` | 初始化搜索过程，评估模板程序 |
| `select_and_create_prompt()` | 选择父代并构建提示词 |
| `generate()` | 调用 LLM 生成候选 |
| `extract_algo_from_response()` | 从 LLM 响应提取代码 |
| `evaluate()` | 评估候选算法 |
| `register()` | 注册结果到数据库 |
| `is_stopped()` | 检查是否满足终止条件 |

## 创建入口点

```python
# my_search/main_mysearch.py

import argparse
from my_search.config import MySearchConfig
from my_search.search import MySearchMethod
from algodisco.providers.llm import OpenAIAPI
from algodisco.utils import load_evaluator, load_logger


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    args = parser.parse_args()

    # 加载配置
    config = MySearchConfig.from_yaml(args.config)

    # 加载组件
    llm = OpenAIAPI(**config.llm_kwargs)
    evaluator = load_evaluator(config.evaluator)
    logger = load_logger(config.logger) if config.logger else None

    # 创建搜索
    search = MySearchMethod(config, evaluator, llm, logger)

    # 运行
    search.run()


if __name__ == "__main__":
    main()
```

## 注册搜索方法

在配置中使用：

```yaml
method:
  class_path: "my_search.search.MySearchMethod"
  kwargs:
    max_samples: 1000
```

## 相关文档

- [IterativeSearchBase API](../api/base-classes.md)
- [AlgoProto API](../api/base-classes.md)
