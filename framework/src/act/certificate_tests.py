# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: Apache-2.0

"""Certificate extension lists.

A test belongs to a certificate if every extension it requires is in the certificate's extension list.
For a group of alternative extensions, one member in the list is enough.

A DUT can be tested for a certificate only if its UDB configuration implements every mandatory
extension of the certificate.
"""

# Mandatory extensions of the RVA23U64 and RVA23S64 profiles, including the extensions they imply, as
# UDB resolves them. B and Sha are checked through their components (Zba, Zbb, Zbs; H and the Sh*
# extensions), because UDB does not add the group names to a configuration that lists only the
# components. Sm is left out: RVA23 sets no machine-mode requirements, and machine-mode tests are
# not part of the certificate.
RVA23_MANDATORY_EXTENSIONS = frozenset(
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
        "Ziccif",
        "Zicclsm",
        "Ziccrse",
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
        # Za extensions
        "Za64rs",
        "Za128rs",
        "Zaamo",
        "Zalrsc",
        "Zawrs",
        # Zf extensions
        "Zfa",
        "Zfhmin",
        # Zc extensions
        "Zca",
        "Zcb",
        "Zcd",
        "Zcmop",
        # Zb extensions (B)
        "Zba",
        "Zbb",
        "Zbs",
        # Zk extensions
        "Zkt",
        # Zv extensions
        "Zvbb",
        "Zvfhmin",
        "Zvkb",
        "Zvkt",
        "Zve32f",
        "Zve32x",
        "Zve64d",
        "Zve64f",
        "Zve64x",
        "Zvl32b",
        "Zvl64b",
        "Zvl128b",
        # Sh extensions (Sha)
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
        "Ssnpm",
        "Ssstateen",
        "Sstc",
        "Sstvala",
        "Sstvecd",
        "Ssu64xl",
        "Supm",
        # Sv extensions
        "Sv39",
        "Svade",
        "Svbare",
        "Svinval",
        "Svnapot",
        "Svpbmt",
    }
)

# Optional extensions of the RVA23U64 and RVA23S64 profiles, with the extensions they imply or require.
# A DUT that implements one is tested on it; a DUT that does not is not required to.
RVA23_OPTIONAL_EXTENSIONS = frozenset(
    {
        # Zi extensions
        "Ziccamoc",
        "Zicfilp",
        "Zicfiss",
        # Za extensions
        "Zabha",
        "Zacas",
        "Zama16b",
        # Zf extensions
        "Zfbfmin",
        "Zfh",
        # Zb extensions (Zbc requires Zbkc)
        "Zbc",
        "Zbkc",
        # Zk extensions
        "Zkr",
        # Zv extensions (Zvkng = Zvkn + Zvkg, Zvksg = Zvks + Zvkg; Zvknhb requires Zvknha)
        "Zvbc",
        "Zvfbfmin",
        "Zvfbfwma",
        "Zvfh",
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
        # Sd extensions
        "Sdtrig",
        # Ss extensions (Sspm requires Smnpm)
        "Smnpm",
        "Sspm",
        "Ssstrict",
        # Sv extensions
        "Sv48",
        "Sv57",
        "Svadu",
        "Svvptc",
    }
)

RVA23_EXTENSIONS = RVA23_MANDATORY_EXTENSIONS | RVA23_OPTIONAL_EXTENSIONS | {"B", "Sha"}

CERTIFICATE_EXTENSIONS = {"RVA23": RVA23_EXTENSIONS}
CERTIFICATE_MANDATORY_EXTENSIONS = {"RVA23": RVA23_MANDATORY_EXTENSIONS}


class CertificateError(Exception):
    """A DUT configuration does not meet a certificate's requirements."""


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


def check_mandatory_extensions(config_name: str, certificate: str, implemented_extensions: frozenset[str]) -> None:
    """Raise CertificateError if the configuration lacks any of the certificate's mandatory extensions."""
    missing = sorted(CERTIFICATE_MANDATORY_EXTENSIONS[certificate] - implemented_extensions)
    if missing:
        raise CertificateError(
            f"{config_name} does not implement the {certificate} mandatory extension(s) {', '.join(missing)}. "
            f"Add them to its UDB configuration, or build without CERTIFICATE={certificate}."
        )
