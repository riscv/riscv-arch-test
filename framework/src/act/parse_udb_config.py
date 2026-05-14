##################################
# parse_udb_config.py
#
# jcarlin@hmc.edu 6 Sept 2025
# SPDX-License-Identifier: Apache-2.0
#
# Parse UDB configuration file
##################################

from __future__ import annotations

import importlib.resources
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console, Group
from rich.live import Live
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.text import Text
from ruamel.yaml import YAML

from act.dut_macros import generate_rvmodel_svh

if TYPE_CHECKING:
    from act.config import Config

from rich import print as rprint


def _find_gemfile() -> Path:
    """Locate the Gemfile bundled with the act package."""
    gemfile_path = Path(str(importlib.resources.files("act"))) / "data" / "Gemfile"
    if not gemfile_path.exists():
        raise RuntimeError(
            "No Gemfile found in act package data. Install the udb gem with 'gem install udb' or reinstall act."
        )
    return gemfile_path


def _bundle_env() -> dict[str, str]:
    """Return an environment dict that forces bundler to use the act Gemfile."""
    env = os.environ.copy()
    env["BUNDLE_GEMFILE"] = str(_find_gemfile())
    return env


def _bundle_exec(cmd: list[str], *, check: bool = False, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
    """Run `bundle exec <cmd>` with the act-bundled Gemfile."""
    return subprocess.run(["bundle", "exec", *cmd], env=_bundle_env(), check=check, **kwargs)  # type: ignore[arg-type]


def _ensure_udb_installed() -> None:
    """Ensure the correct version of the UDB gem is installed via bundler.

    Uses `bundle check` to verify that installed gems match Gemfile.lock.
    If gems are missing or out of date, runs `bundle install` to fix them.
    """
    gemfile = _find_gemfile()
    env = _bundle_env()

    # Check if all gems (including udb) are installed at the correct versions
    try:
        subprocess.run(["bundle", "check"], check=True, cwd=gemfile.parent, capture_output=True, text=True, env=env)
        return  # All gems satisfied — correct version is installed
    except FileNotFoundError as e:
        raise RuntimeError(
            "udb command not found and 'bundle' is not available. See the README for installation instructions."
        ) from e
    except subprocess.CalledProcessError:
        pass  # Gems missing or wrong version — need to install (done below)

    print("UDB gem missing or out of date; running 'bundle install'...")
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            subprocess.run(["bundle", "install"], check=True, cwd=gemfile.parent, env=env)
            break
        except subprocess.CalledProcessError as e:
            if attempt == max_attempts:
                raise RuntimeError("'bundle install' failed. Check Ruby and bundler installation.") from e
            backoff = attempt * 10
            print(f"'bundle install' attempt {attempt} failed. Retrying in {backoff}s...")
            time.sleep(backoff)

    if shutil.which("bundle") is None:
        raise RuntimeError("'bundle' command still not found after install.")


def ensure_udb_installed() -> None:
    """Public wrapper for `_ensure_udb_installed` so callers can run it once
    before any parallel `generate_udb_files` invocations (the underlying
    `bundle install` is not safe to run concurrently)."""
    _ensure_udb_installed()


def prepare_dut_outputs(configs: list[Config], workdir: Path, jobs: int) -> None:
    """Generate all UDB-derived files (extensions.txt, rvtest_config.{h,svh})
    plus rvmodel_macros.svh for every config, in parallel.

    Parallelism is at the file level: every (config, file) pair is its own
    work unit submitted to a single ThreadPoolExecutor, so independent
    `udb-gen` invocations run concurrently across both configs and files.
    The only intra-config ordering kept is `validate cfg` before
    `extensions.txt`, since the validate step is a precondition for that
    one file in the existing flow.

    Handles `bundle install` once up front (the install step isn't safe to
    run concurrently) and renders a transient rich progress bar that
    matches the look of the main build pipeline.
    """
    if not configs:
        return

    _ensure_udb_installed()

    # Pre-create all per-config workdirs.
    config_dirs: list[tuple[Config, Path]] = []
    for cfg in configs:
        config_dir = workdir / cfg.udb_config.stem
        config_dir.mkdir(parents=True, exist_ok=True)
        config_dirs.append((cfg, config_dir))

    # Build the file-level work units. Each unit is (label, callable).
    work_units: list[tuple[str, Callable[[], None]]] = []
    for cfg, config_dir in config_dirs:
        stem = cfg.udb_config.stem

        def _ext_unit(c: Config = cfg, d: Path = config_dir) -> None:
            ext = d / "extensions.txt"
            if not ext.exists() or ext.stat().st_mtime < c.udb_config.stat().st_mtime:
                # validate is a precondition for `udb list extensions`; pair
                # them in this single unit.
                validate_udb_config(c.udb_config)
                generate_extension_list(c.udb_config, d)

        def _h_unit(c: Config = cfg, d: Path = config_dir) -> None:
            _generate_one_dut_header(c.udb_config, d / "rvtest_config.h", "cfg-c-header")

        def _svh_unit(c: Config = cfg, d: Path = config_dir) -> None:
            _generate_one_dut_header(c.udb_config, d / "rvtest_config.svh", "cfg-svh-header")

        def _rvmodel_unit(c: Config = cfg, d: Path = config_dir) -> None:
            generate_rvmodel_svh(c.dut_include_dir, d)

        work_units.append((f"{stem}:extensions.txt", _ext_unit))
        work_units.append((f"{stem}:rvtest_config.h", _h_unit))
        work_units.append((f"{stem}:rvtest_config.svh", _svh_unit))
        work_units.append((f"{stem}:rvmodel_macros.svh", _rvmodel_unit))

    workers = min(len(work_units), jobs) or 1

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[cyan]Preparing DUT configs..."),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("elapsed:"),
        TimeElapsedColumn(),
    )
    progress_task = progress.add_task("prep", total=len(work_units))
    status_text = Text()
    in_flight: set[str] = set()

    def _refresh_status() -> None:
        status_text.truncate(0)
        if not in_flight:
            return
        names = sorted(in_flight)
        if len(names) <= 4:
            status_text.append("  " + ", ".join(names), style="dim")
        else:
            status_text.append(f"  {len(names)} units running, oldest: {names[0]}", style="dim")

    console = Console()
    start = time.monotonic()
    with (
        Live(Group(progress, status_text), console=console, transient=True) as live,
        ThreadPoolExecutor(max_workers=workers) as pool,
    ):
        future_to_label: dict[Future[None], str] = {}
        for label, fn in work_units:
            in_flight.add(label)
            future_to_label[pool.submit(fn)] = label
        _refresh_status()

        for fut in as_completed(future_to_label):
            label = future_to_label[fut]
            try:
                fut.result()
            except Exception:
                # Surface failure via the live console so the transient bar
                # still clears after the exception unwinds.
                live.console.print(f"[bold red]✗ Failed preparing {label}[/]")
                raise
            in_flight.discard(label)
            progress.advance(progress_task)
            _refresh_status()

    elapsed = time.monotonic() - start
    n = len(config_dirs)
    rprint(f"[bold green]✓ DUT configs prepared:[/] {n} config{'s' if n != 1 else ''} in {elapsed:.1f}s")


