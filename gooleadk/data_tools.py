#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_tools.py
dataagent 的专用工具集，负责聊天摘要的持久化存储与检索。
数据以 JSON 格式保存在本地 chat_data/ 目录下。
"""

import json
import openai
import os
import os
from datetime import datetime
from typing import Any

# 数据存储目录（与脚本同级）
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_data")
os.makedirs(DATA_DIR, exist_ok=True)

_SUMMARY_FILE = os.path.join(DATA_DIR, "summaries.jsonl")


def _now() -> str:
    """返回当前时间的 ISO 格式字符串。"""
    return datetime.now().isoformat(sep=" ", timespec="seconds")


# ---------------------------------------------------------------
# 工具 1：保存聊天摘要
# ---------------------------------------------------------------
def save_chat_summary(session_id: str, summary: str, topics: str = "") -> str:
    """
    将一次聊天的优化总结保存到本地知识库。

    每次调用都会在 chat_data/summaries.jsonl 中追加一条记录，
    包含时间戳、会话ID、摘要内容和关联主题。

    Args:
        session_id: 会话标识符，例如 "user_001_session_20250816".
        summary: 优化后的聊天内容总结，要求简洁、结构化。
        topics: 本次聊天涉及的主题标签，用逗号分隔。例如 "Neo4j,图数据库,查询优化".

    Returns:
        保存结果的提示信息（成功或失败）。
    """
    try:
        record = {
            "timestamp": _now(),
            "session_id": session_id,
            "summary": summary,
            "topics": [t.strip() for t in topics.split(",") if t.strip()],
        }
        with open(_SUMMARY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return f"[保存成功] 会话 {session_id} 的摘要已存入知识库，共 {len(record['topics'])} 个主题标签。"
    except Exception as e:
        return f"[保存失败] {type(e).__name__}: {e}"


# ---------------------------------------------------------------
# 工具 2：查询聊天历史
# ---------------------------------------------------------------
def query_chat_history(query: str = "", session_id: str = "") -> str:
    """
    从历史知识库中检索相关的聊天摘要记录。

    支持按关键词或 session_id 过滤。如果都不传，返回最近 10 条记录。

    Args:
        query: 关键词，用于匹配摘要内容或主题标签。例如 "Neo4j".
        session_id: 按特定会话 ID 精确过滤。例如 "user_001_session_20250816".

    Returns:
        匹配的摘要记录列表（JSON 字符串），或提示信息。
    """
    try:
        if not os.path.exists(_SUMMARY_FILE):
            return "知识库为空，暂无历史记录。"

        results: list[dict[str, Any]] = []
        with open(_SUMMARY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # 过滤逻辑
                match = True
                if session_id and record.get("session_id") != session_id:
                    match = False
                if query:
                    q = query.lower()
                    in_summary = q in record.get("summary", "").lower()
                    in_topics = any(q in t.lower() for t in record.get("topics", []))
                    if not (in_summary or in_topics):
                        match = False

                if match:
                    results.append(record)

        # 限制返回数量，按时间倒序
        results = results[-20:][::-1]

        if not results:
            return "未找到匹配的历史记录。"

        return json.dumps(results, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"[查询错误] {type(e).__name__}: {e}"


# ---------------------------------------------------------------
# 工具 3：获取相关资料
# ---------------------------------------------------------------
def get_related_data(topic: str) -> str:
    """
    根据主题从知识库中提取相关的历史资料与经验数据。

    该工具会检索所有包含该主题的聊天摘要，并整合为一份结构化资料。

    Args:
        topic: 主题关键词。例如 "Neo4j 写入", "Kimi API", "图数据库设计".

    Returns:
        与该主题相关的历史资料摘要（JSON 字符串）。
    """
    try:
        raw = query_chat_history(query=topic)
        if raw.startswith("["):
            records = json.loads(raw)
            if not records:
                return f"暂无与主题 '{topic}' 相关的资料。"

            # 整合输出
            related = {
                "topic": topic,
                "record_count": len(records),
                "records": records,
            }
            return json.dumps(related, ensure_ascii=False, indent=2)
        return raw
    except Exception as e:
        return f"[获取资料错误] {type(e).__name__}: {e}"


# ---------------------------------------------------------------
# 工具 4：列出所有主题标签
# ---------------------------------------------------------------
def list_all_topics() -> str:
    """
    列出知识库中已存在的所有主题标签（去重）。

    Returns:
        主题标签列表（JSON 字符串）。
    """
    try:
        if not os.path.exists(_SUMMARY_FILE):
            return json.dumps([], ensure_ascii=False)

        topics = set()
        with open(_SUMMARY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    for t in record.get("topics", []):
                        topics.add(t)
                except json.JSONDecodeError:
                    continue

        return json.dumps(sorted(topics), ensure_ascii=False, indent=2)
    except Exception as e:
        return f"[列出主题错误] {type(e).__name__}: {e}"


# ---------------------------------------------------------------
# 工具 5：LLM 智能总结
# ---------------------------------------------------------------
def summarize_chat(raw_content: str, style: str = "简洁") -> str:
    """
    调用 Kimi LLM 对原始聊天内容进行高质量总结。

    Args:
        raw_content: 原始聊天记录。
        style: 总结风格，可选 "简洁"/"详细"/"结构化"/"问答式"。

    Returns:
        优化后的摘要文本，或错误提示。
    """
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.moonshot.cn/v1")
        client = openai.OpenAI(api_key=api_key, base_url=base_url)

        system_msg = (
            f"你是一位专业的聊天内容总结助手。"
            f"请用「{style}」风格对以下对话进行提炼总结，"
            f"保留关键信息、技术要点和决策结论，去除口语化废话。"
        )

        response = client.chat.completions.create(
            model="kimi-k2.6",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": raw_content},
            ],
            temperature=0.3,
        )
        summary = response.choices[0].message.content
        return summary.strip()
    except Exception as e:
        return f"[总结失败] {type(e).__name__}: {e}"

