##################################
# cp_custom_act3_crypto.py
#
# rwolk@hmc.edu September 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from csv import DictReader
from pathlib import Path

from testgen.coverpoints.registry import add_coverpoint_generator
from testgen.data.state import TestData, return_testcase_registers
from testgen.data.test_chunk import TestChunk
from testgen.formatters import format_single_testcase
from testgen.instructions.vector_params import generate_random_vector_params

##############
# ACT3 Crypto
##############

# Taken From ACT3 riscv-test-suite/env/test_macros_vector.h
ACT3_TEST_DATA = [
    0x0F1E2D3C,
    0x4B5A6978,
    0xF0E1D2C3,
    0xB4A59687,
    0x5A5A5A5A,
    0x5A5A5A5A,
    0xA5A5A5A5,
    0xA5A5A5A5,
    0x10111213,
    0x14151617,
    0xF8F9FAFB,
    0xFCFDFEFF,
    0x01112131,
    0x41516171,
    0x8F9FAFBF,
    0xCFDFEFFF,
    0x00FF00FF,
    0x00FF00FF,
    0xFF00FF00,
    0xFF00FF00,
    0x08800880,
    0x08800880,
    0x80088008,
    0x80088008,
    0x00010203,
    0x04050607,
    0x08090A0B,
    0x0C0D0E0F,
    0x80818283,
    0x84858687,
    0x88898A8B,
    0x8C8D8E8F,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0x00000000,
    0xFFFFFFFF,
    0xFFFFFFFF,
    0xFFFFFFFF,
    0xFFFFFFFF,
    0xFFFFFFFF,
    0xFFFFFFFF,
    0xFFFFFFFF,
    0xFFFFFFFF,
    0xFFFFFFFF,
    0xFFFFFFFF,
    0xFFFFFFFF,
    0xFFFFFFFF,
    0xFFFFFFFF,
    0xFFFFFFFF,
    0xFFFFFFFF,
    0xFFFFFFFF,
]

# Taken From ACT3 riscv-test-suite/rv32i_m/Zvk/src/vaesdf.vs-01.S
# All tests use the same values in this suite
ACT3_TEST_OFFSETS = [
    (0 * 4, 0 * 4),
    (1 * 4, 0 * 4),
    (2 * 4, 2 * 4),
    (0 * 4, 0 * 4),
    (2 * 4, 3 * 4),
    (2 * 4, 3 * 4),
    (2 * 4, 3 * 4),
    (2 * 4, 3 * 4),
    (0 * 4, 4 * 4),
    (4 * 4, 0 * 4),
    (0 * 4, 0 * 4),
    (0 * 4, 11 * 4),
    (2 * 4, 9 * 4),
    (4 * 4, 7 * 4),
    (6 * 4, 5 * 4),
    (8 * 4, 3 * 4),
    (10 * 4, 1 * 4),
]


@add_coverpoint_generator("cp_custom_act3_crypto")
def make_act3_crypto(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    test_chunks: list[TestChunk] = []

    for i, (vd_ptr, vs2_ptr) in enumerate(ACT3_TEST_OFFSETS):
        vd_val_ptr = f"act3_crypto_value_{i}_vd"
        vs2_val_ptr = f"act3_crypto_value_{i}_vs2"

        test_data.register_vector_data(vd_val_ptr, 32, elements=ACT3_TEST_DATA[vd_ptr : vd_ptr + 4])
        test_data.register_vector_data(vs2_val_ptr, 32, elements=ACT3_TEST_DATA[vs2_ptr : vs2_ptr + 4])

        desc = f"ACT3 Vector Crypto Test {i}"
        bin_name = f"test_{i}"

        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            4,
            vl=4,
            vd_val_pointer=vd_val_ptr,
            vs2_val_pointer=vs2_val_ptr,
            additional_no_overlap={("vd", "vs2")},
        )
        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        return_testcase_registers(test_data, params)
        test_chunks.append(tc)

    return test_chunks


##############
# NIST SHA
##############

MESSAGE_SCHEDULE_256 = [
    0x61626364,
    0x62636465,
    0x63646566,
    0x64656667,
    0x65666768,
    0x66676869,
    0x6768696A,
    0x68696A6B,
    0x696A6B6C,
    0x6A6B6C6D,
    0x6B6C6D6E,
    0x6C6D6E6F,
    0x6D6E6F70,
    0x6E6F7071,
    0x80000000,
    0x00000000,
]

