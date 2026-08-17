# -*- coding: utf-8 -*-
"""
math_tools.py — 动态数学函数库

【功能】由 AI 根据需求自动生成和扩展的数学函数集合
【使用方式】
1. dateHelp.py 会自动检查此文件中的函数
2. 当用户提出新的数学需求时，AI 会在此文件中添加新函数
3. 已存在的函数会被直接复用，不会重复创建
"""


def square(x):
    """求一个数的平方"""
    return x ** 2


def cube(x):
    """求一个数的立方"""
    return x ** 3


def factorial(n):
    """求一个正整数的阶乘"""
    if n < 0:
        raise ValueError("n 必须是非负整数")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def fibonacci(n):
    """求第 n 个斐波那契数"""
    if n <= 0:
        return 0
    if n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


import math

def sine(x):
    """求一个数（弧度制）的正弦值"""
    return math.sin(x)



def absolute(x):
    """求一个数的绝对值"""
    if x < 0:
        return -x
    return x

