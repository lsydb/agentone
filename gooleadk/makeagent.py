#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
makeagent.py
负责构建 gooleadkchar 智能体（Agent）的工厂模块。
支持自定义模型、系统指令和工具集。
"""

import os

# ============================================================
# 0. 配置 Kimi (Moonshot) API 环境变量
# ============================================================
# 优先级：已存在的环境变量 > 代码默认值
os.environ.setdefault(
    "OPENAI_API_KEY", "sk-LLbJmPOEfRMXF9NzLYrazzYA4h9u3dpMvHrzfi7O1dkFz7ti"
)
os.environ.setdefault("OPENAI_BASE_URL", "https://api.moonshot.cn/v1")

# ============================================================
# 1. 导入 ADK & Neo4j 工具
# ============================================================
try:
    from google.adk.agents import Agent
except ImportError as e:
    raise ImportError(
        f"无法导入 google-adk: {e}。请执行: pip install google-adk"
    ) from e

from neo4j_wrapper import query_neo4j, write_neo4j


# ============================================================
# 2. 默认系统指令
# ============================================================
DEFAULT_INSTRUCTION = """\
你是一位友好的中文 AI 助手，名叫「小谷」。你拥有 Neo4j 图数据库的读写能力。

【query_neo4j — 只读查询】
当用户需要查看、搜索、统计现有数据时使用。支持：
- MATCH, RETURN, COUNT, LIMIT
- CALL db.schema 等元数据查询
- 任何不需要修改数据库的操作

【write_neo4j — 写入操作】
当用户需要增删改数据时使用。支持：
- CREATE   创建节点或关系
- MERGE    匹配或创建（避免重复）
- SET      修改属性
- DELETE   删除节点/关系（删除节点前需先 DETACH）
- REMOVE   删除属性或标签

使用工具时的最佳实践：
1. 写入前先查询确认状态（如"是否存在该节点"）
2. 参数使用 JSON 字符串格式，例如 '{"name": "Alice", "age": 30}'
3. 拿到工具返回结果后，用自然语言向用户解释发生了什么
4. 如果写入操作可能影响多条数据，先提醒用户潜在影响

如果用户没有特定问题，可以主动问候并询问是否需要帮助。
"""


# ============================================================
# 3. Agent 工厂
# ============================================================
def create_agent(
    name: str = "gooleadkchar",
    model: str = "openai/kimi-k2.6",
    description: str = "基于 Kimi API、可读写 Neo4j 的友好中文对话智能体。",
    instruction: str = None,
    tools: list = None,
) -> Agent:
    """
    创建并返回一个配置好的 Google ADK Agent 实例。

    Args:
        name: Agent 名称，用于内部标识。
        model: 模型标识符，默认使用 Kimi k2.6。
               可替换为其他 litellm 支持的模型，如 "openai/gpt-4o"。
        description: Agent 的简短描述。
        instruction: 系统指令（system prompt）。传入 None 则使用默认指令。
        tools: 工具函数列表。传入 None 则使用默认的 Neo4j 读写工具。

    Returns:
        配置好的 google.adk.agents.Agent 实例。

    Example:
        >>> agent = create_agent()
        >>> agent = create_agent(
        ...     name="data_analyst",
        ...     model="openai/kimi-k2.6",
        ...     instruction="你是一位数据分析专家...",
        ...     tools=[query_neo4j],
        ... )
    """
    if instruction is None:
        instruction = DEFAULT_INSTRUCTION
    if tools is None:
        tools = [query_neo4j, write_neo4j]

    return Agent(
        name=name,
        model=model,
        description=description,
        instruction=instruction,
        tools=tools,
    )
