# Cocotb Example: SimpleCounter

## Overview

This example demonstrates UCAgent's cocotb integration using a simple 8-bit counter module.

## Project Structure

```
cocotb_example/
├── SimpleCounter/
│   ├── SimpleCounter.v              # RTL: 8-bit counter with enable, clear, overflow
│   └── README.md                    # Module specification
└── cocotb_tests/
    ├── Makefile                     # cocotb simulation build
    └── test_SimpleCounter_basic.py  # 5 test cases (reset, enable, counting, clear, overflow)
```

## Run Tests Directly

```bash
cd cocotb_tests
make SIM=icarus
```

## Run via UCAgent

```bash
# From UCAgent root:
bash examples/CocotbWorkflow/run_cocotb_example.sh mcp
```

See `examples/CocotbWorkflow/cocotb.yaml` for the workflow configuration.
