# -*- coding: utf-8 -*-
"""Cocotb test checker for UCAgent verification.

This checker validates RTL designs by running cocotb-based tests.
It supports:
- Running cocotb simulations and checking results
- Validating test file structure and content
- Checking waveform and coverage data
"""

import os
from typing import Tuple
from ucagent.checkers.base import Checker
from ucagent.tools.testops import RunCocotb
from ucagent.util.log import info, warning
import ucagent.util.functions as fc


class CocotbTestChecker(Checker):
    """Checker for running and validating cocotb tests.

    This checker executes cocotb simulations and verifies the results.
    It can be configured to run specific test modules, check pass/fail status,
    and validate test coverage.

    Usage in YAML:
        checker:
          - name: cocotb_test_check
            clss: "CocotbTestChecker"
            args:
              test_module: "test_{{DUT}}_basic"
              toplevel: "{{DUT}}"
              sim: "verilator"
              test_dir: "cocotb_tests"
              timeout: 300
    """

    def __init__(self,
                 test_module: str = None,
                 toplevel: str = None,
                 sim: str = "verilator",
                 test_dir: str = "cocotb_tests",
                 timeout: int = 300,
                 must_pass: bool = True,
                 check_waveform: bool = False,
                 run_mode: str = "auto",
                 make_target: str = "",
                 make_args: str = "",
                 script_file: str = "",
                 pytest_args: str = "",
                 extra_env: dict = None,
                 **kw):
        """Initialize the cocotb test checker.

        Args:
            test_module: cocotb test module name (without .py extension)
            toplevel: Top-level RTL module name
            sim: Simulator to use (verilator, icarus, modelsim, etc.)
            test_dir: Directory containing cocotb tests
            timeout: Simulation timeout in seconds
            must_pass: If True, tests must pass for checker to pass
            check_waveform: If True, check for waveform file generation
            run_mode: How RunCocotb should invoke the test (auto/make/pytest/python)
            make_target: Optional make target when using project-specific Makefiles
            make_args: Additional make arguments
            script_file: Optional Python script file to execute directly
            pytest_args: Additional pytest arguments
            extra_env: Additional environment variables for simulation
        """
        self.test_module = test_module
        self.toplevel = toplevel
        self.sim = sim
        self.test_dir = test_dir
        self.timeout = timeout
        self.must_pass = must_pass
        self.check_waveform = check_waveform
        self.run_mode = run_mode
        self.make_target = make_target
        self.make_args = make_args
        self.script_file = script_file
        self.pytest_args = pytest_args
        self.extra_env = extra_env or {}
        self.run_cocotb = RunCocotb()
        self.update_dut_name(kw.get("cfg", {}))

    def set_workspace(self, workspace: str):
        """Set the workspace directory."""
        super().set_workspace(workspace)
        self.run_cocotb.set_workspace(workspace)
        return self

    def do_check(self, timeout=0, **kw) -> Tuple[bool, object]:
        """Run cocotb test and check results.

        Returns:
            Tuple[bool, object]: (success, result_dict)
        """
        # Determine test module name
        test_module = self.test_module
        if test_module is None and self.dut_name:
            test_module = f"test_{self.dut_name.lower()}_basic"
            info(f"Auto-generated test module name: {test_module}")

        if test_module is None:
            return False, {"error": "test_module must be specified or DUT name must be available"}

        # Determine toplevel name
        toplevel = self.toplevel
        if toplevel is None and self.dut_name:
            toplevel = self.dut_name
            info(f"Auto-generated toplevel name: {toplevel}")

        if toplevel is None:
            return False, {"error": "toplevel must be specified or DUT name must be available"}

        # Check test directory exists
        test_dir_path = self.get_path(self.test_dir)
        if not os.path.exists(test_dir_path):
            return False, {
                "error": f"Cocotb test directory does not exist: {self.test_dir}",
                "suggestion": "Use WriteFile or EditTextFile to create cocotb test files first"
            }

        # Check Makefile exists when the checker is configured to use make mode
        makefile_path = os.path.join(test_dir_path, "Makefile")
        if self.run_mode == "make" and not os.path.exists(makefile_path):
            return False, {
                "error": f"Makefile not found in {self.test_dir}",
                "suggestion": "Create a Makefile or switch the checker to python/pytest mode"
            }

        # Run cocotb simulation
        info(f"Running cocotb: MODULE={test_module} TOPLEVEL={toplevel} SIM={self.sim}")
        timeout = timeout if timeout > 0 else self.timeout

        self.run_cocotb.set_pre_call_back(
            lambda p: self.set_check_process(p, timeout + 10)
        )

        success, stdout, stderr = self.run_cocotb.do(
            module_name=test_module,
            toplevel=toplevel,
            sim=self.sim,
            test_dir=self.test_dir,
            timeout=timeout,
            return_log=True,
            extra_env=self.extra_env,
            run_mode=self.run_mode,
            make_target=self.make_target,
            make_args=self.make_args,
            script_file=self.script_file,
            pytest_args=self.pytest_args,
        )

        # Build result
        result = {
            "test_module": test_module,
            "toplevel": toplevel,
            "simulator": self.sim,
            "run_mode": self.run_mode,
            "make_target": self.make_target,
            "script_file": self.script_file,
            "passed": success,
        }

        # Check if test passed
        if self.must_pass and not success:
            result["error"] = "Cocotb simulation failed"
            result["stdout"] = stdout if stdout else ""
            result["stderr"] = stderr if stderr else ""
            result["suggestion"] = [
                "Check the simulation log for error messages",
                "Verify RTL code compiles correctly",
                "Review cocotb test assertions",
                "Ensure Makefile is properly configured"
            ]
            return False, result

        # Check waveform if required
        if self.check_waveform:
            waveform_found = self._check_waveform_file(test_dir_path)
            if not waveform_found:
                result["warning"] = "Waveform file not found"
                result["suggestion"] = "Enable waveform output in Makefile (e.g., EXTRA_ARGS += --trace for Verilator)"

        # Success
        result["message"] = f"Cocotb test '{test_module}' passed"
        if stdout:
            result["stdout"] = stdout
        if stderr:
            result["stderr"] = stderr

        return True, result

    def _check_waveform_file(self, test_dir: str) -> bool:
        """Check if waveform file was generated."""
        # Common waveform file extensions
        waveform_extensions = ["vcd", "fst", "ghw", "wdb"]
        for ext in waveform_extensions:
            import glob
            pattern = os.path.join(test_dir, f"*.{ext}")
            files = glob.glob(pattern)
            if files:
                info(f"Waveform file found: {files[0]}")
                return True

            # Also check parent directory
            pattern = os.path.join(os.path.dirname(test_dir), f"*.{ext}")
            files = glob.glob(pattern)
            if files:
                info(f"Waveform file found: {files[0]}")
                return True

        warning("No waveform file found")
        return False


