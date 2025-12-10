##################################
# random_values.py
#
# jcarlin@hmc.edu 5 Oct 2025
# SPDX-License-Identifier: Apache-2.0
##################################


from random import choice, randint


def random_int(bits: int, *, signed: bool = True, nonzero: bool = False) -> int:
    """
    Generate a random integer value within the specified bit width.

    Args:
        bits: Number of bits (e.g., 32, 64 for registers, 12 for I-type imm)
        signed: If True, generate signed value (default). If False, unsigned.
        nonzero: If True, exclude zero from the generated values.

    Returns:
        Random integer in the appropriate range:
        - signed=True: random in [-(2^(bits-1)), 2^(bits-1) - 1], excluding 0 if nonzero=True
        - signed=False: random in [0, 2^bits - 1], excluding 0 if nonzero=True

    Examples:
        >>> random_int(32)                           # Random 32-bit signed value
        >>> random_int(12, signed=True)              # Random 12-bit signed immediate
        >>> random_int(5, signed=False)              # Random 5-bit unsigned [0, 31]
        >>> random_int(5, signed=False, nonzero=True)  # Non-zero 5-bit unsigned [1, 31]
    """
    if signed:
        min_val = -(2 ** (bits - 1))
        max_val = (2 ** (bits - 1)) - 1
    else:
        min_val = 0
        max_val = (2**bits) - 1

    return random_range(min_val, max_val, nonzero=nonzero)


def random_range(min_val: int, max_val: int, *, nonzero: bool = False) -> int:
    """
    Generate a random integer within an explicit value range.

    Args:
        min_val: Minimum value (inclusive)
        max_val: Maximum value (inclusive)
        nonzero: If True, exclude zero from the generated values.

    Returns:
        Random integer in [min_val, max_val], excluding 0 if nonzero=True

    Examples:
        >>> random_range(0, 31)                      # Random value [0, 31]
        >>> random_range(5, 15)                      # Random value [5, 15]
        >>> random_range(0, 10)                      # Random value [0, 10]
        >>> random_range(-5, 5, nonzero=True)        # Random value [-5, 5] excluding 0
    """
    # Generate random value, using fast path when possible
    if nonzero and min_val <= 0 <= max_val:
        # Need to exclude zero - check for fast paths
        if min_val == 0:
            # Only positive values: [1, max_val]
            return randint(1, max_val)
        elif max_val == 0:
            # Only negative values: [min_val, -1]
            return randint(min_val, -1)
        else:
            # Both negative and positive - use list comprehension for uniform distribution
            valid_values = [v for v in range(min_val, max_val + 1) if v != 0]
            return choice(valid_values)
    else:
        # Fast path: no filtering needed
        return randint(min_val, max_val)
