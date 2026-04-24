##################################
# build_plan.py
#
# Jordan Carlin jcarlin@hmc.edu 11 March 2026
# SPDX-License-Identifier: Apache-2.0
#
# Construct a list[BuildTask] DAG that mirrors the compilation pipeline
# previously expressed as generated Makefiles.
##################################

import importlib.resources
from collections import defaultdict
from pathlib import Path

from act.build import BuildTask, PythonAction, SubprocessAction, SymlinkAction
from act.config import CompilerType, Config, CoverageSimulator
from act.coverreport import generate_report, merge_summaries
from act.parse_test_constraints import TestMetadata
from act.sail_to_rvvi import sailLog2Trace
from act.sig_modify import process_signature_file
from act.trap_report import generate_trap_report

OBJDUMP_FLAGS = ["-Stsxd", "-M", "no-aliases,numeric"]
SAIL_TIMEOUT = 1800  # 30-minute timeout for Sail simulator runs (allows for parallel CPU contention)
COVERAGE_SIM_TIMEOUT = 1800  # 30-minute timeout for coverage simulator runs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compiler_cmd(config: Config, xlen: int, tests_dir: Path) -> list[str]:
    """Build the full compiler command list including compiler-specific and common flags."""
    cmd = [str(config.compiler_exe)]
    if config.compiler_type == CompilerType.CLANG:
        cmd.extend([f"--target=riscv{xlen}", "-fuse-ld=lld"])
    cmd.extend(
        [
            f"-I{config.dut_include_dir.absolute()}",
            f"-T{config.linker_script.absolute()}",
            "-O0",
            "-g",
            "-mcmodel=medany",
            "-nostdlib",
            f"-I{tests_dir}/env",
        ]
    )
    if config.compiler_type == CompilerType.GCC:
        cmd.extend(["-Wl,--no-warn-rwx-segments"])
    return cmd


def _write_tracelist(tracelist_file: Path, coverage_group: Path, all_traces: tuple[Path, ...]) -> None:
    """Write a tracelist file containing all rvvi traces (which are guaranteed to exist
    by hard dependencies on the rvvi conversion tasks)."""
    contents = (
        f"# Tests for coverage group: {coverage_group}\n"
        "# Generated automatically by riscv-arch-test act framework\n" + "\n".join(str(t) for t in sorted(all_traces))
    )
    if not tracelist_file.exists() or tracelist_file.read_text() != contents:
        tracelist_file.write_text(contents)


# ---------------------------------------------------------------------------
# Per-test task generators
# ---------------------------------------------------------------------------


