# -*- coding: utf-8 -*-
"""
dateHelp.py — Function Calling 版本（使用 openai 库调用 Kimi）

【功能】一个支持 Function Calling 的对话助手
【交互方式】你在终端输入一句话，程序调用 Kimi 大模型返回回答
【特色功能】Kimi 会自己判断是否需要获取当前时间，如果需要就调用工具，
          程序执行工具后把结果返给 Kimi，Kimi 再给出最终回答。
这个流程是先让大模型根据输入信息决定适不适用工具，使用工具后，把历史对话信息和工具结果在大模型生成答案

【使用方式】
1. 确保已设置 KIMI_API_KEY 环境变量
2. 运行：python3 dateHelp.py
3. 输入你的问题，按回车
4. 输入 exit 或 quit 退出

【什么是 Function Calling？】
Function Calling（函数调用）是大模型的一种能力：
- 你告诉 AI "我有这些工具可以用"
- AI 自己判断什么时候需要用哪个工具
- AI 不直接执行工具，而是告诉你"请帮我调用 xx 工具，参数是 yy"
- 你（程序）执行完工具后，把结果发回给 AI
- AI 基于工具结果给出最终回答

这比程序员自己写"if 用户问几点 then 调用时间工具"更智能，
因为 AI 能理解各种变体（"现在几点"、"看下表"、"现在什么时辰"等）。
"""

import os
import json
from openai import OpenAI  # 直接用 openai 库，Kimi API 完全兼容 OpenAI 格式

from currenttime import get_current_time


# ==================== 第1步：配置 ====================
# 创建 OpenAI 客户端，但把 base_url 改成 Kimi 的 API 地址
# 这样就用 OpenAI 的 SDK 调用了 Kimi 的大模型
client = OpenAI(
    api_key=os.getenv("KIMI_API_KEY"),  # 从环境变量读取 API Key
    base_url="https://api.moonshot.cn/v1",  # Kimi 的 API 地址
)
MODEL = "kimi-k2.6"  # 使用的模型名称


# ==================== 第2步：定义工具（Tool） ====================
# 【工具的概念】
# 工具 = 一个程序里的函数，但要用 JSON Schema 格式描述给 AI 看
# AI 根据描述来决定什么时候调用它

# 这是 get_current_time 工具的描述（JSON Schema 格式）
# AI 看到这段描述后就知道：哦，原来我可以调用这个函数来获取当前时间，而且不需要任何参数
TOOLS = [
    {
        "type": "function",  # 类型是函数
        "function": {
            "name": "get_current_time",  # 函数名称
            "description": "获取当前系统的日期和时间。当用户询问当前时间、日期、星期几时，应该调用此工具。",  # 函数用途描述，AI 靠这个判断什么时候调用
            "parameters": {  # 参数定义
                "type": "object",
                "properties": {},  # 空对象表示不需要参数
            },
        },
    }
]

# 工具名称 → 实际 Python 函数的映射表
# 当 AI 说要调用 "get_current_time" 时，我们去这个字典里找到对应的函数并执行
AVAILABLE_TOOLS = {
    "get_current_time": get_current_time,
}


def ask_kimi(messages, tools=None):
    """
    【功能】调用 Kimi 大模型
    【参数】
        messages：对话消息列表
        tools：可选，工具列表（第一次请求时传入，让 AI 知道有哪些工具可用）
    【返回】Kimi 的完整响应对象
    """
    try:
        # 如果传了 tools 参数，Kimi 会知道它可以使用这些工具
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,  # 告诉 AI：你有这些工具可以用
        )
        return response
    except Exception as e:
        # 如果出错，包装成一个类似正常响应的对象
        class FakeChoice:
            def __init__(self):
                self.message = type('Message', (), {
                    'content': f"调用 Kimi 出错了：{e}",
                    'tool_calls': None,
                })()
        class FakeResponse:
            def __init__(self):
                self.choices = [FakeChoice()]
        return FakeResponse()


