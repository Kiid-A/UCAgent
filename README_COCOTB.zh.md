# UCAgent Cocotb 集成指南

使用 UCAgent 进行基于 cocotb 的 RTL 验证的完整指南。

## 概述

UCAgent 现已支持原生 **cocotb** 集成，用于 RTL 验证，实现 AI 驱动的自动化测试生成和执行。

### 核心功能

1. **RunCocotb 工具**: 原生 cocotb 执行，支持多种仿真器
2. **CocotbTestChecker**: 自动化测试验证，可配置通过/失败标准
3. **CocotbTestFileChecker**: 测试文件结构验证
4. **CocotbCoverageChecker**: 覆盖率报告分析
5. **多模式调用**: 支持 `auto`、`make`、`pytest`、`python` 四种执行模式

### 支持的仿真器

- Verilator（开源推荐）
- Icarus Verilog
- ModelSim
- VCS
- Questa

---

## 快速开始

### 前置条件

```bash
# 确保安装 cocotb
pip install cocotb cocotb-test

# 验证 UCAgent 安装
ucagent --version
```

### 步骤 1：准备项目

```
your_project/
├── src/
│   └── YourModule.v
├── cocotb_tests/
│   ├── Makefile
│   └── test_your_module.py
└── README.md
```

### 步骤 2：启动 UCAgent

```bash
ucagent output/ YourModule -s -hm --tui --mcp-server-no-file-tools
```

### 步骤 3：配置 Code Agent

在 Code Agent 的 MCP 配置中添加 UCAgent 服务器：

```json
{
 "mcpServers": {
     "ucagent": {
         "httpUrl": "http://localhost:5000/mcp",
         "timeout": 60000
     }
 }
}
```

### 步骤 4：开始验证

在 Code Agent 中：

```
请按照模板为 YourModule 生成 cocotb 测试。
要求：
1. 使用 RunCocotb 工具执行
2. 包含复位和时钟生成
3. 覆盖基本操作和边界情况
```

---

## 核心组件

### 1. RunCocotb 工具

位于 `ucagent/tools/testops.py`：

```python
RunCocotb().do(
    module_name="test_counter",        # cocotb 测试模块名
    toplevel="SimpleCounter",          # RTL 顶层模块名
    sim="verilator",                   # 仿真器
    test_dir="./cocotb_tests",         # 测试目录
    timeout=300,                       # 超时时间（秒）
    run_mode="auto",                   # auto/make/pytest/python
)
```

**调用模式**：

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `auto` | 自动选择最佳模式 | 默认，推荐 |
| `make` | 使用项目 Makefile | 生产环境 |
| `pytest` | 使用 pytest-cocotb | 测试开发 |
| `python` | 直接执行脚本 | 自定义流程 |

### 2. CocotbTestChecker

位于 `ucagent/checkers/cocotb_test.py`：

```yaml
checker:
  - name: cocotb_test_check
    clss: "CocotbTestChecker"
    args:
      test_module: "test_{DUT}_basic"
      toplevel: "{DUT}"
      sim: "verilator"
      test_dir: "cocotb_tests"
      timeout: 300
      must_pass: true
```

### 3. 模板系统

模板位于 `ucagent/lang/zh/template/cocotb/`：

- `test_{{DUT}}_basic.py` - 测试用例模板
- `Makefile` - 构建配置
- `{{DUT}}_env.py` - 测试环境模板

在 agent 执行时自动替换 `{{DUT}}` 为实际模块名。

---

## 架构说明

### 执行流程

1. **Agent 接收任务** → 从 `Guide_Doc/cocotb_guide.md` 读取模板
2. **生成测试文件** → 使用模板并替换 `{{DUT}}`
3. **执行测试** → 调用 `RunCocotb` 选择合适模式
4. **验证结果** → `CocotbTestChecker` 验证通过/失败
5. **迭代修复** → 修复失败直到所有检查通过

---

## 使用指南

### 基础示例

```python
from ucagent.tools import RunCocotb

# 简单执行
success, stdout, stderr = RunCocotb().do(
    module_name="test_adder",
    toplevel="Adder",
    sim="verilator",
    test_dir="./tests",
    timeout=60
)
```

### 工作流集成

添加到 `config.yaml`：

