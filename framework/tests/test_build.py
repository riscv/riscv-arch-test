##################################
# test_build.py
#
# SPDX-License-Identifier: Apache-2.0
#
# Regression tests for the DAG build executor, focused on delete-on-error:
# a task that fails must not leave a half-written output behind, or a later
# run would treat the stale file as up-to-date and silently skip it.
##################################

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from act.build import BuildResult, BuildTask, PythonAction, build, is_stale


def run_build(tasks: list[BuildTask]) -> BuildResult:
    """Run a single-threaded build, swallowing the progress/console output."""
    with redirect_stdout(io.StringIO()):
        return build(tasks, jobs=1)


def crashing_writer(out: Path) -> None:
    """Write a partial output then fail, mimicking a ref model crashing mid-run."""
    out.write_text("only half the answers\n")
    raise RuntimeError("reference model crashed")


class DeleteOnError(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def test_partial_output_is_removed_on_failure(self) -> None:
        out = self.tmp / "answer.key"
        task = BuildTask(outputs=(out,), action=PythonAction(fn=crashing_writer, args=(out,)))

        result = run_build([task])

        self.assertEqual(result.failed, 1)
        self.assertFalse(out.exists(), "a failed task must not leave its half-written output behind")

    def test_failed_task_reruns_instead_of_caching(self) -> None:
        # The crux: after a failure the task must stay stale so the next run
        # regenerates it, rather than mistaking the leftover for a finished build.
        src = self.tmp / "input.S"
        src.write_text("source\n")
        out = self.tmp / "answer.key"
        task = BuildTask(
            outputs=(out,),
            extra_inputs=(src,),
            action=PythonAction(fn=crashing_writer, args=(out,)),
        )

        run_build([task])
        self.assertTrue(is_stale(task), "a failed task must remain stale")

        second = run_build([task])
        self.assertEqual(second.skipped, 0, "must not silently skip a previously failed task")
        self.assertEqual(second.failed, 1)

    def test_every_output_is_removed_even_if_only_one_was_written(self) -> None:
        first, second = self.tmp / "a.bin", self.tmp / "b.bin"

        def write_first_then_fail() -> None:
            first.write_text("a\n")
            raise RuntimeError("crashed before writing the second output")

        task = BuildTask(outputs=(first, second), action=PythonAction(fn=write_first_then_fail))
        run_build([task])

        self.assertFalse(first.exists())
        self.assertFalse(second.exists())


class SuccessPathUnaffected(unittest.TestCase):
    """Guard against over-zealous cleanup touching healthy builds."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def test_successful_output_is_kept_and_cached(self) -> None:
        out = self.tmp / "answer.key"
        task = BuildTask(outputs=(out,), action=PythonAction(fn=lambda p: p.write_text("all answers\n"), args=(out,)))

        first = run_build([task])
        self.assertEqual(first.succeeded, 1)

        second = run_build([task])
        self.assertEqual(second.skipped, 1, "an up-to-date task should be skipped on re-run")
        self.assertEqual(out.read_text(), "all answers\n")


if __name__ == "__main__":
    unittest.main()
