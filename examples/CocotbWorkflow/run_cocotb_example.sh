#!/bin/bash
#
# SimpleCounter Cocotb 验证 - UCAgent 启动脚本
#
# 使用方法:
#   ./run_cocotb_example.sh [mode] [--backend=<name>]
#
# mode:
#   mcp      - MCP 服务器模式（配合 Code Agent 使用，默认）
#   auto     - 自动运行模式（指定 --backend）
#   direct   - 直接运行已有测试（不启动 UCAgent，仅跑 cocotb）
#
# 示例:
#   ./run_cocotb_example.sh mcp                    # 启动 MCP，等 Code Agent 接入
#   ./run_cocotb_example.sh auto --backend=qwen    # 自动用 qwen 跑完整流程
#   ./run_cocotb_example.sh auto --backend=claude  # 自动用 claude 跑
#   ./run_cocotb_example.sh direct                 # 只跑已有的 cocotb 测试
#

set -e

# ===== 颜色定义 =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ===== 路径定义 =====
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UCAGENT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
EXAMPLE_DIR="${UCAGENT_ROOT}/examples/cocotb_example"
WORKFLOW_CFG="${UCAGENT_ROOT}/examples/CocotbWorkflow/cocotb.yaml"
WORKSPACE="${UCAGENT_ROOT}/output_cocotb_example"

# ===== 参数解析 =====
MODE="${1:-mcp}"
BACKEND_ARG=""
EXTRA_ARGS=""
for arg in "$@"; do
    case "$arg" in
        --backend=*) BACKEND_ARG="$arg" ;;
        mcp|auto|direct) ;;
        *) EXTRA_ARGS="$EXTRA_ARGS $arg" ;;
    esac
done

# ===== 辅助函数 =====
info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }
header() { echo -e "\n${CYAN}========================================${NC}"; echo -e "${CYAN} $1${NC}"; echo -e "${CYAN}========================================${NC}\n"; }

# ===== 环境检查 =====
check_env() {
    header "环境检查"

    # Python
    if ! command -v python &>/dev/null; then
        err "python 未找到"
    fi
    info "Python: $(python --version 2>&1)"

    # cocotb
    if ! python -c "import cocotb" 2>/dev/null; then
        err "cocotb 未安装，请运行: pip install cocotb"
    fi
    info "cocotb: $(python -c 'import cocotb; print(cocotb.__version__)')"

    # 仿真器
    if command -v iverilog &>/dev/null; then
        SIM="icarus"
        info "仿真器: Icarus Verilog ($(iverilog -V 2>&1 | head -1))"
    elif command -v verilator &>/dev/null; then
        SIM="verilator"
        info "仿真器: Verilator ($(verilator --version 2>&1))"
    else
        err "未找到仿真器，请安装 iverilog 或 verilator"
    fi

    # UCAgent（mcp/auto 模式才需要）
    if [ "$MODE" != "direct" ]; then
        if ! python -c "import ucagent" 2>/dev/null; then
            # 尝试从源码加载
            export PYTHONPATH="${UCAGENT_ROOT}:${PYTHONPATH:-}"
            if ! python -c "import ucagent" 2>/dev/null; then
                err "ucagent 模块未找到，请运行: pip install -e . 或 make init"
            fi
        fi
        UCAGENT_VERSION=$(python -c "from ucagent.version import __version__; print(__version__)" 2>/dev/null || echo "unknown")
        info "UCAgent: ${UCAGENT_VERSION}"
    fi

    info "环境检查通过"
}

