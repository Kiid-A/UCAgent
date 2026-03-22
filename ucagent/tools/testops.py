# -*- coding: utf-8 -*-
"""Test operations tools for UCAgent."""

from langchain_core.callbacks import (
    CallbackManagerForToolRun,
)
from .uctool import UCTool
from langchain_core.tools.base import ArgsSchema
from pydantic import BaseModel, Field


from ucagent.util.test_tools import ucagent_lib_path
from ucagent.util.functions import get_toffee_json_test_case, load_toffee_report
from ucagent.util.log import debug, info, warning
import json
import os
import shlex
import shutil
import subprocess
import sys
import psutil
from typing import Tuple


class ArgRunPyTest(BaseModel):
    """Arguments for running a Python test."""
    test_dir_or_file: str = Field(
        ...,
        description="The directory or file containing the Python tests to run."
    )
    pytest_ex_args: str = Field(
        default="",
        description="Additional arguments to pass to pytest, e.g., '-v --capture=no'."
    )
    return_stdout: bool = Field(
        default=False,
        description="Whether to return the standard output of the test run."
    )
    return_stderr: bool = Field(
        default=False,
        description="Whether to return the standard error of the test run."
    )
    timeout: int = Field(
        default=15,
        description="Timeout for the test run in seconds. Default is 15 seconds."
    )


class RunPyTest(UCTool):
    """Tool to run pytest tests in a specified directory or a test file."""

    name: str = "RunPyTest"
    description: str = ("Run pytest tests in a specified directory or a test file."
                        "By default only return if all tests is pass or not.\n"
                        "If arg `return_stdout` is True, it will return the standard output of the test run.\n"
                        "If arg `return_stderr` is True, it will return the standard error of the test run.\n"
                        )
    args_schema: ArgsSchema = ArgRunPyTest
    return_direct: bool = False

    # custom variables
    pytest_args: dict = Field(
        default={},
        description="Additional arguments to pass to pytest, e.g., {'verbose': True, 'capture': 'no'}."
    )

    def do(self,
             test_dir_or_file: str,
             pytest_ex_args: str = "",
             return_stdout: bool = False,
             return_stderr: bool = False,
             timeout: int = 15,
             pytest_ex_env: dict = {},
             run_manager: CallbackManagerForToolRun = None, python_paths: list = None) -> Tuple[int, str, str]:
        """Run the Python tests."""
        assert os.path.exists(test_dir_or_file), \
            f"Test directory or file does not exist: {test_dir_or_file}"
        ret_stdout, ret_stderr = "", ""
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH", "")
        python_path_str = os.path.abspath(os.getcwd()) + ":" + ucagent_lib_path()
        if python_paths is not None:
            for p in python_paths:
                if os.path.exists(p):
                    python_path_str += ":" + os.path.abspath(p)
                    debug(f"Add python path: {p}")
        env["PYTHONPATH"] = python_path_str + ((":" + pythonpath) if pythonpath else "")
        if "XSPCOMM_LOG_LEVEL" not in env:
            env["XSPCOMM_LOG_LEVEL"] = "4"  # 1-DEBUG, 2-INFO, 3-WARNING, 4-ERROR, 5-FATAL
        env.update(pytest_ex_env)
        # Determine the correct working directory and test target
        abs_test_path = os.path.abspath(test_dir_or_file)
        if os.path.isdir(abs_test_path):
            # If it's a directory, set cwd to the directory itself and use relative path
            work_dir = abs_test_path
            if not pytest_ex_args:
                test_target = ["."]
            elif isinstance(pytest_ex_args, str):
                test_target = pytest_ex_args.split()
            elif isinstance(pytest_ex_args, list):
                test_target = pytest_ex_args
            else:
                raise ValueError(f"pytest_ex_args ({pytest_ex_args}) must be a string or a list.")
        else:
            # If it's a file, set cwd to the directory containing the file
            work_dir = os.path.dirname(abs_test_path)
            file_basename = os.path.basename(abs_test_path)
            test_target = [file_basename]
            # Handle pytest_ex_args that may contain absolute paths
            if pytest_ex_args:
                if isinstance(pytest_ex_args, str):
                    test_target.extend(pytest_ex_args.split())
                elif isinstance(pytest_ex_args, list):
                    test_target.extend(pytest_ex_args)
                else:
                    raise ValueError(f"pytest_ex_args ({pytest_ex_args}) must be a string or a list.")

        cmd = ["pytest", "-s", *self.get_pytest_args(), *test_target]
        info(f"Run command: PYTHONPATH={env['PYTHONPATH']} {' '.join(cmd)} (in {work_dir})\n")
        try:
            worker = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE if return_stdout else None,
                stderr=subprocess.PIPE if return_stderr else None,
                text=True,
                env=env,
                bufsize=10,
                cwd=work_dir
            )
            self.pre_call(worker)
            ret_stdout, ret_stderr = worker.communicate(timeout=timeout)  # Set a timeout for the test run
            if not return_stdout:
                ret_stdout = ""
            if not return_stderr:
                ret_stderr = ""
            return True, ret_stdout, ret_stderr
        except subprocess.TimeoutExpired as e:
            try:
                worker.terminate()
                _, alive = psutil.wait_procs([worker], timeout=3)
                if alive:
                    worker.kill()
            except Exception as ex:
                warning(f"Error terminating process: {ex}")
            ret_stdout, ret_stderr = worker.communicate()
            return False, ret_stdout, ret_stderr + f"\nTest run timed out after {e.timeout} seconds. You may try increasing the timeout argment."
        except subprocess.CalledProcessError as e:
            if return_stdout:
                ret_stdout += e.stdout
            if return_stderr:
                ret_stderr += e.stderr
            return False, ret_stdout, ret_stderr + f"\nCalledProcessError: {e}"
        except Exception as e:
            return False, "Test Fail", ret_stderr + f"\Exception: {e}"

    def _run(self,
             test_dir_or_file: str,
             pytest_ex_args: str = "",
             return_stdout: bool = False,
             return_stderr: bool = False,
             timeout: int = 15,
             run_manager: CallbackManagerForToolRun = None) -> str:
        """Run the Python tests and return the output."""
        all_pass, pyt_out, pyt_err = self.do(
            test_dir_or_file,
            pytest_ex_args,
            return_stdout,
            return_stderr,
            timeout,
            run_manager
        )
        ret_str = "Test Pass" if all_pass else "Test Fail\n"
        if return_stdout:
            ret_str += f"Stdout:\n{pyt_out}\n"
        if return_stderr:
            ret_str += f"Stderr:\n{pyt_err}\n"
        return ret_str

    def get_pytest_args(self) -> list:
        """Get additional arguments for pytest."""
        args = []
        for key, value in self.pytest_args.items():
            if isinstance(value, bool):
                if value:
                    args.append(f"--{key}")
            else:
                args.append(f"--{key}={value}")
        return args

    def set_pytest_args(self, py_args):
        """Set additional arguments for pytest."""
        self.pytest_args.update(py_args)
        return self


