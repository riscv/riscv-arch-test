# SPDX-License-Identifier: Apache-2.0

from coverpoint_registry import register
import vector_testgen_common as common

MESSAGE_SCHEDULE_256 = [
    0x61626364, 0x62636465, 0x63646566, 0x64656667, 0x65666768, 0x66676869, 0x6768696A, 0x68696A6B,
    0x696A6B6C, 0x6A6B6C6D, 0x6B6C6D6E, 0x6C6D6E6F, 0x6D6E6F70, 0x6E6F7071, 0x80000000, 0x00000000,
]

K_256 = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]

MESSAGE_SCHEDULE_512 = [
    0x6162636465666768, 0x6263646566676869, 0x636465666768696A, 0x6465666768696A6B, 0x65666768696A6B6C, 0x666768696A6B6C6D, 0x6768696A6B6C6D6E, 0x68696A6B6C6D6E6F,
    0x696A6B6C6D6E6F70, 0x6A6B6C6D6E6F7071, 0x6B6C6D6E6F707172, 0x6C6D6E6F70717273, 0x6D6E6F7071727374, 0x6E6F707172737475, 0x8000000000000000, 0x0000000000000000,
]

K_512 = [
    0x428a2f98d728ae22, 0x7137449123ef65cd, 0xb5c0fbcfec4d3b2f, 0xe9b5dba58189dbbc,
    0x3956c25bf348b538, 0x59f111f1b605d019, 0x923f82a4af194f9b, 0xab1c5ed5da6d8118,
    0xd807aa98a3030242, 0x12835b0145706fbe, 0x243185be4ee4b28c, 0x550c7dc3d5ffb4e2,
    0x72be5d74f27b896f, 0x80deb1fe3b1696b1, 0x9bdc06a725c71235, 0xc19bf174cf692694,
    0xe49b69c19ef14ad2, 0xefbe4786384f25e3, 0x0fc19dc68b8cd5b5, 0x240ca1cc77ac9c65,
    0x2de92c6f592b0275, 0x4a7484aa6ea6e483, 0x5cb0a9dcbd41fbd4, 0x76f988da831153b5,
    0x983e5152ee66dfab, 0xa831c66d2db43210, 0xb00327c898fb213f, 0xbf597fc7beef0ee4,
    0xc6e00bf33da88fc2, 0xd5a79147930aa725, 0x06ca6351e003826f, 0x142929670a0e6e70,
    0x27b70a8546d22ffc, 0x2e1b21385c26c926, 0x4d2c6dfc5ac42aed, 0x53380d139d95b3df,
    0x650a73548baf63de, 0x766a0abb3c77b2a8, 0x81c2c92e47edaee6, 0x92722c851482353b,
    0xa2bfe8a14cf10364, 0xa81a664bbc423001, 0xc24b8b70d0f89791, 0xc76c51a30654be30,
    0xd192e819d6ef5218, 0xd69906245565a910, 0xf40e35855771202a, 0x106aa07032bbd1b8,
    0x19a4c116b8d2d0c8, 0x1e376c085141ab53, 0x2748774cdf8eeb99, 0x34b0bcb5e19b48a8,
    0x391c0cb3c5c95a63, 0x4ed8aa4ae3418acb, 0x5b9cca4f7763e373, 0x682e6ff3d6b2b8a3,
    0x748f82ee5defb2fc, 0x78a5636f43172f60, 0x84c87814a1f0ab72, 0x8cc702081a6439ec,
    0x90befffa23631e28, 0xa4506cebde82bde9, 0xbef9a3f7b2c67915, 0xc67178f2e372532b,
    0xca273eceea26619c, 0xd186b8c721c0c207, 0xeada7dd6cde0eb1e, 0xf57d4f7fee6ed178,
    0x06f067aa72176fba, 0x0a637dc5a2c898a6, 0x113f9804bef90dae, 0x1b710b35131c471b,
    0x28db77f523047d84, 0x32caab7b40c72493, 0x3c9ebe0a15c9bebc, 0x431d67c49c100d4c,
    0x4cc5d4becb3e42b6, 0x597f299cfc657e2a, 0x5fcb6fab3ad6faec, 0x6c44198c4a475817,
]

