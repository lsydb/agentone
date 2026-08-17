# -*- coding: utf-8 -*-
"""
mathHelp.py — 动态数学函数对话助手

【功能】遇到数学问题时：
1. 先查看 math_tools.py 中是否有现成的函数
2. 有 → 直接执行返回结果
3. 没有 → 大模型生成新函数代码 → 写入文件 → 执行

没有函数
轮次1: list_math_functions()  → 查有哪些函数
轮次2: create_math_function() → 生成 sine 代码
轮次3: execute_math_function() → 执行 sine(100)
轮次4: 直接回答 → "100的正弦值是-0.5064"

有现成函数
轮次1: list_math_functions()  → 查有哪些函数
轮次2: execute_math_function() → 执行 square(8) → 返回 64
轮次3: 直接回答 → "8的平方是64"

【使用方式】
python3 mathHelp.py
"""

import os
import json
import inspect
import importlib
from openai import OpenAI

# 动态加载数学函数模块
MATH_TOOLS_PATH = os.path.join(os.path.dirname(__file__), "math_tools.py")

# 如果文件不存在，创建空文件
if not os.path.exists(MATH_TOOLS_PATH):
    with open(MATH_TOOLS_PATH, "w", encoding="utf-8") as f:
        f.write('# -*- coding: utf-8 -*-\n"""\nmath_tools.py — 动态数学函数库\n"""\n')

import math_tools as mt


# ==================== 配置 Kimi API ====================
client = OpenAI(
    api_key=os.getenv("KIMI_API_KEY"),
    base_url="https://api.moonshot.cn/v1",
)
MODEL = "kimi-k2.6"


# ==================== 工具函数 ====================
def list_math_functions():
    """列出 math_tools.py 中所有可用的数学函数"""
    items = []
    for name, obj in inspect.getmembers(mt):
        if inspect.isfunction(obj) and not name.startswith('_'):
            doc = inspect.getdoc(obj) or "无描述"
            try:
                sig = str(inspect.signature(obj))
            except:
                sig = "()"
            items.append(f"- {name}{sig}: {doc}")
    return "\n".join(items) if items else "暂无数学函数"


def execute_math_function(function_name, args):
    """执行 math_tools.py 中已存在的数学函数"""
    if not hasattr(mt, function_name):
        available = list_math_functions()
        return f"❌ 函数 '{function_name}' 不存在。\n\n当前可用函数：\n{available}"
    func = getattr(mt, function_name)
    try:
        result = func(**args)
        return f"结果：{result}"
    except Exception as e:
        return f"❌ 计算出错：{e}"


def create_math_function(function_name, code):
    """在 math_tools.py 中创建一个新的数学函数"""
    if hasattr(mt, function_name):
        return f"ℹ️ 函数 '{function_name}' 已存在，直接调用即可。"
    
    with open(MATH_TOOLS_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n\n{code}\n")
    
    importlib.reload(mt)
    
    if hasattr(mt, function_name):
        return f"✅ 函数 '{function_name}' 已创建并加载成功。"
    return f"⚠️ 函数已写入文件但加载失败，请检查代码格式。"


# ==================== 工具定义（告诉 AI 有哪些工具）====================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_math_functions",
            "description": "列出 math_tools.py 中所有可用的数学函数。当用户提出任何数学问题时，必须先调用此工具查看是否有现成函数可用。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_math_function",
            "description": "执行 math_tools.py 中已存在的数学函数。必须先调用 list_math_functions 确认函数存在后再执行。",
            "parameters": {
                "type": "object",
                "properties": {
                    "function_name": {
                        "type": "string",
                        "description": "要执行的函数名称，如 'square', 'factorial'",
                    },
                    "args": {
                        "type": "object",
                        "description": "函数的关键字参数字典。例如：{'x': 5}, {'n': 10}",
                    },
                },
                "required": ["function_name", "args"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_math_function",
            "description": "在 math_tools.py 中创建一个新的数学函数。当 list_math_functions 返回的列表中没有合适的函数时使用。必须提供完整的 Python 函数代码（包含 def 行、参数和返回值）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "function_name": {
                        "type": "string",
                        "description": "新函数的名称，如 'sqrt', 'double'",
                    },
                    "code": {
                        "type": "string",
                        "description": "完整的函数代码。示例：'def double(x):\\n    \"\"\"求一个数的两倍\"\"\"\\n    return x * 2\\n'",
                    },
                },
                "required": ["function_name", "code"],
            },
        },
    },
]

