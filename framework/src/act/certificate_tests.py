# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0

"""Certificate test-suite mappings."""

RVA23_TEST_SUITES = frozenset(
    {
        ### Unpriv tests
        "I",
        "M",
        "F",
        "D",
        # Zi extensions
        "Zicbom",
        "Zicbop",
        "Zicboz",
        "Zicclsm",
        "Zicond",
        "Zicsr",
        "Zifencei",
        "Zihintntl",
        "ZihintntlZca",
        "Zihintpause",
        "Zihpm",
        "Zimop",
        # Zm extensions
        "Zmmul",
        # Za extensions
        "Zaamo",
        "Zabha",
        "Zacas",
        "ZacasZabha",
        "Zalrsc",
        # Zf extensions
        "ZfaD",
        "ZfaF",
        "ZfaZfh",
        "ZfaZfhD",
        "ZfaZvfh",
        "Zfbfmin",
        "Zfh",
        "ZfhD",
        "Zfhmin",
        "ZfhminD",
        # Zc extensions
        "Zca",
        "Zcb",
        "ZcbM",
        "ZcbZba",
        "ZcbZbb",
        "Zcd",
        "Zcmop",
        # Zb extensions
        "Zba",
        "Zbb",
        "Zbc",
        "Zbs",
        # V extension
        "Vf16",
        "Vf32",
        "Vf64",
        "Vls16",
        "Vls32",
        "Vls64",
        "Vls8",
        "Vx16",
        "Vx32",
        "Vx64",
        "Vx8",
        # Zv extensions
        "Zvbb16",
        "Zvbb32",
        "Zvbb64",
        "Zvbb8",
        "Zvbc64",
        "Zvfbfmin",
        "Zvfbfwma",
        "Zvfhmin",
        "Zvkb16",
        "Zvkb32",
        "Zvkb64",
        "Zvkb8",
        "Zvkg",
        "Zvkg32",
        "Zvkned",
        "Zvkned32",
        "Zvknhb64",
        "Zvksed",
        "Zvksed32",
        "Zvksh",
        "Zvksh32",
        # Misaligned access tests
        "Misalign",
        "MisalignD",
        "MisalignF",
        "MisalignV",
        "MisalignZca",
        ### Priv Tests
        "U",
        "S",
        "H",
        "HV",
        "UV",
        "UF",
        # Exceptions Tests
        "ExceptionsF",
        "ExceptionsH",
        "ExceptionsHV",
        "ExceptionsS",
        "ExceptionsSv",
        "ExceptionsSvZaamo",
        "ExceptionsSvZalrsc",
        "ExceptionsU",
        "ExceptionsVf",
        "ExceptionsVls",
        "ExceptionsVx",
        "ExceptionsZaamo",
        "ExceptionsZalrsc",
        "ExceptionsZc",
        "ExceptionsZicboS",
        "ExceptionsZicboU",
        # Interrupts Tests
        "InterruptsH",
        "InterruptsS",
        "InterruptsU",
        # Za extensions
        "Za64rs",
        "Zama16b",
        "Zawrs",
        "ZawrsS",
        "ZawrsU",
        # Zi extensions
        "Zic64bZicboz",
        "ZicntrS",
        "ZicntrU",
        "ZicsrF",
        # Zk extensions
        "Zkr",
        "ZkrH",
        "ZkrS",
        "ZkrU",
        # Debug extension
        "Sdtrig",
        # Sh extensions
        "Shcounterenw",
        "Shgatpa",
        "Shlcofideleg",
        "Shtvala",
        "Shvstvala",
        "Shvstvecd",
        # Ss extensions
        "Sscofpmf",
        "Sscounterenw",
        "Ssstateen",
        "SsstateenH",
        "SsstrictS",
        "SsstrictV",
        "SstcH",
        "Sstvala",
        "Sstvecd",
        "Ssu64xl",
        # Sv extensions
        "Sv",
        "Svade",
        "Svadu",
        "SvaduH",
        "SvaduPMP",
        "Svbare",
        "SvH",
        "SvHZicbo",
        "Svinval",
        "SvinvalH",
        "Svnapot",
        "Svpbmt",
        "SvPMP",
        "SvPMPZicbo",
        "SvZicbo",
    }
)

CERTIFICATE_TEST_SUITES = {"RVA23": RVA23_TEST_SUITES}


def certificate_exists(certificate: str) -> bool:
    """Check if a certificate exists."""
    return certificate in CERTIFICATE_TEST_SUITES


def get_certificate_test_suites(certificate: str) -> frozenset[str]:
    """Return the test suites for a certificate."""
    try:
        return CERTIFICATE_TEST_SUITES[certificate]
    except KeyError:
        available = ", ".join(CERTIFICATE_TEST_SUITES)
        raise ValueError(f"Unknown certificate '{certificate}'. Available certificates: {available}.")
