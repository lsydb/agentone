#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
neo4j_wrapper.py
Neo4j 图数据库包装器，提供 Cypher 查询能力给 ADK Agent 作为工具使用。

连接信息优先级：
    1. 构造参数传入
    2. 环境变量（NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD）
    3. 默认值（bolt://localhost:7687 / neo4j / neo4j）
"""

import os
from typing import Any

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None


class Neo4jWrapper:
    """Neo4j 数据库连接包装器。"""

    def __init__(
        self,
        uri: str = None,
        user: str = None,
        password: str = None,
    ):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "neo4j")
        self._driver = None

    def _ensure_driver(self):
        """延迟初始化驱动。"""
        if self._driver is None:
            if GraphDatabase is None:
                raise RuntimeError(
                    "neo4j 驱动未安装，请执行: pip install neo4j"
                )
            self._driver = GraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )

    def close(self):
        """关闭数据库连接。"""
        if self._driver:
            self._driver.close()
            self._driver = None

    def run_cypher(self, query: str, parameters: dict = None) -> list[dict[str, Any]]:
        """
        执行 Cypher 查询语句并返回结果列表。

        Args:
            query: 要执行的 Cypher 查询字符串，例如:
                MATCH (n:Person {name: $name}) RETURN n.age AS age
            parameters: 查询参数字典，用于替换 Cypher 中的 $变量，例如:
                {"name": "Alice"}

        Returns:
            结果记录列表，每条记录是一个字典。例如:
                [{"age": 30}, {"age": 25}]
        """
        self._ensure_driver()
        parameters = parameters or {}
        with self._driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]

    def run_cypher_tool(self, query: str, parameters: str = "{}") -> str:
        """
        供 ADK Agent 调用的 Cypher 查询工具。

        执行 Cypher 查询并返回 JSON 格式的字符串结果，方便大模型解析。

        Args:
            query: Cypher 查询语句。例如:
                "MATCH (n:Person) RETURN n.name AS name, n.age AS age LIMIT 10"
            parameters: JSON 格式的参数字符串（可选）。例如:
                '{"name": "Alice"}'

        Returns:
            JSON 字符串表示的查询结果。例如:
                '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]'
            如果出错，返回错误信息字符串。
        """
        import json

        try:
            params = json.loads(parameters) if parameters else {}
            records = self.run_cypher(query, params)
            return json.dumps(records, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"[Cypher 查询错误] {type(e).__name__}: {e}"


# 模块级单例，方便 Agent 直接引用
_default_wrapper: Neo4jWrapper | None = None


def get_neo4j_wrapper() -> Neo4jWrapper:
    """获取默认的 Neo4jWrapper 实例（单例）。"""
    global _default_wrapper
    if _default_wrapper is None:
        _default_wrapper = Neo4jWrapper()
    return _default_wrapper


def query_neo4j(query: str, parameters: str = "{}") -> str:
    """
    执行 Neo4j Cypher 查询，返回结果。

    当用户询问与知识图谱、人物关系、节点属性等相关问题时，
    你可以使用此工具查询 Neo4j 数据库获取准确信息。

    Args:
        query: Cypher 查询语句。示例:
            "MATCH (p:Person)-[:KNOWS]->(friend) WHERE p.name = $name RETURN friend.name"
        parameters: JSON 字符串格式的查询参数。示例:
            '{"name": "Alice"}'

    Returns:
        查询结果（JSON 字符串）或错误信息。
    """
    wrapper = get_neo4j_wrapper()
    return wrapper.run_cypher_tool(query, parameters)

def close_neo4j():
    """关闭 Neo4j 连接（程序退出时调用）。"""
    global _default_wrapper
    if _default_wrapper:
        _default_wrapper.close()
        _default_wrapper = None


def write_neo4j(query: str, parameters: str = "{}") -> str:
    """
    执行 Neo4j Cypher 写入操作（CREATE / MERGE / SET / DELETE 等）。

    当用户需要增删改图数据库中的节点、关系或属性时使用此工具。
    虽然底层也是 Cypher 执行，但语义上区分读写，帮助 Agent 正确选择工具。

    Args:
        query: Cypher 写入语句。示例:
            "CREATE (p:Person {name: $name, age: $age}) RETURN p"
        parameters: JSON 字符串格式的查询参数。示例:
            '{"name": "David", "age": 25}'

    Returns:
        操作结果（JSON 字符串）或错误信息。
    """
    wrapper = get_neo4j_wrapper()
    return wrapper.run_cypher_tool(query, parameters)

