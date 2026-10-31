##################################
# data/vector_data.py
#
# Vector test data that is not emitted per label
# SPDX-License-Identifier: Apache-2.0
##################################

"""Vector test data types."""

from dataclasses import dataclass

VECTOR_RANDOM_DATA_FILE = "vector_random_data.h"
VECTOR_RANDOM_DATA_LABEL = "vector_ls_random_base"
LENGTH_DATA_POOL_LABEL = "vector_length_data"


@dataclass(frozen=True)
class PooledVectorData:
    """Operand data read from an instruction's random pool of 64-bit words, starting offset bytes into it."""

    pool: tuple[int, ...]
    offset: int


VectorData = list[int] | PooledVectorData
