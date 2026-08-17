# -*- coding: utf-8 -*-
"""
【文件说明】
这是"文章拾光"网站的后端程序，用 Flask 框架搭建。
主要功能：
1. 提供一个网页界面
2. 接收用户输入的微信文章链接
3. 抓取文章内容
4. 调用 Kimi AI 进行概括
5. 返回原文和概括结果给网页显示

【什么是 Flask？】
Flask 是一个用 Python 写的 Web 框架，用来搭建网站后端。
简单说：它负责接收浏览器发来的请求，处理完后再把结果返回给浏览器。
"""

# ==================== 第1步：导入需要的工具 ====================
# Python 有很多"工具箱"（也叫"模块"或"库"），我们要先把需要用到的导入进来

import os      # os：操作系统相关，比如读写文件、操作路径等
import re      # re：正则表达式，用来处理文本匹配（本项目其实没用到，但先保留）
from datetime import datetime  # datetime：获取当前日期时间

# Flask 相关：这是搭建网站的核心工具
# Flask：创建网站应用
# request：获取浏览器发来的请求数据
# jsonify：把 Python 数据转成 JSON 格式（浏览器能懂的格式）
# render_template：渲染 HTML 模板（就是把网页模板和数据结合起来）
from flask import Flask, request, jsonify, render_template

# requests：用来发送网络请求，比如"打开一个网页链接并获取内容"
import requests

# BeautifulSoup：解析 HTML 网页，从中提取我们需要的信息
# 比如从微信文章网页里，提取标题、作者、正文
from bs4 import BeautifulSoup


# ==================== 第2步：创建 Flask 应用 ====================
# 用 Flask() 创建一个"应用对象"，可以理解为"创建了一个网站"
# __name__ 是一个特殊变量，表示当前文件的名字，Flask 用它来找模板文件和静态文件的位置
app = Flask(__name__)


# ==================== 第3步：配置常量 ====================
# 常量是一些固定不变的值，用大写字母命名是一种约定
# 这样以后如果要改地址或模型名，只需要改这一处

# Kimi API 的基础地址，所有请求都发给这个地址
KIMI_BASE_URL = "https://api.moonshot.cn/v1"

# 使用的 AI 模型名称，kimi-k2.6 是 Kimi 的一个较快的模型
KIMI_MODEL = "kimi-k2.6"


# ==================== 第4步：定义"抓取微信文章"的函数 ====================
def fetch_wechat_article(url):
    """
    【功能】抓取一篇微信公众文章的内容
    【参数】url：文章的网址链接（字符串）
    【返回】一个元组：(标题, 作者, 正文内容)
    
    【原理】
    微信文章其实就是个网页，我们用 requests 去"访问"这个网页，
    然后用 BeautifulSoup 去"解析"网页的 HTML 代码，从中提取标题、作者、正文。
    """
    
    # 【请求头 headers】
    # 很多网站会检查"你是谁"，如果看起来不像正常浏览器，就会拒绝访问。
    # 所以我们模拟一个真实的浏览器，告诉对方："我是 Chrome 浏览器"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9",  # 告诉对方：我优先看中文内容
    }
    
    # 【发送请求】
    # requests.get() 就是"用 GET 方式打开这个网址"
    # headers=headers：带上我们伪装成浏览器的身份
    # timeout=15：最多等 15 秒，超过就报错，防止一直卡住
    resp = requests.get(url, headers=headers, timeout=15)
    
    # 【检查请求是否成功】
    # raise_for_status() 的意思是：如果返回的状态码不是 200（成功），就抛出异常
    # 比如 404 就是网页不存在，500 是服务器内部错误
    resp.raise_for_status()
    
    # 【设置编码】
    # 微信网页用的是 UTF-8 编码（中文），如果不设置，可能会显示乱码
    resp.encoding = "utf-8"
    
    # 【解析网页 HTML】
    # BeautifulSoup 把网页的 HTML 代码解析成一个"树状结构"
    # "html.parser" 是 Python 内置的 HTML 解析器
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # -------------------- 提取标题 --------------------
    # 微信文章的标题通常在 <h1 class="rich_media_title"> 标签里
    # 有时候也会在 <meta property="og:title"> 里（这是网页的元信息）
    # soup.find() 就是"找到第一个匹配的标签"
    title_tag = soup.find("h1", class_="rich_media_title") or soup.find(
        "meta", property="og:title"
    )
    
    # 从标签中提取文字
    # 如果是 <meta> 标签，内容在 content 属性里
    # 如果是普通标签，用 get_text() 获取标签里的文字
    if title_tag and title_tag.name == "meta":
        title = title_tag.get("content", "").strip()  # .strip() 去掉首尾空格
    elif title_tag:
        title = title_tag.get_text(strip=True)
    else:
        title = "未获取到标题"  # 如果找不到，给个默认值
    
    # -------------------- 提取作者/公众号名称 --------------------
    # 作者通常在 <a id="js_name"> 或 <span class="rich_media_meta_nickname"> 里
    author_tag = soup.find("a", id="js_name") or soup.find("span", class_="rich_media_meta_nickname")
    if author_tag:
        author = author_tag.get_text(strip=True)
    else:
        author = "未获取到作者"
    
    # -------------------- 提取正文内容 --------------------
    # 微信文章正文在 <div id="js_content"> 标签里
    content_tag = soup.find("div", id="js_content")
    
    if content_tag:
        # 正文中包含很多段落、标题、列表等
        # find_all(["p", "h1", ...]) 找到所有段落、各级标题、列表项、引用块
        lines = []
        for e in content_tag.find_all(["p", "h1", "h2", "h3", "h4", "li", "blockquote"]):
            text = e.get_text(strip=True)  # 获取纯文字，去掉多余空格
            if text:  # 如果文字不为空，才加入列表
                lines.append(text)
        
        # 如果上面的方法没找到内容，就用备选方案：直接取所有文字
        if not lines:
            lines = [l for l in content_tag.get_text("\n").splitlines() if l.strip()]
        
        # 【去重】
        # 微信文章有时候会出现重复的段落（比如因为排版问题）
        # 用 set 来记录已经见过的段落，跳过重复的
        seen = set()  # set 是一种"集合"，里面不能放重复的东西
        unique_lines = []
        for line in lines:
            if line not in seen:
                seen.add(line)  # 把新段落加入集合
                unique_lines.append(line)  # 同时加入结果列表
        
        # 用 "\n\n"（两个换行）把段落连接起来，形成完整正文
        content = "\n\n".join(unique_lines)
    else:
        content = ""  # 如果没找到正文，返回空字符串
    
    # 返回三个值：标题、作者、正文
    return title, author, content


