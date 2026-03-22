#coding=utf-8
"""
{{DUT}} Cocotb 测试环境模板

本文件定义了 {{DUT}} 的测试环境组件，包括：
- 接口句柄类（Interface Handle）
- 环境配置类（Environment）
- 事务级模型（Transaction）
- 驱动器/监视器（Driver/Monitor）

Agent 需要根据 DUT 的实际接口完善这些类。
"""

import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer
from cocotb.binary import BinaryValue
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


# ============================================================================
# 事务定义（Transaction）
# ============================================================================

@dataclass
class {{DUT}}Transaction:
    """
    {{DUT}} 事务类
    
    用于封装一次完整的 DUT 操作
    Agent 需要根据 DUT 的协议定义事务字段
    """
    # 输入字段
    input_data: int = 0
    control: int = 0
    valid: bool = False
    
    # 输出字段（预期值）
    expected_output: int = 0
    expected_ready: bool = True
    
    # 元数据
    timestamp: float = field(default_factory=lambda: 0.0)
    description: str = ""
    
    def __str__(self) -> str:
        return (f"{{DUT}}Transaction(input=0x{self.input_data:x}, "
                f"ctrl=0x{self.control:x}, valid={self.valid})")


# ============================================================================
# 接口句柄类（Interface Handle）
# ============================================================================

class {{DUT}}Interface:
    """
    {{DUT}} 接口句柄类
    
    提供对 DUT 信号的便捷访问
    Agent 需要根据 DUT 的实际端口定义信号映射
    """
    
    def __init__(self, dut):
        """
        初始化接口句柄
        
        Args:
            dut: cocotb DUT 句柄
        """
        self.dut = dut
        
        # ======================================================================
        # 时钟和复位信号（必须根据实际 DUT 修改）
        # ======================================================================
        self.clk = dut.clk
        self.rst_n = getattr(dut, 'rst_n', None)  # 低电平有效复位（可选）
        self.rst = getattr(dut, 'rst', None)      # 高电平有效复位（可选）
        
        # ======================================================================
        # 输入信号（Agent 需要根据 DUT 端口定义）
        # ======================================================================
        # 示例：
        # self.io_valid = dut.io_valid
        # self.io_ready = dut.io_ready
        # self.io_data = dut.io_data
        # self.io_addr = dut.io_addr
        
        # 使用 getattr 安全访问（信号可能存在也可能不存在）
        self._init_input_signals()
        
        # ======================================================================
        # 输出信号（Agent 需要根据 DUT 端口定义）
        # ======================================================================
        self._init_output_signals()
        
        # ======================================================================
        # 内部状态
        # ======================================================================
        self.transaction_count = 0
        self.error_count = 0
    
    def _init_input_signals(self):
        """初始化输入信号列表"""
        # Agent 需要在此添加 DUT 的输入信号
        # 例如：
        # self.input_signals = ['io_valid', 'io_ready', 'io_data']
        self.input_signals = []
        
        # 自动绑定存在的信号
        for sig_name in self.input_signals:
            if hasattr(self.dut, sig_name):
                setattr(self, sig_name, getattr(self.dut, sig_name))
            else:
                self.dut._log.warning(f"Input signal '{sig_name}' not found")
                setattr(self, sig_name, None)
    
    def _init_output_signals(self):
        """初始化输出信号列表"""
        # Agent 需要在此添加 DUT 的输出信号
        self.output_signals = []
        
        for sig_name in self.output_signals:
            if hasattr(self.dut, sig_name):
                setattr(self, sig_name, getattr(self.dut, sig_name))
            else:
                self.dut._log.warning(f"Output signal '{sig_name}' not found")
                setattr(self, sig_name, None)
    
    # ======================================================================
    # 便捷方法（Agent 可以根据需要添加）
    # ======================================================================
    
    async def wait_ready(self, timeout_cycles: int = 100) -> bool:
        """
        等待模块就绪
        
        Args:
            timeout_cycles: 超时周期数
            
        Returns:
            True 如果就绪，False 如果超时
        """
        if not hasattr(self, 'io_ready') or self.io_ready is None:
            return True  # 没有 ready 信号，假设总是就绪
        
        for _ in range(timeout_cycles):
            await RisingEdge(self.clk)
            if self.io_ready.value == 1:
                return True
        return False
    
    def drive_input(self, data: int, valid: bool = True):
        """
        驱动输入信号
        
        Args:
            data: 输入数据
            valid: 有效信号
        """
        if hasattr(self, 'io_data') and self.io_data is not None:
            self.io_data.value = data
        if hasattr(self, 'io_valid') and self.io_valid is not None:
            self.io_valid.value = 1 if valid else 0
    
    def check_output(self, expected: int, signal_name: str = "result") -> bool:
        """
        检查输出信号
        
        Args:
            expected: 期望值
            signal_name: 输出信号名称
            
        Returns:
            True 如果匹配，False 否则
        """
        if not hasattr(self.dut, signal_name):
            self.dut._log.warning(f"Output signal '{signal_name}' not found")
            return True
        
        actual = getattr(self.dut, signal_name).value
        if actual != expected:
            self.dut._log.error(f"Output mismatch: expected=0x{expected:x}, "
                               f"actual=0x{actual:x}")
            self.error_count += 1
            return False
        return True


