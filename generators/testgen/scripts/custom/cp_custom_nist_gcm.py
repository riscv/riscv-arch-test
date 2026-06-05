# SPDX-License-Identifier: Apache-2.0

from coverpoint_registry import register
from pathlib import Path
from csv import DictReader
import vector_testgen_common as common

nist_count = 0

def get_128_bits(field: str, num: int) -> int:
    mask_128 = (1 << 128) - 1
    return (int(field, 16) >> (num * 128)) & mask_128

@register("cp_custom_nist_gcm")
def make(test: str, _sew: int):
    common.writeLine("######################################################################################################")
    common.writeLine("# These tests include data from the NIST GCM standard, specifically the worked examples in Appendix B")
    common.writeLine("# They are worked examples from the standard that can be used to provide further edge values for these")
    common.writeLine("# tests as they are light on edges otherwise, and these examples have answers that have been derived")
    common.writeLine("# outside of any reference implementation of the algorithms, making them clear examples of the right")
    common.writeLine("# behavior.")
    common.writeLine("# Data From: https://csrc.nist.rip/groups/ST/toolkit/BCM/documents/proposedmodes/gcm/gcm-spec.pdf")
    common.writeLine("######################################################################################################")
    nist_test_vectors = Path(__file__).resolve().parent / 'data' / 'gcm_test_vectors_wide.csv'

    with nist_test_vectors.open('r') as file:
        reader = DictReader(row for row in file if not row.startswith('#'))
        present_labels = {0: 'vs_corner_zero_emul4'}
        for i, row in enumerate(reader):
            data = extract_data(row)
            make_tests(test, data, present_labels, i)

def extract_data(row: dict[str, str]) -> dict[str, int]:
    A = row['A']
    C = row['C']
    H = row['H']
    data: dict[str, int] = {}

    c_padding = 32 - len(C) if len(C) <= 32 else 128 - len(C)
    C = C + '0' * c_padding


    if row['X1'] == '':
        pass
    elif len(C) == 32:
        data['X1'] = int(row['X1'], 16)
        data['C1'] = int(row['C'], 16)
    elif A == "":
        for i in range(1, 5):
            data[f'X{i}'] = int(row[f'X{i}'], 16)
            data[f'C{i}'] = get_128_bits(row['C'], i-1)
    else:
        A_padding = 64 - len(A)
        A = A + '0' * A_padding
        for i in range(1, 3):
            data[f'A{i}'] = get_128_bits(A, i-1)
        for i in range(1, 5):
            data[f'C{i}'] = get_128_bits(row['C'], i-1)
        for i in range(1, 7):
            data[f'X{i}'] = int(row[f'X{i}'], 16)

    data['H'] = int(H, 16)
    data['AorC'] = int(row['len(A)||len(C)'], 16)
    return data

def make_tests(test: str, data: dict[str, int], present_labels: dict[int, str], test_case: int) -> None:
    x_idx = 0
    vd_val = vs1_val = 0
    vs2_val = data['H']

    if 'A1' in data:
        # GHASH(H, ACCUMULATOR, A1)
        vs1_val = data['A1']
        emit(test, vd_val, vs1_val, vs2_val, present_labels, f'testcase_{test_case}_A1')
        x_idx += 1
        vd_val = data[f'X{x_idx}'] # Update Accumulator With Expected Value for Next Test

        # GHASH(H, ACCUMULATOR, A2)
        vs1_val = data['A2']
        emit(test, vd_val, vs1_val, vs2_val, present_labels, f'testcase_{test_case}_A2')
        x_idx += 1
        vd_val = data[f'X{x_idx}'] # Update Accumulator With Expected Value for Next Test

    if 'C1' in data:
        # GHASH(H, ACCUMULATOR, C1)
        vs1_val = data['C1']
        emit(test, vd_val, vs1_val, vs2_val, present_labels, f'testcase_{test_case}_C1')
        x_idx += 1
        vd_val = data[f'X{x_idx}'] # Update Accumulator With Expected Value for Next Test

    if 'C4' in data:
        # Either we only have C1, or we have all of C1 --> C4

        # GHASH(H, ACCUMULATOR, C2)
        vs1_val = data['C2']
        emit(test, vd_val, vs1_val, vs2_val, present_labels, f'testcase_{test_case}_C2')
        x_idx += 1
        vd_val = data[f'X{x_idx}'] # Update Accumulator With Expected Value for Next Test

        # GHASH(H, ACCUMULATOR, C3)
        vs1_val = data['C3']
        emit(test, vd_val, vs1_val, vs2_val, present_labels, f'testcase_{test_case}_C3')
        x_idx += 1
        vd_val = data[f'X{x_idx}'] # Update Accumulator With Expected Value for Next Test

        # GHASH(H, ACCUMULATOR, C4)
        vs1_val = data['C4']
        emit(test, vd_val, vs1_val, vs2_val, present_labels, f'testcase_{test_case}_C4')
        x_idx += 1
        vd_val = data[f'X{x_idx}'] # Update Accumulator With Expected Value for Next Test

    # GHASH(H, ACCUMULATOR, AorC)
    vs1_val = data['AorC']
    emit(test, vd_val, vs1_val, vs2_val, present_labels, f'testcase_{test_case}_AorC')

def emit(test: str, vd_val: int, vs1_val: int, vs2_val: int, present_labels: dict[int, str], description: str) -> None:
    if test == 'vghsh.vv':
        vd_val_ptr = handle_label(vd_val, present_labels)
        vs1_val_ptr = handle_label(vs1_val, present_labels)
    else:
        vd_val_ptr = handle_label(vd_val ^ vs1_val, present_labels)

    vs2_val_ptr = handle_label(vs2_val, present_labels)

    cp = f'cp_custom_nist_gcm_{description}'
    cp_description = f'NIST GCM Example ' + description.replace('_', ' ')

    if test == 'vghsh.vv':
        instruction_data = common.randomizeVectorInstructionData(test, 32, common.getBaseSuiteTestCount(), lmul=4, additional_no_overlap=[['vd', 'vs1', 'vs2']], vs2_val_ptr=vs2_val_ptr, vs1_val_ptr=vs1_val_ptr, vd_val_ptr=vd_val_ptr)
    else:
        instruction_data = common.randomizeVectorInstructionData(test, 32, common.getBaseSuiteTestCount(), lmul=4, additional_no_overlap=[['vd', 'vs2']], vs2_val_ptr=vs2_val_ptr, vd_val_ptr=vd_val_ptr)

    common.writeTest(cp_description, test, cp, instruction_data, sew=32, lmul=4, vl=4, egs=4)
    common.incrementBasetestCount()

def handle_label(val: int, present_labels: dict[int, str]) -> str:
    global nist_count

    if val in present_labels:
        return present_labels[val]
    else:
        nist_count += 1
        ptr = f'nist_case_constant_{nist_count}'

        mask = (1 << 32) - 1
        values = [(val >> (32 * i)) & mask for i in range(4)]

        common.registerCustomData(ptr, values, 32)
        present_labels[val] = ptr

        return ptr
