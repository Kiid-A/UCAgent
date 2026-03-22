# Cocotb 验证框架使用指南

## 概述

本目录提供了使用 cocotb 进行 RTL 验证的模板文件。UCAgent 会根据这些模板自动生成适合你 DUT 的测试框架。

## 快速开始：使用 Checker 进行自动化验证

UCAgent 提供了专门的 Checker 来自动化 cocotb 验证流程。通过在 YAML 配置中定义 checker，可以让 Agent 自动：
- 生成 cocotb 测试文件
- 运行仿真并检查结果
- 分析覆盖率报告
- 推进验证流程

### Checker 类型

#### 1. CocotbTestChecker - 仿真运行检查器

**用途**: 运行 cocotb 仿真并验证结果

**配置示例**:
```yaml
checker:
  - name: cocotb_simulation_check
    clss: "CocotbTestChecker"
    args:
      test_module: "test_{DUT}_basic"   # 测试模块名（不含.py）
      toplevel: "{DUT}"                  # 顶层 RTL 模块名
      sim: "verilator"                   # 仿真器类型
      test_dir: "cocotb_tests"           # 测试目录
      timeout: 300                       # 超时时间（秒）
      must_pass: true                    # 是否必须通过
      check_waveform: true               # 是否检查波形文件
```

**参数说明**:
- `test_module`: cocotb 测试模块名（不含 .py 后缀），如 `test_SimpleCounter_basic`
- `toplevel`: 顶层 RTL 模块名，如 `SimpleCounter`
- `sim`: 仿真器类型，支持 `verilator`, `icarus`, `modelsim`, `vcs`, `questa`
- `test_dir`: 包含 Makefile 和测试文件的目录
- `timeout`: 仿真超时时间（秒）
- `must_pass`: 如果为 true，仿真失败会导致 checker 失败
- `check_waveform`: 如果为 true，检查是否生成了波形文件

**返回值**:
- 成功：`{"passed": true, "message": "Cocotb test passed", ...}`
- 失败：`{"passed": false, "error": "Cocotb simulation failed", "stdout": "...", "stderr": "..."}`

#### 2. CocotbTestFileChecker - 测试文件结构检查器

**用途**: 验证 cocotb 测试文件的结构和内容

**配置示例**:
```yaml
checker:
  - name: test_file_structure_check
    clss: "CocotbTestFileChecker"
    args:
      test_file: "cocotb_tests/test_{DUT}_basic.py"
      min_tests: 3           # 最少测试函数数量
      require_reset: true    # 是否要求有复位测试
      require_clock: true    # 是否要求有时钟生成
```

**参数说明**:
- `test_file`: 测试文件路径（相对于 workspace）
- `min_tests`: 要求的最少测试函数数量
- `require_reset`: 如果为 true，要求有包含 "reset" 的测试函数
- `require_clock`: 如果为 true，要求有时钟生成代码

**检查内容**:
- 文件是否存在
- 是否包含 `import cocotb`
- 是否有 `@cocotb.test()` 装饰的函数
- 测试函数数量是否满足要求
- 是否有复位测试和时钟生成（如果要求）

#### 3. CocotbCoverageChecker - 覆盖率检查器

**用途**: 分析 cocotb 覆盖率报告

**配置示例**:
```yaml
checker:
  - name: cocotb_coverage_check
    clss: "CocotbCoverageChecker"
    args:
      coverage_dir: "coverage"
      min_line_coverage: 0.8      # 最低行覆盖率 80%
      min_toggle_coverage: 0.7    # 最低翻转覆盖率 70%
```

**参数说明**:
- `coverage_dir`: 覆盖率报告目录
- `min_line_coverage`: 最低行覆盖率要求（0.0-1.0）
- `min_toggle_coverage`: 最低翻转覆盖率要求（0.0-1.0）

### 完整工作流示例

参考 `examples/CocotbWorkflow/cocotb.yaml`：