class RunUnityChipTest(RunPyTest):
    """Tool to run tests in a specified directory or a test file."""

    name: str = "RunUnityChipTest"
    description: str = ("Run tests in a specified directory or a test file. "
                        "This tool is specifically designed for UnityChip tests.\n"
                        "Afert running the tests, it will return:\n"
                        "- The stdout/stderr output of the test run (default off).\n"
                        "- a json test report, include how many tests passed/failed, an overview of the functional coverage/un-coverage data.\n"
                        "If arg `return_stdout` is True, it will return the standard output of the test run.\n"
                        "If arg `return_stderr` is True, it will return the standard error of the test run.\n"
                        )

    # custom variables
    workspace: str = Field(
        default=".",
        description="The workspace directory where the Unity tests are located."
    )
    result_dir: str = Field(
        default="uc_test_report",
        description="Directory to save the Unity test results."
    )
    result_json_path: str = Field(
        default="toffee_report.json",
        description="Path to save the JSON results of the Unity tests."
    )

    def do(self,
             test_dir_or_file: str,
             pytest_ex_args: str = "",
             return_stdout: bool = False,
             return_stderr: bool = False,
             timeout: int = 15,
             pytest_ex_env:dict = {},
             run_manager: CallbackManagerForToolRun = None, return_all_checks=False) -> dict:
        """Run the Unity chip tests."""
        shutil.rmtree(self.result_dir, ignore_errors=True)
        all_pass, pyt_out, pyt_err = RunPyTest.do(self,
                                          os.path.join(self.workspace, test_dir_or_file),
                                          pytest_ex_args,
                                          return_stdout,
                                          return_stderr,
                                          timeout,
                                          pytest_ex_env,
                                          run_manager,
                                          python_paths = [self.workspace, os.path.join(self.workspace, test_dir_or_file)])
        result_json_path = os.path.join(self.result_dir, self.result_json_path)
        ret_data = {
            "run_test_success": all_pass,
        }
        if os.path.exists(result_json_path):
            ret_data = load_toffee_report(result_json_path, self.workspace, all_pass, return_all_checks)
        info(f"Run UnityChip test report:\n{json.dumps(ret_data, indent=2)}\n")
        return ret_data, pyt_out, pyt_err

    def _run(self,
             test_dir_or_file: str,
             pytest_ex_args: str = "",
             return_stdout: bool = False,
             return_stderr: bool = False,
             timeout: int = 15,
             run_manager: CallbackManagerForToolRun = None) -> str:
        """Run the Unity chip tests and return the output."""
        data, pyt_out, pyt_err = self.do(
            test_dir_or_file,
            pytest_ex_args,
            return_stdout,
            return_stderr,
            timeout,
            run_manager
        )
        ret_str = "[Test Report]:\n" + json.dumps(data, indent=2) + "\n"
        if return_stdout:
            ret_str += f"[Stdout]:\n{pyt_out}\n"
        if return_stderr:
            ret_str += f"[Stderr]:\n{pyt_err}\n"
        return ret_str

    def __init__(self, workspace:str=None, report_dir: str = "uc_test_report", **kwargs):
        """Initialize the tool with custom arguments."""
        super().__init__(**kwargs)
        self.set_pytest_args({
            "toffee-report": True,
            "report-dump-json": True,
            "report-name": "index.html",
        })
        self.result_dir = report_dir
        if workspace is None:
            return
        self.set_workspace(workspace)

    def set_workspace(self, workspace: str):
        """Set the workspace directory."""
        self.workspace = os.path.abspath(workspace)
        self.result_dir = os.path.join(self.workspace, self.result_dir)
        self.set_pytest_args({
            "report-dir": self.result_dir
        })
        return self


