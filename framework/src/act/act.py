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
from act.makefile_gen import generate_makefiles
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
    workdir: Annotated[Path | None, typer.Option("--workdir", "-w", help="Path to working directory")] = None,
    coverage: Annotated[
        bool, typer.Option("--coverage/--no-coverage", help="Enable or disable coverage generation")
    ] = False,
) -> None:
    if workdir is None:
        workdir = Path.cwd() / "work"
    # Generate test list
    full_test_dict = generate_test_dict(test_dir)
    rv32_common_tests = get_common_tests(full_test_dict, 32)
    rv64_common_tests = get_common_tests(full_test_dict, 64)

    configs = []
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
        configs.append({"config": config, "xlen": config_params["MXLEN"], "selected_tests": selected_tests})

    # TODO: Add a check that all configs use the same header files/compiler/etc. Otherwise error out or don't use common tests

    # Generate Makefiles
    generate_makefiles(
        configs,
        rv32_common_tests,
        rv64_common_tests,
        test_dir.absolute(),
        coverpoint_dir.absolute(),
        workdir.absolute(),
        coverage,
    )
    print(f"Makefiles generated in {workdir}")
    print(f"Run make -C {workdir} compile to build all tests.")


def main() -> None:
    act_app()


if __name__ == "__main__":
    main()
