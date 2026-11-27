# SPDX-License-Identifier: Apache-2.0
"""Regression checks for the three-source FMA edge and rounding-mode cross."""

import re
import unittest
from itertools import product
from pathlib import Path

from testgen.coverpoints import generate_tests_for_coverpoint
from testgen.data.config import TestConfig
from testgen.data.edges import FLOAT_EDGES
from testgen.data.state import TestData
from testgen.data.test_chunk import group_test_chunks


class FmaTests(unittest.TestCase):
    def test_fma_edge_rounding_cross_matches_existing_bins(self) -> None:
        frm_modes = ("dyn", "rdn", "rmm", "rne", "rtz", "rup")
        template_dir = Path(__file__).resolve().parents[2] / "coverage/src/covergroupgen/templates"
        for suffix, width, edges in (
            ("h", 16, FLOAT_EDGES.half),
            ("s", 32, FLOAT_EDGES.single),
            ("d", 64, FLOAT_EDGES.double),
        ):
            variant = "" if suffix == "s" else "_" + suffix.upper()
            data = TestData(TestConfig(xlen=64, flen=width, testsuite="F"), "fmadd." + suffix)
            cp = "cr_fs1_fs2_fs3_edges_frm4" + variant
            chunks = generate_tests_for_coverpoint("fmadd." + suffix, "FR4", cp, data)
            expected = set(product(edges, edges, edges, frm_modes))
            actual = set()
            covered = set()
            bins = []
            template = (template_dir / f"cp_fs1_edges{variant}.sv").read_text()
            for name, expression in re.findall(r"bins (\w+)\s*=\s*\{([^}]+)\}", template):
                values = [int(value, 16) for value in re.findall(r"\d+'h([0-9a-fA-F]+)", expression)]
                bins.append((name, values[0], values[-1]))
            self.assertEqual(len(bins), 26)
            for chunk in chunks:
                values = tuple(chunk.data_values[:3])
                names = []
                for value in values:
                    hits = [name for name, low, high in bins if low <= value <= high]
                    self.assertEqual(len(hits), 1)
                    names.append(hits[0])
                instruction = next(line for line in chunk.code if "# perform operation" in line)
                self.assertEqual(len(set(re.findall(r"f(\d+)", instruction))), 4)
                mode = instruction.split(" # perform operation")[0].rsplit(", ", 1)[1]
                self.assertIn(mode, frm_modes)
                actual.add((*values, mode))
                covered.add((*names, mode))
            self.assertEqual(len(chunks), len(edges) ** 3 * len(frm_modes))
            self.assertEqual(actual, expected)
            bin_names = [name for name, _, _ in bins]
            self.assertEqual(covered, set(product(bin_names, bin_names, bin_names, frm_modes)))
            for inf in ("posinfinity", "neginfinity"):
                for zero in ("pos0", "neg0"):
                    for nan in ("posQNaN", "negQNaN"):
                        for mode in frm_modes:
                            self.assertIn((inf, zero, nan, mode), covered)
                            self.assertIn((zero, inf, nan, mode), covered)
            groups = group_test_chunks(chunks, 1000)
            self.assertTrue(all(len(files) == 1 and len(files[0]) <= 400 for _, files in groups))
            data.destroy()
