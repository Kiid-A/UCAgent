# UCAgent Cocotb Integration Guide

Comprehensive guide for using UCAgent with cocotb-based RTL verification workflows.

## Overview

UCAgent supports native **cocotb** integration for RTL verification, enabling AI-driven automated test generation and execution for hardware designs.

### Key Features

1. **RunCocotb Tool**: Native cocotb execution with multi-simulator support
2. **CocotbTestChecker**: Automated test validation with configurable pass/fail criteria
3. **CocotbTestFileChecker**: Test file structure validation
4. **CocotbCoverageChecker**: Coverage report analysis
5. **Multi-Mode Invocation**: Support for `auto`, `make`, `pytest`, and `python` execution modes

### Supported Simulators

- Verilator (recommended for open-source)
- Icarus Verilog
- ModelSim
- VCS
- Questa

---

## Quick Start

### Prerequisites

```bash
# Ensure cocotb is installed
pip install cocotb cocotb-test

# Verify UCAgent installation
ucagent --version
```

### Step 1: Prepare Your Project

```
your_project/
├── src/
│   └── YourModule.v
├── cocotb_tests/
│   ├── Makefile
│   └── test_your_module.py
└── README.md
```

### Step 2: Start UCAgent

```bash
ucagent output/ YourModule -s -hm --tui --mcp-server-no-file-tools
```

### Step 3: Configure Code Agent

Add UCAgent MCP server to your Code Agent's settings:

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

### Step 4: Start Verification

In your Code Agent:

```
Please generate cocotb tests for YourModule following the template.
Requirements:
1. Use RunCocotb tool for execution
2. Include reset and clock generation
3. Cover basic operations and edge cases
```

---

## Core Components

### 1. RunCocotb Tool

Located in `ucagent/tools/testops.py`, provides:

```python
RunCocotb().do(
    module_name="test_counter",        # cocotb test module
    toplevel="SimpleCounter",          # RTL top-level module
    sim="verilator",                   # simulator
    test_dir="./cocotb_tests",         # test directory
    timeout=300,                       # timeout in seconds
    run_mode="auto",                   # auto/make/pytest/python
    make_target="cocotb",              # optional make target
    make_args="TOP_MODULE=xxx",        # optional make args
)
```

**Invocation Modes**:

| Mode | Description | Use Case |
|------|-------------|----------|
| `auto` | Automatically selects best mode | Default, recommended |
| `make` | Uses project Makefile | Production workflows |
| `pytest` | Uses pytest-cocotb | Test development |
| `python` | Direct script execution | Custom flows |

### 2. CocotbTestChecker

Located in `ucagent/checkers/cocotb_test.py`:

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

### 3. Template System

Templates in `ucagent/lang/zh/template/cocotb/`:

- `test_{{DUT}}_basic.py` - Test case template
- `Makefile` - Build configuration
- `{{DUT}}_env.py` - Test environment template

Auto-rendered with actual DUT name during agent execution.

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                    UCAgent Core                         │
├─────────────────────────────────────────────────────────┤
│  Tools                      │  Checkers                 │
│  ├─ RunCocotb              │  ├─ CocotbTestChecker      │
│  ├─ RunPyTest              │  ├─ CocotbTestFileChecker  │
│  └─ ...                    │  └─ CocotbCoverageChecker  │
├─────────────────────────────────────────────────────────┤
│  Template System                                        │
│  └─ cocotb/                                             │
│      ├─ test_{{DUT}}_basic.py                          │
│      ├─ Makefile                                        │
│      └─ {{DUT}}_env.py                                 │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              cocotb Simulation Flow                     │
│  Makefile → Verilator/Icarus → Waveform (VCD/FST)      │
└─────────────────────────────────────────────────────────┘
```

### Execution Flow

1. **Agent receives task** → Reads templates from `Guide_Doc/cocotb_guide.md`
2. **Generates test files** → Uses templates with `{{DUT}}` substitution
3. **Executes tests** → Calls `RunCocotb` with appropriate mode
4. **Validates results** → `CocotbTestChecker` verifies pass/fail
5. **Iterates** → Fixes failures until all checks pass

---

## Usage Guide

### Basic Example

```python
from ucagent.tools import RunCocotb