def validate_udb_config(udb_config_file: Path) -> None:
    try:
        _bundle_exec(["udb", "validate", "cfg", str(udb_config_file)], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        rprint(f"[bold red]✗ UDB configuration validation failed for {udb_config_file.name}[/]")
        if e.stdout:
            sys.stdout.buffer.write(e.stdout)
        if e.stderr:
            sys.stderr.buffer.write(e.stderr)
        sys.exit(1)


def get_config_params(udb_config_file: Path) -> dict[str, int | bool | str | list[int | str | bool]]:
    yaml = YAML(typ="safe", pure=True)
    udb_config = yaml.load(udb_config_file.read_text())
    config_params = udb_config["params"]
    return config_params


def generate_extension_list(udb_config_file: Path, output_dir: Path) -> None:
    extension_list_file = output_dir / "extensions.txt"
    if not extension_list_file.exists() or (extension_list_file.stat().st_mtime < udb_config_file.stat().st_mtime):
        generate_cmd = [
            "udb",
            "list",
            "extensions",
            "--config",
            str(udb_config_file),
            "--output",
            str(extension_list_file),
        ]
        _bundle_exec(generate_cmd, check=True, capture_output=True)


def get_implemented_extensions(extension_list_file: Path) -> set[str]:
    return set(extension_list_file.read_text().splitlines())


def _generate_one_dut_header(udb_config_file: Path, output_file: Path, subcommand: str) -> None:
    """Run `udb-gen <subcommand>` for the given config and write the result to output_file."""
    if output_file.exists() and output_file.stat().st_mtime >= udb_config_file.stat().st_mtime:
        return
    output_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["udb-gen", subcommand, "-c", str(udb_config_file), "-o", str(output_file)]
    try:
        _bundle_exec(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        rprint(f"[bold red]✗ Failed to generate {output_file.name} for {udb_config_file.stem}[/]")
        if e.stdout:
            sys.stdout.buffer.write(e.stdout)
        if e.stderr:
            sys.stderr.buffer.write(e.stderr)
        raise


def generate_dut_headers(udb_config_file: Path, output_dir: Path) -> None:
    """Generate the C and SystemVerilog DUT config headers for a given UDB config."""
    _generate_one_dut_header(udb_config_file, output_dir / "rvtest_config.h", "cfg-c-header")
    _generate_one_dut_header(udb_config_file, output_dir / "rvtest_config.svh", "cfg-svh-header")


def generate_udb_files(udb_config_file: Path, output_dir: Path) -> None:
    if (
        not (output_dir / "extensions.txt").exists()
        or (output_dir / "extensions.txt").stat().st_mtime < udb_config_file.stat().st_mtime
    ):
        _ensure_udb_installed()
        validate_udb_config(udb_config_file)
        generate_extension_list(udb_config_file, output_dir)

    generate_dut_headers(udb_config_file, output_dir)

    # TODO: Generate Sail config file from UDB