K_256 = [
    0x428A2F98,
    0x71374491,
    0xB5C0FBCF,
    0xE9B5DBA5,
    0x3956C25B,
    0x59F111F1,
    0x923F82A4,
    0xAB1C5ED5,
    0xD807AA98,
    0x12835B01,
    0x243185BE,
    0x550C7DC3,
    0x72BE5D74,
    0x80DEB1FE,
    0x9BDC06A7,
    0xC19BF174,
    0xE49B69C1,
    0xEFBE4786,
    0x0FC19DC6,
    0x240CA1CC,
    0x2DE92C6F,
    0x4A7484AA,
    0x5CB0A9DC,
    0x76F988DA,
    0x983E5152,
    0xA831C66D,
    0xB00327C8,
    0xBF597FC7,
    0xC6E00BF3,
    0xD5A79147,
    0x06CA6351,
    0x14292967,
    0x27B70A85,
    0x2E1B2138,
    0x4D2C6DFC,
    0x53380D13,
    0x650A7354,
    0x766A0ABB,
    0x81C2C92E,
    0x92722C85,
    0xA2BFE8A1,
    0xA81A664B,
    0xC24B8B70,
    0xC76C51A3,
    0xD192E819,
    0xD6990624,
    0xF40E3585,
    0x106AA070,
    0x19A4C116,
    0x1E376C08,
    0x2748774C,
    0x34B0BCB5,
    0x391C0CB3,
    0x4ED8AA4A,
    0x5B9CCA4F,
    0x682E6FF3,
    0x748F82EE,
    0x78A5636F,
    0x84C87814,
    0x8CC70208,
    0x90BEFFFA,
    0xA4506CEB,
    0xBEF9A3F7,
    0xC67178F2,
]

MESSAGE_SCHEDULE_512 = [
    0x6162636465666768,
    0x6263646566676869,
    0x636465666768696A,
    0x6465666768696A6B,
    0x65666768696A6B6C,
    0x666768696A6B6C6D,
    0x6768696A6B6C6D6E,
    0x68696A6B6C6D6E6F,
    0x696A6B6C6D6E6F70,
    0x6A6B6C6D6E6F7071,
    0x6B6C6D6E6F707172,
    0x6C6D6E6F70717273,
    0x6D6E6F7071727374,
    0x6E6F707172737475,
    0x8000000000000000,
    0x0000000000000000,
]

K_512 = [
    0x428A2F98D728AE22,
    0x7137449123EF65CD,
    0xB5C0FBCFEC4D3B2F,
    0xE9B5DBA58189DBBC,
    0x3956C25BF348B538,
    0x59F111F1B605D019,
    0x923F82A4AF194F9B,
    0xAB1C5ED5DA6D8118,
    0xD807AA98A3030242,
    0x12835B0145706FBE,
    0x243185BE4EE4B28C,
    0x550C7DC3D5FFB4E2,
    0x72BE5D74F27B896F,
    0x80DEB1FE3B1696B1,
    0x9BDC06A725C71235,
    0xC19BF174CF692694,
    0xE49B69C19EF14AD2,
    0xEFBE4786384F25E3,
    0x0FC19DC68B8CD5B5,
    0x240CA1CC77AC9C65,
    0x2DE92C6F592B0275,
    0x4A7484AA6EA6E483,
    0x5CB0A9DCBD41FBD4,
    0x76F988DA831153B5,
    0x983E5152EE66DFAB,
    0xA831C66D2DB43210,
    0xB00327C898FB213F,
    0xBF597FC7BEEF0EE4,
    0xC6E00BF33DA88FC2,
    0xD5A79147930AA725,
    0x06CA6351E003826F,
    0x142929670A0E6E70,
    0x27B70A8546D22FFC,
    0x2E1B21385C26C926,
    0x4D2C6DFC5AC42AED,
    0x53380D139D95B3DF,
    0x650A73548BAF63DE,
    0x766A0ABB3C77B2A8,
    0x81C2C92E47EDAEE6,
    0x92722C851482353B,
    0xA2BFE8A14CF10364,
    0xA81A664BBC423001,
    0xC24B8B70D0F89791,
    0xC76C51A30654BE30,
    0xD192E819D6EF5218,
    0xD69906245565A910,
    0xF40E35855771202A,
    0x106AA07032BBD1B8,
    0x19A4C116B8D2D0C8,
    0x1E376C085141AB53,
    0x2748774CDF8EEB99,
    0x34B0BCB5E19B48A8,
    0x391C0CB3C5C95A63,
    0x4ED8AA4AE3418ACB,
    0x5B9CCA4F7763E373,
    0x682E6FF3D6B2B8A3,
    0x748F82EE5DEFB2FC,
    0x78A5636F43172F60,
    0x84C87814A1F0AB72,
    0x8CC702081A6439EC,
    0x90BEFFFA23631E28,
    0xA4506CEBDE82BDE9,
    0xBEF9A3F7B2C67915,
    0xC67178F2E372532B,
    0xCA273ECEEA26619C,
    0xD186B8C721C0C207,
    0xEADA7DD6CDE0EB1E,
    0xF57D4F7FEE6ED178,
    0x06F067AA72176FBA,
    0x0A637DC5A2C898A6,
    0x113F9804BEF90DAE,
    0x1B710B35131C471B,
    0x28DB77F523047D84,
    0x32CAAB7B40C72493,
    0x3C9EBE0A15C9BEBC,
    0x431D67C49C100D4C,
    0x4CC5D4BECB3E42B6,
    0x597F299CFC657E2A,
    0x5FCB6FAB3AD6FAEC,
    0x6C44198C4A475817,
]