# Simple execution
success, stdout, stderr = RunCocotb().do(
    module_name="test_adder",
    toplevel="Adder",
    sim="verilator",
    test_dir="./tests",
    timeout=60
)

if success:
    print("Test passed")
else:
    print("Test failed")
    print(stderr)
```

### Workflow Integration

Add to your `config.yaml`:

```yaml
stage:
  - name: generate_cocotb_test
    task:
      - "Generate cocotb test file using templates"
      - "Include reset, clock, and basic assertions"
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
      - "Execute test using RunCocotb"
      - "Fix any failures"
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

## Downstream Project Integration

Any RTL project can use UCAgent's cocotb feature by creating a workspace configuration. No modifications to UCAgent are needed.

### Step 1: Create workspace directory

```bash
mkdir my_project_workspace && cd my_project_workspace
```

### Step 2: Prepare RTL and docs

```
my_project_workspace/
├── MyModule/
│   ├── MyModule.v       # RTL source
│   └── README.md        # Module specification (interfaces, behavior)
└── config.yaml          # Workflow configuration (see below)
```

### Step 3: Write workflow config

Copy and customize `examples/CocotbWorkflow/cocotb.yaml`:

```yaml
template_overwrite:
  DUT: "MyModule"
  OUT: "output"

un_write_dirs:
  - "MyModule/"

stage:
  - name: generate_cocotb_framework
    desc: "Generate cocotb test framework"
    task:
      - "Read MyModule/README.md to understand the DUT"
      - "Generate cocotb_tests/Makefile"
      - "Generate cocotb_tests/test_{DUT}_basic.py"
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
    desc: "Run cocotb tests"
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

### Step 4: Launch UCAgent

```bash
# MCP mode (with Code Agent like Qwen, Claude Code, etc.)
ucagent . MyModule --config config.yaml -s -hm --tui --mcp-server-no-file-tools

# Or direct LLM mode
ucagent . MyModule --config config.yaml -s -l
```

### Step 5: (Optional) Use make mode for complex projects

For projects with existing Makefile-based build flows:

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

## Troubleshooting

### 1. "MODULE not found" Error

**Cause**: Test module name mismatch

**Solution**:
```python
# Ensure module_name matches file name (without .py)
module_name="test_adder"  # for test_adder.py
```

### 2. Makefile Not Found

**Cause**: Wrong test directory or missing Makefile

**Solution**:
```bash
# Check Makefile exists
ls cocotb_tests/Makefile

# Or switch to pytest mode
RunCocotb().do(run_mode="pytest", script_file="test_adder.py")
```

### 3. Simulator Not Found

**Cause**: Simulator not in PATH

**Solution**:
```bash
# For Verilator
sudo apt install verilator

# Or use Icarus (usually easier to install)
sudo apt install iverilog
```

---

## File Structure Reference

```
ucagent/
├── tools/
│   └── testops.py              # RunCocotb implementation
├── checkers/
│   └── cocotb_test.py          # CocotbTestChecker, CocotbTestFileChecker, CocotbCoverageChecker
└── lang/zh/
    ├── template/cocotb/        # Templates
    │   ├── test_{{DUT}}_basic.py
    │   ├── Makefile
    │   └── {{DUT}}_env.py
    └── doc/Guide_Doc/
        └── cocotb_guide.md     # User guide

examples/
├── cocotb_example/             # Complete example (SimpleCounter)
└── CocotbWorkflow/             # Workflow config example
```

---

## References

- [UCAgent Official Docs](https://ucagent.open-verify.cc/)
- [cocotb Documentation](https://docs.cocotb.org/)
- [Verilator Guide](https://veripool.org/guide/latest/)