# ===== 准备工作区 =====
prepare_workspace() {
    header "准备工作区: ${WORKSPACE}"

    mkdir -p "${WORKSPACE}"

    # 复制 SimpleCounter RTL
    mkdir -p "${WORKSPACE}/SimpleCounter"
    cp "${EXAMPLE_DIR}/SimpleCounter/SimpleCounter.v" "${WORKSPACE}/SimpleCounter/"
    cp "${EXAMPLE_DIR}/SimpleCounter/README.md" "${WORKSPACE}/SimpleCounter/"
    info "RTL 文件已复制"

    # 复制已有的测试文件（供参考）
    mkdir -p "${WORKSPACE}/cocotb_tests"
    cp "${EXAMPLE_DIR}/cocotb_tests/Makefile" "${WORKSPACE}/cocotb_tests/"
    cp "${EXAMPLE_DIR}/cocotb_tests/test_SimpleCounter_basic.py" "${WORKSPACE}/cocotb_tests/"
    info "测试文件已复制"

    info "工作区准备完成"
    echo ""
    echo "  工作区: ${WORKSPACE}"
    echo "  RTL:    ${WORKSPACE}/SimpleCounter/SimpleCounter.v"
    echo "  测试:   ${WORKSPACE}/cocotb_tests/"
}

# ===== 模式 1: 直接运行 cocotb 测试 =====
run_direct() {
    header "直接运行 cocotb 测试"

    cd "${WORKSPACE}/cocotb_tests"

    info "使用 ${SIM} 仿真器运行 SimpleCounter 测试..."
    echo ""

    rm -rf sim_build
    make SIM="${SIM}" MODULE=test_SimpleCounter_basic 2>&1 || true

    echo ""
    info "测试运行完成。波形文件在 ${WORKSPACE}/cocotb_tests/sim_build/"
}

# ===== 模式 2: MCP 服务器模式 =====
run_mcp() {
    header "启动 UCAgent MCP 服务器"

    echo -e "  MCP 地址: ${GREEN}http://localhost:5000/mcp${NC}"
    echo ""
    echo -e "${YELLOW}下一步操作:${NC}"
    echo "  1. 在另一个终端中启动你的 Code Agent（如 qwen、claude 等）"
    echo "  2. 确保 Code Agent 的 MCP 配置指向 http://localhost:5000/mcp"
    echo "  3. 在 Code Agent 中发送初始提示词开始验证"
    echo ""
    echo -e "${YELLOW}Code Agent MCP 配置示例:${NC}"
    cat << 'EOF'
{
  "mcpServers": {
    "ucagent": {
      "httpUrl": "http://localhost:5000/mcp",
      "timeout": 300000
    }
  }
}
EOF
    echo ""
    echo "按 Ctrl+C 停止服务器"
    echo ""

    cd "${WORKSPACE}"
    exec python "${UCAGENT_ROOT}/ucagent.py" . SimpleCounter \
        --config "${WORKFLOW_CFG}" \
        -s -hm \
        --tui \
        --mcp-server-no-file-tools \
        --no-embed-tools \
        $EXTRA_ARGS
}

# ===== 模式 3: 自动运行模式 =====
run_auto() {
    header "自动运行模式"

    if [ -z "$BACKEND_ARG" ]; then
        err "自动模式需要指定 --backend=<name>，例如: ./run_cocotb_example.sh auto --backend=qwen"
    fi

    info "使用后端: ${BACKEND_ARG}"
    echo ""

    cd "${WORKSPACE}"
    exec python "${UCAGENT_ROOT}/ucagent.py" . SimpleCounter \
        --config "${WORKFLOW_CFG}" \
        -s -hm \
        --tui \
        --mcp-server-no-file-tools \
        --no-embed-tools \
        --loop \
        ${BACKEND_ARG} \
        $EXTRA_ARGS
}

# ===== 清理函数 =====
cleanup() {
    if [ "${KEEP_WORKSPACE:-}" != "1" ]; then
        echo ""
        info "工作区保留在: ${WORKSPACE}"
        info "如需清理: rm -rf ${WORKSPACE}"
    fi
}
trap cleanup EXIT

# ===== 主流程 =====
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  UCAgent Cocotb 示例 - SimpleCounter     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"

check_env
prepare_workspace

case "$MODE" in
    direct)
        run_direct
        ;;
    mcp)
        run_mcp
        ;;
    auto)
        run_auto
        ;;
    *)
        err "未知模式: $MODE\n使用方法: $0 [mcp | auto | direct] [--backend=<name>]"
        ;;
esac
