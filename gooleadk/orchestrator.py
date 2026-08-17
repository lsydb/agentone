#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
orchestrator.py
顶层智能体：识别用户意图，路由到 gooleadkchar（Neo4j）或 dataagent（数据总结）。
"""
import asyncio
import os

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai.types import Content, Part

from makeagent import create_agent, DEFAULT_INSTRUCTION as CHAT_INSTRUCTION
from dataagent import build_data_agent
from neo4j_wrapper import close_neo4j

# 加载系统指令（文件必须存在，无兜底）
_PROMPT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orchestrator_prompt.md")
ORCHESTRATOR_INSTRUCTION = open(_PROMPT_FILE, "r", encoding="utf-8").read()

# 子 Agent Runner 缓存
_runners = {}


async def _run_sub(key: str, text: str) -> str:
    """向子 Agent 发消息并返回文本回复。Runner 首次使用时创建。"""
    if key not in _runners:
        if key == "chat":
            agent = create_agent(name="gooleadkchar", instruction=CHAT_INSTRUCTION)
            app = "chat_sub"
        else:
            agent = build_data_agent()
            app = "data_sub"
        r = Runner(
            agent=agent, app_name=app,
            session_service=InMemorySessionService(),
            artifact_service=InMemoryArtifactService(),
        )
        await r.session_service.create_session(app_name=app, user_id="sub", session_id="sub")
        _runners[key] = r

    msg = Content(role="user", parts=[Part(text=text)])
    resp = ""
    async for e in _runners[key].run_async(user_id="sub", session_id="sub", new_message=msg):
        if e.content and e.content.parts:
            for p in e.content.parts:
                if p.text:
                    resp += p.text
    return resp


async def call_chat_agent(query: str) -> str:
    """调用 Neo4j 操作智能体（小谷）。"""
    return await _run_sub("chat", query)


async def call_data_agent(task: str) -> str:
    """调用数据总结智能体（数小助）。"""
    return await _run_sub("data", task)


def build_orchestrator_agent():
    return create_agent(
        name="orchestrator",
        model="openai/kimi-k2.6",
        description="总控智能体，负责对话意图识别并路由到子智能体。",
        instruction=ORCHESTRATOR_INSTRUCTION,
        tools=[call_chat_agent, call_data_agent],
    )


async def send_message(runner, user_id, text):
    msg = Content(role="user", parts=[Part(text=text)])
    resp = ""
    async for e in runner.run_async(user_id=user_id, session_id=user_id, new_message=msg):
        if e.content and e.content.parts:
            for p in e.content.parts:
                if p.text:
                    resp += p.text
    return resp


async def main():
    print("正在初始化总控智能体...")
    agent = build_orchestrator_agent()
    runner = Runner(
        agent=agent, app_name="orchestrator_app",
        session_service=InMemorySessionService(),
        artifact_service=InMemoryArtifactService(),
    )
    await runner.session_service.create_session(
        app_name="orchestrator_app", user_id="user", session_id="main"
    )

    print("=" * 55)
    print("🎯 总控智能体已启动")
    print("   子智能体: gooleadkchar（Neo4j）| dataagent（数据总结）")
    print("   输入 quit / exit / q 退出")
    print("=" * 55)

    while True:
        try:
            text = await asyncio.to_thread(input, "\n👤 你: ")
        except (KeyboardInterrupt, EOFError):
            break
        text = text.strip()
        if text.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break
        if not text:
            continue

        print("🎯 总指挥: ", end="", flush=True)
        try:
            print(await send_message(runner, "user", text))
        except Exception as e:
            print(f"\n[运行错误] {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        close_neo4j()
        print("\n资源已清理。")

