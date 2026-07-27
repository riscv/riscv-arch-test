##################################
# cli.py
#
# Provides a helper to generate the cover-float test vectors.
# rwolk@g.hmc.edu July 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from pathlib import Path

import cover_float


def generate_coverfloat(output_dir: Path, jobs: int) -> bool:
    """
    Builds the coverfloat testvectors into a work directory.
    """

    testvectors_dir = output_dir / "testvectors"
    processed_vectors_dir = output_dir / "processed"

    testvectors_dir.mkdir(parents=True, exist_ok=True)
    processed_vectors_dir.mkdir(parents=True, exist_ok=True)

    config = cover_float.Config(
        output_dir=output_dir,
        full_coverage_testgen=False,  # This generates too many tests otherwise,
        quiet=True,
        silent=False,  # Still display 1 progress bar,
        release=True,
        jobs=jobs,
    )

    return cover_float.generate(config)