HASH_ROUND_VALUES_256 = [
    [0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A, 0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19],
    [0x5D6AEBB1, 0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xFA2A4606, 0x510E527F, 0x9B05688C, 0x1F83D9AB],
    [0x2F2D5FCF, 0x5D6AEBB1, 0x6A09E667, 0xBB67AE85, 0x4EB1CFCE, 0xFA2A4606, 0x510E527F, 0x9B05688C],
    [0x97651825, 0x2F2D5FCF, 0x5D6AEBB1, 0x6A09E667, 0x62D5C49E, 0x4EB1CFCE, 0xFA2A4606, 0x510E527F],
    [0x4A8D64D5, 0x97651825, 0x2F2D5FCF, 0x5D6AEBB1, 0x6494841B, 0x62D5C49E, 0x4EB1CFCE, 0xFA2A4606],
    [0xF921C212, 0x4A8D64D5, 0x97651825, 0x2F2D5FCF, 0x05C4F88A, 0x6494841B, 0x62D5C49E, 0x4EB1CFCE],
    [0x55C8EF48, 0xF921C212, 0x4A8D64D5, 0x97651825, 0x7FF91C94, 0x05C4F88A, 0x6494841B, 0x62D5C49E],
    [0x485835B7, 0x55C8EF48, 0xF921C212, 0x4A8D64D5, 0x39A5B2CA, 0x7FF91C94, 0x05C4F88A, 0x6494841B],
    [0xD237E6DB, 0x485835B7, 0x55C8EF48, 0xF921C212, 0xA401D211, 0x39A5B2CA, 0x7FF91C94, 0x05C4F88A],
    [0x359F2BCE, 0xD237E6DB, 0x485835B7, 0x55C8EF48, 0xC09FFEC4, 0xA401D211, 0x39A5B2CA, 0x7FF91C94],
    [0x3A474B2B, 0x359F2BCE, 0xD237E6DB, 0x485835B7, 0x9037B3B8, 0xC09FFEC4, 0xA401D211, 0x39A5B2CA],
    [0xB8E2B4CB, 0x3A474B2B, 0x359F2BCE, 0xD237E6DB, 0x443ED29E, 0x9037B3B8, 0xC09FFEC4, 0xA401D211],
    [0x1762215C, 0xB8E2B4CB, 0x3A474B2B, 0x359F2BCE, 0xEE1C97A8, 0x443ED29E, 0x9037B3B8, 0xC09FFEC4],
]