class ArgRunCocotb(BaseModel):
    """Arguments for running a cocotb simulation."""
    module_name: str = Field(
        ...,
        description="The cocotb test module name to run (for example 'test_counter' or 'tb_packet_gen_and_parse')."
    )
    toplevel: str = Field(
        ...,
        description="The top-level RTL entity/module name (e.g., 'SimpleCounter', 'Adder')."
    )
    sim: str = Field(
        default="verilator",
        description="Simulator to use: 'verilator', 'icarus', 'modelsim', 'vcs', 'questa', etc."
    )
    test_dir: str = Field(
        default=".",
        description="Directory containing the cocotb test and/or Makefile."
    )
    timeout: int = Field(
        default=60,
        description="Timeout for the simulation in seconds."
    )
    return_log: bool = Field(
        default=True,
        description="Whether to return the simulation log output."
    )
    extra_env: dict = Field(
        default={},
        description="Additional environment variables to pass to the simulation."
    )
    run_mode: str = Field(
        default="auto",
        description="Invocation mode: 'auto', 'make', 'pytest', or 'python'."
    )
    make_target: str = Field(
        default="",
        description="Optional make target, such as 'cocotb' or 'run_system_test_server_loopback'."
    )
    make_args: str = Field(
        default="",
        description="Additional make arguments, for example 'TOP_MODULE=mkTop TB_FILE=tb_xxx.py'."
    )
    script_file: str = Field(
        default="",
        description="Python test script to execute when using 'python' or 'pytest' mode."
    )
    pytest_args: str = Field(
        default="",
        description="Additional pytest arguments when using 'pytest' mode."
    )


