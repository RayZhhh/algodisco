# 贡献指南

欢迎为 AlgoDisco 项目贡献代码！

## 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/your-org/algodisco.git
cd `algodisco`

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 项目结构

```
algodisco/
├── base/              # 核心抽象类
│   ├── algo.py        # AlgoProto
│   ├── evaluator.py   # Evaluator
│   ├── llm.py         # LanguageModel
│   ├── logger.py      # Logger
│   └── search_method.py
├── methods/           # 搜索方法实现
│   ├── funsearch/
│   ├── openevolve/
│   └── ...
├── providers/         # LLM 和日志提供商
│   ├── llm/
│   └── logger/
└── toolkit/           # 工具类
├── configs/               # 配置文件
└── docs/                  # 文档
```

## 添加新搜索方法

1. 在 `algodisco/methods/` 下创建新目录
2. 实现搜索类（继承 `IterativeSearchBase`）
3. 创建配置类（使用 dataclass）
4. 添加入口点脚本
5. 添加配置文件模板

## 添加新 LLM 提供商

1. 在 `algodisco/providers/llm/` 下创建新文件
2. 继承 `LanguageModel` 基类
3. 实现 `chat_completion` 和 `embedding` 方法

## 代码规范

- 使用类型提示
- 遵循 PEP 8
- 添加 docstring
- 写单元测试

## 提交 PR

1. Fork 仓库
2. 创建功能分支
3. 编写代码和测试
4. 更新文档
5. 提交 Pull Request

## 问题反馈

请通过 GitHub Issues 报告 bug 和功能请求。