# ==================== 第5步：定义"调用 Kimi AI 概括"的函数 ====================
def summarize(api_key, title, content):
    """
    【功能】调用 Kimi API 对文章进行概括
    【参数】
        api_key：你的 Kimi API 密钥（字符串）
        title：文章标题
        content：文章正文
    【返回】概括结果（字符串）
    
    【什么是 API？】
    API 就像"服务员"，你发一个请求（点菜），对方处理完后返回结果（上菜）。
    这里我们向 Kimi 的服务器发请求，让它帮我们概括文章。
    """
    
    # 【截断过长的内容】
    # Kimi API 有字数限制，如果文章太长，只取前 6000 个字符
    # 三目运算符：条件 ? 结果A : 结果B
    # 如果 content 长度超过 6000，就截断并加上提示；否则保持不变
    content = content[:6000] + "\n……（内容过长，已截断）" if len(content) > 6000 else content
    
    # 【构建请求数据】
    # payload 就是"要发给 Kimi 的数据包"
    # 它是一个字典（dict），类似 JavaScript 的对象
    payload = {
        "model": KIMI_MODEL,  # 使用哪个 AI 模型
        "messages": [  # 对话消息列表
            {
                "role": "system",  # system：设定 AI 的身份和行为
                "content": (
                    "你是一个专业的文章概括助手。请用简洁清晰的中文概括用户提供的文章，"
                    "输出格式：\n1. 一句话总结\n2. 核心要点（3~7 条，用列表）\n3. 简短点评"
                ),
            },
            {
                "role": "user",  # user：用户说的话
                "content": f"请概括以下文章：\n\n标题：{title}\n\n正文：\n{content}",
                # f"..." 是 f-string，可以在字符串中嵌入变量
            },
        ],
        "temperature": 1,  # temperature 控制 AI 的"创造性"，1 是标准值
    }
    
    # 【发送 POST 请求】
    # POST 是 HTTP 请求的一种方式，用来"提交数据"
    # requests.post() 向 Kimi 的服务器发送请求
    resp = requests.post(
        f"{KIMI_BASE_URL}/chat/completions",  # 完整的 API 地址
        headers={
            "Authorization": f"Bearer {api_key}",  # Bearer Token 认证方式
            "Content-Type": "application/json",  # 告诉对方：我发的是 JSON 数据
        },
        json=payload,  # 自动把 payload 字典转成 JSON 格式发送
        timeout=120,  # 最多等 120 秒（AI 思考需要时间）
    )
    
    # 【检查响应状态】
    # 如果状态码不是 200，说明出错了
    if resp.status_code != 200:
        # 抛出异常，让上层调用者处理
        # resp.text[:300] 只显示前 300 个字符的错误信息，避免太长
        raise RuntimeError(f"HTTP {resp.status_code} - {resp.text[:300]}")
    
    # 【解析返回结果】
    # resp.json() 把返回的 JSON 字符串转成 Python 字典
    # 然后按照 Kimi API 的返回结构，一步步提取出概括内容
    return resp.json()["choices"][0]["message"]["content"].strip()