```yaml
stage:
  # 阶段 1: 生成 Cocotb 测试框架
  - name: generate_cocotb_framework
    desc: "生成 Cocotb 测试框架"
    task:
      - "读取 DUT 规格文档"
      - "生成 cocotb_tests/Makefile"
      - "生成 cocotb_tests/test_{DUT}_basic.py"
      - "生成 cocotb_tests/{DUT}_env.py"
    checker:
      - name: test_file_structure_check
        clss: "CocotbTestFileChecker"
        args:
          test_file: "cocotb_tests/test_{DUT}_basic.py"
          min_tests: 3
          require_reset: true

  # 阶段 2: 运行基础测试
  - name: run_basic_tests
    desc: "运行基础 Cocotb 测试"
    task:
      - "使用 RunCocotb 运行测试"
      - "修复仿真问题"
    checker:
      - name: cocotb_simulation_check
        clss: "CocotbTestChecker"
        args:
          test_module: "test_{DUT}_basic"
          toplevel: "{DUT}"
          sim: "verilator"
          test_dir: "cocotb_tests"
          timeout: 300
          must_pass: true

  # 阶段 3: 扩展测试覆盖率
  - name: extend_test_coverage
    desc: "扩展测试覆盖率"
    task:
      - "添加边界测试"
      - "添加性能测试"
    checker:
      - name: cocotb_simulation_check
        clss: "CocotbTestChecker"
        args:
          test_module: "test_{DUT}_edge_cases"
          toplevel: "{DUT}"
          sim: "verilator"
          test_dir: "cocotb_tests"
          timeout: 300

  # 阶段 4: 生成验证报告
  - name: generate_verification_report
    desc: "生成验证报告"
    task:
      - "运行所有测试"
      - "创建验证报告"
    checker:
      - name: cocotb_coverage_check
        clss: "CocotbCoverageChecker"
        args:
          coverage_dir: "coverage"
          min_line_coverage: 0.8
```

### 使用工具运行 cocotb

#### RunCocotb 工具

在任务中使用 `RunCocotb` 工具：

```python
# 在 Agent 任务中
RunCocotb().do(
    module_name="test_SimpleCounter_basic",
    toplevel="SimpleCounter",
    sim="verilator",
    test_dir="cocotb_tests",
    timeout=300
)
```

#### 与 Checker 配合

Checker 会自动调用 `RunCocotb` 工具，你只需要在 YAML 中配置参数。

### 调试技巧

#### 1. 查看仿真日志

当 checker 失败时，会返回详细的日志输出：
```json
{
  "error": "Cocotb simulation failed",
  "stdout": "cocotb output...",
  "stderr": "error messages...",
  "suggestion": [
    "Check the simulation log for error messages",
    "Verify RTL code compiles correctly",
    "Review cocotb test assertions"
  ]
}
```

#### 2. 手动运行仿真

在调试时，可以手动运行仿真：
```bash
cd cocotb_tests
make MODULE=test_SimpleCounter_basic SIM=verilator
```

#### 3. 检查波形

如果启用了波形输出：
```bash
gtkwave results.vcd
```

### 与 UnityTest 对比

| 特性 | UnityTest | Cocotb |
|------|-----------|--------|
| 测试框架 | pytest + picker | cocotb |
| 仿真控制 | Python 接口 | 直接时序控制 |
| 波形支持 | 有限 | 完整支持 |
| 覆盖率 | toffee 报告 | 仿真器原生支持 |
| 适用场景 | 功能验证 | 时序验证 |

两者可以互补使用：
- UnityTest: 快速功能验证
- Cocotb: 精确时序和协议验证

## 模板文件说明

### 1. `test_{{DUT}}_basic.py` - 测试用例模板

**用途**: 包含基础的 cocotb 测试用例框架

**主要组件**:
- 时钟生成代码
- 复位序列函数
- 基础测试用例模板

**Agent 任务**:
- 根据 DUT 的实际接口修改信号名称
- 填充测试用例的具体激励和断言
- 添加更多的测试场景

### 2. `Makefile` - 仿真构建模板

**用途**: 定义 cocotb 仿真的编译和运行规则

**支持的仿真器**:
- `verilator` (默认，免费开源)
- `icarus` (免费开源)
- `modelsim` / `questa`
- `vcs`

