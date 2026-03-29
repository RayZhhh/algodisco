# 搜索方法 API

## FunSearch

```python
from algodisco.methods.funsearch.search import FunSearch
from algodisco.methods.funsearch.config import FunSearchConfig
```

### FunSearchConfig

```python
@dataclass
class FunSearchConfig:
    template_program: str
    task_description: str = ""
    language: str = "python"
    num_samplers: int = 4
    num_evaluators: int = 4
    examples_per_prompt: int = 2
    samples_per_prompt: int = 4
    max_samples: Optional[int] = 1000
    llm_max_tokens: Optional[int] = None
    llm_timeout_seconds: int = 120
    db_num_islands: int = 10
    db_max_island_capacity: Optional[int] = None
    db_reset_period: int = 4 * 60 * 60
    db_cluster_sampling_temperature_init: float = 0.1
    db_cluster_sampling_temperature_period: int = 30_000
    db_save_frequency: Optional[int] = 100
    keep_metadata_keys: List[str] = field(default_factory=list)
```

### FunSearch

```python
class FunSearch(IterativeSearchBase):
    def __init__(
        self,
        config: FunSearchConfig,
        evaluator,
        llm: LanguageModel = None,
        logger: Optional[AlgoSearchLoggerBase] = None,
        prompt_constructor: PromptAdapter = PromptAdapter(),
        *,
        tool_mode=False,
    ):
```

#### 方法

##### run()

```python
def run(self) -> None:
    """启动搜索过程"""
```

##### initialize()

```python
def initialize(self) -> None:
    """初始化搜索过程"""
```

##### is_stopped()

```python
def is_stopped(self) -> bool:
    """检查终止条件"""
```

---

## OpenEvolve

```python
from algodisco.methods.openevolve.search import OpenEvolve
from algodisco.methods.openevolve.config import OpenEvolveConfig
```

### OpenEvolveConfig

```python
@dataclass
class OpenEvolveConfig:
    template_program: str
    task_description: str = ""
    language: str = "python"
    diff_based_evolution: bool = False
    num_top_programs: int = 1
    num_diverse_programs: int = 1
    include_artifacts: bool = False
    num_samplers: int = 4
    num_evaluators: int = 4
    exploration_ratio: float = 0.2
    exploitation_ratio: float = 0.7
    elite_selection_ratio: float = 0.1
    samples_per_prompt: int = 1
    max_samples: Optional[int] = 1000
    llm_max_tokens: int = 1024
    llm_timeout_seconds: int = 120
    db_num_islands: int = 10
    db_reset_period: int = 4 * 60 * 60
    db_save_frequency: int = 100
```

### OpenEvolve

```python
class OpenEvolve(IterativeSearchBase):
    def __init__(
        self,
        config: OpenEvolveConfig,
        evaluator,
        llm: LanguageModel = None,
        logger: Optional[AlgoSearchLoggerBase] = None,
        prompt_constructor: PromptConstructor = None,
        *,
        tool_mode=False,
    ):
```

---

## EoH

```python
from algodisco.methods.eoh.search import EoHSearch
from algodisco.methods.eoh.config import EoHConfig
```

### EoHConfig

```python
@dataclass
class EoHConfig:
    template_program: str
    task_description: str = ""
    language: str = "python"
    pop_size: int = 10
    selection_num: int = 2
    use_e2_operator: bool = True
    use_m1_operator: bool = True
    use_m2_operator: bool = True
    num_samplers: int = 4
    num_evaluators: int = 4
    max_samples: Optional[int] = 1000
    llm_max_tokens: int = 1024
    llm_timeout_seconds: int = 120
    db_save_frequency: int = 100
    init_samples_ratio: float = 2.0
```

### EoHSearch

```python
class EoHSearch(IterativeSearchBase):
    def __init__(
        self,
        config: EoHConfig,
        evaluator,
        llm: LanguageModel = None,
        logger: Optional[AlgoSearchLoggerBase] = None,
        prompt_constructor: EoHPromptAdapter = EoHPromptAdapter(),
        *,
        tool_mode=False,
    ):
```

---

## (1+1)-EPS

```python
from algodisco.methods.one_plus_one_eps.search import OnePlusOneEPS
from algodisco.methods.one_plus_one_eps.config import OnePlusOneEPSConfig
```

### OnePlusOneEPSConfig

```python
@dataclass
class OnePlusOneEPSConfig:
    template_program: str
    task_description: str = ""
    language: str = "python"
    num_samplers: int = 4
    num_evaluators: int = 4
    samples_per_prompt: int = 4
    max_samples: Optional[int] = 1000
    llm_max_tokens: int = 1024
    llm_timeout_seconds: int = 120
```

---

## RandSample

```python
from algodisco.methods.randsample.search import RandSample
from algodisco.methods.randsample.config import RandSampleConfig
```

### RandSampleConfig

```python
@dataclass
class RandSampleConfig:
    template_program: str
    task_description: str = ""
    language: str = "python"
    num_samplers: int = 1
    num_evaluators: int = 4
    max_samples: Optional[int] = 1000
    llm_max_tokens: int = 1024
    llm_timeout_seconds: int = 120
```
