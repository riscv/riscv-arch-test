# SPDX-License-Identifier: Apache-2.0
"""Assemble pooled operand labels and check their bounds for each supported VLEN."""

import shutil
import subprocess
import tempfile
import unittest
from itertools import pairwise
from pathlib import Path

from testgen.asm.sections import generate_vector_data_section
from testgen.constants import VECTOR_LENGTH_DATA_POOL_BYTES, VLEN_MAX
from testgen.data.config import TestConfig
from testgen.data.state import TestData
from testgen.data.vector_data import PooledVectorData


@unittest.skipUnless(shutil.which("riscv64-unknown-elf-gcc"), "requires the RISC-V GNU toolchain")
class VectorPoolTest(unittest.TestCase):
    def test_assembled_operands(self) -> None:
        data = TestData(TestConfig(xlen=64, flen=64, testsuite="Vx8", sew=8), "vadd.vv")
        groups: list[list[tuple[str, int]]] = []
        # Four maximum-size operands exercise the tightest packing. Mixed sizes exercise alignment.
        for sizes in [(4096, 4096, 4096, 4096), (512, 1024, 2048, 4096), (64, 128, 256, 512)] * 16:
            data.increment_test_count()
            group = []
            for operand, size in enumerate(sizes):
                label = f"operand_{data.test_count}_{operand}"
                data.register_pooled_vector_data(label, 8, size)
                group.append((label, size))
            groups.append(group)
        labels = [(label, value, eew) for label, (value, eew) in data.vector_labels.items()]
        assembly = ".data\n" + generate_vector_data_section(labels) + "\n"
        offsets: dict[int, dict[str, int]] = {}
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "pool.S"
            obj = Path(tmp) / "pool.o"
            source.write_text(assembly)
            for vlen in (32, 64, 128, 256, 512, 1024, 2048, 4096):
                subprocess.run(
                    [
                        "riscv64-unknown-elf-gcc",
                        "-c",
                        "-march=rv64g",
                        "-mabi=lp64d",
                        f"-DUDB_VLEN={vlen}",
                        str(source),
                        "-o",
                        str(obj),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                symbols = subprocess.check_output(["riscv64-unknown-elf-nm", "-P", str(obj)], text=True)
                offsets[vlen] = {
                    parts[0]: int(parts[2], 16) for line in symbols.splitlines() if (parts := line.split())
                }
                base = offsets[vlen]["vector_length_data"]
                for group in groups:
                    intervals = []
                    for label, size in group:
                        offset = offsets[vlen][label] - base
                        # Setup may load a whole register even when the operand uses fractional LMUL.
                        length = max((size * vlen + VLEN_MAX - 1) // VLEN_MAX, vlen // 8)
                        self.assertEqual(offset % 8, 0)
                        self.assertGreaterEqual(offset, 0)
                        self.assertLessEqual(offset + length, VECTOR_LENGTH_DATA_POOL_BYTES)
                        intervals.append((offset, offset + length))
                    intervals.sort()
                    for left, right in pairwise(intervals):
                        self.assertLessEqual(left[1], right[0])
        # At the maximum, full-size operands fill their slots. Smaller DUTs use varied interior offsets.
        interior_offsets = set()
        for group in groups:
            for label, size in group:
                if size != VLEN_MAX:
                    continue
                value, _ = data.vector_labels[label]
                self.assertIsInstance(value, PooledVectorData)
                assert isinstance(value, PooledVectorData)
                self.assertEqual(offsets[4096][label], value.slot * VLEN_MAX)
                interior_offsets.add(offsets[128][label] - value.slot * VLEN_MAX)
        self.assertGreater(len(interior_offsets), 16)


if __name__ == "__main__":
    unittest.main()