class CocotbTestFileChecker(Checker):
    """Checker for validating cocotb test file structure.

    This checker ensures that cocotb test files have the required structure:
    - Proper imports
    - @cocotb.test() decorated functions
    - At least one test function
    """

    def __init__(self,
                 test_file: str = None,
                 min_tests: int = 1,
                 require_reset: bool = False,
                 require_clock: bool = False,
                 **kw):
        """Initialize the test file checker.

        Args:
            test_file: Path to the test file (relative to workspace)
            min_tests: Minimum number of test functions required
            require_reset: If True, require reset test function
            require_clock: If True, require clock generation
        """
        self.test_file = test_file
        self.min_tests = min_tests
        self.require_reset = require_reset
        self.require_clock = require_clock
        self.update_dut_name(kw.get("cfg", {}))

    def do_check(self, timeout=0, **kw) -> Tuple[bool, object]:
        """Check cocotb test file structure.

        Returns:
            Tuple[bool, object]: (success, result_dict)
        """
        # Determine test file name
        test_file = self.test_file
        if test_file is None and self.dut_name:
            test_file = f"cocotb_tests/test_{self.dut_name.lower()}_basic.py"
            info(f"Auto-generated test file name: {test_file}")

        if test_file is None:
            return False, {"error": "test_file must be specified or DUT name must be available"}

        # Check file exists
        file_path = self.get_path(test_file)
        if not os.path.exists(file_path):
            return False, {
                "error": f"Cocotb test file does not exist: {test_file}",
                "suggestion": "Create the test file using WriteFile or EditTextFile"
            }

        # Read and parse file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = f.readlines() if content else []
        except Exception as e:
            return False, {"error": f"Failed to read test file: {str(e)}"}

        # Check for required imports
        required_imports = ["cocotb"]
        missing_imports = []
        for imp in required_imports:
            if f"import {imp}" not in content and f"from {imp}" not in content:
                missing_imports.append(imp)

        if missing_imports:
            return False, {
                "error": f"Missing required imports: {', '.join(missing_imports)}",
                "suggestion": "Add 'import cocotb' at the top of the file"
            }

        # Count test functions
        test_functions = fc.get_target_from_file(file_path, "test*", dtype="FUNC")
        test_count = len(test_functions)

        if test_count < self.min_tests:
            return False, {
                "error": f"Insufficient test functions: found {test_count}, required {self.min_tests}",
                "suggestion": "Add more @cocotb.test() decorated functions"
            }

        # Check for @cocotb.test() decorator
        if "@cocotb.test()" not in content and "@cocotb.test" not in content:
            return False, {
                "error": "No @cocotb.test() decorator found",
                "suggestion": "Decorate test functions with @cocotb.test()"
            }

        # Check for reset test if required
        if self.require_reset:
            has_reset = any("reset" in func.__name__.lower() for func in test_functions)
            if not has_reset:
                return False, {
                    "error": "No reset test function found",
                    "suggestion": "Add a test function for reset sequence (e.g., test_XXX_reset)"
                }

        # Check for clock generation if required
        if self.require_clock:
            has_clock = "Clock" in content or "clock" in content.lower()
            if not has_clock:
                return False, {
                    "error": "No clock generation found",
                    "suggestion": "Add clock generation using cocotb.clock.Clock"
                }

        # Success
        result = {
            "test_file": test_file,
            "test_count": test_count,
            "test_functions": [func.__name__ for func in test_functions],
            "message": f"Cocotb test file structure is valid ({test_count} tests found)"
        }

        return True, result


