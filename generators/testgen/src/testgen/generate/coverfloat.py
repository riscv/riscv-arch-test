##################################
# cli.py
#
# Provides a helper to generate the cover-float test vectors.
# rwolk@g.hmc.edu July 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import os
import subprocess
from pathlib import Path


def generate_coverfloat() -> None:
    """
    Build the cover-float test vectors in a subprocess.

    Builds with AGGRESSIVENESS=0 to prevent the fused multiply-add crosses from growing too big.
    """

    # Cover-Float runs with its own uv context. So, we need to unset the current virtual
    # environment.
    env = os.environ.copy()
    if "VIRTUAL_ENV" in env:
        del env["VIRTUAL_ENV"]

    cover_float_dir = Path(__file__).parent.parent / "cover-float"
    subprocess.run(
        ["make", "--silent", "--directory", str(cover_float_dir), "AGGRESSIVENESS=0", "processed-tests-only"],
        check=True,
        env=env,
    )
