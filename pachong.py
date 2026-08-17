# -*- coding: utf-8 -*-
"""
微信公众号文章爬虫 + Kimi 大模型概括
功能：
1. 运行时手动输入文章 URL
2. 抓取文章标题、公众号、正文
3. 调用 Kimi API 对正文进行概括
4. 原文和概括分别保存为两个文件
"""

import os
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# Kimi API 配置
KIMI_BASE_URL = "https://api.moonshot.cn/v1"
KIMI_API_URL = f"{KIMI_BASE_URL}/chat/completions"
KIMI_MODEL = "kimi-k2.6"  # Kimi K2.6 模型（更快）


def fetch_wechat_article(url):
    """抓取微信公众号文章的标题、作者和正文内容"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    resp.encoding = "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")

    # 标题
    title_tag = soup.find("h1", class_="rich_media_title") or soup.find(
        "meta", property="og:title"
    )
    if title_tag is None:
        title = "未获取到标题"
    elif title_tag.name == "meta":
        title = title_tag.get("content", "").strip()
    else:
        title = title_tag.get_text(strip=True)

    # 作者/公众号名称
    author_tag = soup.find("a", id="js_name") or soup.find(
        "span", class_="rich_media_meta_nickname"
    )
    author = author_tag.get_text(strip=True) if author_tag else "未获取到作者"

    # 正文
    content_tag = soup.find("div", id="js_content")
    if content_tag:
        lines = []
        for elem in content_tag.find_all(["p", "h1", "h2", "h3", "h4", "li", "blockquote"]):
            text = elem.get_text(strip=True)
            if text:
                lines.append(text)
        if not lines:
            lines = [line for line in content_tag.get_text("\n").splitlines() if line.strip()]
        # 去重（微信文章常出现重复段落），保持顺序
        seen = set()
        unique_lines = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                unique_lines.append(line)
        content = "\n\n".join(unique_lines)
    else:
        content = "未获取到正文（可能需要微信环境访问）"

    return title, author, content


def summarize_with_kimi(api_key, title, content):
    """调用 Kimi API 对文章内容进行概括"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # 简单截断，避免超出上下文限制（8k 模型保守截断）
    max_chars = 6000
    if len(content) > max_chars:
        content = content[:max_chars] + "\n……（内容过长，已截断）"

    payload = {
        "model": KIMI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一个专业的文章概括助手。请用简洁清晰的中文概括用户提供的文章，"
                    "输出格式：\n1. 一句话总结\n2. 核心要点（3~7 条，用列表）\n3. 简短点评"
                ),
            },
            {
                "role": "user",
                "content": f"请概括以下文章：\n\n标题：{title}\n\n正文：\n{content}",
            },
        ],
        "temperature": 1,  # kimi-k3 模型仅允许 temperature=1
    }

    resp = requests.post(KIMI_API_URL, headers=headers, json=payload, timeout=120)
    if resp.status_code != 200:
        # 打印 Kimi 返回的详细错误信息，方便排查
        raise RuntimeError(f"HTTP {resp.status_code} - {resp.text[:300]}")
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def safe_filename(name):
    """将标题转为安全的文件名"""
    name = re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("_")
    return name[:50] if name else "article"


def main():
    print("=" * 50)
    print("微信公众号文章爬虫 + Kimi 智能概括")
    print("=" * 50)

    # 1. 手动输入 URL（自动清理粘贴时混入的空格、换行、退格等杂字符）
    raw_url = input("\n请输入文章链接：")
    url = re.sub(r"\s+", "", raw_url)  # 去除所有空白字符
    if not url:
        print("❌ 未输入链接，程序退出")
        return
    if url != raw_url.strip():
        print(f"⚠️ 检测到链接中混入空白字符，已自动清理")

    # 2. 抓取文章
    print(f"\n正在抓取：{url}\n{'-' * 50}")
    try:
        title, author, content = fetch_wechat_article(url)
    except Exception as e:
        print(f"❌ 抓取失败：{e}")
        return

    print(f"标题：{title}")
    print(f"公众号：{author}")
    print(f"正文长度：{len(content)} 字")

    # 抓取结果校验：正文太短说明抓取失败，不继续浪费 API 调用
    if content.startswith("未获取到") or len(content) < 50:
        print("\n❌ 未能成功抓取文章正文，请检查链接是否完整（特别是长链接容易在终端被截断）。")
        print("💡 提示：粘贴长链接时如果终端显示换行/空格，请用英文引号包住链接再粘贴。")
        return

    # 3. 手动输入 Kimi API Key（明文显示输入）
    print()
    api_key = input("请输入 Kimi API Key：").strip()
    if not api_key:
        print("❌ 未输入 API Key，程序退出")
        return

    # 4. 调用 Kimi 概括
    print("\n正在调用 Kimi API 进行概括，请稍候……")
    try:
        summary = summarize_with_kimi(api_key, title, content)
    except Exception as e:
        print(f"❌ Kimi API 调用失败：{e}")
        # 即使概括失败，也保存原文
        summary = None

    # 5. 分两个文件存储：原文 + 概括
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = safe_filename(title)
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    original_file = os.path.join(output_dir, f"{timestamp}_{base_name}_原文.txt")
    summary_file = os.path.join(output_dir, f"{timestamp}_{base_name}_概括.txt")

    with open(original_file, "w", encoding="utf-8") as f:
        f.write(f"标题：{title}\n公众号：{author}\n链接：{url}\n{'=' * 50}\n\n{content}")
    print(f"\n✅ 原文已保存：{original_file}")

    if summary:
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(f"标题：{title}\n公众号：{author}\n链接：{url}\n{'=' * 50}\n\n【Kimi 概括】\n\n{summary}")
        print(f"✅ 概括已保存：{summary_file}")
        print(f"\n{'=' * 50}\n【Kimi 概括预览】\n\n{summary}")


if __name__ == "__main__":
    main()