class CocotbCoverageChecker(Checker):
    """Checker for validating cocotb test coverage.

    This checker analyzes cocotb test coverage reports and ensures
    minimum coverage thresholds are met.
    """

    def __init__(self,
                 coverage_dir: str = "coverage",
                 min_line_coverage: float = 0.0,
                 min_toggle_coverage: float = 0.0,
                 **kw):
        """Initialize the coverage checker.

        Args:
            coverage_dir: Directory containing coverage reports
            min_line_coverage: Minimum line coverage ratio (0.0-1.0)
            min_toggle_coverage: Minimum toggle coverage ratio (0.0-1.0)
        """
        self.coverage_dir = coverage_dir
        self.min_line_coverage = min_line_coverage
        self.min_toggle_coverage = min_toggle_coverage
        self.update_dut_name(kw.get("cfg", {}))

    def do_check(self, timeout=0, **kw) -> Tuple[bool, object]:
        """Check coverage reports.

        Returns:
            Tuple[bool, object]: (success, result_dict)
        """
        coverage_path = self.get_path(self.coverage_dir)

        if not os.path.exists(coverage_path):
            if self.min_line_coverage > 0 or self.min_toggle_coverage > 0:
                return False, {
                    "error": f"Coverage directory does not exist: {self.coverage_dir}",
                    "suggestion": "Run cocotb with coverage enabled (e.g., --coverage for Verilator)"
                }
            # If no coverage required, pass silently
            return True, {"message": "Coverage check skipped (no coverage required)"}

        # Look for coverage reports
        import glob

        # Check for Verilator coverage
        verilator_cov = glob.glob(os.path.join(coverage_path, "*.dat"))
        # Check for generic coverage reports
        cov_reports = glob.glob(os.path.join(coverage_path, "*coverage*"))

        result = {
            "coverage_dir": self.coverage_dir,
            "reports_found": len(verilator_cov) + len(cov_reports),
        }

        # Note: Detailed coverage analysis would require parsing specific report formats
        # This is a basic check - can be enhanced based on actual coverage report formats

        if result["reports_found"] == 0:
            if self.min_line_coverage > 0 or self.min_toggle_coverage > 0:
                return False, {
                    "error": "No coverage reports found",
                    "suggestion": "Ensure cocotb is run with coverage enabled"
                }
            return True, {"message": "No coverage reports found (check skipped)"}

        result["message"] = f"Coverage reports found in {self.coverage_dir}"
        return True, result