HASH_ROUND_VALUES_512 = [
    [
        0x6A09E667F3BCC908,
        0xBB67AE8584CAA73B,
        0x3C6EF372FE94F82B,
        0xA54FF53A5F1D36F1,
        0x510E527FADE682D1,
        0x9B05688C2B3E6C1F,
        0x1F83D9ABFB41BD6B,
        0x5BE0CD19137E2179,
    ],
    [
        0xF6AFCE9D2263455D,
        0x6A09E667F3BCC908,
        0xBB67AE8584CAA73B,
        0x3C6EF372FE94F82B,
        0x58CB0218E01B86F9,
        0x510E527FADE682D1,
        0x9B05688C2B3E6C1F,
        0x1F83D9ABFB41BD6B,
    ],
    [
        0x0B7056A534AE5F62,
        0xF6AFCE9D2263455D,
        0x6A09E667F3BCC908,
        0xBB67AE8584CAA73B,
        0xF8C7198FE39E4C8C,
        0x58CB0218E01B86F9,
        0x510E527FADE682D1,
        0x9B05688C2B3E6C1F,
    ],
    [
        0x2CA82233760C9942,
        0x0B7056A534AE5F62,
        0xF6AFCE9D2263455D,
        0x6A09E667F3BCC908,
        0x303ECCCCD65953DE,
        0xF8C7198FE39E4C8C,
        0x58CB0218E01B86F9,
        0x510E527FADE682D1,
    ],
    [
        0xA023F17CE52CDA7B,
        0x2CA82233760C9942,
        0x0B7056A534AE5F62,
        0xF6AFCE9D2263455D,
        0xFFDEE5EEDCC9CA42,
        0x303ECCCCD65953DE,
        0xF8C7198FE39E4C8C,
        0x58CB0218E01B86F9,
    ],
    [
        0x8F0A67D9D591A1A7,
        0xA023F17CE52CDA7B,
        0x2CA82233760C9942,
        0x0B7056A534AE5F62,
        0xCB4CFBB166505F2F,
        0xFFDEE5EEDCC9CA42,
        0x303ECCCCD65953DE,
        0xF8C7198FE39E4C8C,
    ],
    [
        0xB466267371ACC493,
        0x8F0A67D9D591A1A7,
        0xA023F17CE52CDA7B,
        0x2CA82233760C9942,
        0x73D6C84C54D399EE,
        0xCB4CFBB166505F2F,
        0xFFDEE5EEDCC9CA42,
        0x303ECCCCD65953DE,
    ],
    [
        0x658269F1A312FCCD,
        0xB466267371ACC493,
        0x8F0A67D9D591A1A7,
        0xA023F17CE52CDA7B,
        0xCDC40314975FB275,
        0x73D6C84C54D399EE,
        0xCB4CFBB166505F2F,
        0xFFDEE5EEDCC9CA42,
    ],
    [
        0x65E3519C5B88181B,
        0x658269F1A312FCCD,
        0xB466267371ACC493,
        0x8F0A67D9D591A1A7,
        0xA657850AB3970C5A,
        0xCDC40314975FB275,
        0x73D6C84C54D399EE,
        0xCB4CFBB166505F2F,
    ],
    [
        0x56604FBB4B6393EC,
        0x65E3519C5B88181B,
        0x658269F1A312FCCD,
        0xB466267371ACC493,
        0xE8B3BE22FBE64DF7,
        0xA657850AB3970C5A,
        0xCDC40314975FB275,
        0x73D6C84C54D399EE,
    ],
    [
        0xC4562769A37D02C0,
        0x56604FBB4B6393EC,
        0x65E3519C5B88181B,
        0x658269F1A312FCCD,
        0x0062E70A1EF705C1,
        0xE8B3BE22FBE64DF7,
        0xA657850AB3970C5A,
        0xCDC40314975FB275,
    ],
    [
        0x27C0B4C9186E1736,
        0xC4562769A37D02C0,
        0x56604FBB4B6393EC,
        0x65E3519C5B88181B,
        0xBC9740477A18AE2D,
        0x0062E70A1EF705C1,
        0xE8B3BE22FBE64DF7,
        0xA657850AB3970C5A,
    ],
    [
        0xF17F52FB02F4EB74,
        0x27C0B4C9186E1736,
        0xC4562769A37D02C0,
        0x56604FBB4B6393EC,
        0xBE58522CB9590EE1,
        0xBC9740477A18AE2D,
        0x0062E70A1EF705C1,
        0xE8B3BE22FBE64DF7,
    ],
]