HASH_ROUND_VALUES_256 = [
    [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19],
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
    [0x6A09E667F3BCC908, 0xBB67AE8584CAA73B, 0x3C6EF372FE94F82B, 0xA54FF53A5F1D36F1, 0x510E527FADE682D1, 0x9B05688C2B3E6C1F, 0x1F83D9ABFB41BD6B, 0x5BE0CD19137E2179],
    [0xF6AFCE9D2263455D, 0x6A09E667F3BCC908, 0xBB67AE8584CAA73B, 0x3C6EF372FE94F82B, 0x58CB0218E01B86F9, 0x510E527FADE682D1, 0x9B05688C2B3E6C1F, 0x1F83D9ABFB41BD6B],
    [0x0B7056A534AE5F62, 0xF6AFCE9D2263455D, 0x6A09E667F3BCC908, 0xBB67AE8584CAA73B, 0xF8C7198FE39E4C8C, 0x58CB0218E01B86F9, 0x510E527FADE682D1, 0x9B05688C2B3E6C1F],
    [0x2CA82233760C9942, 0x0B7056A534AE5F62, 0xF6AFCE9D2263455D, 0x6A09E667F3BCC908, 0x303ECCCCD65953DE, 0xF8C7198FE39E4C8C, 0x58CB0218E01B86F9, 0x510E527FADE682D1],
    [0xA023F17CE52CDA7B, 0x2CA82233760C9942, 0x0B7056A534AE5F62, 0xF6AFCE9D2263455D, 0xFFDEE5EEDCC9CA42, 0x303ECCCCD65953DE, 0xF8C7198FE39E4C8C, 0x58CB0218E01B86F9],
    [0x8F0A67D9D591A1A7, 0xA023F17CE52CDA7B, 0x2CA82233760C9942, 0x0B7056A534AE5F62, 0xCB4CFBB166505F2F, 0xFFDEE5EEDCC9CA42, 0x303ECCCCD65953DE, 0xF8C7198FE39E4C8C],
    [0xB466267371ACC493, 0x8F0A67D9D591A1A7, 0xA023F17CE52CDA7B, 0x2CA82233760C9942, 0x73D6C84C54D399EE, 0xCB4CFBB166505F2F, 0xFFDEE5EEDCC9CA42, 0x303ECCCCD65953DE],
    [0x658269F1A312FCCD, 0xB466267371ACC493, 0x8F0A67D9D591A1A7, 0xA023F17CE52CDA7B, 0xCDC40314975FB275, 0x73D6C84C54D399EE, 0xCB4CFBB166505F2F, 0xFFDEE5EEDCC9CA42],
    [0x65E3519C5B88181B, 0x658269F1A312FCCD, 0xB466267371ACC493, 0x8F0A67D9D591A1A7, 0xA657850AB3970C5A, 0xCDC40314975FB275, 0x73D6C84C54D399EE, 0xCB4CFBB166505F2F],
    [0x56604FBB4B6393EC, 0x65E3519C5B88181B, 0x658269F1A312FCCD, 0xB466267371ACC493, 0xE8B3BE22FBE64DF7, 0xA657850AB3970C5A, 0xCDC40314975FB275, 0x73D6C84C54D399EE],
    [0xC4562769A37D02C0, 0x56604FBB4B6393EC, 0x65E3519C5B88181B, 0x658269F1A312FCCD, 0x0062E70A1EF705C1, 0xE8B3BE22FBE64DF7, 0xA657850AB3970C5A, 0xCDC40314975FB275],
    [0x27C0B4C9186E1736, 0xC4562769A37D02C0, 0x56604FBB4B6393EC, 0x65E3519C5B88181B, 0xBC9740477A18AE2D, 0x0062E70A1EF705C1, 0xE8B3BE22FBE64DF7, 0xA657850AB3970C5A],
    [0xF17F52FB02F4EB74, 0x27C0B4C9186E1736, 0xC4562769A37D02C0, 0x56604FBB4B6393EC, 0xBE58522CB9590EE1, 0xBC9740477A18AE2D, 0x0062E70A1EF705C1, 0xE8B3BE22FBE64DF7],
]

