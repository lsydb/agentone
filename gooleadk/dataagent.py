#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dataagent.py
数据总结与资料检索 Agent。
通过 makeagent 工厂创建，负责：
    1. 对聊天内容进行优化总结并保存
    2. 提供历史资料查询与主题检索
"""
import asyncio
import os
import sys

try:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.artifacts import InMemoryArtifactService
    from google.genai.types import Content, Part
except ImportError as e:
    print(f"[错误] 无法导入 google-adk: {e}")
    sys.exit(1)

from makeagent import create_agent
from data_tools import (
    summarize_chat,
    save_chat_summary,
    query_chat_history,
    get_related_data,
    list_all_topics,
)


# ---------------------------------------------------------------
# Data Agent 系统指令
# ---------------------------------------------------------------
DATA_AGENT_INSTRUCTION = """\
你是一位专业的数据总结与资料检索助理，名叫「数小助」。

你的核心职责：
1. **聊天总结**：将用户提供的原始对话内容进行提炼、优化，生成结构化摘要。
2. **知识保存**：使用 save_chat_summary 将摘要持久化到知识库。
3. **资料检索**：当用户需要历史资料或相关数据时，使用 query_chat_history 或 get_related_data 查询。

【可用工具说明】

summarize_chat — LLM 智能总结
    调用 Kimi LLM 对原始聊天内容进行高质量总结。
    - raw_content: 原始聊天记录
    - style: 总结风格（"简洁"/"详细"/"结构化"/"问答式"）
    返回优化后的摘要文本。

save_chat_summary — 保存聊天摘要
    将摘要写入知识库。参数说明：
    - session_id: 会话标识（如 "alice_20250816"）
    - summary: 优化后的摘要正文（可选）
    - topics: 主题标签，逗号分隔（如 "Neo4j, 查询优化, 数据建模"）
    - raw_content: 原始聊天记录（可选）。如果传了 raw_content 且 summary 为空，会自动调用 summarize_chat 生成摘要。

query_chat_history — 查询历史记录
    按关键词或 session_id 检索已保存的摘要。支持模糊匹配。

get_related_data — 获取主题资料
    输入一个主题词，系统会整合所有相关历史记录，返回结构化资料。

list_all_topics — 列出所有主题
    查看知识库中已有的全部主题标签。

【工作原则】
1. 如果用户提供了原始聊天记录但没有现成摘要，优先调用 summarize_chat 生成高质量摘要。
2. 保存时应为用户指定合适的主题标签，便于后续检索。
3. 检索到资料后，用自然语言整合呈现，不要只罗列 JSON。
4. 如果知识库为空，诚实告知用户。
"""


# ---------------------------------------------------------------
# 构建 Data Agent
# ---------------------------------------------------------------
def build_data_agent():
    """通过 makeagent 工厂创建 dataagent。"""
    return create_agent(
        name="dataagent",
        model="openai/kimi-k2.6",
        description="聊天内容总结与历史资料检索专家。",
        instruction=DATA_AGENT_INSTRUCTION,
        tools=[
            summarize_chat,
            save_chat_summary,
            query_chat_history,
            get_related_data,
            list_all_topics,
        ],
    )


# ---------------------------------------------------------------
# Runner & 交互
# ---------------------------------------------------------------
async def create_runner(agent) -> Runner:
    return Runner(
        agent=agent,
        app_name="dataagent_app",
        session_service=InMemorySessionService(),
        artifact_service=InMemoryArtifactService(),
    )


async def send_message(runner: Runner, user_id: str, text: str) -> str:
    msg = Content(role="user", parts=[Part(text=text)])
    response_text = ""
    async for event in runner.run_async(
        user_id=user_id, session_id=user_id, new_message=msg
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text
    return response_text


async def chat_loop(runner: Runner):
    user_id = "data_user_001"
    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=user_id,
    )

    print("=" * 55)
    print("📚 欢迎使用 Data Agent — 聊天总结与资料检索")
    print("   模型: kimi-k2.6 | 工具: 保存/查询/主题检索")
    print("-" * 55)
    print("  示例用法:")
    print('    "把刚才的对话总结并保存，主题：Neo4j入门"')
    print('    "查询关于图数据库的历史记录"')
    print('    "列出所有已有主题"')
    print("   quit/exit/q — 退出")
    print("=" * 55)

    while True:
        try:
            user_input = await asyncio.to_thread(input, "\n👤 你: ")
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break

        user_input = user_input.strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break
        if not user_input:
            continue

        print("📚 数小助: ", end="", flush=True)
        try:
            reply = await send_message(runner, user_id, user_input)
            print(reply)
        except Exception as e:
            print(f"\n[运行错误] {e}")


# ---------------------------------------------------------------
# 入口
# ---------------------------------------------------------------
async def main():
    print("正在初始化 Data Agent...")
    agent = build_data_agent()
    runner = await create_runner(agent)
    await chat_loop(runner)


if __name__ == "__main__":
    asyncio.run(main())