@add_coverpoint_generator("cp_custom_nist_sha")
def make_nist_sha(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    """Tests generated from NIST SHA examples"""

    sew = test_data.config.sew
    assert sew is not None, "SEW must be set for vector tests"

    message = [
        "######################################################################################################",
        "# These tests include data from the SHA examples given by NIST. They use the data from the message",
        "# schedule blocks given in the second example, first block. This was chosen because of the examples",
        "# it has the most non-zero entries in the message schedule which hopefully makes it more interesting.",
        "# No more information than is given in these files is used for testing. The intermediate hash values",
        "# are taken from the lines numbered t=1..11, and the first hash values are the standard first values",
        "# for their respective hashes (with 16 schedule values given, this is the maximum we can reach).",
        "# Data Taken From: https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Standards-and-Guidelines/documents/examples/SHA256.pdf",
        "# and https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Standards-and-Guidelines/documents/examples/SHA512.pdf",
        "######################################################################################################",
    ]

    schedule = MESSAGE_SCHEDULE_256 if sew == 32 else MESSAGE_SCHEDULE_512
    hash_round_values = HASH_ROUND_VALUES_256 if sew == 32 else HASH_ROUND_VALUES_512
    k = K_256 if sew == 32 else K_512

    if instr_name == "vsha2ms.vv":
        vd = schedule[0:4]
        vs2 = [schedule[4], schedule[9], schedule[10], schedule[11]]
        vs1 = schedule[12:16]

        vd_val_ptr = "custom_nist_sha_vd"
        vs2_val_ptr = "custom_nist_sha_vs2"
        vs1_val_ptr = "custom_nist_sha_vs1"

        test_data.register_vector_data(vd_val_ptr, sew, elements=vd)
        test_data.register_vector_data(vs2_val_ptr, sew, elements=vs2)
        test_data.register_vector_data(vs1_val_ptr, sew, elements=vs1)

        desc = "NIST SHA Example Message Schedule"
        bin_name = ""

        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            lmul=4,
            additional_no_overlap={("vd", "vs1"), ("vd", "vs2"), ("vs2", "vs1")},
            vd_val_pointer=vd_val_ptr,
            vs1_val_pointer=vs1_val_ptr,
            vs2_val_pointer=vs2_val_ptr,
        )

        tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
        tc.code.insert(0, "\n".join(message))
        return_testcase_registers(test_data, params)

        return [tc]
    else:
        test_chunks: list[TestChunk] = []
        for i, values in enumerate(hash_round_values):
            a, b, c, d, e, f, g, h = values
            # Sail semantics have the MSB --> LSB, our semantics go LSB --> MSB
            # let {a @ b @ e @ f} : bits(4*SEW) = get_velem(vs2, 4*SEW, i);
            vs2 = [f, e, b, a]
            # let {c @ d @ g @ h} : bits(4*SEW) = get_velem(vd, 4*SEW, i);
            vd = [h, g, d, c]

            # vsha2cl requires the relevant schedule words in the low two bits, and vsha2ch requires them
            # in the high bits. There is no other difference between the operations
            schedule_range = range(i, i + 4) if instr_name == "vsha2cl.vv" else range(i - 2, i + 2)
            vs1 = [(schedule[j] + k[j]) & (2**sew - 1) if j >= 0 else 0 for j in schedule_range]

            vd_val_ptr = f"custom_nist_sha_{i}_vd"
            vs2_val_ptr = f"custom_nist_sha_{i}_vs2"
            vs1_val_ptr = f"custom_nist_sha_{i}_vs1"

            test_data.register_vector_data(vd_val_ptr, sew, elements=vd)
            test_data.register_vector_data(vs2_val_ptr, sew, elements=vs2)
            test_data.register_vector_data(vs1_val_ptr, sew, elements=vs1)

            desc = f"NIST SHA Example: Test {i}"
            bin_name = f"b{i}"

            params = generate_random_vector_params(
                test_data,
                instr_name,
                instr_type,
                lmul=4,
                additional_no_overlap={("vd", "vs1"), ("vd", "vs2"), ("vs2", "vs1")},
                vd_val_pointer=vd_val_ptr,
                vs1_val_pointer=vs1_val_ptr,
                vs2_val_pointer=vs2_val_ptr,
            )

            tc = format_single_testcase(instr_name, instr_type, test_data, params, desc, bin_name, coverpoint)
            tc.code.insert(0, "\n".join(message))
            return_testcase_registers(test_data, params)

            test_chunks.append(tc)

        return test_chunks


##############
# NIST GCM
##############


