# SimpleCounter Cocotb Makefile

TOPLEVEL := SimpleCounter

# RTL 源文件
VERILOG_SOURCES = $(PWD)/../SimpleCounter/SimpleCounter.v

# 仿真器配置
SIM ?= icarus
TOPLEVEL_LANG = verilog
MODULE ?= test_SimpleCounter_basic

# Verilator 配置
ifeq ($(SIM),verilator)
    EXTRA_ARGS += --trace
    EXTRA_ARGS += --trace-struct
    VERILATOR_ARGS += -O3
    VERILATOR_ARGS += -Wall
endif

# 编译选项
COMPILE_ARGS += -I$(PWD)/../SimpleCounter

# 包含 cocotb 的 Makefile
include $(shell cocotb-config --makefiles)/Makefile.sim

wave:
	gtkwave results.vcd &

.PHONY: wave
