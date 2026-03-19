# 系统架构

AlgoDisco 采用模块化架构设计，包含以下核心组件：

## 架构图

```
+------------------------------------------------------------------------------+
|                              Config (YAML)                                   |
+-------------------------------+----------------------------------------------+
                              |
        +---------------------+---------------------+
        |                     |                     |
        v                     v                     v
+----------------+    +----------------+    +----------------+
| LLM Provider  |    | Search Method  |    |   Evaluator   |
+----------------+    +----------------+    +----------------+
| - OpenAIAPI   |    | - FunSearch    |    | - Simple       |
| - ClaudeAPI   |    | - OpenEvolve   |    | - Ray-based    |
| - VLLMServer  |    | - EoH          |    +----------------+
| - SGLangServer|    | - (1+1)-EPS    |
+----------------+    | - RandSample   |
                      | - BehaveSim    |
                      +----------------+
                              |
                              v
                      +----------------+
                      |     Logger     |
                      +----------------+
                      | - PickleLogger |
                      | - WandBLogger  |
                      | - SwanLabLogger|
                      +----------------+
```

## 核心模块

### 1. 配置层 (Configuration)

YAML 配置文件定义搜索参数、LLM 提供商、评估器和日志器。

**文件位置**: `configs/*.yaml`

### 2. LLM 提供商 (LLM Providers)

负责与各种 LLM 服务交互。

**文件位置**: `algodisco/providers/llm/`

| 类名 |
|------|
| `OpenAIAPI` |
| `ClaudeAPI` |
| `VLLMServer` |
| `SGLangServer` |

### 3. 搜索方法 (Search Methods)

实现各种进化搜索算法。

**文件位置**: `algodisco/methods/*/`

| 方法 | 核心类 |
|------|--------|
| FunSearch | `FunSearch` |
| OpenEvolve | `OpenEvolve` |
| EoH | `EoH` |
| (1+1)-EPS | `OnePlusOneEPS` |
| RandSample | `RandSample` |
| BehaveSim | `BehaveSim` |

### 4. 评估器 (Evaluator)

执行并评估生成的算法。

**文件位置**: `algodisco/base/evaluator.py`

```python
class Evaluator(ABC):
    @abstractmethod
    def evaluate_program(self, program_str: str) -> EvalResult:
        pass
```

### 5. 日志器 (Logger)

记录搜索过程和结果。

**文件位置**: `algodisco/providers/logger/`

| 类名 |
|------|
| `BasePickleLogger` |
| `WandbLogger` |
| `SwanLabLogger` |

### 6. 沙箱执行 (Sandbox)

安全执行不受信任的代码。

**文件位置**: `algodisco/toolkit/sandbox/`

## 数据流

1. **初始化**: 加载配置 → 创建 LLM → 创建评估器 → 创建日志器
2. **搜索循环**:
   - 选择父代并构建提示词
   - 调用 LLM 生成候选算法
   - 从响应中提取代码
   - 在沙箱中评估候选算法
   - 将结果注册到数据库
   - 记录到日志器
3. **终止**: 达到最大采样数或手动停止

## 关键类

### AlgoProto

算法表示的基类，包含：
- `algo_id`: 唯一标识符
- `program`: 程序代码
- `language`: 编程语言
- `score`: 评估分数
- `metadata`: 附加元数据

### IterativeSearchBase

迭代搜索方法的抽象基类，定义生命周期：
- `initialize()`: 初始化搜索过程
- `select_and_create_prompt()`: 选择候选并构建提示词
- `generate()`: 生成新候选
- `extract_algo_from_response()`: 从响应中提取算法
- `evaluate()`: 评估候选
- `register()`: 注册结果
- `is_stopped()`: 检查终止条件

## 扩展点

AlgoDisco 设计为可扩展的，主要扩展点包括：

1. **自定义评估器**: 实现 `Evaluator` 接口
2. **自定义搜索方法**: 继承 `IterativeSearchBase`
3. **自定义 LLM 提供商**: 继承 `LanguageModel`
4. **自定义日志器**: 继承 `AlgoSearchLoggerBase`