AVAILABLE_TOOLS = {
    "list_math_functions": list_math_functions,
    "execute_math_function": execute_math_function,
    "create_math_function": create_math_function,
}


# ==================== 核心函数 ====================
def ask_kimi(messages, tools=None):
    """调用 Kimi 大模型"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
        )
        return response
    except Exception as e:
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
    """处理 AI 返回的工具调用请求"""
    tool_results = []
    
    for tool_call in response_message.tool_calls:
        tool_name = tool_call.function.name
        
        try:
            tool_args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            tool_args = {}
        
        print(f"🔧 Kimi 要求调用工具：{tool_name}，参数：{tool_args}")
        
        if tool_name in AVAILABLE_TOOLS:
            tool_func = AVAILABLE_TOOLS[tool_name]
            try:
                result = tool_func(**tool_args)
                print(f"✅ 工具执行结果：{result}")
            except Exception as e:
                result = f"工具执行出错：{e}"
                print(f"❌ {result}")
        else:
            result = f"错误：未找到工具 {tool_name}"
            print(f"❌ {result}")
        
        tool_results.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_name,
            "content": result,
        })
    
    return tool_results


def chat():
    """主对话循环 —— 支持多轮工具调用"""
    print("=" * 50)
    print("🔢 欢迎使用 mathHelp 数学对话助手！")
    print("💡 我会自动查看数学函数库，有则执行，无则创建")
    print("🚪 输入 exit 或 quit 退出")
    print("=" * 50)
    
    messages = [
        {
            "role": "system",
            "content": (
                "你是一个数学计算助手。\n\n"
                "【处理规则】\n"
                "1. 用户提出数学问题时，先调用 list_math_functions 查看有哪些函数可用\n"
                "2. 如果有合适的函数，调用 execute_math_function 执行并回答结果\n"
                "3. 如果没有合适的函数，调用 create_math_function 生成新函数代码，然后调用 execute_math_function 执行\n"
                "4. 向用户展示计算过程和结果\n\n"
                "【生成函数的要求】\n"
                "- 函数名简洁英文，参数清晰\n"
                "- 包含 docstring 说明功能\n"
                "- 代码必须是合法的 Python 语法"
            ),
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
        
        messages.append({"role": "user", "content": user_input})
        
        # 支持多轮工具调用（最多5轮防止无限循环）
        max_rounds = 5
        for round_num in range(1, max_rounds + 1):
            print("🤖 Kimi 正在思考...")
            response = ask_kimi(messages, tools=TOOLS)
            assistant_message = response.choices[0].message

            # ===== 打印 LLM 原始返回内容 =====
            print(f"\n{'─' * 40}")
            print(f"【第 {round_num} 轮 LLM 原始返回】")
            print(f"content: {assistant_message.content!r}")
            if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                print(f"tool_calls:")
                for tc in assistant_message.tool_calls:
                    print(f"  - name={tc.function.name}, arguments={tc.function.arguments}")
            else:
                print("tool_calls: None")
            print(f"{'─' * 40}\n")
            # ================================

            # 没有 tool_calls，直接显示回答
            if not hasattr(assistant_message, 'tool_calls') or not assistant_message.tool_calls:
                reply = assistant_message.content
                print(f"Kimi: {reply}")
                messages.append({"role": "assistant", "content": reply})
                break
            
            # 有 tool_calls，执行工具后继续循环
            print(f"🔍 Kimi 决定调用 {len(assistant_message.tool_calls)} 个工具")
            
            messages.append({
                "role": "assistant",
                "content": assistant_message.content or "",
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
            
            tool_result_messages = handle_tool_calls(assistant_message)
            messages.extend(tool_result_messages)
            
        else:
            print("⚠️ 工具调用次数过多，强制结束。")
            messages.append({
                "role": "assistant",
                "content": "抱歉，处理这个问题需要太多步骤了。"
            })


if __name__ == "__main__":
    chat()