@register("cp_custom_nist_sha")
def make(test: str, sew: int):
    common.writeLine("######################################################################################################")
    common.writeLine("# These tests include data from the SHA examples given by NIST. They use the data from the message")
    common.writeLine("# schedule blocks given in the second example, first block. This was chosen because of the examples")
    common.writeLine("# it has the most non-zero entries in the message schedule which hopefully makes it more interesting.")
    common.writeLine("# No more information than is given in these files is used for testing. The intermediate hash values")
    common.writeLine("# are taken from the lines numbered t=1..11, and the first hash values are the standard first values")
    common.writeLine("# for their respective hashes (with 16 schedule values given, this is the maximum we can reach).")
    common.writeLine("# Data Taken From: https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Standards-and-Guidelines/documents/examples/SHA256.pdf")
    common.writeLine("# and https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Standards-and-Guidelines/documents/examples/SHA512.pdf")
    common.writeLine("######################################################################################################")

    schedule = MESSAGE_SCHEDULE_256 if sew == 32 else MESSAGE_SCHEDULE_512
    hash_round_values = HASH_ROUND_VALUES_256 if sew == 32 else HASH_ROUND_VALUES_512
    k = K_256 if sew == 32 else K_512

    if test == "vsha2ms":
        vd = schedule[0:4]
        vs2 = [schedule[4], schedule[9], schedule[10], schedule[11]]
        vs1 = schedule[12:16]

        vd_val_ptr = "custom_nist_sha_vd"
        vs2_val_ptr = "custom_nist_sha_vs2"
        vs1_val_ptr = "custom_nist_sha_vs1"

        common.registerCustomData(vd_val_ptr, vd, sew)
        common.registerCustomData(vs2_val_ptr, vs2, sew)
        common.registerCustomData(vs1_val_ptr, vs1, sew)

        description = f"NIST SHA Example Message Schedule"
        cp = f"cp_custom_nist_sha"

        instruction_data = common.randomizeVectorInstructionData(test, sew, common.getBaseSuiteTestCount(), lmul=4, additional_no_overlap=[['vd', 'vs1', 'vs2']], vd_val_ptr=vd_val_ptr, vs1_val_ptr=vs1_val_ptr, vs2_val_ptr=vs2_val_ptr)

        common.writeTest(description, test, cp, instruction_data, sew, lmul=4, vl=4, egs=4, )
    else:
        for i, values in enumerate(hash_round_values):
            a, b, c, d, e, f, g, h = values
            vd = [c, d, g, h]
            vs2 = [a, b, e, f]
            vs1 = [schedule[j] + k[j] for j in range(i, i+4)]

            vd_val_ptr = f"custom_nist_sha_{i}_vd"
            vs2_val_ptr = f"custom_nist_sha_{i}_vs2"
            vs1_val_ptr = f"custom_nist_sha_{i}_vs1"

            common.registerCustomData(vd_val_ptr, vd, sew)
            common.registerCustomData(vs2_val_ptr, vs2, sew)
            common.registerCustomData(vs1_val_ptr, vs1, sew)

            description = f"NIST SHA Example: Test {i}"
            cp = f"cp_custom_nist_sha_{i}"

            instruction_data = common.randomizeVectorInstructionData(test, sew, common.getBaseSuiteTestCount(), lmul=4, additional_no_overlap=[['vd', 'vs1', 'vs2']], vd_val_ptr=vd_val_ptr, vs1_val_ptr=vs1_val_ptr, vs2_val_ptr=vs2_val_ptr)

            common.writeTest(description, test, cp, instruction_data, sew, lmul=4, vl=4, egs=4, )
            common.incrementBasetestCount()