# ============================================================================
# 环境配置类（Environment Configuration）
# ============================================================================

class {{DUT}}Config:
    """
    {{DUT}} 测试环境配置
    
    Agent 可以根据需要添加配置选项
    """
    
    def __init__(self):
        # 时钟配置（单位：ns）
        self.clock_period_ns = 10
        self.clock Duty_cycle = 0.5
        
        # 复位配置
        self.reset_cycles = 3
        
        # 超时配置
        self.timeout_cycles = 1000
        
        # 日志级别
        self.log_level = "INFO"
        
        # 覆盖率收集
        self.enable_coverage = True
        
        # 波形输出
        self.enable_waveform = True


# ============================================================================
# 测试环境类（Test Environment）
# ============================================================================

class {{DUT}}Env:
    """
    {{DUT}} 测试环境
    
    整合接口、配置、驱动器和监视器
    """
    
    def __init__(self, dut, config: Optional[{{DUT}}Config] = None):
        """
        初始化测试环境
        
        Args:
            dut: cocotb DUT 句柄
            config: 环境配置（可选）
        """
        self.dut = dut
        self.config = config or {{DUT}}Config()
        
        # 初始化接口
        self.interface = {{DUT}}Interface(dut)
        
        # 统计信息
        self.transactions = []
        self.passed_tests = 0
        self.failed_tests = 0
        
        dut._log.info(f"{{DUT}}Env initialized")
    
    async def reset(self):
        """执行 DUT 复位"""
        from test_{{DUT}}_basic import reset_dut
        await reset_dut(self.dut, reset_cycles=self.config.reset_cycles)
    
    async def run_transaction(self, trans: {{DUT}}Transaction) -> bool:
        """
        运行单个事务
        
        Args:
            trans: 事务对象
            
        Returns:
            True 如果成功，False 如果失败
        """
        self.dut._log.debug(f"Running transaction: {trans}")
        
        # TODO: Agent 需要实现具体的事务执行逻辑
        # 示例模板：
        # 
        # # 驱动输入
        # self.interface.drive_input(trans.input_data, trans.valid)
        # 
        # # 等待就绪
        # ready = await self.interface.wait_ready()
        # if not ready:
        #     self.dut._log.error("Transaction timeout")
        #     self.failed_tests += 1
        #     return False
        # 
        # # 等待输出
        # await RisingEdge(self.interface.clk)
        # 
        # # 检查输出
        # success = self.interface.check_output(trans.expected_output)
        # 
        # if success:
        #     self.passed_tests += 1
        # else:
        #     self.failed_tests += 1
        # 
        # return success
        
        self.passed_tests += 1
        return True
    
    def report(self):
        """生成测试报告"""
        self.dut._log.info("=" * 60)
        self.dut._log.info("{{DUT}} Test Report")
        self.dut._log.info("=" * 60)
        self.dut._log.info(f"Passed: {self.passed_tests}")
        self.dut._log.info(f"Failed: {self.failed_tests}")
        total = self.passed_tests + self.failed_tests
        if total > 0:
            rate = self.passed_tests / total * 100
            self.dut._log.info(f"Pass Rate: {rate:.1f}%")
        self.dut._log.info("=" * 60)


# ============================================================================
# 覆盖率收集器（可选，用于功能覆盖率）
# ============================================================================

class {{DUT}}CoverageCollector:
    """
    {{DUT}} 功能覆盖率收集器
    
    Agent 可以根据验证计划定义覆盖率收集点
    """
    
    def __init__(self, dut):
        self.dut = dut
        self.covered_points = set()
        self.total_points = set()
        
        # 定义覆盖率收集点
        # Agent 需要根据验证计划添加
        self._init_coverage_points()
    
    def _init_coverage_points(self):
        """初始化覆盖率收集点"""
        # 示例：
        # self.total_points.add("FC-INPUT-RANGE-NORMAL")
        # self.total_points.add("FC-INPUT-RANGE-EDGE")
        pass
    
    def mark_covered(self, point_name: str):
        """标记一个覆盖率点已覆盖"""
        self.covered_points.add(point_name)
        self.dut._log.debug(f"Coverage point '{point_name}' covered")
    
    def report(self) -> Dict[str, float]:
        """生成覆盖率报告"""
        total = len(self.total_points)
        covered = len(self.covered_points)
        rate = (covered / total * 100) if total > 0 else 0.0
        
        return {
            "total_points": total,
            "covered_points": covered,
            "coverage_rate": rate,
            "uncovered": list(self.total_points - self.covered_points)
        }
