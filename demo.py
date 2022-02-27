# -*- coding  :   utf-8 -*-
# @Author     :   zhaojiangbing
# @File       :   demo.py
# @Software   :   PyCharm


import asyncio

from aiotest import AioTestScheduler

atsch = AioTestScheduler()


@atsch(total=4, concurrent=2, is_run=True, a=3, b=4)  # total请求的总次数， concurrent并发数, is_run是否可运行, a, b为装饰函数的参数
async def test_one(a, b):
    await asyncio.sleep(2)
    assert a > b, "我是断言"


@atsch(total=4, concurrent=2, is_run=True, a=3, b=4)
async def test_two(a, b):
    await asyncio.sleep(2)
    raise Exception("我是异常")


if __name__ == '__main__':
    atsch.run(is_print_report=True, is_print_exc=True, is_all=False)

    # is_print_report是否打印测试报告, is_print_exc是否打印异常, is_all是否运行所有被atsch装饰的函数
