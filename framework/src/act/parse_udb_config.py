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
from pathlib import Path
from typing import TYPE_CHECKING

from rich import print as rprint
from ruamel.yaml import YAML

from act.build import BuildTask, PythonAction, build
from act.dut_macros import generate_rvmodel_svh

if TYPE_CHECKING:
    from act.config import Config


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
    """Public wrapper for `_ensure_udb_installed` so callers can trigger the
    one-time `bundle install` outside of any parallel execution context
    (the install step isn't safe to run concurrently)."""
    _ensure_udb_installed()


def _validate_with_marker(udb_config_file: Path, marker: Path) -> None:
    """Run `udb validate cfg` and touch a sentinel marker on success.

    The marker is the BuildTask's primary output — its mtime drives the
    DAG's staleness check, so the validate runs once whenever the UDB
    config has changed and is then reused as a dep by every UDB-gen task
    for that config.
    """
    validate_udb_config(udb_config_file)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()


def prepare_dut_outputs(configs: list[Config], workdir: Path, jobs: int) -> None:
    """Generate every DUT-derived file (extensions.txt, rvtest_config.{h,svh},
    rvmodel_macros.svh) for every config, in parallel, using the same
    `build()` DAG executor as the main pipeline.

    Per config we emit:
      - a `validate` BuildTask whose output is a sentinel marker;
      - one BuildTask per UDB-derived file, with the marker in `deps` so
        validation must succeed before any UDB generator runs;
      - a BuildTask for `rvmodel_macros.svh`, which has no UDB dependency.

    Staleness, parallel scheduling, the transient progress widget and the
    failure-skips-dependents behaviour are all handled by `build()`.
    `bundle install` is run once up front because it isn't safe to run
    concurrently.
    """
    if not configs:
        return

    _ensure_udb_installed()

    tasks: list[BuildTask] = []
    for cfg in configs:
        config_dir = workdir / cfg.udb_config.stem
        config_dir.mkdir(parents=True, exist_ok=True)
        src = cfg.udb_config

        marker = config_dir / ".validated"
        tasks.append(
            BuildTask(
                outputs=(marker,),
                action=PythonAction(_validate_with_marker, (src, marker)),
                extra_inputs=(src,),
            )
        )

        for out_name, sub in (
            ("rvtest_config.h", "cfg-c-header"),
            ("rvtest_config.svh", "cfg-svh-header"),
        ):
            tasks.append(
                BuildTask(
                    outputs=(config_dir / out_name,),
                    action=PythonAction(_generate_one_dut_header, (src, config_dir / out_name, sub)),
                    extra_inputs=(src,),
                    deps=(marker,),
                )
            )

        tasks.append(
            BuildTask(
                outputs=(config_dir / "extensions.txt",),
                action=PythonAction(generate_extension_list, (src, config_dir)),
                extra_inputs=(src,),
                deps=(marker,),
            )
        )

        tasks.append(
            BuildTask(
                outputs=(config_dir / "rvmodel_macros.svh",),
                action=PythonAction(generate_rvmodel_svh, (cfg.dut_include_dir, config_dir)),
                extra_inputs=(cfg.dut_include_dir / "rvmodel_macros.h",),
            )
        )

    start = time.monotonic()
    result = build(tasks, jobs=jobs, phase_label="Preparing DUT configs")
    elapsed = time.monotonic() - start

    if result.errors:
        rprint(f"[bold red]✗ DUT prep failed:[/] {result.failed} task(s)", file=sys.stderr)
        sys.exit(1)

    n = len(configs)
    suffix = "all up to date" if result.succeeded == 0 else f"in {elapsed:.1f}s"
    rprint(f"[bold green]✓ DUT configs prepared:[/] {n} config{'s' if n != 1 else ''} {suffix}")


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


# TODO: Generate Sail config file from UDB