def handle_tool_calls(response_message):
    """
    【功能】处理 AI 返回的工具调用请求
    【参数】response_message：AI 返回的消息对象
    【返回】一个列表，包含工具执行结果的消息（用于发给 AI 进行下一轮对话）
    
    【Function Calling 的核心流程】
    1. AI 返回 message.tool_calls，表示"我想调用这些工具"
    2. 我们遍历每个 tool_call，找到对应的函数执行
    3. 把执行结果打包成 "tool" 角色的消息
    4. 把这些消息加进对话历史，再次发给 AI
    """
    tool_results = []  # 存放所有工具执行结果的消息
    
    # 遍历 AI 要求调用的每个工具
    for tool_call in response_message.tool_calls:
        tool_name = tool_call.function.name  # AI 想调用的工具名称
        
        # 解析 AI 传过来的参数（JSON 字符串 → Python 字典）
        # 我们的 get_current_time 不需要参数，所以参数是空字典 {}
        try:
            tool_args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            tool_args = {}
        
        print(f"🔧 Kimi 要求调用工具：{tool_name}，参数：{tool_args}")
        
        # 在 AVAILABLE_TOOLS 字典里找到对应的函数并执行
        if tool_name in AVAILABLE_TOOLS:
            tool_func = AVAILABLE_TOOLS[tool_name]
            try:
                result = tool_func(**tool_args)  # **tool_args 把字典展开成关键字参数
                print(f"✅ 工具执行结果：{result}")
            except Exception as e:
                result = f"工具执行出错：{e}"
                print(f"❌ {result}")
        else:
            result = f"错误：未找到工具 {tool_name}"
            print(f"❌ {result}")
        
        # 把工具执行结果打包成消息
        # role="tool" 表示这是工具返回的结果
        # tool_call_id 必须和 AI 发过来的 tool_call.id 一致，这样 AI 才知道对应哪个调用
        tool_results.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_name,
            "content": result,
        })
    
    return tool_results


def chat():
    """
    【功能】主对话循环（Function Calling 版本）
    【流程】
    1. 发消息给 Kimi（带上 tools 参数）
    2. 检查 Kimi 的回复中是否有 tool_calls
       - 如果有 → 执行工具 → 把结果发回给 Kimi → 拿到最终回答
       - 如果没有 → 直接显示 Kimi 的回答
    3. 继续下一轮对话
    """
    print("=" * 50)
    print("🤖 欢迎使用 dateHelp 对话助手（Function Calling 版）！")
    print("💡 你可以问我任何问题，我会调用 Kimi 大模型回答你")
    print("⏰ 当你问时间相关问题时，Kimi 会自动调用 get_current_time 工具")
    print("🚪 输入 exit 或 quit 退出")
    print("=" * 50)
    
    # 对话历史，用于维护上下文
    messages = [
        {
            "role": "system",
            "content": "你是一个 helpful 的中文对话助手。请用简洁友好的中文回答用户的问题。",
        }
    ]
    
    while True:
        print()
        user_input = input("你: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() in ("exit", "quit", "退出", "拜拜"):
            print("👋 再见！")
            break
        
        # 把用户输入加入对话历史
        messages.append({"role": "user", "content": user_input})
        
        # ========== 第1轮请求：发给 Kimi，告诉它有哪些工具 ==========
        print("🤖 Kimi 正在思考...")
        response = ask_kimi(messages, tools=TOOLS)
        assistant_message = response.choices[0].message
        
        # ========== 判断 Kimi 是否想调用工具 ==========
        # tool_calls 是 AI 返回的"我想调用这些工具"的指令列表
        if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
            print(f"🔍 Kimi 决定调用 {len(assistant_message.tool_calls)} 个工具")
            
            # 先把 Kimi 的"调用请求"加入对话历史
            # 这一步很重要！AI 需要知道自己之前"说过要调用工具"
            messages.append({
                "role": "assistant",
                "content": assistant_message.content or "",  # content 可能为空，因为 AI 在等工具结果
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in assistant_message.tool_calls
                ],
            })
            
            # 执行工具，获取结果消息列表
            tool_result_messages = handle_tool_calls(assistant_message)
            
            # 把工具执行结果加入对话历史
            messages.extend(tool_result_messages)
            
            # ========== 第2轮请求：把工具结果发回给 Kimi ==========
            print("🤖 Kimi 正在基于工具结果回答...")
            response = ask_kimi(messages)
            assistant_message = response.choices[0].message
        
        # ========== 显示最终回答 ==========
        reply = assistant_message.content
        print(f"Kimi: {reply}")
        
        # 把 Kimi 的回答加入对话历史，维持上下文
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    chat()
