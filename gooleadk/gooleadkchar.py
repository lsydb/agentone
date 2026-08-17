#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
【异步版】Google ADK + Kimi + Neo4j 智能体对话，支持多用户同时使用。
Agent 构建逻辑已抽离至 makeagent.py，此处只负责 Runner、会话管理与交互。
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

from neo4j_wrapper import close_neo4j
from makeagent import create_agent


async def create_runner(agent) -> Runner:
    return Runner(
        agent=agent,
        app_name="gooleadkchar_app",
        session_service=InMemorySessionService(),
        artifact_service=InMemoryArtifactService(),
    )


async def ensure_user_session(runner: Runner, user_id: str, created_users: set):
    if user_id not in created_users:
        await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=user_id,
        )
        created_users.add(user_id)
        return True
    return False


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


async def demo_concurrent(runner: Runner, created_users: set):
    demos = [
        ("Alice", "你好，请自我介绍一下"),
        ("Bob", "数据库里现在有哪些标签？"),
        ("Charlie", "帮我创建一个 Person 节点，名字叫 David，年龄 25 岁"),
    ]
    for uid, _ in demos:
        await ensure_user_session(runner, uid, created_users)

    async def run_one(user_id: str, question: str):
        print(f"\n🚀 [{user_id}] 提问: {question}")
        print(f"🤖 [{user_id}] 小谷: ", end="", flush=True)
        reply = await send_message(runner, user_id, question)
        print(reply)

    await asyncio.gather(*(run_one(uid, q) for uid, q in demos))
    print("\n✅ 并发演示结束")


async def chat_loop(runner: Runner):
    current_user = "user_001"
    created_users = set()
    await ensure_user_session(runner, current_user, created_users)

    print("=" * 55)
    print("🤖 欢迎使用 Google ADK + Kimi + Neo4j 智能体对话")
    print("   模式: 异步 | 模型: kimi-k2.6 | 工具: Neo4j 读写")
    print("-" * 55)
    print("  命令:")
    print("    !user <用户名>  — 切换或新建用户")
    print("    !users          — 查看所有在线用户")
    print("    !demo           — 演示多用户并发对话")
    print("    quit/exit/q     — 退出程序")
    print("=" * 55)

    while True:
        prompt = f"\n👤 [{current_user}] 你: "
        try:
            user_input = await asyncio.to_thread(input, prompt)
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break

        user_input = user_input.strip()
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break
        if not user_input:
            continue

        if user_input.startswith("!user "):
            new_user = user_input[6:].strip()
            if new_user:
                is_new = await ensure_user_session(runner, new_user, created_users)
                current_user = new_user
                print(f"✅ {'已创建并' if is_new else ''}切换到用户: {current_user}")
            continue

        if user_input == "!users":
            if created_users:
                print("👥 在线用户:", ", ".join(sorted(created_users)))
                print(f"   当前用户: {current_user}")
            else:
                print("👥 暂无在线用户")
            continue

        if user_input == "!demo":
            await demo_concurrent(runner, created_users)
            continue

        print("🤖 小谷: ", end="", flush=True)
        try:
            reply = await send_message(runner, current_user, user_input)
            print(reply)
        except Exception as e:
            print(f"\n[运行错误] {e}")


async def main():
    print("正在初始化异步 Google ADK + Kimi + Neo4j 智能体...")
    print(f"API Base: {os.environ.get('OPENAI_BASE_URL')}")
    agent = create_agent()
    runner = await create_runner(agent)
    try:
        await chat_loop(runner)
    finally:
        close_neo4j()
        print("\nNeo4j 连接已关闭。")


if __name__ == "__main__":
    asyncio.run(main())