**常用命令**:
```bash
# 运行默认测试
make

# 运行特定测试模块
make MODULE=test_DUT_basic

# 使用不同仿真器
make SIM=verilator
make SIM=icarus

# 清理
make clean
```

**Agent 任务**:
- 修改 `VERILOG_SOURCES` 指向正确的 RTL 文件
- 根据需要调整编译选项

### 3. `{{DUT}}_env.py` - 测试环境模板

**用途**: 定义测试环境组件，提供高级抽象接口

**主要类**:
- `{{DUT}}Transaction`: 事务级数据封装
- `{{DUT}}Interface`: DUT 信号句柄
- `{{DUT}}Config`: 环境配置
- `{{DUT}}Env`: 完整测试环境
- `{{DUT}}CoverageCollector`: 覆盖率收集器

**Agent 任务**:
- 根据 DUT 端口定义信号映射
- 实现事务级的驱动和检查方法
- 添加功能覆盖率收集点

## 使用流程

### 阶段 1: 生成测试框架

UCAgent 会：
1. 读取这些模板文件
2. 根据你的 DUT 名称和接口进行替换
3. 生成到工作区的 `cocotb_tests/` 目录

### 阶段 2: 完善测试代码

你需要（或让 Agent）：
1. 检查生成的信号名称是否正确
2. 根据验证计划添加测试用例
3. 完善断言和检查逻辑

### 阶段 3: 运行仿真

使用 `RunCocotb` 工具：
```python
RunCocotb().do(
    module_name="test_DUT_basic",
    toplevel="DUT",
    sim="verilator",
    test_dir="./cocotb_tests",
    timeout=300
)
```

### 阶段 4: 调试和迭代

如果测试失败：
1. 查看日志输出定位问题
2. 修改测试代码或 DUT
3. 重新运行直到通过

## 最佳实践

### 1. 信号命名一致性

确保模板中的信号名称与 DUT 实际端口一致：
```python
# 在 {{DUT}}_env.py 中
self.io_valid = dut.io_valid  # 必须与 RTL 端口名匹配
self.io_data = dut.io_data
```

### 2. 分层测试结构

```
test_DUT_basic.py      # 基础功能测试
test_DUT_edge.py       # 边界条件测试
test_DUT_random.py     # 随机测试
test_DUT_performance.py # 性能测试
```

### 3. 断言明确

每个测试用例应该有清晰的断言：
```python
@cocotb.test()
async def test_something(dut):
    # ... 设置 ...

    # 明确的断言，带错误信息
    assert dut.output.value == expected, \
        f"Expected 0x{expected:x}, got 0x{dut.output.value:x}"
```

### 4. 日志输出

充分利用 cocotb 的日志功能：
```python
dut._log.info("Starting test...")
dut._log.debug(f"Signal value: {dut.signal.value}")
dut._log.error("Test failed!")
```

### 5. 覆盖率驱动

使用覆盖率收集器跟踪验证进度：
```python
coverage = {{DUT}}CoverageCollector(dut)
coverage.mark_covered("FC-INPUT-NORMAL")
print(coverage.report())
```

## 常见问题

### Q1: 仿真器找不到？

确保已安装并配置：
```bash
# Verilator
sudo apt install verilator  # Ubuntu
brew install verilator      # macOS

# Icarus
sudo apt install iverilog
```

### Q2: 波形如何查看？

在 Makefile 中启用波形：
```makefile
EXTRA_ARGS += --trace  # Verilator 生成 VCD/FST
```

查看波形：
```bash
gtkwave results.vcd
```

### Q3: 如何调试 cocotb 测试？

1. 增加日志级别
2. 使用 `pdb` 断点（需要 `SIM=icarus` 支持）
3. 添加临时的 `dut._log.info()` 输出

## 参考资源

- [cocotb 官方文档](https://docs.cocotb.org/)
- [cocotb 示例库](https://github.com/cocotb/cocotb/tree/master/examples)
- [Verilator 文档](https://veripool.org/guide/latest/)