class RunCocotb(UCTool):
    """Tool to run cocotb simulations for RTL verification.
    
    This tool executes cocotb tests using the standard Makefile-based flow.
    It supports multiple simulators and provides detailed log output for debugging.
    
    Usage example:
        RunCocotb().do(
            module_name="test_counter",
            toplevel="SimpleCounter",
            sim="verilator",
            test_dir="./cocotb_tests",
            timeout=300
        )
    """

    name: str = "RunCocotb"
    description: str = (
        "Run cocotb simulation for RTL verification.\n"
        "Supports setting module name, toplevel entity, and simulator type.\n"
        "Returns simulation pass/fail status and optional log output.\n"
        "Use this tool when you need to verify RTL designs using cocotb framework.\n"
        "Common simulators: verilator (free), icarus (free), modelsim, vcs, questa.\n"
    )
    args_schema: ArgsSchema = ArgRunCocotb
    return_direct: bool = False

    # custom variables
    workspace: str = Field(
        default=".",
        description="The workspace directory for cocotb tests."
    )
    result_dir: str = Field(
        default="cocotb_results",
        description="Directory to save cocotb simulation results."
    )

    def _split_cli_args(self, value) -> list[str]:
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return shlex.split(value)
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value]
        raise ValueError(f"Unsupported command argument type: {type(value)}")

    def _resolve_test_dir(self, test_dir: str) -> str:
        base_dir = self.workspace if getattr(self, "workspace", None) else os.getcwd()
        if not test_dir or test_dir == ".":
            return os.path.abspath(base_dir)
        if os.path.isabs(test_dir):
            return os.path.abspath(test_dir)
        return os.path.abspath(os.path.join(base_dir, test_dir))

    def _resolve_script_path(self, abs_test_dir: str, script_file: str) -> str | None:
        if not script_file:
            return None
        if os.path.isabs(script_file):
            return os.path.abspath(script_file)
        return os.path.abspath(os.path.join(abs_test_dir, script_file))

    def do(self,
           module_name: str,
           toplevel: str,
           sim: str = "verilator",
           test_dir: str = ".",
           timeout: int = 60,
           return_log: bool = True,
           extra_env: dict = {},
           run_mode: str = "auto",
           make_target: str = "",
           make_args: str = "",
           script_file: str = "",
           pytest_args: str = "",
           run_manager: CallbackManagerForToolRun = None) -> Tuple[bool, str, str]:
        """Run a cocotb simulation.

        Supports the standard Makefile-based flow, pytest-based cocotb flow,
        and direct execution of project-specific cocotb Python scripts.
        """
        import psutil

        ret_stdout, ret_stderr = "", ""
        env = os.environ.copy()

        env["MODULE"] = module_name
        env["TOPLEVEL"] = toplevel
        env["SIM"] = sim
        env["TOPLEVEL_LANG"] = env.get("TOPLEVEL_LANG", "verilog")
        env.update({k: str(v) for k, v in (extra_env or {}).items()})

        abs_test_dir = self._resolve_test_dir(test_dir)
        if not os.path.exists(abs_test_dir):
            return False, "", f"Test directory does not exist: {abs_test_dir}"

        default_script = script_file or f"{module_name}.py"
        abs_script_path = self._resolve_script_path(abs_test_dir, default_script) if default_script else None
        if abs_script_path and not os.path.exists(abs_script_path):
            abs_script_path = None

        python_paths = [os.path.abspath(os.getcwd()), abs_test_dir]
        if abs_script_path:
            script_dir = os.path.dirname(abs_script_path)
            if script_dir and script_dir not in python_paths:
                python_paths.append(script_dir)
        pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = ":".join([p for p in python_paths if p] + ([pythonpath] if pythonpath else []))

        makefile_path = os.path.join(abs_test_dir, "Makefile")
        has_makefile = os.path.exists(makefile_path)
        run_mode = (run_mode or "auto").lower()
        if run_mode == "auto":
            if has_makefile and (make_target or make_args):
                run_mode = "make"
            elif abs_script_path is not None:
                run_mode = "python"
            elif has_makefile:
                run_mode = "make"
            else:
                run_mode = "pytest"

        work_dir = abs_test_dir
        if run_mode == "make":
            if not has_makefile:
                return False, "", f"Makefile not found in test directory: {abs_test_dir}"
            cmd = ["make", *self._split_cli_args(make_target), *self._split_cli_args(make_args)]
        elif run_mode == "python":
            if abs_script_path is None:
                return False, "", f"Python cocotb script not found: {script_file or default_script}"
            script_arg = os.path.relpath(abs_script_path, abs_test_dir) if abs_script_path.startswith(abs_test_dir) else abs_script_path
            cmd = [sys.executable, script_arg]
        elif run_mode == "pytest":
            cmd = ["pytest", "-s"]
            if abs_script_path is not None:
                script_arg = os.path.relpath(abs_script_path, abs_test_dir) if abs_script_path.startswith(abs_test_dir) else abs_script_path
                cmd.append(script_arg)
            else:
                cmd.append(f"--cocotb-module={module_name}")
            cmd.extend(self._split_cli_args(pytest_args))
        else:
            return False, "", f"Unsupported run_mode: {run_mode}"

        info(f"Run cocotb [{run_mode}]: {' '.join(cmd)} MODULE={module_name} TOPLEVEL={toplevel} SIM={sim} (in {work_dir})")
        
        try:
            worker = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE if return_log else subprocess.DEVNULL,
                stderr=subprocess.PIPE if return_log else subprocess.DEVNULL,
                text=True,
                env=env,
                bufsize=1,
                cwd=work_dir
            )
            self.pre_call(worker)
            ret_stdout, ret_stderr = worker.communicate(timeout=timeout)
            success = worker.returncode == 0
            return success, ret_stdout if return_log else "", ret_stderr if return_log else ""
            
        except subprocess.TimeoutExpired as e:
            try:
                worker.terminate()
                _, alive = psutil.wait_procs([worker], timeout=3)
                if alive:
                    worker.kill()
            except Exception as ex:
                warning(f"Error terminating process: {ex}")
            ret_stdout, ret_stderr = worker.communicate()
            return False, ret_stdout, ret_stderr + f"\nSimulation timed out after {timeout} seconds. Consider increasing timeout."
            
        except FileNotFoundError:
            return False, "", f"Command not found: {cmd[0]}. Please ensure the required runtime is installed and available in PATH."
            
        except Exception as e:
            return False, "", f"Error running cocotb: {str(e)}"

    def _run(self,
             module_name: str,
             toplevel: str,
             sim: str = "verilator",
             test_dir: str = ".",
             timeout: int = 60,
             return_log: bool = True,
             extra_env: dict = {},
             run_mode: str = "auto",
             make_target: str = "",
             make_args: str = "",
             script_file: str = "",
             pytest_args: str = "",
             run_manager: CallbackManagerForToolRun = None) -> str:
        """Run cocotb simulation and return formatted result."""
        success, stdout, stderr = self.do(
            module_name,
            toplevel,
            sim,
            test_dir,
            timeout,
            return_log,
            extra_env,
            run_mode,
            make_target,
            make_args,
            script_file,
            pytest_args,
            run_manager
        )
        
        result = f"=== Cocotb Simulation {'PASSED' if success else 'FAILED'} ===\n"
        result += f"Module: {module_name}\n"
        result += f"Toplevel: {toplevel}\n"
        result += f"Simulator: {sim}\n"
        
        if return_log:
            if stdout:
                result += f"\n=== STDOUT ===\n{stdout}\n"
            if stderr:
                result += f"\n=== STDERR ===\n{stderr}\n"
        
        if not success:
            result += "\n=== FAILURE ANALYSIS ===\n"
            result += "Check the log output above for error messages.\n"
            result += "Common issues:\n"
            result += "  - Simulator not installed or not in PATH\n"
            result += "  - RTL compilation errors\n"
            result += "  - Cocotb test assertion failures\n"
            result += "  - Timeout (increase timeout argument if needed)\n"
        
        return result

    def __init__(self, workspace: str = None, result_dir: str = "cocotb_results", **kwargs):
        """Initialize the RunCocotb tool."""
        super().__init__(**kwargs)
        self.result_dir = result_dir
        if workspace is not None:
            self.set_workspace(workspace)

    def set_workspace(self, workspace: str):
        """Set the workspace directory."""
        self.workspace = os.path.abspath(workspace)
        self.result_dir = os.path.join(self.workspace, self.result_dir)
        return self
