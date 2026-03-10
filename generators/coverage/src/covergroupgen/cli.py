#!/usr/bin/env python3

##################################
# cli.py
#
# Command-line interface for covergroup generation.
# jcarlin@hmc.edu March 2026
# SPDX-License-Identifier: Apache-2.0
##################################

"""Top-level command-line interface for covergroup generation."""

from pathlib import Path
from typing import Annotated

import typer

from covergroupgen.generate import generate_covergroups

# CLI interface setup
covergroupgen_app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]}, add_completion=False)


@covergroupgen_app.command()
def run(
    testplan_dir: Annotated[
        Path, typer.Argument(exists=True, file_okay=False, help="Directory containing testplan CSV files")
    ],
    *,
    output_dir: Annotated[
        Path, typer.Option("-o", "--output", file_okay=False, help="Output directory for covergroups")
    ] = Path("coverpoints"),
    extensions: Annotated[
        str, typer.Option("--extensions", "-e", help="Comma-separated list of extensions to generate covergroups for")
    ] = "all",
    exclude: Annotated[
        str,
        typer.Option(
            "--exclude", "-x", help="Comma-separated list of extensions to exclude from covergroup generation"
        ),
    ] = "",
) -> None:
    """Generate functional covergroups for RISC-V instructions from CSV testplans."""
    generate_covergroups(testplan_dir, output_dir, extensions, exclude)


def main() -> None:
    covergroupgen_app()


if __name__ == "__main__":
    main()
