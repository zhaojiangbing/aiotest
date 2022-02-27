# -*- coding  :   utf-8 -*-
# @Author     :   zhaojiangbing
# @File       :   async_test.py
# @Software   :   PyCharm


"""实现异步函数测试模块, 支持压力测试."""


import time
import traceback
import asyncio


class AioTestTask(object):
    """测试任务类, 和待测试的函数一一对应."""

    def __init__(self, scheduler, func, is_run=True, total=1, concurrent=1, *args, **kargs):
        """

        :param scheduler: AioTestScheduler, 调度器.
        :param func: 被测试的函数.
        :param is_run: bool, 是否可运行.
        :param total: int, 被运行的总次数.
        :param concurrent: int, 并发数.
        :param args: func位置参数.
        :param kargs: func关键字参数.
        """

        assert total >= concurrent, "total不能比concurrent小"

        self._scheduler = scheduler
        self._func = func
        self._run = is_run
        self._total = total
        self._concurrent = concurrent
        self._args = args
        self._kargs = kargs
        self._total_time = 0  # 记录task运行的总时间
        self._concurrent_times = []  # 记录每一轮并发的时间
        self._futures = []  # 记录每一次运行产生的future
        self._fail = 0  # 记录运行total次中失败的次数
        self.loop = self._scheduler.loop

    def create_run_futures(self, is_run=True):
        """创建和运行future.

        :param is_run: bool, True 创建并运行, False 只创建.
        :return:
        """

        total = self._total
        while total > 0:
            futures = []

            if total > self._concurrent:
                conc = self._concurrent  # conc为每一轮的并发数
            else:
                conc = total

            for i in range(conc):
                future = asyncio.ensure_future(self.check_exception(self._func, *self._args, **self._kargs))  # 创建future
                futures.append(future)

            total = total - self._concurrent

            if futures and is_run:
                start_time = time.time()
                self.loop.run_until_complete(asyncio.gather(*futures))  # 运行futures列表
                process_time = time.time() - start_time
                self._concurrent_times.append(process_time)  # 保存每一轮时间
                self._total_time += process_time  # 求总时间

            self._futures += futures

    async def check_exception(self, func, *args, **kargs):
        """检查异常, 并统计异常函数个数.

        :param func: 被检查的函数.
        :param args: func函数的位置参数.
        :param kargs: func函数的关键字参数.
        :return:
        """

        try:
            await func(*args, **kargs)
        except:
            self._fail += 1  # 统计失败个数
            if self._scheduler._is_print_exc:
                print("----------------------num: {}----------------------\n{}{}".
                      format(self._scheduler._num, traceback.format_exc(), "\n"))
        finally:
            self._scheduler._num += 1  # 统计调度器第几次调用

    def print_report(self):
        result = "succeeds：{}, fails: {}, total_time：{}, concurrent_times：{}".format(
            self._total - self._fail, self._fail, self._total_time, self._concurrent_times)
        print(result)


class AioTestScheduler(object):
    """异步测试调度器."""

    def __init__(self, loop=None):
        self._is_all = False
        self._num = 1  # 记录调度函数的总次数
        self._tasks = []  # 存放创建的 AioTestTask 实例(task)
        self._is_print_exc = True  # 当被测试的函数抛出异常时, 是否打印
        self._is_print_report = True  # 是否打印测试结果
        self.loop = loop or asyncio.get_event_loop()
        self._total_time = 0

    def __call__(self, total=1, concurrent=1, is_run=True, *args, **kwargs):
        """把测试函数装饰为task.

        :param total: int, 运行的总次数.
        :param concurrent: int, 运行的并发数.
        :param is_run: bool, 是否可运行.
        :param args: 被装饰函数的位置参数.
        :param kwargs: 被装饰函数的关键字参数.
        :return:
        """

        def inner(func):
            """
            :param func: 待测试的函数.
            :return:
            """

            task = AioTestTask(self, func, is_run, total, concurrent, *args, **kwargs)  # 封装为task
            self._tasks.append(task)  # 把task存放到调度器
        return inner

    def _run_task(self):
        """所有task的futures依次运行, 同时每个task的futures根据并发数批次运行."""

        for task in self._tasks:
            if task._run:
                task.create_run_futures()

    def _run_all_task(self):
        """所有task的future同时运行."""

        futures = []
        for task in self._tasks:
            if task._run:  # 是否可运行
                task.create_run_futures(is_run=False)
            futures += task._futures
        start_time = time.time()
        self.loop.run_until_complete(asyncio.gather(*futures))  # 运行任务列表
        self._total_time = time.time() - start_time

    def print_report(self):
        """打印测试报告."""

        for task in self._tasks:
            if task._run:
                print("----------------------{} report: \n".format(task._func.__name__))
                if self._is_all:
                    print("succeeds：{}, fails: {}, total_time: {}".
                          format(task._total - task._fail, task._fail, self._total_time))
                else:
                    task.print_report()

    def run(self, is_print_report=True, is_print_exc=True, is_all=False):
        """运行调度器.

        :param is_print_report: bool, 是否打印测试结果.
        :param is_print_exc: bool, 当被测试的函数抛出异常时, 是否打印.
        :param is_all: bool, 是否同时运行所有task.
        :return:
        """

        self._is_print_report = is_print_report
        self._is_print_exc = is_print_exc
        self._is_all = is_all

        if self._is_all:
            self._run_all_task()  # 所有task的future同时运行
        else:
            self._run_task()  # 所有task的future依次运行

        if self._is_print_report:  # 是否打印结果
            self.print_report()