```yaml
stage:
  - name: generate_cocotb_test
    task:
      - "使用模板生成 cocotb 测试文件"
      - "包含复位、时钟和基本断言"
    output_files:
      - "cocotb_tests/test_{DUT}_basic.py"
    checker:
      - name: test_structure_check
        clss: "CocotbTestFileChecker"
        args:
          test_file: "cocotb_tests/test_{DUT}_basic.py"
          min_tests: 3
          require_reset: true

  - name: run_cocotb_test
    task:
      - "使用 RunCocotb 执行测试"
      - "修复任何失败"
    checker:
      - name: cocotb_run_check
        clss: "CocotbTestChecker"
        args:
          test_module: "test_{DUT}_basic"
          toplevel: "{DUT}"
          sim: "verilator"
          must_pass: true
```

---

## 下游项目接入

任何 RTL 项目都可以使用 UCAgent 的 cocotb 功能，只需创建一个工作区配置即可，无需修改 UCAgent。

### 第 1 步：创建工作区目录

```bash
mkdir my_project_workspace && cd my_project_workspace
```

### 第 2 步：准备 RTL 和文档

```
my_project_workspace/
├── MyModule/
│   ├── MyModule.v       # RTL 源码
│   └── README.md        # 模块规格说明（接口、行为）
└── config.yaml          # 工作流配置（见下文）
```

### 第 3 步：编写工作流配置

复制并定制 `examples/CocotbWorkflow/cocotb.yaml`：

```yaml
template_overwrite:
  DUT: "MyModule"
  OUT: "output"

un_write_dirs:
  - "MyModule/"

stage:
  - name: generate_cocotb_framework
    desc: "生成 cocotb 测试框架"
    task:
      - "读取 MyModule/README.md 了解 DUT 接口"
      - "生成 cocotb_tests/Makefile"
      - "生成 cocotb_tests/test_{DUT}_basic.py"
    output_files:
      - "cocotb_tests/Makefile"
      - "cocotb_tests/test_{DUT}_basic.py"
    checker:
      - name: file_check
        clss: "CocotbTestFileChecker"
        args:
          test_file: "cocotb_tests/test_{DUT}_basic.py"
          min_tests: 3
          require_reset: true

  - name: run_basic_tests
    desc: "运行 cocotb 测试"
    checker:
      - name: cocotb_check
        clss: "CocotbTestChecker"
        args:
          test_module: "test_{DUT}_basic"
          toplevel: "{DUT}"
          sim: "verilator"
          test_dir: "cocotb_tests"
          timeout: 300
          must_pass: true
```

### 第 4 步：启动 UCAgent

```bash
# MCP 模式（配合 Code Agent 使用，如 Qwen、Claude Code 等）
ucagent . MyModule --config config.yaml -s -hm --tui --mcp-server-no-file-tools

# 或直接 LLM 模式
ucagent . MyModule --config config.yaml -s -l
```

### 第 5 步：（可选）复杂项目使用 make 模式

如果项目已有 Makefile 构建流程：

```yaml
checker:
  - name: cocotb_check
    clss: "CocotbTestChecker"
    args:
      run_mode: "make"
      make_target: "cocotb"
      make_args: "TOP_MODULE=mkMyModule TB_FILE=tb_test.py"
      test_dir: "test/cocotb"
      timeout: 300
      must_pass: true
```

---

## 常见问题

### 1. "MODULE not found" 错误

**原因**: 测试模块名不匹配

**解决方案**：
```python
# 确保 module_name 与文件名匹配（不含 .py）
module_name="test_adder"  # 对应 test_adder.py
```

### 2. 仿真器未找到

```bash
# 对于 Verilator
sudo apt install verilator

# 或使用 Icarus（通常更容易安装）
sudo apt install iverilog
```

---

## 文件结构参考

```
ucagent/
├── tools/
│   └── testops.py              # RunCocotb 实现
├── checkers/
│   └── cocotb_test.py          # CocotbTestChecker 等检查器
└── lang/zh/
    ├── template/cocotb/        # 模板
    │   ├── test_{{DUT}}_basic.py
    │   ├── Makefile
    │   └── {{DUT}}_env.py
    └── doc/Guide_Doc/
        └── cocotb_guide.md     # 用户指南

examples/
├── cocotb_example/             # 完整示例（SimpleCounter）
└── CocotbWorkflow/             # 工作流配置示例
```

---

## 参考资源

- [UCAgent 官方文档](https://ucagent.open-verify.cc/)
- [cocotb 文档](https://docs.cocotb.org/)
- [Verilator 指南](https://veripool.org/guide/latest/)
