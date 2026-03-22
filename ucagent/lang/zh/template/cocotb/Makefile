# ==============================================================================
#
# {{DUT}} Cocotb Makefile 模板
#
# 使用说明：
#   make              - 运行默认测试
#   make MODULE=test_{{DUT|lower}}_basic  - 运行特定测试
#   make SIM=verilator - 使用 Verilator 仿真器
#   make SIM=icarus   - 使用 Icarus Verilog
#   make clean        - 清理生成的文件
#
# 环境变量：
#   MODULE           - cocotb 测试模块名（不含.py 后缀）
#   TOPLEVEL         - 顶层模块名
#   SIM              - 仿真器类型
#   TOPLEVEL_LANG    - 顶层语言 (verilog/vhdl)
#
# ==============================================================================

# DUT 名称
TOPLEVEL := {{DUT}}

# 所有 RTL 源文件（Agent 需要根据实际项目修改）
# 方式 1: 直接列出文件
# VERILOG_SOURCES = $(PWD)/../../{{DUT}}/{{DUT}}.v

# 方式 2: 从文件列表读取（推荐）
# include $(PWD)/../../{{DUT}}/{{DUT}}.f
# VERILOG_SOURCES = $(addprefix $(PWD)/../../{{DUT}}/, $(shell cat {{DUT}}.f))

# 方式 3: 使用通配符
VERILOG_SOURCES = $(wildcard $(PWD)/../../{{DUT}}/*.v)

# 或者手动指定（如果文件不多）
# VERILOG_SOURCES = $(PWD)/{{DUT}}.v

# 仿真器配置
# 可选值：verilator, icarus, modelsim, vcs, questa
SIM ?= verilator

# 顶层语言
TOPLEVEL_LANG = verilog

# cocotb 测试模块（可通过命令行覆盖：make MODULE=test_basic）
MODULE ?= test_{{DUT|lower}}_basic

# Verilator 特定配置
ifeq ($(SIM),verilator)
    # 启用波形输出
    EXTRA_ARGS += --trace
    EXTRA_ARGS += --trace-struct
    
    # 优化级别（0-3，越高越快但编译越慢）
    VERILATOR_ARGS += -O3
    
    # 警告级别
    VERILATOR_ARGS += -Wall
    VERILATOR_ARGS += -Wno-WIDTH
    
    # 其他有用的选项
    # VERILATOR_ARGS += --coverage        # 启用代码覆盖率
    # VERILATOR_ARGS += --assert          # 启用断言
endif

# Icarus 特定配置
ifeq ($(SIM),icarus)
    # Icarus 特定选项
    EXTRA_ARGS += -DICARUS
endif

# 编译选项
COMPILE_ARGS += -I$(PWD)/../../{{DUT}}

# Python 路径（如果需要导入额外的 Python 模块）
# export PYTHONPATH += $(PWD)/

# 包含 cocotb 的 Makefile
include $(shell cocotb-config --makefiles)/Makefile.sim

# ==============================================================================
# 自定义目标
# ==============================================================================

# 运行所有测试
all:
	@echo "Running all {{DUT}} tests..."
	$(MAKE) MODULE=test_{{DUT|lower}}_basic
	$(MAKE) MODULE=test_{{DUT|lower}}_edge_cases

# 生成波形查看命令（需要 gtkwave）
wave:
	@echo "Opening waveform in gtkwave..."
	gtkwave results.vcd &

# 清理
clean:
	rm -rf sim_build/
	rm -rf *.vcd *.fst *.ghw
	rm -rf results_*
	rm -rf __pycache__/
	rm -rf *.log
	find . -name "*.pyc" -delete

# 帮助信息
help:
	@echo "{{DUT}} Cocotb Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all     - Run all tests"
	@echo "  clean   - Remove generated files"
	@echo "  wave    - Open waveform in gtkwave"
	@echo "  help    - Show this help"
	@echo ""
	@echo "Variables:"
	@echo "  MODULE  - Test module to run (default: test_{{DUT|lower}}_basic)"
	@echo "  SIM     - Simulator to use (default: verilator)"
	@echo ""
	@echo "Examples:"
	@echo "  make MODULE=test_{{DUT|lower}}_basic SIM=verilator"
	@echo "  make MODULE=test_{{DUT|lower}}_edge_cases SIM=icarus"

.PHONY: all clean wave help