def get_128_bits(field: str, num: int) -> int:
    mask_128 = (1 << 128) - 1
    return (int(field, 16) >> (num * 128)) & mask_128


@add_coverpoint_generator("cp_custom_nist_gcm")
def make_nist_gcm(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]:
    message = [
        "######################################################################################################",
        "# These tests include data from the NIST GCM standard, specifically the worked examples in Appendix B",
        "# They are worked examples from the standard that can be used to provide further edge values for these",
        "# tests as they are light on edges otherwise, and these examples have answers that have been derived",
        "# outside of any reference implementation of the algorithms, making them clear examples of the right",
        "# behavior.",
        "# Data From: https://csrc.nist.rip/groups/ST/toolkit/BCM/documents/proposedmodes/gcm/gcm-spec.pdf",
        "######################################################################################################",
    ]
    nist_test_vectors = Path(__file__).resolve().parent / "data" / "gcm_test_vectors_wide.csv"

    test_chunks: list[TestChunk] = []

    with nist_test_vectors.open("r") as file:
        reader = DictReader(row for row in file if not row.startswith("#"))
        present_labels = {}
        for i, row in enumerate(reader):
            data = extract_data(row)
            test_chunks.extend(make_tests(instr_name, instr_type, test_data, coverpoint, data, present_labels, i))

        for tc in test_chunks:
            tc.code.insert(0, "\n".join(message))

    return test_chunks


def extract_data(row: dict[str, str]) -> dict[str, int]:
    A = row["A"]
    C = row["C"]
    H = row["H"]
    data: dict[str, int] = {}

    c_padding = 32 - len(C) if len(C) <= 32 else 128 - len(C)
    C = C + "0" * c_padding

    if row["X1"] == "":
        pass
    elif len(C) == 32:
        data["X1"] = int(row["X1"], 16)
        data["C1"] = int(row["C"], 16)
    elif A == "":
        for i in range(1, 5):
            data[f"X{i}"] = int(row[f"X{i}"], 16)
            # This data is presented with the first 128 bits (MSB) being the first C value
            data[f"C{i}"] = get_128_bits(C, 4 - i)
    else:
        A_padding = 64 - len(A)
        A = A + "0" * A_padding
        # This data is presented with the first 128 bits (MSB) being the first A/C value
        for i in range(1, 3):
            data[f"A{i}"] = get_128_bits(A, 2 - i)
        for i in range(1, 5):
            data[f"C{i}"] = get_128_bits(C, 4 - i)
        for i in range(1, 7):
            data[f"X{i}"] = int(row[f"X{i}"], 16)

    data["H"] = int(H, 16)
    data["AorC"] = int(row["len(A)||len(C)"], 16)
    return data


