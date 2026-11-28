##################################
# data/vector_data.py
#
# Vector test data that is not emitted per label
# SPDX-License-Identifier: Apache-2.0
##################################

"""Vector test data types."""

from dataclasses import dataclass

from testgen.constants import VECTOR_LENGTH_DATA_SLOT_BYTES, VLEN_MAX

VECTOR_RANDOM_DATA_FILE = "vector_random_data.h"
VECTOR_RANDOM_DATA_LABEL = "vector_ls_random_base"
LENGTH_DATA_POOL_LABEL = "vector_length_data"


@dataclass
class PooledVectorData:
    """One operand's slot in a shared pool, with its offset selected for the configured VLEN."""

    pool: tuple[int, ...]
    slot: int
    offset_seed: int
    load_bytes: int = 0  # most bytes a setup load reads from the operand at VLEN_MAX

    def record_load(self, lmul: float) -> None:
        self.load_bytes = max(self.load_bytes, int(VLEN_MAX * lmul) // 8)
        assert self.load_bytes <= VECTOR_LENGTH_DATA_SLOT_BYTES, f"LMUL={lmul} setup load overflows its pool slot"

    def assembly_offset(self) -> str:
        """Choose an eight-byte-aligned offset that leaves room for the setup loads at the configured VLEN."""
        load_bytes = f"((UDB_VLEN * {self.load_bytes} + {VLEN_MAX - 1}) / {VLEN_MAX})"
        choices = f"(({VECTOR_LENGTH_DATA_SLOT_BYTES} - {load_bytes}) / 8 + 1)"
        return f"{self.slot * VECTOR_LENGTH_DATA_SLOT_BYTES} + ({self.offset_seed} % {choices}) * 8"


VectorData = list[int] | PooledVectorData
