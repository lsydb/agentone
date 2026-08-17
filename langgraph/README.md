# LangGraph Agent 项目

基于 LangChain + LangGraph 的 Agent 开发环境。

## 环境准备

1. 激活虚拟环境
   ```bash
   source ../.venv/bin/activate
   ```

2. 复制环境变量模板并填写真实 API Key
   ```bash
   cp .env.example .env
   ```

3. 编辑 `.env` 文件，填入你的 `OPENAI_API_KEY`（或其他模型 Key）

## 已安装核心依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| langchain | 1.3.15 | LangChain 核心框架 |
| langgraph | 1.2.11 | 图结构 Agent 编排 |
| langchain-openai | 1.5.1 | OpenAI 模型集成 |
| langchain-community | 0.4.2 | 社区工具与扩展 |
| langsmith | 0.11.0 | 调用链追踪与调试 |
| python-dotenv | 1.2.3 | 环境变量加载 |

## 目录结构

```
langgraph/
├── .env.example          # API Key 模板
├── README.md             # 本文件
└── (你的 Agent 代码将放在这里)
```