# ==================== 第6步：定义网页路由 ====================
# 【什么是路由？】
# 路由就是"网址和处理函数的对应关系"
# 比如用户访问 http://localhost:5001/，Flask 就知道要执行哪个函数

# 【路由1：首页】
# @app.route("/") 是一个"装饰器"，它把下面的函数和 "/" 这个网址绑定
# 当用户访问网站根目录时，就执行 index() 函数
@app.route("/")
def index():
    """
    【功能】返回首页
    【原理】render_template("index.html") 会去 templates/ 文件夹里找 index.html
           然后把 HTML 内容返回给浏览器，浏览器就会显示出网页
    """
    return render_template("index.html")


# 【路由2：处理抓取请求】
# methods=["POST"] 表示这个路由只接受 POST 请求
# POST 请求通常用来"提交数据"，比如用户填了表单后点击提交
@app.route("/api/fetch", methods=["POST"])
def api_fetch():
    """
    【功能】接收前端传来的链接和 API Key，抓取文章并概括，返回结果
    【返回】JSON 格式的数据，包含标题、作者、原文、概括
    """
    
    # 【获取前端传来的数据】
    # request.json 把浏览器发来的 JSON 数据转成 Python 字典
    # or {} 表示如果 request.json 为空，就用空字典代替
    data = request.json or {}
    
    # .get("url", "") 从字典里取 "url" 这个键的值，如果没有就返回空字符串
    # .strip() 去掉首尾空格（防止用户不小心多打了空格）
    url = data.get("url", "").strip()
    api_key = data.get("apiKey", "").strip()
    
    # 【参数校验】
    # 如果用户没填链接，返回错误信息
    # jsonify() 把字典转成 JSON 格式
    # 后面的 400 是 HTTP 状态码，表示"请求参数错误"
    if not url:
        return jsonify({"error": "请输入文章链接"}), 400
    
    # 如果没填 API Key
    if not api_key:
        return jsonify({"error": "请输入 Kimi API Key"}), 400
    
    # 检查 API Key 格式，Kimi 的 Key 都以 "sk-" 开头
    if not api_key.startswith("sk-"):
        return jsonify({"error": "API Key 格式异常，应以 sk- 开头，请检查是否输入完整"}), 400
    
    # 【抓取文章】
    # try...except 是异常处理，防止程序因为报错而崩溃
    try:
        title, author, content = fetch_wechat_article(url)
    except Exception as e:
        # 500 是"服务器内部错误"
        return jsonify({"error": f"抓取失败：{e}"}), 500
    
    # 检查是否成功抓到正文
    # 如果正文为空或太短（少于50字），说明抓取失败
    if not content or len(content) < 50:
        return jsonify({"error": "未能成功抓取文章正文，请检查链接是否有效"}), 400
    
    # 【调用 Kimi 概括】
    try:
        summary = summarize(api_key, title, content)
    except Exception as e:
        return jsonify({"error": f"Kimi 概括失败：{e}"}), 500
    
    # 【返回成功结果】
    # 把所有数据打包成字典，转成 JSON 返回给前端
    return jsonify({
        "title": title,       # 文章标题
        "author": author,     # 作者/公众号
        "url": url,           # 原文链接
        "original": content,  # 原文内容
        "summary": summary,   # Kimi 概括
    })


# ==================== 第7步：启动服务 ====================
# 【if __name__ == "__main__" 是什么意思？】
# 这是一个 Python 的惯用写法。
# 当直接运行这个文件时，__name__ 的值是 "__main__"，条件成立，执行下面的代码。
# 当这个文件被其他文件导入时，__name__ 的值是文件名，条件不成立，不执行。
# 这样可以避免被导入时意外启动服务器。

if __name__ == "__main__":
    # 【app.run() 启动 Flask 服务器】
    # host="0.0.0.0"：允许任何 IP 访问（不仅限于本机）
    # port=5001：使用 5001 端口
    # debug=True：开启调试模式，代码改了会自动重启，报错会显示详细信息
    # ⚠️ debug=True 只适合开发，正式上线要关掉！
    app.run(host="0.0.0.0", port=5001, debug=True)