def make_tests(
    instr_name: str,
    instr_type: str,
    test_data: TestData,
    coverpoint: str,
    data: dict[str, int],
    present_labels: dict[int, str],
    test_case: int,
) -> list[TestChunk]:
    x_idx = 0
    vd_val = vs1_val = 0
    vs2_val = data["H"]

    test_chunks: list[TestChunk] = []

    if "A1" in data:
        # GHASH(H, ACCUMULATOR, A1)
        vs1_val = data["A1"]
        test_chunks.append(
            emit(
                instr_name,
                instr_type,
                test_data,
                coverpoint,
                vd_val,
                vs1_val,
                vs2_val,
                present_labels,
                f"testcase_{test_case}_A1",
            )
        )
        x_idx += 1
        vd_val = data[f"X{x_idx}"]  # Update Accumulator With Expected Value for Next Test

        # GHASH(H, ACCUMULATOR, A2)
        vs1_val = data["A2"]
        test_chunks.append(
            emit(
                instr_name,
                instr_type,
                test_data,
                coverpoint,
                vd_val,
                vs1_val,
                vs2_val,
                present_labels,
                f"testcase_{test_case}_A2",
            )
        )
        x_idx += 1
        vd_val = data[f"X{x_idx}"]  # Update Accumulator With Expected Value for Next Test

    if "C1" in data:
        # GHASH(H, ACCUMULATOR, C1)
        vs1_val = data["C1"]
        test_chunks.append(
            emit(
                instr_name,
                instr_type,
                test_data,
                coverpoint,
                vd_val,
                vs1_val,
                vs2_val,
                present_labels,
                f"testcase_{test_case}_C1",
            )
        )
        x_idx += 1
        vd_val = data[f"X{x_idx}"]  # Update Accumulator With Expected Value for Next Test

    if "C4" in data:
        # Either we only have C1, or we have all of C1 --> C4

        # GHASH(H, ACCUMULATOR, C2)
        vs1_val = data["C2"]
        test_chunks.append(
            emit(
                instr_name,
                instr_type,
                test_data,
                coverpoint,
                vd_val,
                vs1_val,
                vs2_val,
                present_labels,
                f"testcase_{test_case}_C2",
            )
        )
        x_idx += 1
        vd_val = data[f"X{x_idx}"]  # Update Accumulator With Expected Value for Next Test

        # GHASH(H, ACCUMULATOR, C3)
        vs1_val = data["C3"]
        test_chunks.append(
            emit(
                instr_name,
                instr_type,
                test_data,
                coverpoint,
                vd_val,
                vs1_val,
                vs2_val,
                present_labels,
                f"testcase_{test_case}_C3",
            )
        )
        x_idx += 1
        vd_val = data[f"X{x_idx}"]  # Update Accumulator With Expected Value for Next Test

        # GHASH(H, ACCUMULATOR, C4)
        vs1_val = data["C4"]
        test_chunks.append(
            emit(
                instr_name,
                instr_type,
                test_data,
                coverpoint,
                vd_val,
                vs1_val,
                vs2_val,
                present_labels,
                f"testcase_{test_case}_C4",
            )
        )
        x_idx += 1
        vd_val = data[f"X{x_idx}"]  # Update Accumulator With Expected Value for Next Test

    # GHASH(H, ACCUMULATOR, AorC)
    vs1_val = data["AorC"]
    test_chunks.append(
        emit(
            instr_name,
            instr_type,
            test_data,
            coverpoint,
            vd_val,
            vs1_val,
            vs2_val,
            present_labels,
            f"testcase_{test_case}_AorC",
        )
    )

    return test_chunks


def emit(
    instr_name: str,
    instr_type: str,
    test_data: TestData,
    coverpoint: str,
    vd_val: int,
    vs1_val: int,
    vs2_val: int,
    present_labels: dict[int, str],
    desc: str,
) -> TestChunk:
    if instr_name == "vghsh.vv":
        vd_val_ptr = handle_label(vd_val, present_labels, test_data, f"{desc}_vd")
        vs1_val_ptr = handle_label(vs1_val, present_labels, test_data, f"{desc}_vs1")
    else:
        vd_val_ptr = handle_label(vd_val ^ vs1_val, present_labels, test_data, f"{desc}_vd")
        vs1_val_ptr = ""  # Make the type checker happy

    vs2_val_ptr = handle_label(vs2_val, present_labels, test_data, f"{desc}_vs2")

    pretty_desc = "NIST GCM Example " + desc.replace("_", " ")

    if instr_name == "vghsh.vv":
        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            lmul=4,
            additional_no_overlap={("vd", "vs1"), ("vs1", "vs2"), ("vs2", "vd")},
            vs2_val_pointer=vs2_val_ptr,
            vs1_val_pointer=vs1_val_ptr,
            vd_val_pointer=vd_val_ptr,
        )
    else:
        params = generate_random_vector_params(
            test_data,
            instr_name,
            instr_type,
            lmul=4,
            additional_no_overlap={("vd", "vs2")},
            vs2_val_pointer=vs2_val_ptr,
            vd_val_pointer=vd_val_ptr,
        )

    tc = format_single_testcase(instr_name, instr_type, test_data, params, pretty_desc, desc, coverpoint)
    return_testcase_registers(test_data, params)

    return tc


def handle_label(val: int, present_labels: dict[int, str], test_data: TestData, label: str) -> str:
    if val in present_labels:
        return present_labels[val]
    else:
        # The NIST data comes as (MSB --> LSB) a0a1..a127 representing a0+a1x+...+a127x^127
        # The RISC-V representation of this data places a byte containing a0...a7 in the lowest address
        # in the order (MSB --> LSB) a0 --> a7
        single_byte_values = [(val >> (8 * i)) & 0xFF for i in range(128 // 8)][::-1]

        test_data.register_vector_data(label, 8, elements=single_byte_values)
        present_labels[val] = label

        return label
