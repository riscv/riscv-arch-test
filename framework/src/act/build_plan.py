##################################
# build_plan.py
#
# Jordan Carlin jcarlin@hmc.edu 11 March 2026
# SPDX-License-Identifier: Apache-2.0
#
# Construct a list[BuildTask] DAG for the driver-based build: certified test
# objects that never see rvmodel_macros.h, a driver library per config, and the
# links that join them.
##################################

import hashlib
import importlib.resources
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pyjson5

from act.build_types import COVERAGE_STEP_TIMEOUT_SECONDS, BuildTask, PythonAction, SubprocessAction, SymlinkAction
from act.config import Config, CoverageSimulator, RefModelType, spike_isa_string
from act.coverreport import generate_report, merge_summaries
from act.parse_test_constraints import TestMetadata
from act.sail_to_rvvi import sailLog2Trace
from act.sig_modify import process_signature_file
from act.toolchain import Toolchain
from act.trap_report import generate_trap_report

# Flags used when generating .elf.objdump files.
# -x: print all headers (file, section, program segment, relocation)
# -d: disassemble executable sections
# -S: intermix original source lines with each disassembled instruction (requires DWARF debug info)
# -M no-aliases,numeric: suppress pseudo-instructions; use numeric register names (x0–x31, f0–f31)
_OBJDUMP_FLAGS_COMMON = ["-x", "-d", "-S", "-M", "no-aliases,numeric"]

