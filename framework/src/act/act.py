##################################
# act.py
#
# jcarlin@hmc.edu 14 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Main entry point for RISC-V architecture verification framework
##################################

from pathlib import Path
from typing import Annotated

import typer

from act.config import load_config
from act.makefile_gen import ConfigData, generate_makefiles
from act.parse_test_constraints import generate_test_dict
from act.parse_udb_config import generate_udb_files, get_config_params, get_implemented_extensions
from act.select_tests import get_common_tests, select_tests

# CLI interface setup
act_app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})


@act_app.command()
def run_act(
    config_files: Annotated[
        list[Path], typer.Argument(exists=True, file_okay=True, dir_okay=False, help="Path to configuration file(s)")
    ],
    test_dir: Annotated[
        Path, typer.Option("--test-dir", "-t", exists=True, file_okay=False, help="Path to tests directory")
    ] = Path("tests"),
    coverpoint_dir: Annotated[
        Path, typer.Option("--coverpoint-dir", "-c", exists=True, file_okay=False, help="Path to coverpoint directory")
    ] = Path("coverpoints"),
    workdir: Annotated[
        Path | None,
        typer.Option("--workdir", "-w", file_okay=False, help="Path to working directory", show_default="./work"),
    ] = None,
    extensions: Annotated[
        str,
        typer.Option("--extensions", "-e", help="Comma-separated list of extensions to generate tests for"),
    ] = "all",
    exclude: Annotated[
        str,
        typer.Option("--exclude", "-x", help="Comma-separated list of extensions to exclude from test generation"),
    ] = "",
    *,
    coverage: Annotated[bool, typer.Option(help="Enable coverage generation")] = False,
    debug: Annotated[bool, typer.Option(help="Enable debug output (signature objdump and trace files)")] = False,
) -> None:
    if workdir is None:
        workdir = Path.cwd() / "work"
    # Generate test list
    full_test_dict = generate_test_dict(test_dir, extensions, exclude)
    rv32i_common_tests = get_common_tests(full_test_dict, 32, False)
    rv32e_common_tests = get_common_tests(full_test_dict, 32, False)
    rv64i_common_tests = get_common_tests(full_test_dict, 64, False)
    rv64e_common_tests = get_common_tests(full_test_dict, 64, False)
    common_test_dicts = [rv32i_common_tests, rv32e_common_tests, rv64i_common_tests, rv64e_common_tests]

    configs: list[ConfigData] = []
    for config_file in config_files:
        # Load configuration
        config = load_config(config_file)
        udb_config_file = config.udb_config
        config_dir = workdir / config.udb_config.stem
        config_dir.mkdir(parents=True, exist_ok=True)

        # UDB integration
        generate_udb_files(udb_config_file, config_dir)
        implemented_extensions = get_implemented_extensions(config_dir / "extensions.txt")
        config_params = get_config_params(udb_config_file)

        # Select tests for config
        selected_tests = select_tests(full_test_dict, implemented_extensions, config_params)
        configs.append(
            {
                "config": config,
                "xlen": config_params["MXLEN"],
                "e_ext": "E" in implemented_extensions,
                "selected_tests": selected_tests,
            }
        )

    # Validate configurations
    validate_configs(configs)

    # Generate Makefiles
    generate_makefiles(
        configs,
        common_test_dicts,
        test_dir.absolute(),
        coverpoint_dir.absolute(),
        workdir.absolute(),
        coverage,
        debug,
    )
    print(f"Makefiles generated in {workdir}")
    print(f"Run make -C {workdir} compile to build all tests.")


def validate_configs(configs: list[ConfigData]) -> None:
    """Validate that configurations are consistent."""
    configs_by_xlen: dict[int, list[ConfigData]] = {}

    # Group configs by XLEN
    for config_data in configs:
        xlen = config_data["xlen"]
        if xlen not in configs_by_xlen:
            configs_by_xlen[xlen] = []
        configs_by_xlen[xlen].append(config_data)

    # Validate each XLEN group
    for xlen, xlen_configs in configs_by_xlen.items():
        if len(xlen_configs) < 2:
            continue

        ref_data = xlen_configs[0]
        ref_config = ref_data["config"]
        ref_model_header = ref_config.dut_include_dir / "model_test.h"
        ref_linker_script = ref_config.linker_script

        for config_data in xlen_configs[1:]:
            config = config_data["config"]

            # Validate compiler_exe
            if ref_config.compiler_exe != config.compiler_exe:
                raise ValueError(
                    f"Inconsistent compiler_exe for XLEN {xlen}: "
                    f"{ref_config.name} uses {ref_config.compiler_exe}, "
                    f"{config.name} uses {config.compiler_exe}"
                )

            # Validate objdump_exe
            if ref_config.objdump_exe != config.objdump_exe:
                raise ValueError(
                    f"Inconsistent objdump_exe for XLEN {xlen}: "
                    f"{ref_config.name} uses {ref_config.objdump_exe}, "
                    f"{config.name} uses {config.objdump_exe}"
                )

            # Validate ref_model_exe
            if ref_config.ref_model_exe != config.ref_model_exe:
                raise ValueError(
                    f"Inconsistent ref_model_exe for XLEN {xlen}: "
                    f"{ref_config.name} uses {ref_config.ref_model_exe}, "
                    f"{config.name} uses {config.ref_model_exe}"
                )

            # Validate linker_script content
            if ref_linker_script.read_bytes() != config.linker_script.read_bytes():
                raise ValueError(
                    f"Inconsistent linker_script content for XLEN {xlen} between {ref_config.name} and {config.name}"
                )

            # Validate model_test.h content
            model_header = config.dut_include_dir / "model_test.h"
            if not ref_model_header.exists():
                # Force read to raise FileNotFoundError if missing, as implied by requirement
                ref_model_header.read_bytes()

            if ref_model_header.read_bytes() != model_header.read_bytes():
                raise ValueError(
                    f"Inconsistent model_test.h content for XLEN {xlen} between {ref_config.name} and {config.name}"
                )


def main() -> None:
    act_app()


if __name__ == "__main__":
    main()
