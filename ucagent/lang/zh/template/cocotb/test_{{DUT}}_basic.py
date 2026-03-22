#coding=utf-8
"""
{{DUT}} Cocotb 基础测试模板

本文件提供了 {{DUT}} 模块的 cocotb 测试基础框架，包括：
- 时钟生成
- 复位序列
- 基本接口操作 handle

Agent 需要根据实际 DUT 的接口信号填充测试逻辑。
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer
from cocotb.binary import BinaryValue
from cocotb.handle import LogicObject, LogicArrayObject


# ============================================================================
# 通用工具函数（Agent 可根据需要修改）
# ============================================================================

async def reset_dut(dut, reset_signal_name="rst_n", reset_cycles=3):
    """
    执行 DUT 复位序列
    
    Args:
        dut: DUT 句柄
        reset_signal_name: 复位信号名称（低电平有效）
        reset_cycles: 保持复位的时钟周期数
    """
    # 检查复位信号是否存在
    if not hasattr(dut, reset_signal_name):
        dut._log.warning(f"Reset signal '{reset_signal_name}' not found in DUT")
        return
    
    reset_sig = getattr(dut, reset_signal_name)
    
    # 拉低复位（复位有效）
    reset_sig.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    
    # 释放复位
    reset_sig.value = 1
    for _ in range(reset_cycles):
        await RisingEdge(dut.clk)
    
    dut._log.info("Reset sequence completed")


async def wait_cycles(dut, n, clk_signal="clk"):
    """等待 N 个时钟周期"""
    clk = getattr(dut, clk_signal)
    for _ in range(n):
        await RisingEdge(clk)


# ============================================================================
# 测试用例模板（Agent 需要填充具体测试逻辑）
# ============================================================================

@cocotb.test()
async def test_{{DUT|lower}}_reset(dut):
    """
    测试 {{DUT}} 复位功能
    
    验证内容：
    1. 复位后所有输出应该回到初始状态
    2. 复位期间输出应该保持默认值
    3. 复位释放后模块应该能够正常工作
    
    Agent 任务：
    - 根据 DUT 的实际复位行为完善断言
    - 检查复位后所有寄存器的初始值
    """
    dut._log.info("Starting reset test")
    
    # 启动时钟（假设时钟频率为 100MHz，周期 10ns）
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())
    
    # 执行复位
    await reset_dut(dut)
    
    # TODO: Agent 需要在此添加复位后的检查
    # 例如：
    # assert dut.some_output.value == 0, "Output should be 0 after reset"
    # assert dut.ready.value == 1, "Ready should be high after reset"
    
    dut._log.info("Reset test passed")


@cocotb.test()
async def test_{{DUT|lower}}_basic_operation(dut):
    """
    测试 {{DUT}} 基本操作功能
    
    验证内容：
    1. 基本数据通路功能
    2. 控制信号响应
    3. 状态机基本转换
    
    Agent 任务：
    - 根据 DUT 的功能定义输入激励
    - 检查输出响应是否符合预期
    - 使用 mark_function 标记功能覆盖率（如果使用 unity_test 框架）
    """
    dut._log.info("Starting basic operation test")
    
    # 启动时钟
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())
    
    # 复位
    await reset_dut(dut)
    
    # TODO: Agent 需要在此添加基本功能测试
    # 示例模板：
    # 
    # # 设置输入
    # dut.io_valid.value = 1
    # dut.io_data.value = 0x1234
    # 
    # # 等待一个周期
    # await RisingEdge(dut.clk)
    # 
    # # 检查输出
    # assert dut.io_ready.value == 1, "Module should be ready"
    # assert dut.result.value == expected_value, "Output mismatch"
    
    dut._log.info("Basic operation test passed")


@cocotb.test()
async def test_{{DUT|lower}}_edge_cases(dut):
    """
    测试 {{DUT}} 边界情况
    
    验证内容：
    1. 输入边界值（最小值、最大值）
    2. 连续操作
    3. 异常输入处理
    
    Agent 任务：
    - 识别 DUT 的边界条件
    - 设计边界测试用例
    - 验证模块在边界条件下的行为
    """
    dut._log.info("Starting edge cases test")
    
    # 启动时钟
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())
    
    # 复位
    await reset_dut(dut)
    
    # TODO: Agent 需要在此添加边界测试
    # 例如：
    # - 输入全 0
    # - 输入全 1
    # - 输入最大值
    # - 连续背对背操作
    
    dut._log.info("Edge cases test passed")


# ============================================================================
# 更多测试用例...
# ============================================================================

# Agent 应该根据验证需求添加更多测试：
# - test_{{DUT|lower}}_interrupt.py: 中断处理测试
# - test_{{DUT|lower}}_performance.py: 性能测试
# - test_{{DUT|lower}}_stress.py: 压力测试
# - test_{{DUT|lower}}_random.py: 随机测试
# 
# 提示：可以使用以下命令运行特定测试：
#   make MODULE=test_{{DUT|lower}}_basic
#   make MODULE=test_{{DUT|lower}}_edge_cases