def gen_compile_tasks(
    test_name: Path,
    test_metadata: TestMetadata,
    base_dir: Path,
    xlen: int,
    config: Config,
    compiler_cmd: list[str],
    compile_inputs: tuple[Path, ...] = (),
    sail_inputs: tuple[Path, ...] = (),
    debug: bool = False,
    fast: bool = False,
) -> list[BuildTask]:
    """Generate BuildTasks for the compilation pipeline of a single test.

    Build Pipeline:
        add.S -> add.sig.elf -> add.sig (sail) -> add.results (sig_modify) -> add.elf
        Optional: add.sig.elf.objdump (if debug), add.elf.objdump (if not fast)

    Args:
        test_name: Name of the test.
        test_metadata: Metadata for the test.
        base_dir: Base directory for the build.
        xlen: XLEN (32 or 64).
        config: Configuration object.
        compiler_cmd: Pre-built compiler command prefix (from _compiler_cmd).
        compile_inputs: Shared inputs for compilation (env headers, DUT headers, linker script).
        sail_inputs: Shared inputs for the Sail reference model (e.g. sail.json).
        debug: Whether to generate debug output (signature objdump and trace files).
        fast: Whether to disable objdump generation for faster builds.
    """
    tasks: list[BuildTask] = []

    # Paths
    build_dir = base_dir / "build"
    elf_dir = base_dir / "elfs"
    sig_elf = build_dir / test_name.with_suffix(".sig.elf")
    sig_file = build_dir / test_name.with_suffix(".sig")
    result_file = build_dir / test_name.with_suffix(".results")
    sig_trace_file = build_dir / test_name.with_suffix(".sig.trace")
    sig_log_file = build_dir / test_name.with_suffix(".sig.log")
    final_elf = elf_dir / test_name.with_suffix(".elf")
    sail_config_path = config.dut_include_dir / "sail.json"

    # Metadata — substitute ${XLEN} placeholder used by priv tests
    march = test_metadata.march.replace("${XLEN}", str(xlen))
    test_flen = test_metadata.flen
    test_path = test_metadata.test_path
    mabi = f"{'i' if xlen == 32 else ''}lp{xlen}{'e' if test_metadata.e_ext else ''}"

    # 1. sig.elf – compile with -DSIGNATURE
    sig_elf_cmd = [
        *compiler_cmd,
        "-o",
        str(sig_elf),
        f"-march={march}",
        f"-mabi={mabi}",
        "-DSIGNATURE",
        f"-DXLEN={xlen}",
        f"-DTEST_FLEN={test_flen}",
        str(test_path),
    ]
    tasks.append(
        BuildTask(
            outputs=(sig_elf,),
            extra_inputs=(test_path, *compile_inputs),
            action=SubprocessAction(cmd=sig_elf_cmd),
        )
    )

    # 1a. sig.elf.objdump (optional, debug only)
    if debug and config.objdump_exe is not None:
        objdump_file = Path(f"{sig_elf}.objdump")
        tasks.append(
            BuildTask(
                outputs=(objdump_file,),
                deps=(sig_elf,),
                action=SubprocessAction(
                    cmd=[str(config.objdump_exe), *OBJDUMP_FLAGS, str(sig_elf)],
                    stdout_file=objdump_file,
                ),
            )
        )

    # 2. sig – run Sail reference model
    sail_cmd = [str(config.ref_model_exe)]
    if debug:
        sail_cmd.append("--trace-all")
        sail_cmd.extend(["--trace-output", str(sig_trace_file)])
    sail_cmd.extend(["--config", str(sail_config_path)])
    sail_cmd.extend(config.ref_model_type.signature_flags(sig_file, xlen // 8))
    sail_cmd.append(str(sig_elf))

    tasks.append(
        BuildTask(
            outputs=(sig_file,),
            deps=(sig_elf,),
            extra_inputs=sail_inputs,
            action=SubprocessAction(cmd=sail_cmd, stdout_file=sig_log_file, timeout=SAIL_TIMEOUT),
        )
    )

    # 2a. trap report (optional, debug only)
    if debug:
        trap_report_file = Path(f"{sig_file}.trap_report")
        # Derive nm executable from objdump executable (e.g. riscv64-unknown-elf-objdump -> riscv64-unknown-elf-nm)
        nm_exe: Path | None = None
        if config.objdump_exe is not None:
            candidate = Path(str(config.objdump_exe).replace("objdump", "nm"))
            if candidate.exists():
                nm_exe = candidate
        tasks.append(
            BuildTask(
                outputs=(trap_report_file,),
                deps=(sig_file,),
                extra_inputs=(sig_elf,),
                action=PythonAction(fn=generate_trap_report, args=(sig_file, xlen, sig_elf, nm_exe)),
            )
        )

    # 3. results – process signature file
    tasks.append(
        BuildTask(
            outputs=(result_file,),
            deps=(sig_file,),
            action=PythonAction(fn=process_signature_file, args=(sig_file, xlen)),
        )
    )

    # 4. final.elf – compile with -DRVTEST_SELFCHECK
    final_elf_cmd = [
        *compiler_cmd,
        "-o",
        str(final_elf),
        f"-march={march}",
        f"-mabi={mabi}",
        "-DRVTEST_SELFCHECK",
        f"-DXLEN={xlen}",
        f"-DTEST_FLEN={test_flen}",
        f'-DSIGNATURE_FILE="{result_file}"',
        str(test_path),
    ]
    tasks.append(
        BuildTask(
            outputs=(final_elf,),
            extra_inputs=(test_path, *compile_inputs),
            deps=(result_file,),
            action=SubprocessAction(cmd=final_elf_cmd),
        )
    )

    # 4a. final.elf.objdump (optional, not in fast mode)
    if not fast and config.objdump_exe is not None:
        objdump_file = Path(f"{final_elf}.objdump")
        tasks.append(
            BuildTask(
                outputs=(objdump_file,),
                deps=(final_elf,),
                action=SubprocessAction(
                    cmd=[str(config.objdump_exe), *OBJDUMP_FLAGS, str(final_elf)],
                    stdout_file=objdump_file,
                ),
            )
        )

    return tasks


def gen_rvvi_tasks(
    test_name: Path,
    base_dir: Path,
    config: Config,
    sail_inputs: tuple[Path, ...] = (),
    fast: bool = False,
) -> list[BuildTask]:
    """Generate BuildTasks for RVVI trace generation (coverage pipeline)."""
    tasks: list[BuildTask] = []

    # Paths
    coverage_dir = base_dir / "coverage"
    elf_dir = base_dir / "elfs"
    elf = elf_dir / test_name.with_suffix(".elf")
    objdump_link = coverage_dir / test_name.with_suffix(".elf.objdump")
    sail_trace = coverage_dir / test_name.with_suffix(".trace")
    sail_log = coverage_dir / test_name.with_suffix(".log")
    rvvi_trace = coverage_dir / test_name.with_suffix(".rvvi")

    # Symlink objdump into coverage dir
    if not fast and config.objdump_exe is not None:
        objdump_orig_file = Path(f"{elf}.objdump")
        tasks.append(
            BuildTask(
                outputs=(objdump_link,),
                deps=(elf,),
                action=SymlinkAction(src=objdump_orig_file, dst=objdump_link),
            )
        )

    # Run Sail with trace
    sail_cmd = [
        str(config.ref_model_exe),
        "--trace-all",
        "--trace-output",
        str(sail_trace),
        "--config",
        str(config.dut_include_dir / "sail.json"),
        str(elf),
    ]
    tasks.append(
        BuildTask(
            outputs=(sail_trace,),
            deps=(elf,),
            extra_inputs=sail_inputs,
            action=SubprocessAction(cmd=sail_cmd, stdout_file=sail_log, timeout=SAIL_TIMEOUT),
        )
    )

    # Convert to RVVI
    tasks.append(
        BuildTask(
            outputs=(rvvi_trace,),
            deps=(sail_trace,),
            action=PythonAction(fn=sailLog2Trace, args=(sail_trace, rvvi_trace)),
        )
    )

    return tasks


def gen_coverage_tasks(
    coverage_targets: dict[Path, list[Path]],
    coverpoint_dir: Path,
    base_dir: Path,
    config_report_dir: Path,
    dut_header_dir: Path,
    coverage_simulator: CoverageSimulator,
) -> list[BuildTask]:
    """Generate BuildTasks for coverage UCDB generation, reports, and summary merging."""
    tasks: list[BuildTask] = []
    coverage_reports: list[Path] = []

    # Resolve package resources once for use in commands and dependency tracking.
    # Uses importlib.resources.files() which returns a real filesystem path when the
    # package is installed from source (the current workflow). If act is ever published
    # as a zipped wheel, these resources will need to be materialized via as_file() with
    # a context that spans task execution.
    act_resources = importlib.resources.files("act")
    fcov_path = Path(str(act_resources / "fcov")).absolute()
    script_name = "riscv-arch-test.do" if coverage_simulator == CoverageSimulator.QUESTA else "riscv-arch-test-vcs.sh"
    sim_script = Path(str(act_resources / script_name)).absolute()

    # Collect file dependencies for staleness checking.
    # Coverage simulation depends on coverpoints, fcov infrastructure, DUT config headers, and the simulator script.
    coverpoint_files = tuple(sorted(p.absolute() for p in coverpoint_dir.rglob("*") if p.is_file()))
    fcov_files = tuple(sorted(p.absolute() for p in fcov_path.rglob("*") if p.is_file()))
    dut_svh_files = tuple(sorted(p.absolute() for p in dut_header_dir.iterdir() if p.suffix == ".svh"))
    coverage_inputs = (*coverpoint_files, *fcov_files, *dut_svh_files, sim_script)

    for coverage_group, traces in sorted(coverage_targets.items()):
        # Paths
        coverage_dir = base_dir / coverage_group
        base_name = coverage_dir / coverage_group.stem
        tracelist_file = base_name.with_suffix(".tracelist")
        coverage_db_ext = "ucdb" if coverage_simulator == CoverageSimulator.QUESTA else "vdb"
        simulator_artifact = base_name.with_suffix(f".{coverage_db_ext}")
        simulator_log = base_name.with_suffix(f".{coverage_db_ext}.log")
        work_dir = base_name.parent / f"{coverage_db_ext}_work"
        report_file_base = config_report_dir / coverage_group.stem
        summary_file = Path(f"{report_file_base}_summary.txt")

        # Deps: all rvvi traces for this coverage group
        rvvi_deps = tuple(sorted(traces))

        # Tracelist generation task: hard-deps on all rvvi traces (failure propagates).
        tracelist_file.parent.mkdir(parents=True, exist_ok=True)
        tasks.append(
            BuildTask(
                outputs=(tracelist_file,),
                deps=rvvi_deps,
                action=PythonAction(fn=_write_tracelist, args=(tracelist_file, coverage_group, rvvi_deps)),
            )
        )

        # Coverage collection task
        if coverage_simulator == CoverageSimulator.QUESTA:
            do_script = (
                f"do {sim_script} "
                f"{tracelist_file} "
                f"{simulator_artifact} "
                f"{work_dir} "
                f"{fcov_path} "
                f"{coverpoint_dir} "
                f"{dut_header_dir} "
                f"{{{coverage_group.stem.upper()}_COVERAGE}}"
            )
            coverage_cmd = ["vsim", "-c", "-do", do_script]
        else:
            coverage_cmd = [
                "bash",
                str(sim_script),
                str(tracelist_file),
                str(simulator_artifact),
                str(work_dir),
                str(fcov_path),
                str(coverpoint_dir),
                str(dut_header_dir),
                f"{coverage_group.stem.upper()}_COVERAGE",
            ]

        tasks.append(
            BuildTask(
                outputs=(simulator_artifact,),
                deps=(tracelist_file,),
                extra_inputs=coverage_inputs,
                action=SubprocessAction(
                    cmd=coverage_cmd, stdout_file=simulator_log, cwd=coverage_dir, timeout=COVERAGE_SIM_TIMEOUT
                ),
            )
        )

        # Coverage report generation
        coverage_reports.append(summary_file)
        tasks.append(
            BuildTask(
                outputs=(summary_file,),
                deps=(simulator_artifact,),
                action=PythonAction(
                    fn=generate_report, args=(simulator_artifact, report_file_base, coverage_simulator)
                ),
            )
        )

    # Overall summary merging — hard deps so any failure propagates.
    if coverage_reports:
        overall_summary = config_report_dir / "_overall_summary.txt"
        report_deps = tuple(sorted(coverage_reports))
        tasks.append(
            BuildTask(
                outputs=(overall_summary,),
                deps=report_deps,
                action=PythonAction(fn=merge_summaries, args=(sorted(coverage_reports), overall_summary)),
            )
        )

    return tasks


# ---------------------------------------------------------------------------
# Top-level build plan construction
# ---------------------------------------------------------------------------


def generate_build_plan(
    config: Config,
    xlen: int,
    selected_tests: dict[str, TestMetadata],
    tests_dir: Path,
    coverpoint_dir: Path,
    workdir: Path,
    coverage_enabled: bool,
    coverage_simulator: CoverageSimulator,
    debug: bool = False,
    fast: bool = False,
) -> list[BuildTask]:
    """Build the full DAG of tasks for a single config."""
    tasks: list[BuildTask] = []

    config_wkdir = workdir / config.name
    config_coverage_dir = config_wkdir / "coverage"
    config_report_dir = config_wkdir / "reports"

    coverage_targets: defaultdict[Path, list[Path]] = defaultdict(list)
    compiler_cmd = _compiler_cmd(config, xlen, tests_dir)

    # Collect shared file dependencies that affect all compilations.
    # Any change to env headers, DUT headers, or the linker script should trigger recompilation.
    env_headers = tuple(sorted(p.absolute() for p in (tests_dir / "env").iterdir() if p.is_file()))
    dut_headers = tuple(sorted(p.absolute() for p in config.dut_include_dir.iterdir() if p.suffix == ".h"))
    compile_inputs = (*env_headers, *dut_headers, config.linker_script.absolute())

    # Sail config affects reference model output
    sail_config = config.dut_include_dir / "sail.json"
    sail_inputs = (sail_config.absolute(),) if sail_config.exists() else ()

    for test_name_str, test_metadata in sorted(selected_tests.items()):
        test_name = Path(test_name_str)

        # Compile test
        tasks.extend(
            gen_compile_tasks(
                test_name,
                test_metadata,
                config_wkdir,
                xlen,
                config,
                compiler_cmd,
                compile_inputs,
                sail_inputs,
                debug,
                fast,
            )
        )

        # Coverage trace generation
        if coverage_enabled:
            trace_name = test_name.with_suffix(".rvvi")
            trace_path = config_coverage_dir / trace_name
            coverage_group_dir = trace_path.parent.relative_to(config_coverage_dir)
            coverage_targets[coverage_group_dir].append(trace_path.absolute())

            tasks.extend(
                gen_rvvi_tasks(
                    test_name,
                    config_wkdir,
                    config,
                    sail_inputs,
                    fast,
                )
            )

    # Coverage report tasks
    if coverage_enabled and coverage_targets:
        tasks.extend(
            gen_coverage_tasks(
                coverage_targets,
                coverpoint_dir,
                config_coverage_dir,
                config_report_dir,
                config.dut_include_dir,
                coverage_simulator,
            )
        )

    return tasks
