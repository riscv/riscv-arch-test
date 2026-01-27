#!/usr/bin/env python3
"""
Test script to verify FP register initialization implementation
"""

import sys
sys.path.insert(0, '/workspaces/riscv-arch-test')

from riscv_ctg.cross_comb import cross
from ordered_set import OrderedSet

def test_get_source_fp_regs():
    """Test extraction of source FP registers"""
    print("Testing get_source_fp_regs()...")
    
    # Mock instruction sequence with FP registers
    cross_comb_instrs = [
        {'instr': 'fadd.s', 'rd': 'f1', 'rs1': 'f2', 'rs2': 'f3'},
        {'instr': 'fmul.s', 'rd': 'f4', 'rs1': 'f1', 'rs2': 'f5'},
        {'instr': 'add', 'rd': 'x1', 'rs1': 'x2', 'rs2': 'x3'},  # GP register
    ]
    
    source_fp_regs = cross.get_source_fp_regs(cross_comb_instrs)
    expected = OrderedSet(['f2', 'f3', 'f1', 'f5'])
    
    assert source_fp_regs == expected, f"Expected {expected}, got {source_fp_regs}"
    print("✓ get_source_fp_regs() works correctly")
    print(f"  Found source FP registers: {list(source_fp_regs)}")

def test_get_fp_init_str():
    """Test generation of FP register initialization code"""
    print("\nTesting get_fp_init_str()...")
    
    cross_comb_instrs = [
        {'instr': 'fadd.s', 'rd': 'f1', 'rs1': 'f2', 'rs2': 'f3'},
        {'instr': 'fmul.s', 'rd': 'f4', 'rs1': 'f1', 'rs2': 'f5'},
    ]
    
    freg = 'x10'  # Temporary register
    fp_init_strs = cross.get_fp_init_str(cross_comb_instrs, freg)
    
    assert len(fp_init_strs) > 0, "Expected non-empty initialization strings"
    assert any('LI' in s for s in fp_init_strs), "Expected LI instruction in initialization"
    assert any('FLREG' in s for s in fp_init_strs), "Expected FLREG instruction in initialization"
    
    print("✓ get_fp_init_str() works correctly")
    print(f"  Generated {len(fp_init_strs)} initialization statements:")
    for i, init_str in enumerate(fp_init_strs):
        print(f"    {i+1}. {init_str[:60]}{'...' if len(init_str) > 60 else ''}")

def test_no_fp_regs():
    """Test with GP-only instructions"""
    print("\nTesting with GP-only instructions...")
    
    cross_comb_instrs = [
        {'instr': 'add', 'rd': 'x1', 'rs1': 'x2', 'rs2': 'x3'},
        {'instr': 'sub', 'rd': 'x4', 'rs1': 'x1', 'rs2': 'x5'},
    ]
    
    source_fp_regs = cross.get_source_fp_regs(cross_comb_instrs)
    assert len(source_fp_regs) == 0, "Expected no FP registers in GP-only sequence"
    
    freg = 'x10'
    fp_init_strs = cross.get_fp_init_str(cross_comb_instrs, freg)
    assert len(fp_init_strs) == 0, "Expected no initialization for GP-only sequence"
    
    print("✓ Correctly handles GP-only instructions (no FP initialization)")

if __name__ == '__main__':
    print("=" * 70)
    print("FP Register Initialization Tests")
    print("=" * 70)
    
    try:
        test_get_source_fp_regs()
        test_get_fp_init_str()
        test_no_fp_regs()
        
        print("\n" + "=" * 70)
        print("✓ All tests passed!")
        print("=" * 70)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
