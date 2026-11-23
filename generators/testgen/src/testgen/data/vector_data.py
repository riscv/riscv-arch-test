##################################
# data/vector_data.py
#
# Vector test data that is not emitted per label
# SPDX-License-Identifier: Apache-2.0
##################################

"""Vector test data types."""

from dataclasses import dataclass

from testgen.constants import VLEN_MAX

VECTOR_RANDOM_DATA_FILE = "vector_random_data.h"
VECTOR_RANDOM_DATA_LABEL = "vector_ls_random_base"
LENGTH_DATA_POOL_LABEL = "vector_length_data"


@dataclass(frozen=True)
class PooledVectorData:
    """One operand's slot in a shared pool, with its offset selected for the configured VLEN."""

    pool: tuple[int, ...]
    slot: int
    max_bytes: int
    offset_seed: int

    def assembly_offset(self) -> str:
        """Choose an eight-byte-aligned offset that leaves room for the full operand, including tails."""
        operand_bytes = f"((UDB_VLEN * {self.max_bytes} + {VLEN_MAX - 1}) / {VLEN_MAX})"
        choices = f"(({VLEN_MAX} - {operand_bytes}) / 8 + 1)"
        return f"{self.slot * VLEN_MAX} + ({self.offset_seed} % {choices}) * 8"


VectorData = list[int] | PooledVectorData