# Extra flags added in debug mode:
# -t: print the full symbol table
# -s: print a full hex+ASCII dump of every section
_OBJDUMP_FLAGS_DEBUG = [*_OBJDUMP_FLAGS_COMMON, "-t", "-s"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sail_platform_base(data: dict[object, object], name: str, path: Path) -> int:
    platform = data.get("platform")
    if not isinstance(platform, dict):
        raise TypeError(f"Sail config {path} is missing the `platform` object.")

    device = platform.get(name)
    if not isinstance(device, dict):
        raise TypeError(f"Sail config {path} is missing the `platform.{name}` object.")

    if device.get("supported") is not True:
        raise ValueError(
            f"Sail config {path} must set `platform.{name}.supported` to true. "
            "ACT signature generation requires this Sail device even when the DUT uses a different "
            "interrupt mechanism or does not provide the same device. Enable the device in the sail "
            "config and place it in an IO memory region. Select an address that does not map to DUT "
            "memory, or it may overlap the DUT's own IO memory."
        )

    base = device.get("base")
    if not isinstance(base, int):
        raise TypeError(f"Sail config {path} must set `platform.{name}.base` to an integer.")
    return base


def _sail_platform_defines(sail_config_path: Path) -> tuple[str, ...]:
    """Build compiler defines for Sail platform devices used by sail_macros.h."""
    if not sail_config_path.exists():
        raise FileNotFoundError(f"Sail config file not found: {sail_config_path}")

    config_data = pyjson5.loads(sail_config_path.read_text())
    if not isinstance(config_data, dict):
        raise TypeError(f"Sail config {sail_config_path} must contain a JSON object.")

    clint_base = _sail_platform_base(config_data, "clint", sail_config_path)
    sig_base = _sail_platform_base(config_data, "simple_interrupt_generator", sail_config_path)
    return (
        f"-DSAIL_CLINT_BASE_ADDRESS=0x{clint_base:x}",
        f"-DSAIL_SIMPLE_INTERRUPT_GENERATOR_BASE_ADDRESS=0x{sig_base:x}",
    )


def _ref_model_sig_cmd(
    config: Config,
    sig_elf: Path,
    sig_file: Path,
    sig_trace_file: Path,
    xlen: int,
    debug: bool,
    enable_experimental_extensions: bool,
) -> list[str]:
    """Build the command for invoking the reference model to produce a signature file."""
    if config.ref_model_type == RefModelType.SAIL:
        sail_config_path = config.dut_include_dir / "sail.json"
        cmd = [str(config.ref_model_exe)]
        if enable_experimental_extensions:
            cmd.append("--enable-experimental-extensions")
        if debug:
            cmd.append("--trace")
            cmd.extend(["--trace-output", str(sig_trace_file)])
        cmd.extend(["--config", str(sail_config_path)])
        cmd.extend(config.ref_model_type.signature_flags(sig_file, xlen // 8))
        cmd.append(str(sig_elf))
        return cmd
    if config.ref_model_type == RefModelType.SPIKE:
        cmd = [str(config.ref_model_exe), f"--isa={spike_isa_string(xlen)}"]
        if debug:
            cmd.extend(["-l", "--log-commits", f"--log={sig_trace_file}"])
        cmd.extend(config.ref_model_type.signature_flags(sig_file, xlen // 8))
        cmd.append(str(sig_elf))
        return cmd
    raise ValueError(f"Unsupported reference model type: {config.ref_model_type}")


# ---------------------------------------------------------------------------
# Driver library
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DriverBuild:
    """Driver objects for one config, keyed by -mabi.

    ``ref`` is assembled against sail_macros.h and linked into the reference
    model's ELFs. ``dut`` is assembled against the DUT's rvmodel_macros.h; it is
    empty when the config supplies no rvmodel_macros.h, and the build then stops
    at the certified objects.
    """

    ref: dict[str, Path]
    dut: dict[str, Path]


def mabi_for(xlen: int, e_ext: bool) -> str:
    """ABI every test and driver object of this XLEN/base is built with."""
    return f"{'i' if xlen == 32 else ''}lp{xlen}{'e' if e_ext else ''}"


def gen_driver_tasks(
    config: Config,
    xlen: int,
    e_exts: set[bool],
    env_dir: Path,
    header_dir: Path,
    out_dir: Path,
    toolchain: Toolchain,
    signature_compile_flags: tuple[str, ...],
    rvmodel_dir: Path | None,
    env_files: tuple[Path, ...],
    header_files: tuple[Path, ...],
) -> tuple[list[BuildTask], DriverBuild]:
    """Assemble rvmodel_driver.S once per ABI, for the reference model and, when
    rvmodel_macros.h is available, for the DUT."""
    tasks: list[BuildTask] = []
    ref: dict[str, Path] = {}
    dut: dict[str, Path] = {}
    source = env_dir / "rvmodel_driver.S"
    dut_headers: tuple[Path, ...] = ()
    if rvmodel_dir is not None:
        dut_headers = tuple(sorted(p.absolute() for p in rvmodel_dir.iterdir() if p.suffix == ".h"))

    for e_ext in sorted(e_exts):
        mabi = mabi_for(xlen, e_ext)
        march = toolchain.march_flags(
            xlen, f"rv{xlen}{'e' if e_ext else 'i'}_zicsr_zifencei", assembly=True, e_ext=e_ext
        )
        common = [
            *toolchain.compile_prefix(xlen),
            "-c",
            "-O0",
            "-g",
            "-mcmodel=medany",
            "-nostdlib",
            *march,
            f"-mabi={mabi}",
            f"-DXLEN={xlen}",
            "-DTEST_FLEN=32",
            f"-I{env_dir}",
            f"-I{header_dir.absolute()}",
        ]
        variants: list[tuple[str, list[str], tuple[Path, ...]]] = [("ref", list(signature_compile_flags), ())]
        if rvmodel_dir is not None:
            variants.append(("dut", ["-DRVTEST_SELFCHECK", f"-I{rvmodel_dir.absolute()}"], dut_headers))
        for variant, flags, extra_headers in variants:
            obj = out_dir / "driver" / variant / mabi / "rvmodel_driver.o"
            tasks.append(
                BuildTask(
                    outputs=(obj,),
                    extra_inputs=(source, *env_files, *header_files, *extra_headers),
                    action=SubprocessAction(cmd=[*common, *flags, "-o", str(obj), str(source)]),
                    label=f"{variant} driver ({config.name}, {mabi})",
                )
            )
            (ref if variant == "ref" else dut)[mabi] = obj
    return tasks, DriverBuild(ref=ref, dut=dut)


# ---------------------------------------------------------------------------
# Per-test task generators
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TestOutputs:
    """What one test produces: its certified object, and its ELF when linked."""

    name: Path  # e.g. priv/Hello/Hello_boot-00
    obj: Path
    results: Path | None  # golden signature, for the provenance digest
    elf: Path | None
    march: str
    mabi: str
    flen: str


def write_sigdigest_header(results: Path, out: Path) -> None:
    """Emit `#define RVCP_SIG_DIGEST` holding the sha256 of the golden signatures."""
    digest = hashlib.sha256(results.read_bytes()).hexdigest()
    out.write_text(f'#define RVCP_SIG_DIGEST "{digest}"\n')


def gen_compile_tasks(
    test_name: Path,
    test_metadata: TestMetadata,
    out_dir: Path,
    header_dir: Path,
    env_dir: Path,
    xlen: int,
    config: Config,
    toolchain: Toolchain,
    drivers: DriverBuild,
    signature_compile_flags: tuple[str, ...] = (),
    compile_inputs: tuple[Path, ...] = (),
    c_runtime_sources: tuple[Path, ...] = (),
    ref_model_inputs: tuple[Path, ...] = (),
    kit_stamp: Path | None = None,
    debug: bool = False,
    fast: bool = False,
    enable_experimental_extensions: bool = False,
) -> tuple[list[BuildTask], TestOutputs]:
    """Generate BuildTasks for the compilation pipeline of a single test.

    Every test is built into a certified object that never sees rvmodel_macros.h:
        add.S -> add.sig.o + reference driver -> add.sig.elf -> add.sig (ref model)
              -> add.results -> add.o (expected signature baked in)
    and, when the DUT driver exists, linked into the ELF that runs on the DUT:
        add.o + DUT driver -> add.elf
    Tests with NEEDS_SIGNATURE: false skip the reference-model steps.

    Args:
        test_name: Name of the test.
        test_metadata: Metadata for the test.
        out_dir: Directory for this build's outputs (build/, objects/, elfs/).
        header_dir: Directory with the config's generated headers.
        env_dir: Directory that contains shared test-environment headers.
        xlen: XLEN (32 or 64).
        config: Configuration object.
        toolchain: Toolchain used to resolve compiler ISA flags for this test.
        drivers: Driver objects to link against.
        compile_inputs: Shared inputs for compilation.
        c_runtime_sources: Runtime sources compiled into C tests.
        ref_model_inputs: Shared inputs for the reference model (e.g. sail.json for Sail).
        kit_stamp: Header force-included into the certified object (act-package only).
        debug: Whether to generate debug output (signature objdump and trace files).
        fast: Whether to disable objdump generation for faster builds.
    """
    tasks: list[BuildTask] = []

    # Paths
    build_dir = out_dir / "build"
    sig_obj = build_dir / test_name.with_suffix(".sig.o")
    sig_elf = build_dir / test_name.with_suffix(".sig.elf")
    sig_file = build_dir / test_name.with_suffix(".sig")
    result_file = build_dir / test_name.with_suffix(".results")
    digest_file = build_dir / test_name.with_suffix(".sigdigest.h")
    sig_trace_file = build_dir / test_name.with_suffix(".sig.trace")
    sig_log_file = build_dir / test_name.with_suffix(".sig.log")
    obj = out_dir / "objects" / test_name.with_suffix(".o")
    final_elf = out_dir / "elfs" / test_name.with_suffix(".elf")

    # Metadata
    march_flags = toolchain.march_flags(
        xlen,
        test_metadata.march,
        assembly=not test_metadata.is_c_test,
        e_ext=test_metadata.e_ext,
    )
    test_flen = test_metadata.flen
    test_path = test_metadata.test_path
    mabi = mabi_for(xlen, test_metadata.e_ext)
    c_compile_flags = (
        ["-ffreestanding", "-fno-builtin", "-msmall-data-limit=0", "-std=gnu99"] if test_metadata.is_c_test else []
    )

    # Compilation sources and inputs. A C test and its runtime are partially linked
    # (-r) into one relocatable object, so every test is exactly one certified object.
    test_sources = [str(test_path)]
    if test_metadata.is_c_test:
        test_sources = [str(source) for source in c_runtime_sources] + test_sources
    test_inputs = (test_path, *compile_inputs)

    object_prefix = [
        *toolchain.compile_prefix(xlen),
        "-r" if test_metadata.is_c_test else "-c",
        "-O0",
        "-g",
        "-mcmodel=medany",
        "-nostdlib",
        f"-I{env_dir}",
        f"-I{header_dir.absolute()}",
        *c_compile_flags,
        *march_flags,
        f"-mabi={mabi}",
        f"-DXLEN={xlen}",
        f"-DTEST_FLEN={test_flen}",
        f'-DTEST_FILE="{test_name.name}"',
    ]
    link_prefix = [
        *toolchain.compile_prefix(xlen),
        f"-T{config.linker_script.absolute()}",
        "-nostdlib",
        "-mcmodel=medany",
        *march_flags,
        f"-mabi={mabi}",
    ]
    link_inputs = (config.linker_script.absolute(),)

    if test_metadata.needs_signature:
        # 1. sig.o - the test object in signature-generation mode
        tasks.append(
            BuildTask(
                outputs=(sig_obj,),
                extra_inputs=test_inputs,
                action=SubprocessAction(
                    cmd=[*object_prefix, "-DSIGNATURE", *signature_compile_flags, "-o", str(sig_obj), *test_sources]
                ),
                intermediate=True,
            )
        )

        # 2. sig.elf - linked against the reference model's driver
        ref_driver = drivers.ref[mabi]
        tasks.append(
            BuildTask(
                outputs=(sig_elf,),
                deps=(sig_obj, ref_driver),
                extra_inputs=link_inputs,
                action=SubprocessAction(cmd=[*link_prefix, "-o", str(sig_elf), str(sig_obj), str(ref_driver)]),
                intermediate=True,
            )
        )

        # 2a. sig.elf.objdump (optional, debug only)
        if debug and config.objdump_exe is not None:
            objdump_file = Path(f"{sig_elf}.objdump")
            tasks.append(
                BuildTask(
                    outputs=(objdump_file,),
                    deps=(sig_elf,),
                    action=SubprocessAction(
                        cmd=[str(config.objdump_exe), *_OBJDUMP_FLAGS_DEBUG, str(sig_elf)],
                        stdout_file=objdump_file,
                    ),
                )
            )

        # 3. sig - run reference model
        ref_model_cmd = _ref_model_sig_cmd(
            config, sig_elf, sig_file, sig_trace_file, xlen, debug, enable_experimental_extensions
        )
        ref_model_outputs = (sig_file, sig_trace_file) if debug else (sig_file,)
        tasks.append(
            BuildTask(
                outputs=ref_model_outputs,
                deps=(sig_elf,),
                extra_inputs=ref_model_inputs,
                action=SubprocessAction(cmd=ref_model_cmd, stdout_file=sig_log_file),
                intermediate=True,
            )
        )

        # 3a. trap report (optional, debug only)
        if debug:
            trap_report_file = Path(f"{sig_file}.trap_report")
            # Derive nm executable from objdump executable (e.g. riscv64-unknown-elf-objdump -> riscv64-unknown-elf-nm)
            nm_exe: Path | None = None
            if config.objdump_exe is not None:
                objdump_exe = config.objdump_exe
                candidate = objdump_exe.with_name(objdump_exe.name.replace("objdump", "nm"))
                if candidate.exists():
                    nm_exe = candidate
            tasks.append(
                BuildTask(
                    outputs=(trap_report_file,),
                    deps=(sig_file, sig_elf),
                    action=PythonAction(fn=generate_trap_report, args=(sig_file, xlen, sig_elf, nm_exe)),
                )
            )

        # 4. results - process signature file, and its digest for the provenance line
        tasks.append(
            BuildTask(
                outputs=(result_file,),
                deps=(sig_file,),
                action=PythonAction(fn=process_signature_file, args=(sig_file, xlen)),
                intermediate=True,
            )
        )
        tasks.append(
            BuildTask(
                outputs=(digest_file,),
                deps=(result_file,),
                action=PythonAction(fn=write_sigdigest_header, args=(result_file, digest_file)),
                intermediate=True,
            )
        )

    # 5. certified object - expected signature baked in, no rvmodel_macros.h.
    # Non-signature tests start here.
    obj_cmd = [
        *object_prefix,
        "-DRVTEST_SELFCHECK",
        *(
            [f'-DSIGNATURE_FILE="{result_file}"', "-include", str(digest_file)]
            if test_metadata.needs_signature
            else ["-DRVTEST_NOSIG"]
        ),
        *(["-include", str(kit_stamp)] if kit_stamp is not None else []),
        "-o",
        str(obj),
        *test_sources,
    ]
    tasks.append(
        BuildTask(
            outputs=(obj,),
            extra_inputs=(*test_inputs, *((kit_stamp,) if kit_stamp is not None else ())),
            deps=(result_file, digest_file) if test_metadata.needs_signature else (),
            action=SubprocessAction(cmd=obj_cmd),
        )
    )

    # 6. final.elf - the certified object linked against the DUT's driver
    dut_driver = drivers.dut.get(mabi)
    if dut_driver is not None:
        tasks.append(
            BuildTask(
                outputs=(final_elf,),
                deps=(obj, dut_driver),
                extra_inputs=link_inputs,
                action=SubprocessAction(cmd=[*link_prefix, "-o", str(final_elf), str(obj), str(dut_driver)]),
            )
        )

        # 6a. final.elf.objdump (optional, not in fast mode)
        if not fast and config.objdump_exe is not None:
            objdump_file = Path(f"{final_elf}.objdump")
            objdump_flags = _OBJDUMP_FLAGS_DEBUG if debug else _OBJDUMP_FLAGS_COMMON
            tasks.append(
                BuildTask(
                    outputs=(objdump_file,),
                    deps=(final_elf,),
                    action=SubprocessAction(
                        cmd=[str(config.objdump_exe), *objdump_flags, str(final_elf)],
                        stdout_file=objdump_file,
                    ),
                )
            )

    outputs = TestOutputs(
        name=test_name.with_suffix(""),
        obj=obj,
        results=result_file if test_metadata.needs_signature else None,
        elf=final_elf if dut_driver is not None else None,
        march=test_metadata.march.replace("${XLEN}", str(xlen)),
        mabi=mabi,
        flen=test_flen,
    )
    return tasks, outputs


def gen_rvvi_tasks(
    test_name: Path,
    base_dir: Path,
    config: Config,
    ref_model_inputs: tuple[Path, ...] = (),
    fast: bool = False,
    enable_experimental_extensions: bool = False,
) -> list[BuildTask]:
    """Generate BuildTasks for RVVI trace generation (coverage pipeline).

    Only supported when the reference model is Sail; the converter parses Sail's
    trace format.
    """
    if config.ref_model_type != RefModelType.SAIL:
        raise ValueError(
            f"Coverage trace generation requires the Sail reference model, "
            f"but ref_model_type={config.ref_model_type.value} was selected."
        )
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
                deps=(objdump_orig_file,),
                action=SymlinkAction(src=objdump_orig_file, dst=objdump_link),
            )
        )

    # Run Sail with trace
    sail_cmd = [str(config.ref_model_exe)]
    if enable_experimental_extensions:
        sail_cmd.append("--enable-experimental-extensions")
    sail_cmd.extend(
        [
            "--trace",
            "--trace-output",
            str(sail_trace),
            "--config",
            str(config.dut_include_dir / "sail.json"),
            str(elf),
        ]
    )
    tasks.append(
        BuildTask(
            outputs=(sail_trace,),
            deps=(elf,),
            extra_inputs=ref_model_inputs,
            action=SubprocessAction(cmd=sail_cmd, stdout_file=sail_log),
            intermediate=True,
        )
    )

    # Convert to RVVI
    tasks.append(
        BuildTask(
            outputs=(rvvi_trace,),
            deps=(sail_trace,),
            action=PythonAction(fn=sailLog2Trace, args=(sail_trace, rvvi_trace)),
            intermediate=True,
        )
    )

    return tasks


def gen_coverage_tasks(
    coverage_targets: dict[Path, list[Path]],
    coverpoint_dir: Path,
    base_dir: Path,
    config_report_dir: Path,
    udb_header_dir: Path,
    env_header_dir: Path,
    coverage_simulator: CoverageSimulator,
    verbose: bool = False,
    dry_run: bool = False,
    enable_experimental_extensions: bool = False,
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
    # Coverage simulation depends on coverpoints, fcov infrastructure, generated DUT
    # config header (in udb_header_dir), and the simulator script.
    coverpoint_files = tuple(sorted(p.absolute() for p in coverpoint_dir.rglob("*") if p.is_file()))
    fcov_files = tuple(sorted(p.absolute() for p in fcov_path.rglob("*") if p.is_file()))
    udb_svh_files = tuple(sorted(p.absolute() for p in udb_header_dir.iterdir() if p.suffix == ".svh"))
    env_svh_files = tuple(sorted(p.absolute() for p in env_header_dir.iterdir() if p.suffix == ".svh"))
    coverage_inputs = (*coverpoint_files, *fcov_files, *udb_svh_files, *env_svh_files, sim_script)

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

        # Write tracelist file, but only when its contents actually change so its mtime
        # reflects real changes. This lets us include it in extra_inputs below without
        # forcing a coverage rebuild on every run.
        if not dry_run:
            tracelist_file.parent.mkdir(parents=True, exist_ok=True)
            tracelist_contents = (
                f"# Tests for coverage group: {coverage_group}\n"
                "# Generated automatically by riscv-arch-test act framework\n"
                + "\n".join(str(trace) for trace in sorted(traces))
            )
            if not tracelist_file.exists() or tracelist_file.read_text() != tracelist_contents:
                tracelist_file.write_text(tracelist_contents)

        # Coverage collection task
        coverage_tag = f"{coverage_group.stem.upper()}_COVERAGE"
        coverage_define_list = [coverage_tag]
        if verbose:
            coverage_define_list.append("FCOV_VERBOSE")
        if enable_experimental_extensions:
            coverage_define_list.append("ENABLE_EXPERIMENTAL_EXTENSIONS")
        coverage_defines = " ".join(coverage_define_list)
        if coverage_simulator == CoverageSimulator.QUESTA:
            do_script = (
                f"do {sim_script} "
                f"{tracelist_file} "
                f"{simulator_artifact} "
                f"{work_dir} "
                f"{fcov_path} "
                f"{coverpoint_dir} "
                f"{udb_header_dir} "
                f"{env_header_dir} "
                f"{{{coverage_defines}}}"
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
                str(udb_header_dir),
                str(env_header_dir),
                coverage_defines,
            ]

        # Deps: all rvvi traces for this coverage group must be done
        # The rvvi traces have the same stems as the traces list but with .rvvi suffix
        rvvi_deps = tuple(sorted(traces))

        tasks.append(
            BuildTask(
                outputs=(simulator_artifact,),
                deps=rvvi_deps,
                extra_inputs=coverage_inputs if dry_run else (*coverage_inputs, tracelist_file),
                action=SubprocessAction(cmd=coverage_cmd, stdout_file=simulator_log, cwd=coverage_dir),
                intermediate=True,
                timeout=COVERAGE_STEP_TIMEOUT_SECONDS,
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

    # Overall summary merging
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


def find_rvmodel_dir(config: Config, override: Path | None = None) -> Path | None:
    """Directory holding the DUT's rvmodel_macros.h, or None when there is none.

    Without it the build stops at the certified objects.
    """
    candidate = override if override is not None else config.dut_include_dir
    return candidate.absolute() if (candidate / "rvmodel_macros.h").is_file() else None


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
    verbose: bool = False,
    dry_run: bool = False,
    enable_experimental_extensions: bool = False,
    rvmodel_dir: Path | None = None,
    out_dir: Path | None = None,
    kit_stamp: Path | None = None,
) -> tuple[list[BuildTask], list[TestOutputs]]:
    """Build the full DAG of tasks for a single config.

    Args:
        rvmodel_dir: Directory with the DUT's rvmodel_macros.h. When None, the
            build produces the certified objects but no ELFs.
        out_dir: Where build/, objects/, elfs/ and driver/ go (default: workdir/<config>).
        kit_stamp: Header force-included into every certified object (act-package).
    """
    if coverage_enabled and config.ref_model_type != RefModelType.SAIL:
        raise ValueError(
            "Coverage generation is only supported with the Sail reference model, "
            f"but ref_model_type={config.ref_model_type.value} was selected for "
            f"config '{config.name}'. Switch back to Sail or drop --coverage."
        )
    if coverage_enabled and rvmodel_dir is None:
        raise ValueError(
            f"Coverage runs the linked ELFs, but config '{config.name}' has no rvmodel_macros.h "
            f"in {config.dut_include_dir}, so the build stops at the certified objects."
        )

    tasks: list[BuildTask] = []
    outputs: list[TestOutputs] = []

    header_dir = workdir / config.name
    config_wkdir = out_dir if out_dir is not None else header_dir
    config_coverage_dir = config_wkdir / "coverage"
    config_report_dir = config_wkdir / "reports"

    coverage_targets: defaultdict[Path, list[Path]] = defaultdict(list)
    toolchain = Toolchain(config.compiler_exe, config.compiler_type)

    # Collect shared file dependencies that affect all compilations. Test objects
    # depend on the env and generated headers only; rvmodel_macros.h affects the
    # DUT driver, and the linker script affects the links.
    env_dir = tests_dir / "env"
    env_files = tuple(sorted(p.absolute() for p in env_dir.iterdir() if p.is_file()))
    c_runtime_sources = tuple((env_dir / name).absolute() for name in ("c_test_start.S", "c_test_support.c"))
    udb_headers = tuple(sorted(p.absolute() for p in header_dir.iterdir() if p.suffix == ".h"))
    compile_inputs = (*env_files, *udb_headers)

    # Sail config affects reference model output (Spike has no equivalent file).
    ref_model_inputs: tuple[Path, ...] = ()
    # sail_macros.h is included by every signature build, so the platform defines are
    # needed whatever the reference model is; only the model's own inputs are Sail-specific.
    sail_config = config.dut_include_dir / "sail.json"
    signature_compile_flags = _sail_platform_defines(sail_config)
    if config.ref_model_type == RefModelType.SAIL:
        ref_model_inputs = (sail_config.absolute(),)

    driver_tasks, drivers = gen_driver_tasks(
        config,
        xlen,
        {metadata.e_ext for metadata in selected_tests.values()},
        env_dir,
        header_dir,
        config_wkdir,
        toolchain,
        signature_compile_flags,
        rvmodel_dir,
        env_files,
        udb_headers,
    )
    tasks.extend(driver_tasks)

    for test_name_str, test_metadata in sorted(selected_tests.items()):
        test_name = Path(test_name_str)

        # Compile test
        test_tasks, test_outputs = gen_compile_tasks(
            test_name,
            test_metadata,
            config_wkdir,
            header_dir,
            env_dir,
            xlen,
            config,
            toolchain,
            drivers,
            signature_compile_flags,
            compile_inputs,
            c_runtime_sources,
            ref_model_inputs,
            kit_stamp,
            debug,
            fast,
            enable_experimental_extensions,
        )
        tasks.extend(test_tasks)
        outputs.append(test_outputs)

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
                    ref_model_inputs,
                    fast,
                    enable_experimental_extensions,
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
                header_dir,
                tests_dir / "env",
                coverage_simulator,
                verbose,
                dry_run,
                enable_experimental_extensions,
            )
        )

    return tasks, outputs
