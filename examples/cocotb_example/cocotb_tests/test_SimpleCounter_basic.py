#coding=utf-8
"""
SimpleCounter Cocotb 基础测试

测试内容：
1. 复位功能测试
2. 使能控制测试
3. 计数递增测试
4. 清零功能测试
5. 溢出检测测试
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer


async def reset_dut(dut, reset_cycles=3):
    """执行复位序列"""
    dut.rst_n.value = 0
    dut.enable.value = 0
    dut.clear.value = 0
    for _ in range(reset_cycles):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    dut._log.info("Reset completed")


@cocotb.test()
async def test_reset(dut):
    """
    测试复位功能

    验证复位后 count=0, overflow=0
    """
    dut._log.info("Starting reset test")

    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    assert int(dut.count.value) == 0, f"count should be 0 after reset, got {dut.count.value}"
    assert dut.overflow.value == 0, f"overflow should be 0 after reset, got {dut.overflow.value}"

    dut._log.info("Reset test PASSED")


@cocotb.test()
async def test_enable_control(dut):
    """
    测试使能控制

    验证 enable=0 时计数不增加，enable=1 时计数递增
    """
    dut._log.info("Starting enable control test")

    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    # enable=0，计数应该不变
    dut.enable.value = 0
    for _ in range(5):
        await RisingEdge(dut.clk)
    assert int(dut.count.value) == 0, f"count should remain 0 when enable=0, got {dut.count.value}"

    # enable=1
    dut.enable.value = 1
    await RisingEdge(dut.clk)  # enable 被 RTL 采样，count 变为 1
    await RisingEdge(dut.clk)  # 采样点
    count_val = int(dut.count.value)
    assert count_val >= 1, f"count should be >= 1 after enabled cycles, got {count_val}"

    dut._log.info("Enable control test PASSED")


@cocotb.test()
async def test_counting(dut):
    """
    测试计数递增

    验证连续计数后 count 值正确递增
    """
    dut._log.info("Starting counting test")

    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    # 启用计数器，等一个沿让 enable 生效
    dut.enable.value = 1
    await RisingEdge(dut.clk)
    start_count = int(dut.count.value)

    # 再等 10 个沿
    for _ in range(10):
        await RisingEdge(dut.clk)

    end_count = int(dut.count.value)
    delta = end_count - start_count
    assert delta == 10, f"count should increment by 10, got delta={delta} (start={start_count}, end={end_count})"

    dut._log.info(f"Counting test PASSED (count={end_count})")


@cocotb.test()
async def test_clear(dut):
    """
    测试同步清零

    验证 clear 可以清零计数器，释放后可以继续计数
    """
    dut._log.info("Starting clear test")

    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    # 先计数几个周期
    dut.enable.value = 1
    for _ in range(5):
        await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    assert int(dut.count.value) > 0, "count should be > 0 before clear"

    # 执行清零
    dut.clear.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    assert int(dut.count.value) == 0, f"count should be 0 after clear, got {dut.count.value}"

    # 释放清零，继续计数
    dut.clear.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    assert int(dut.count.value) >= 1, f"count should resume after clear release, got {dut.count.value}"

    dut._log.info("Clear test PASSED")


@cocotb.test()
async def test_overflow(dut):
    """
    测试溢出检测

    验证 count 从 0xFF 回绕到 0x00，overflow 拉高一个周期
    """
    dut._log.info("Starting overflow test")

    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    # 启用计数，等一沿让 enable 生效
    dut.enable.value = 1
    await RisingEdge(dut.clk)

    # 运行到 count=0xFF（从当前值开始再跑足够的沿）
    start = int(dut.count.value)
    remaining = 255 - start
    for _ in range(remaining):
        await RisingEdge(dut.clk)
    assert int(dut.count.value) == 255, f"count should be 0xFF, got {int(dut.count.value)}"

    # 再一个沿触发溢出
    await RisingEdge(dut.clk)
    assert int(dut.count.value) == 0, f"count should wrap to 0, got {int(dut.count.value)}"
    assert dut.overflow.value == 1, f"overflow should be 1 at wrap, got {dut.overflow.value}"

    # 下一个周期 overflow 应该回到 0
    await RisingEdge(dut.clk)
    assert dut.overflow.value == 0, f"overflow should clear after 1 cycle, got {dut.overflow.value}"

    dut._log.info("Overflow test PASSED")
