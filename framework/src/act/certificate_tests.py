# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0

"""Certificate extension lists.

A test belongs to a certificate if every extension it requires is in the certificate's extension list.
For a group of alternative extensions, one member in the list is enough.
"""

RVA23_EXTENSIONS = frozenset(
    {
        # Single letter extensions
        "I",
        "M",
        "A",
        "F",
        "D",
        "C",
        "V",
        "S",
        "U",
        "H",
        # Zi extensions
        "Zic64b",
        "Zicbom",
        "Zicbop",
        "Zicboz",
        "Ziccamoa",
        "Ziccamoc",
        "Ziccif",
        "Zicclsm",
        "Ziccrse",
        "Zicfilp",
        "Zicfiss",
        "Zicntr",
        "Zicond",
        "Zicsr",
        "Zifencei",
        "Zihintntl",
        "Zihintpause",
        "Zihpm",
        "Zimop",
        # Zm extensions
        "Zmmul",
        # Zk extensions
        "Zkt",
        # Za extensions
        "Za64rs",
        "Za128rs",
        "Zaamo",
        "Zabha",
        "Zacas",
        "Zalrsc",
        "Zama16b",
        "Zawrs",
        # Zf extensions
        "Zfa",
        "Zfbfmin",
        "Zfh",
        "Zfhmin",
        # Zc extensions
        "Zca",
        "Zcb",
        "Zcd",
        "Zcmop",
        # Zb extensions (B; Zbc requires Zbkc)
        "B",
        "Zba",
        "Zbb",
        "Zbc",
        "Zbkc",
        "Zbs",
        # Zk extensions
        "Zkr",
        # Zv extensions
        "Zvbb",
        "Zvbc",
        "Zve32f",
        "Zve32x",
        "Zve64d",
        "Zve64f",
        "Zve64x",
        "Zvfbfmin",
        "Zvfbfwma",
        "Zvfh",
        "Zvfhmin",
        "Zvkb",
        "Zvkg",
        "Zvkn",
        "Zvkned",
        "Zvkng",
        "Zvknha",
        "Zvknhb",
        "Zvks",
        "Zvksed",
        "Zvksg",
        "Zvksh",
        "Zvkt",
        "Zvl32b",
        "Zvl64b",
        "Zvl128b",
        # Sd extensions
        "Sdtrig",
        # Sh extensions (Sha)
        "Sha",
        "Shcounterenw",
        "Shgatpa",
        "Shtvala",
        "Shvsatpa",
        "Shvstvala",
        "Shvstvecd",
        # Ss extensions
        "Ssccptr",
        "Sscofpmf",
        "Sscounterenw",
        "Sspm",
        "Ssstateen",
        "Ssstrict",
        "Sstc",
        "Sstvala",
        "Sstvecd",
        "Ssu64xl",
        "Ssnpm",
        "Smnpm",
        "Supm",
        # Sv extensions
        "Sv39",
        "Sv48",
        "Sv57",
        "Svade",
        "Svadu",
        "Svbare",
        "Svinval",
        "Svnapot",
        "Svpbmt",
        "Svvptc",
    }
)

CERTIFICATE_EXTENSIONS = {"RVA23": RVA23_EXTENSIONS}


def certificate_exists(certificate: str) -> bool:
    """Check if a certificate exists."""
    return certificate in CERTIFICATE_EXTENSIONS


def get_certificate_extensions(certificate: str) -> frozenset[str]:
    """Return the extensions that a certificate covers."""
    try:
        return CERTIFICATE_EXTENSIONS[certificate]
    except KeyError:
        available = ", ".join(CERTIFICATE_EXTENSIONS)
        raise ValueError(f"Unknown certificate '{certificate}'. Available certificates: {available}.")
