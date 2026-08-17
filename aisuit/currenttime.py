"""
currenttime.py

【功能】返回当前系统时间的工具模块
【用途】当对话中检测到用户问"现在几点"时，
      dateHelp.py 会调用此工具获取当前时间，
      再传给大模型让它基于准确时间回答。
"""

from datetime import datetime  # 导入 datetime 模块，用于获取当前日期和时间


def get_current_time():
    """
    【功能】获取并格式化当前系统时间
    【返回】字符串，格式为 "2025年08月09日 19:35:08"
    
    【说明】
    datetime.now() 会返回当前时间的一个"时间对象"
    strftime() 是"string format time"的缩写，把 time 对象格式化成字符串
    
    %Y = 4位年份（如 2025）
    %m = 2位月份（01-12）
    %d = 2位日期（01-31）
    %H = 24小时制小时（00-23）
    %M = 分钟（00-59）
    %S = 秒（00-59）
    """
    now = datetime.now()  # 获取当前的日期和时间
    return now.strftime("%Y年%m月%d日 %H:%M:%S")


def get_current_hour_minute():
    """
    【功能】只返回当前几点几分（用于简单问答）
    【返回】字符串，如 "19点35分"
    """
    now = datetime.now()
    return now.strftime("%H点%M分")


# ============ 直接运行此文件时的测试代码 ============
if __name__ == "__main__":
    print("【currenttime.py 测试】")
    print(f"完整时间: {get_current_time()}")
    print(f"简单时间: {get_current_hour_minute()}")
