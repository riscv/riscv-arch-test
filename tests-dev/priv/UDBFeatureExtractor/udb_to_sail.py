#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 RISC-V International
#
# Convert a UDB configuration into a Sail RISC-V (0.16) configuration file.
#
# Written by David Harris with assistance from Claude.
#
#   udb_to_sail.py <udb.yaml> -o sail.json [--config-dir DIR] [--sail-extra extra.json] [--compare old.json]
#
# The output starts from Sail's own default configuration for the XLEN (sail_riscv_sim
# --print-default-config) and sets every key that a UDB parameter or extension determines.  The
# memory map comes from the configuration directory's link.ld (main memory) and rvmodel_macros.h
# (CLINT location and the access-fault address, which must stay unmapped).  Keys that UDB does not
# describe can be supplied with --sail-extra, a JSON object of dotted keys such as
# {"base.writable_fiom": true} (the feature extractor prints these as "# sail:" lines).  Keys left
# at Sail's default, and UDB values Sail cannot express, are listed at the top of the output.

from __future__ import annotations

import argparse
import copy
import json
import math
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pyjson5
from ruamel.yaml import YAML

SAIL_SCHEMA = "https://github.com/riscv/sail-riscv/releases/download/0.16/sail_riscv_config_schema.json"

# UDB extensions that Sail names differently
SAIL_EXT_PATH = {"Smstateen": "Stateen.Smstateen", "Ssstateen": "Stateen.Ssstateen"}

# Sail stateen bits, the UDB parameter that describes each (if any), and how to derive the bit
# from the extension list when neither UDB nor the extractor gives it
STATEEN_TYPE = {"rw": "CSRBit_Writable", "read-only-0": "CSRBit_ReadOnlyZero", "read-only-1": "CSRBit_ReadOnlyOne"}
STATEEN_UDB = {
    "mstateen0.ENVCFG": "MSTATEEN_ENVCFG_TYPE",
    "mstateen0.CONTEXT": "MSTATEEN_CONTEXT_TYPE",
    "hstateen0.ENVCFG": "HSTATEEN_ENVCFG_TYPE",
    "hstateen0.CONTEXT": "HSTATEEN_CONTEXT_TYPE",
}

XTVAL = {
    # Sail xtval_nonzero key: UDB parameters (M-mode first; all must agree for Sail to model them)
    "illegal_instruction": [
        "REPORT_ENCODING_IN_MTVAL_ON_ILLEGAL_INSTRUCTION",
        "REPORT_ENCODING_IN_STVAL_ON_ILLEGAL_INSTRUCTION",
        "REPORT_ENCODING_IN_VSTVAL_ON_ILLEGAL_INSTRUCTION",
    ],
    "virtual_instruction": ["REPORT_ENCODING_IN_VSTVAL_ON_VIRTUAL_INSTRUCTION"],
    "software_breakpoint": [f"REPORT_VA_IN_{m}TVAL_ON_BREAKPOINT" for m in ("M", "S", "VS")],
    "load_address_misaligned": [f"REPORT_VA_IN_{m}TVAL_ON_LOAD_MISALIGNED" for m in ("M", "S", "VS")],
    "load_access_fault": [f"REPORT_VA_IN_{m}TVAL_ON_LOAD_ACCESS_FAULT" for m in ("M", "S", "VS")],
    "load_page_fault": [f"REPORT_VA_IN_{m}TVAL_ON_LOAD_PAGE_FAULT" for m in ("M", "S", "VS")],
    "samo_address_misaligned": [f"REPORT_VA_IN_{m}TVAL_ON_STORE_AMO_MISALIGNED" for m in ("M", "S", "VS")],
    "samo_access_fault": [f"REPORT_VA_IN_{m}TVAL_ON_STORE_AMO_ACCESS_FAULT" for m in ("M", "S", "VS")],
    "samo_page_fault": [f"REPORT_VA_IN_{m}TVAL_ON_STORE_AMO_PAGE_FAULT" for m in ("M", "S", "VS")],
    "fetch_address_misaligned": [f"REPORT_VA_IN_{m}TVAL_ON_INSTRUCTION_MISALIGNED" for m in ("M", "S", "VS")],
    "fetch_access_fault": [f"REPORT_VA_IN_{m}TVAL_ON_INSTRUCTION_ACCESS_FAULT" for m in ("M", "S", "VS")],
    "fetch_page_fault": [f"REPORT_VA_IN_{m}TVAL_ON_INSTRUCTION_PAGE_FAULT" for m in ("M", "S", "VS")],
    "software_check": [
        f"REPORT_CAUSE_IN_{m}TVAL_ON_{k}_SOFTWARE_CHECK"
        for k in ("LANDING_PAD", "SHADOW_STACK")
        for m in ("M", "S", "VS")
    ],
}

TINST = {
    "load_address_misaligned": "TINST_VALUE_ON_LOAD_ADDRESS_MISALIGNED",
    "load_access_fault": "TINST_VALUE_ON_LOAD_ACCESS_FAULT",
    "load_page_fault": "TINST_VALUE_ON_LOAD_PAGE_FAULT",
    "load_guest_page_fault": "TINST_VALUE_ON_FINAL_LOAD_GUEST_PAGE_FAULT",
    "samo_address_misaligned": "TINST_VALUE_ON_STORE_AMO_ADDRESS_MISALIGNED",
    "samo_access_fault": "TINST_VALUE_ON_STORE_AMO_ACCESS_FAULT",
    "samo_page_fault": "TINST_VALUE_ON_STORE_AMO_PAGE_FAULT",
    "samo_guest_page_fault": "TINST_VALUE_ON_FINAL_STORE_AMO_GUEST_PAGE_FAULT",
}

CLINT_SIZE = 0xC000
IO_SIZE = 0x20000  # CLINT, then the simple interrupt generator 64 KiB above it
PAGE = 0x1000


def log2(v: int) -> int:
    return int(math.log2(v))


def mask(bits: list[bool] | None) -> int:
    return sum(1 << i for i, b in enumerate(bits or []) if b)


def sail_default(sim: str, xlen: int) -> dict[str, Any]:
    cmd = [sim, "--print-default-config"] + (["--rv32"] if xlen == 32 else [])
    return pyjson5.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)


def leaves(d: object, prefix: str = "") -> dict[str, Any]:
    """Dotted leaf keys of a Sail configuration; {len, value} bitvectors and option types are leaves."""
    if isinstance(d, dict) and d and not ({"len", "value"} >= set(d) or set(d) <= {"None", "Some"}):
        out: dict[str, Any] = {}
        for k, v in d.items():
            out.update(leaves(v, f"{prefix}.{k}" if prefix else k))
        return out
    return {prefix: d}


class ReadLog(dict):
    """A dict of UDB parameters that remembers which ones were looked at."""

    def __init__(self, data: dict[str, Any], log: set[str]) -> None:
        super().__init__(data)
        self.log = log

    def __getitem__(self, k: str) -> Any:  # noqa: ANN401
        self.log.add(k)
        return super().__getitem__(k)

    def get(self, k: str, default: Any = None) -> Any:  # noqa: ANN401
        self.log.add(k)
        return super().get(k, default)

    def __contains__(self, k: object) -> bool:
        self.log.add(str(k))
        return super().__contains__(k)


class Converter:
    def __init__(self, udb: dict[str, Any], default: dict[str, Any], extra: dict[str, Any]) -> None:
        # The parameters and extensions read since the last set() are recorded as that key's sources
        self.reads: set[str] = set()
        self.sources: dict[str, set[str]] = {}
        self.p: dict[str, Any] = ReadLog(udb.get("params") or {}, self.reads)
        self.exts: set[str] = {e["name"] if isinstance(e, dict) else str(e) for e in udb["implemented_extensions"]}
        self.ext_versions = {
            e["name"]: str(e.get("version", "")) for e in udb["implemented_extensions"] if isinstance(e, dict)
        }
        self.xlen = int(self.p.get("MXLEN", 64))
        self.cfg = copy.deepcopy(default)
        self.extra = extra
        self.set_keys: set[str] = set()
        self.unmodelled: list[str] = []  # UDB values Sail cannot express

    # -- helpers ------------------------------------------------------------------------------
    def has(self, *names: str) -> bool:
        self.reads.update(f"ext:{n}" for n in names)
        return any(n in self.exts for n in names)

    def set(self, key: str, value: object) -> None:
        node = self.cfg
        parts = key.split(".")
        for k in parts[:-1]:
            node = node[k]
        old = node.get(parts[-1])
        if isinstance(old, dict) and "value" in old and isinstance(value, int) and not isinstance(value, bool):
            value = {"len": old["len"], "value": f"0x{value:X}"}
        node[parts[-1]] = value
        self.set_keys.add(key)
        self.sources[key] = set(self.reads)
        self.reads.clear()

    def set_param(self, key: str, param: str, fn: Callable[[Any], object] | None = None) -> bool:
        if param not in self.p:
            return False
        self.set(key, fn(self.p[param]) if fn else self.p[param])
        return True

    def agree(self, key: str, params: list[str]) -> None:
        values = {p: self.p[p] for p in params if p in self.p}
        if not values:
            return
        first = next(iter(values.values()))
        self.set(key, bool(first))
        if any(v != first for v in values.values()):
            self.unmodelled.append(f"{key}: Sail has one setting but UDB has {values}")

    def interrupts(self) -> int:
        """The interrupt codes this hart can have, as a mask."""
        irq = 0x888 | (0x222 if self.has("S") else 0) | (0x1444 if self.has("H") else 0)
        return irq | (1 << 13 if self.has("Sscofpmf") else 0)

    def exceptions(self) -> int:
        """The exception codes this hart can raise, as a mask (Sail rejects reserved ones)."""
        exc = 0x00FDBFFF
        if not self.has("H"):
            exc &= ~((1 << 10) | (0xF << 20))
        return exc

    # -- sections -----------------------------------------------------------------------------
    def base(self) -> None:
        p = self.p
        sm = self.ext_versions.get("Sm", "")
        m = re.search(r"1\.(1[123])", sm)
        if m:
            self.set("base.privileged_isa_version", f"Privileged_ISA_1_{m.group(1)}")
        self.set("base.xlen", self.xlen)
        self.set("base.E", self.has("E") and not self.has("I"))
        hpm_en = p.get("HPM_COUNTER_EN") if self.has("Zihpm") else None
        self.set("base.writable_hpm_counters", mask(hpm_en) & ~7)
        widths = {
            p[f"HPM_COUNTER{i}_WIDTH"] for i in range(3, 32) if hpm_en and hpm_en[i] and f"HPM_COUNTER{i}_WIDTH" in p
        }
        if widths:
            self.set("base.hpmcounter_width_bits", max(widths))
            if len(widths) > 1:
                self.unmodelled.append(f"base.hpmcounter_width_bits: Sail has one width but UDB has {sorted(widths)}")
        for csr, param in (
            ("scounteren", "SCOUNTENABLE_EN"),
            ("mcounteren", "MCOUNTENABLE_EN"),
            ("hcounteren", "HCOUNTENABLE_EN"),
        ):
            self.set(f"base.{csr}_writable_bits", mask(p.get(param)))
        if "MCOUNTINHIBIT_IMPLEMENTED" in p:
            self.set("base.mcountinhibit.supported", bool(p["MCOUNTINHIBIT_IMPLEMENTED"]))
            self.set("base.mcountinhibit.writable_bits", mask(p.get("COUNTINHIBIT_EN")) & ~2)
        for tvec, modes, aligns in (
            (
                "mtvec",
                "MTVEC_MODES",
                {"direct": "MTVEC_BASE_ALIGNMENT_DIRECT", "vectored": "MTVEC_BASE_ALIGNMENT_VECTORED"},
            ),
            ("stvec", "STVEC_MODES", {"vectored": "STVEC_BASE_ALIGNMENT_VECTORED"}),
            ("vstvec", "VSTVEC_MODES", {}),
        ):
            if modes in p:
                self.set(f"base.{tvec}.direct.supported", 0 in p[modes])
                self.set(f"base.{tvec}.vectored.supported", 1 in p[modes])
            for mode, param in aligns.items():
                self.set_param(f"base.{tvec}.{mode}.base_alignment", param, log2)
        behavior = p.get("MTVEC_ILLEGAL_WRITE_BEHAVIOR")
        if behavior == "retain":
            self.set("base.reserved_behavior.xtvec_mode", "Xtvec_Ignore")
        elif behavior is not None:
            self.unmodelled.append(f"base.reserved_behavior.xtvec_mode: MTVEC_ILLEGAL_WRITE_BEHAVIOR = {behavior}")
        medeleg = mask(p.get("MEDELEG_DELEGATABLE"))
        if medeleg & ~self.exceptions():
            self.unmodelled.append(
                f"base.medeleg.delegatable_bits: Sail rejects reserved bits 0x{medeleg & ~self.exceptions():X}"
            )
            medeleg &= self.exceptions()
        if self.cfg["base"]["privileged_isa_version"] != "Privileged_ISA_1_13":
            # software check (18) and hardware error (19) are reserved before 1.13
            keep = 1 << 18 if self.has("Zicfilp", "Zicfiss") else 0
            if medeleg & ~keep & (3 << 18):
                self.unmodelled.append("base.medeleg.delegatable_bits: bits 18/19 need privileged ISA 1.13")
            medeleg &= ~(3 << 18) | keep
        self.set("base.medeleg.delegatable_bits", medeleg)
        # mideleg bits 2, 6, 10 and 12 are read-only one with H, so Sail does not count them as delegatable
        self.set("base.mideleg.delegatable_bits", mask(p.get("MIDELEG_DELEGATABLE")) & self.interrupts() & 0x2222)
        if self.xlen == 32 and not self.has("Sscofpmf"):
            self.set("base.hpmevent_width_bits", 32)
        for key, params in XTVAL.items():
            self.agree(f"base.xtval_nonzero.{key}", params)
        for field, param in (("fs", "MSTATUS_FS_LEGAL_VALUES"), ("vs", "MSTATUS_VS_LEGAL_VALUES")):
            legal = sorted(p.get(param, [0]))
            states = {(0, 1, 2, 3): "ExtContext_FourState", (0, 3): "ExtContext_TwoState", (0,): "ExtContext_Off"}
            if tuple(legal) in states:
                self.set(f"base.mstatus.{field}_legal_states", states[tuple(legal)])
            else:
                self.unmodelled.append(f"base.mstatus.{field}_legal_states: UDB {param} = {legal}")

    def memory(self) -> None:
        p = self.p
        self.set_param("memory.physaddr_bits", "PHYS_ADDR_WIDTH")
        self.set("memory.asidlen", p.get("ASID_WIDTH", 0) if self.has("S") else 0)
        self.set("memory.vmidlen", p.get("VMID_WIDTH", 0) if self.has("H") else 0)
        n = p.get("NUM_PMP_ENTRIES", 0)
        count = 0 if n == 0 else 16 if n <= 16 else 64
        self.set("memory.pmp.count", count)
        if count > 16 and self.cfg["base"]["privileged_isa_version"] == "Privileged_ISA_1_11":
            self.set("base.privileged_isa_version", "Privileged_ISA_1_12")
            self.unmodelled.append(
                "base.privileged_isa_version: Sail allows more than 16 PMP entries only from 1.12, so 1.12 is used"
            )
        self.set("memory.pmp.usable_count", p.get("NUM_USABLE_PMP_ENTRIES", n))
        if n:
            self.set_param("memory.pmp.grain", "PMP_GRANULARITY", lambda g: g - 2)
            for mode in ("TOR", "NA4", "NAPOT"):
                self.set_param(f"memory.pmp.{mode.lower()}_supported", f"PMP_{mode}_SUPPORTED")
        ok: dict[str, None] = {"None": None}
        align = {"Some": "AlignmentException"}
        if "MISALIGNED_LDST" in p:
            self.set("memory.misaligned.exceptions.load_store", ok if p["MISALIGNED_LDST"] else align)
        if "VECTOR_LS_MISALIGNED_LEGAL" in p:
            self.set("memory.misaligned.exceptions.vector", ok if p["VECTOR_LS_MISALIGNED_LEGAL"] else align)
        if "MISALIGNED_AMO" in p:
            self.set("memory.misaligned.exceptions.amo", ok if p["MISALIGNED_AMO"] else align)
        lrsc = {
            "always raise misaligned exception": align,
            "always raise access fault": {"Some": "AccessFault"},
        }
        # LRSC_MISALIGNED_BEHAVIOR is defined only when misaligned AMOs trap; otherwise Sail's default stays
        if p.get("LRSC_MISALIGNED_BEHAVIOR") in lrsc:
            self.set("memory.misaligned.exceptions.lrsc", lrsc[p["LRSC_MISALIGNED_BEHAVIOR"]])
        elif "LRSC_MISALIGNED_BEHAVIOR" in p:
            self.unmodelled.append(
                f"memory.misaligned.exceptions.lrsc: LRSC_MISALIGNED_BEHAVIOR = {p['LRSC_MISALIGNED_BEHAVIOR']}"
            )
        if p.get("MISALIGNED_SPLIT_STRATEGY") == "sequential_bytes":
            # Split into aligned pieces in increasing address order.  Byte-sized pieces would look
            # the same: a piece can only fault at a page or PMP boundary, which is piece-aligned.
            self.set("memory.misaligned.order_decreasing", False)
            self.set("memory.misaligned.byte_by_byte", False)
            self.set("memory.misaligned.default_allowed_within_exp", 0)

    def platform(self) -> None:
        p = self.p
        if "VENDOR_ID_BANK" in p:
            self.set("platform.vendorid", (p["VENDOR_ID_BANK"] << 7) | p.get("VENDOR_ID_OFFSET", 0))
        self.set("platform.archid", p.get("ARCH_ID_VALUE", 0) if p.get("MARCHID_IMPLEMENTED", True) else 0)
        self.set("platform.impid", p.get("IMP_ID_VALUE", 0) if p.get("MIMPID_IMPLEMENTED", True) else 0)
        if self.has("Zicbom", "Zicbop", "Zicboz"):
            self.set_param("platform.cache_block_size_exp", "CACHE_BLOCK_SIZE", log2)
        strategy = p.get("LRSC_RESERVATION_STRATEGY")
        size = {
            "reserve naturally-aligned 64-byte region": 6,
            "reserve naturally-aligned 128-byte region": 7,
            "reserve exactly enough to cover the access": 2 if self.xlen == 32 else 3,
        }
        if strategy in size:
            self.set("platform.reservation.reservation_set_size_exp", size[strategy])
        elif strategy is not None:
            self.unmodelled.append(
                f"platform.reservation.reservation_set_size_exp: LRSC_RESERVATION_STRATEGY = {strategy}"
            )
        self.set_param("platform.reservation.require_exact_reservation_addr", "LRSC_FAIL_ON_NON_EXACT_LRSC")
        for kind, param in (("software", "MSI_INTR_IMPL"), ("external", "MEI_INTR_IMPL"), ("timer", "MTI_INTR_IMPL")):
            self.set_param(f"platform.interrupts.machine.{kind}.supported", param, bool)
        self.set_param("platform.wfi_available_to_user_mode", "WFI_U_MODE")
        # Which DUT event numbers count Sail's events is not described by UDB; count nothing
        self.set("platform.event_selectors", [])

    def extensions(self) -> None:
        p = self.p
        ext_cfg = self.cfg["extensions"]
        for name, node in ext_cfg.items():
            if name == "Stateen":
                for sub in ("Smstateen", "Ssstateen"):
                    self.set(f"extensions.Stateen.{sub}.supported", sub in self.exts)
            elif "supported" in node:
                self.reads.add(f"ext:{name}")
                present = name in self.exts
                if name == "A":
                    present |= self.exts >= {"Zaamo", "Zalrsc"}
                elif name == "B":
                    present |= self.exts >= {"Zba", "Zbb", "Zbs"}
                self.set(f"extensions.{name}.supported", present)
            if "mutable_misa" in node:
                self.reads.add(f"MUTABLE_MISA_{name}")
                self.set(f"extensions.{name}.mutable_misa", bool(p.get(f"MUTABLE_MISA_{name}", False)))
        if self.has("Ssstrict") and not self.has("S"):
            self.set("extensions.Ssstrict.supported", False)
            self.unmodelled.append("extensions.Ssstrict.supported: Sail requires S for Ssstrict, so it is off")
        sail_names = set(ext_cfg) | {"Smstateen", "Ssstateen"}
        always = {"I", "E", "Sm", "Zca", "C", "Q", "Zve32x", "Zve32f", "Zve64x", "Zve64f", "Zve64d"}
        missing = sorted(n for n in self.exts - sail_names - always if not re.fullmatch(r"Zvl\d+b", n))
        if "Q" in self.exts:
            missing.insert(0, "Q")
        if missing:
            self.unmodelled.append("extensions not modelled by Sail: " + " ".join(missing))

        for kind, param in (("software", "SSI_INTR_IMPL"), ("external", "SEI_INTR_IMPL"), ("timer", "STI_INTR_IMPL")):
            self.set_param(f"extensions.S.interrupts.{kind}.supported", param, bool)

        # Vector
        level = (
            "Full"
            if self.has("V")
            else "Float_double"
            if self.has("Zve64d")
            else "Float_single"
            if self.has("Zve64f", "Zve32f")
            else "Integer"
            if self.has("Zve64x", "Zve32x")
            else "Disabled"
        )
        self.set("extensions.V.support_level", level)
        if level != "Disabled":
            self.set_param("extensions.V.vlen_exp", "VLEN", log2)
            self.set_param("extensions.V.elen_exp", "ELEN", log2)
            self.set_param(
                "extensions.V.reserved_behavior.illegal_vtype",
                "VILL_SET_ON_RESERVED_VTYPE",
                lambda v: "IllegalVtype_SetVill" if v else "IllegalVtype_Illegal",
            )
            vl = p.get("RVV_VL_WHEN_AVL_LT_DOUBLE_VLMAX")
            if vl in ("VLMAX", "ceil(AVL/2)"):
                self.set("extensions.V.vl_use_ceil", vl != "VLMAX")
            elif vl is not None:
                self.unmodelled.append(f"extensions.V.vl_use_ceil: RVV_VL_WHEN_AVL_LT_DOUBLE_VLMAX = {vl}")
            eew = p.get("VECTOR_LS_INDEX_MAX_EEW")
            if eew is not None:
                eew_bits = self.xlen if eew == "XLEN" else int(eew)
                self.set("extensions.V.max_index_eew_exp", min(log2(eew_bits), log2(p.get("ELEN", eew_bits))))

        # Hypervisor
        if self.has("H"):
            self.set_param("extensions.H.geilen", "NUM_EXTERNAL_GUEST_INTERRUPTS")
            for key, param in TINST.items():
                v = p.get(param)
                if v in ("always zero", "always transformed standard instruction"):
                    self.set(f"extensions.H.transformed_instruction.{key}", v != "always zero")
                elif v is not None:
                    self.unmodelled.append(f"extensions.H.transformed_instruction.{key}: {param} = {v}")
            self.agree(
                "extensions.H.guest_page_fault_writes_htval",
                ["REPORT_GPA_IN_HTVAL_ON_GUEST_PAGE_FAULT"]
                + [f"REPORT_GPA_IN_TVAL_ON_{k}_GUEST_PAGE_FAULT" for k in ("LOAD", "STORE_AMO", "INSTRUCTION")],
            )
            for n in (32, 39, 48, 57):
                self.set_param(f"extensions.H.hgatp_modes.Sv{n}x4", f"SV{n}X4_TRANSLATION")
                self.set_param(f"extensions.H.vsatp_modes.Sv{n}", f"SV{n}_VSMODE_TRANSLATION")

        self.set_param("extensions.Zawrs.nto.is_nop", "ZAWRS_NTO_IS_NOP")
        self.set_param("extensions.Zkr.sseed_read_only_zero", "SSEED_READ_ONLY_ZERO")
        self.set_param("extensions.Zkr.useed_read_only_zero", "USEED_READ_ONLY_ZERO")
        if self.has("S"):
            self.set("extensions.Svbare.supported", self.has("Svbare") or bool(p.get("SATP_MODE_BARE")))
        self.set_param(
            "extensions.Svbare.sfence_vma_illegal_if_svbare_only", "TRAP_ON_SFENCE_VMA_WHEN_SATP_MODE_IS_READ_ONLY"
        )
        for ext in ("Smmpm", "Smnpm", "Ssnpm"):
            if f"SUPPORTED_PMLEN_{ext.upper()}" in p:
                for n in (7, 16):
                    self.set(f"extensions.{ext}.supported_pmlen_{n}", n in p[f"SUPPORTED_PMLEN_{ext.upper()}"])
        self.set_param("extensions.Ssqosid.rcid_length", "RCID_WIDTH")
        self.set_param("extensions.Ssqosid.mcid_length", "MCID_WIDTH")
        self.sdtrig()
        self.stateen()

    def sdtrig(self) -> None:
        p = self.p
        t = "extensions.Sdtrig"
        if not self.has("Sdtrig"):
            for ctx in ("mcontext", "hcontext", "scontext", "icount", "itrigger", "etrigger", "mcontrol6"):
                self.set(f"{t}.{ctx}.supported", False)
            return
        n = p.get("SDTRIG_NUM_TRIGGERS")
        if n is not None:
            if n > 16:
                self.unmodelled.append(f"{t}.num_triggers: SDTRIG_NUM_TRIGGERS = {n}, Sail allows at most 16")
            self.set(f"{t}.num_triggers", min(n, 16))
        self.set_param(f"{t}.breakpoint_reentrancy", "SDTRIG_BREAKPOINT_REENTRANCY")
        self.set(f"{t}.mcontext.supported", bool(p.get("MCONTEXT_IMPLEMENTED")))
        self.set(f"{t}.hcontext.supported", bool(p.get("HCONTEXT_IMPLEMENTED")) and self.has("H"))
        self.set(f"{t}.scontext.supported", bool(p.get("SCONTEXT_IMPLEMENTED")) and self.has("S"))
        for trig in ("icount", "itrigger", "etrigger", "mcontrol6"):
            per = p.get(f"SDTRIG_{trig.upper()}_SUPPORTED_TRIGGERS")
            if per is not None:
                self.set(f"{t}.{trig}.supported", any(per))
                if any(per) and not all(per):
                    self.unmodelled.append(f"{t}.{trig}.supported: Sail applies it to every trigger, UDB has {per}")
        self.set_param(f"{t}.icount.count_hardwired_one", "SDTRIG_ICOUNT_COUNT_HARDWIRED_1")
        self.set_param(f"{t}.icount.self_write_sets_pending", "SDTRIG_ICOUNT_SELF_WRITE_SETS_PENDING")
        for trig, param in (
            ("etrigger.supported_exceptions", "EXCEPTIONS"),
            ("itrigger.supported_interrupts", "INTERRUPTS"),
        ):
            codes = p.get(f"SDTRIG_{trig.split('.')[0].upper()}_SUPPORTED_{param}")
            if codes is not None:
                legal = self.exceptions() if param == "EXCEPTIONS" else self.interrupts()
                self.set(f"{t}.{trig}", sum(1 << c for c in codes if c < self.xlen) & legal)
        maskmax = p.get("SDTRIG_MCONTROL6_MASKMAX6")
        if maskmax is not None:
            if maskmax > self.xlen - 1:
                self.unmodelled.append(
                    f"{t}.mcontrol6.maskmax6: SDTRIG_MCONTROL6_MASKMAX6 = {maskmax}, Sail allows at most XLEN-1"
                )
            self.set(f"{t}.mcontrol6.maskmax6", min(maskmax, self.xlen - 1))
        self.set_param(f"{t}.mcontrol6.max_chain_length", "SDTRIG_MAX_CHAIN_LENGTH")
        self.set(
            f"{t}.textra.mhselect.mcontext_match",
            bool(p.get("SDTRIG_TEXTRA_MHSELECT_MCONTEXT_MATCH")) and bool(p.get("MCONTEXT_IMPLEMENTED")),
        )
        self.set(f"{t}.textra.mhselect.vmid_match", bool(p.get("SDTRIG_TEXTRA_MHSELECT_VMID_MATCH")) and self.has("H"))
        self.set(
            f"{t}.textra.sselect.scontext_match",
            bool(p.get("SDTRIG_TEXTRA_SSELECT_SCONTEXT_MATCH"))
            and bool(self.cfg["extensions"]["Sdtrig"]["scontext"]["supported"]),
        )
        self.set(f"{t}.textra.sselect.asid_match", bool(p.get("SDTRIG_TEXTRA_SSELECT_ASID_MATCH")) and self.has("S"))
        self.set_param(f"{t}.textra.mhvalue_len", "SDTRIG_TEXTRA_MHVALUE_LEN")
        self.set_param(f"{t}.textra.svalue_len", "SDTRIG_TEXTRA_SVALUE_LEN")

    def stateen(self) -> None:
        """Bits with a UDB parameter take it; the others are writable exactly when what they guard exists."""
        if not self.has("Smstateen", "Ssstateen"):
            return
        sdtrig = self.cfg["extensions"]["Sdtrig"]
        context = self.has("Sdtrig") and (sdtrig["scontext"]["supported"] or sdtrig["hcontext"]["supported"])
        exists = {
            "mstateen0.C": False,
            "mstateen0.FCSR": self.has("Zfinx"),
            "mstateen0.SE0": self.has("S"),
            # P1P13 guards hedelegh, which exists only on RV32
            "mstateen0.P1P13": self.has("H")
            and self.xlen == 32
            and self.cfg["base"]["privileged_isa_version"] == "Privileged_ISA_1_13",
            "mstateen0.ENVCFG": self.has("S"),
            "mstateen0.CONTEXT": context,
            "mstateen0.SRMCFG": self.has("Ssqosid"),
            "mstateen1.SE1": self.has("S"),
            "mstateen2.SE2": self.has("S"),
            "mstateen3.SE3": self.has("S"),
            "hstateen0.C": False,
            "hstateen0.FCSR": self.has("Zfinx"),
            "hstateen0.ENVCFG": self.has("H"),
            "hstateen0.CONTEXT": self.has("Sdtrig") and sdtrig["scontext"]["supported"],
            "sstateen0.C": False,
            "sstateen0.FCSR": self.has("Zfinx"),
        }
        for bit, present in exists.items():
            value = "CSRBit_Writable" if present else "CSRBit_ReadOnlyZero"
            param = STATEEN_UDB.get(bit)
            if param in self.p:
                value = STATEEN_TYPE[self.p[param]]
                if not present and value != "CSRBit_ReadOnlyZero":
                    self.unmodelled.append(
                        f"extensions.Stateen.{bit}: {param} = {self.p[param]} but the feature is absent"
                    )
                    value = "CSRBit_ReadOnlyZero"
            self.set(f"extensions.Stateen.{bit}", value)

    def apply_extra(self) -> None:
        for key, value in self.extra.items():
            node = self.cfg
            try:
                for k in key.split(".")[:-1]:
                    node = node[k]
            except (KeyError, TypeError):
                self.unmodelled.append(f"{key}: not a Sail 0.16 key (value {value!r})")
                continue
            self.set(key, value)
        p1p13 = "extensions.Stateen.mstateen0.P1P13"
        if self.xlen == 64 and self.extra.get(p1p13, "CSRBit_ReadOnlyZero") != "CSRBit_ReadOnlyZero":
            # P1P13 guards hedelegh, which RV64 does not have; Sail insists the bit is read-only zero
            self.unmodelled.append(f"{p1p13}: measured {self.extra[p1p13]}, but Sail requires read-only zero on RV64")
            self.set(p1p13, "CSRBit_ReadOnlyZero")

    def regions(self, plat: dict[str, Any]) -> None:
        """Main memory from link.ld, and one IO region holding the CLINT and the interrupt generator."""
        default_regions = self.cfg["memory"]["regions"]
        ram_attrs = copy.deepcopy(next(r for r in default_regions if r["attributes"]["mem_type"] == "MainMemory"))
        io_attrs = copy.deepcopy(
            next(
                r for r in default_regions if r["attributes"]["mem_type"] == "IOMemory" and r["attributes"]["writable"]
            )
        )
        a = ram_attrs["attributes"]
        if self.has("Zacas", "Ziccamoc"):
            # Sail requires AMOCASQ for Ziccamoc on either XLEN
            a["atomic_support"] = "AMOCASQ" if self.xlen == 64 or self.has("Ziccamoc") else "AMOCASD"
        elif self.has("A", "Zaamo"):
            a["atomic_support"] = "AMOArithmetic"
        else:
            a["atomic_support"] = "AMONone"
        a["reservability"] = "RsrvEventual" if self.has("A", "Zalrsc") else "RsrvNone"
        a["supports_cbo_zero"] = self.has("Zicboz")
        granule = 16 if self.has("Zama16b") else self.p.get("MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE", 0)
        if self.p.get("MISALIGNED_AMO") and granule < 16:
            # Sail lets a misaligned AMO proceed only inside the granule; the extractor's probe is a
            # word AMO at offset 2, so a hart that allows misaligned AMOs needs at least 16 bytes
            self.unmodelled.append(
                f"misaligned_atomicity_granule_size_exp: 16 bytes used, MISALIGNED_AMO is true but the granule is {granule}"
            )
            granule = 16
        a["misaligned_atomicity_granule_size_exp"] = log2(granule) if granule else 0
        a["vector_misaligned_atomicity_granule_size_exp"] = a["misaligned_atomicity_granule_size_exp"]

        def region(base: int, size: int, attrs: dict[str, Any]) -> dict[str, Any]:
            r = copy.deepcopy(attrs)
            r["base"] = {"len": 64, "value": f"0x{base:X}"}
            r["size"] = {"len": 64, "value": f"0x{size:X}"}
            return r

        ram_base, ram_size = plat["ram_base"], plat["ram_size"]
        regions = [region(ram_base & ~(PAGE - 1), (ram_size + PAGE - 1) & ~(PAGE - 1), ram_attrs)]
        regions.append(region(plat["clint_base"], IO_SIZE, io_attrs))
        self.set("memory.regions", sorted(regions, key=lambda r: int(r["base"]["value"], 16)))
        self.set("memory.dtb_address", {"len": 64, "value": f"0x{plat['clint_base'] + IO_SIZE - PAGE:X}"})
        self.set("platform.clint.supported", True)
        self.set("platform.clint.base", plat["clint_base"])
        self.set("platform.clint.size", CLINT_SIZE)
        self.set("platform.simple_interrupt_generator.supported", True)
        self.set("platform.simple_interrupt_generator.base", plat["clint_base"] + 0x10000)
        top = max(ram_base + ram_size, plat["clint_base"] + IO_SIZE) - 1
        pa = self.cfg["memory"]["physaddr_bits"]
        if top >> pa:
            self.unmodelled.append(f"memory.regions: address 0x{top:X} needs more than physaddr_bits = {pa}")

    def convert(self, plat: dict[str, Any] | None) -> dict[str, Any]:
        self.base()
        self.memory()
        self.platform()
        self.extensions()
        if plat:
            self.regions(plat)
        self.apply_extra()
        self.cfg["$schema"] = SAIL_SCHEMA
        return self.cfg

    def relevant(self, key: str) -> bool:
        """Whether a Sail key affects this configuration (Sail ignores the rest)."""
        parts = key.split(".")
        has, p = self.has, self.p
        if parts[0] == "extensions":
            ext = parts[1]
            if ext == "Stateen":
                return (
                    has("Smstateen", "Ssstateen")
                    and (parts[2] != "hstateen0" or has("H"))
                    and (parts[2] != "sstateen0" or has("S"))
                )
            if ext == "V":
                return parts[2] == "support_level" or has("V", "Zve32x", "Zve64x")
            if ext == "C":
                return has("C", "Zca")
            if ext == "A":
                return has("A", "Zaamo", "Zalrsc")
            if ext == "B":
                return has("B", "Zba", "Zbb", "Zbs")
            return parts[-1] == "supported" and len(parts) == 3 or has(ext)
        by_prefix = {
            "base.vstvec": has("H"),
            "base.hcounteren_writable_bits": has("H"),
            "base.stvec": has("S"),
            "base.scounteren_writable_bits": has("S"),
            "base.medeleg": has("S"),
            "base.mideleg": has("S"),
            "base.mcounteren_writable_bits": has("U"),
            "base.hpmcounter": has("Zihpm"),
            "base.hpmevent": has("Zihpm"),
            "base.mcountinhibit.writable_bits": bool(p.get("MCOUNTINHIBIT_IMPLEMENTED")),
            "base.xtval_nonzero.virtual_instruction": has("H"),
            "base.xtval_nonzero.load_guest_page_fault": has("H"),
            "base.xtval_nonzero.samo_guest_page_fault": has("H"),
            "base.xtval_nonzero.fetch_guest_page_fault": has("H"),
            "base.xtval_nonzero.load_page_fault": has("S"),
            "base.xtval_nonzero.samo_page_fault": has("S"),
            "base.xtval_nonzero.fetch_page_fault": has("S"),
            "base.xtval_nonzero.software_check": has("Zicfilp", "Zicfiss"),
            "base.xtval_nonzero.hardware_breakpoint": has("Sdtrig"),
            "base.xtval_nonzero.reserved_exceptions": False,
            "base.reserved_behavior.amocas_odd_register": has("Zacas"),
            "base.reserved_behavior.fcsr_rm": has("F", "Zfinx"),
            "base.reserved_behavior.pmpcfg_write_only": bool(p.get("NUM_PMP_ENTRIES")),
            "base.reserved_behavior.xenvcfg_cbie": has("Zicbom"),
            "base.reserved_behavior.rv32zdinx_odd_register": has("Zdinx") and self.xlen == 32,
            "base.mstatus.vs_legal_states": has("V", "Zve32x", "S"),
            "memory.asidlen": has("S"),
            "memory.vmidlen": has("H"),
            "memory.pmp.grain": bool(p.get("NUM_PMP_ENTRIES")),
            "memory.pmp.tor": bool(p.get("NUM_PMP_ENTRIES")),
            "memory.pmp.na4": bool(p.get("NUM_PMP_ENTRIES")),
            "memory.pmp.napot": bool(p.get("NUM_PMP_ENTRIES")),
            "memory.misaligned.exceptions.vector": has("V", "Zve32x"),
            "memory.misaligned.exceptions.amo": has("A", "Zaamo"),
            "memory.misaligned.exceptions.lrsc": has("A", "Zalrsc"),
            "memory.misaligned.order_decreasing": bool(p.get("MISALIGNED_LDST")),
            "memory.misaligned.byte_by_byte": bool(p.get("MISALIGNED_LDST")),
            "memory.misaligned.default_allowed_within_exp": bool(p.get("MISALIGNED_LDST")),
            "platform.cache_block_size_exp": has("Zicbom", "Zicbop", "Zicboz"),
            "platform.reservation": has("A", "Zalrsc"),
            "platform.wfi_available_to_user_mode": has("U"),
            "platform.event_selectors": has("Zihpm"),
        }
        for prefix, rel in by_prefix.items():
            if key == prefix or key.startswith((prefix + ".", prefix + "_")):
                return rel
        return True

    def defaulted(self) -> list[str]:
        """Relevant leaf keys still at Sail's default."""
        return [
            key
            for key in leaves(self.cfg)
            if key != "$schema"
            and self.relevant(key)
            and not any(key == s or key.startswith(s + ".") for s in self.set_keys)
        ]


# ---------------------------------------------------------------------------------------------
# Platform facts from link.ld and rvmodel_macros.h


def macro_value(cc: str, xlen: int, include_dir: Path, macro: str, work: Path) -> int | None:
    """Evaluate an rvmodel_macros.h address macro by assembling `.dword MACRO` (handles .EQU symbols)."""
    src = work / f"{macro}.S"
    src.write_text(f'#include "rvmodel_macros.h"\n.data\n#ifdef {macro}\n.dword {macro}\n#endif\n')
    obj = work / f"{macro}.o"
    abi = "ilp32" if xlen == 32 else "lp64"
    r = subprocess.run(
        [cc, f"-march=rv{xlen}i_zicsr", f"-mabi={abi}", "-c", f"-I{include_dir}", str(src), "-o", str(obj)],
        capture_output=True,
        check=False,
    )
    if r.returncode:
        return None
    binfile = work / f"{macro}.bin"
    objcopy = re.sub(r"(gcc|clang)$", "objcopy", cc) if cc.endswith("gcc") else "riscv64-unknown-elf-objcopy"
    subprocess.run([objcopy, "-O", "binary", "-j", ".data", str(obj), str(binfile)], check=True)
    data = binfile.read_bytes()
    return int.from_bytes(data[:8], "little") if len(data) >= 8 else None


def platform_facts(
    config_dir: Path, xlen: int, cc: str = "riscv64-unknown-elf-gcc"
) -> tuple[dict[str, Any], list[str]]:
    """RAM from link.ld, CLINT and access-fault address from rvmodel_macros.h, and a CLINT placement."""
    notes = []
    text = (config_dir / "link.ld").read_text()

    def num(sym: str) -> int:
        m = re.search(rf"^\s*{sym}\s*=\s*(0x[0-9a-fA-F]+|\d+)\s*([KM]?)\s*;", text, re.MULTILINE)
        if not m:
            m = re.search(
                rf"{'ORIGIN' if sym == 'RAM_ORIGIN' else 'LENGTH'}\s*=\s*(0x[0-9a-fA-F]+|\d+)\s*([KM]?)", text
            )
        if not m:
            raise ValueError(f"{config_dir}/link.ld: cannot find {sym}")
        return int(m.group(1), 0) << {"": 0, "K": 10, "M": 20}[m.group(2)]

    ram_base, ram_size = num("RAM_ORIGIN"), num("RAM_LENGTH")
    with tempfile.TemporaryDirectory() as tmp:
        macros = {
            m: macro_value(cc, xlen, config_dir, m, Path(tmp))
            for m in ("RVMODEL_MTIME_ADDRESS", "RVMODEL_MTIMECMP_ADDRESS", "RVMODEL_ACCESS_FAULT_ADDRESS")
        }
    fault = macros["RVMODEL_ACCESS_FAULT_ADDRESS"]
    busy = [(ram_base, ram_base + ram_size)]
    if fault is not None:
        if ram_base <= fault < ram_base + ram_size:
            notes.append(
                f"RVMODEL_ACCESS_FAULT_ADDRESS 0x{fault:X} is inside RAM per link.ld; Sail will not fault there"
            )
        busy.append((fault, fault + 1))

    def free(base: int) -> bool:
        return (
            base % 0x10000 == 0
            and base + IO_SIZE <= 1 << min(xlen, 34)
            and all(base + IO_SIZE <= lo or base >= hi for lo, hi in busy)
        )

    clint = None
    mtime = macros["RVMODEL_MTIME_ADDRESS"]
    if mtime is not None and free(mtime - 0xBFF8):
        clint = mtime - 0xBFF8
    else:
        if mtime is not None:
            notes.append(f"RVMODEL_MTIME_ADDRESS 0x{mtime:X} is not a free CLINT location for Sail; CLINT moved")
        for base in [0x2000000, 0x40000000, 0xC0000000, *range(0x10000, 1 << 32, 0x1000000)]:
            if free(base):
                clint = base
                break
    if clint is None:
        raise ValueError("no free address for Sail's CLINT")
    return {"ram_base": ram_base, "ram_size": ram_size, "clint_base": clint, "access_fault": fault, **macros}, notes


# ---------------------------------------------------------------------------------------------


def render(cfg: dict[str, Any], header: list[str]) -> str:
    body = {"$schema": cfg["$schema"], **{k: v for k, v in cfg.items() if k != "$schema"}}
    return "".join(f"// {line}\n" for line in header) + json.dumps(body, indent=2) + "\n"


def convert_file(
    udb_path: Path,
    config_dir: Path | None,
    extra: dict[str, Any],
    sim: str = "sail_riscv_sim",
    cc: str = "riscv64-unknown-elf-gcc",
) -> tuple[str, dict[str, Any], Converter, list[str]]:
    udb = YAML(typ="safe").load(udb_path.read_text())
    xlen = int((udb.get("params") or {}).get("MXLEN", 64))
    conv = Converter(udb, sail_default(sim, xlen), extra)
    plat, notes = platform_facts(config_dir, xlen, cc) if config_dir else (None, [])
    cfg = conv.convert(plat)
    header = [f"Sail configuration generated by udb_to_sail.py from {udb_path.name}"]
    header += [f"note: {n}" for n in notes]
    header += [f"not expressible in Sail: {u}" for u in conv.unmodelled]
    defaulted = conv.defaulted()
    if defaulted:
        header.append("left at Sail's default (no UDB parameter or measurement): " + ", ".join(defaulted))
    return render(cfg, header), cfg, conv, notes


# Keys that place Sail's own devices; they differ between configurations without mattering
LAYOUT = ("memory.regions", "memory.dtb_address", "platform.clint", "platform.simple_interrupt_generator")


def bits(v: object) -> object:
    return int(str(v["value"]).replace("_", ""), 16) if isinstance(v, dict) and "value" in v else v


def effective_misaligned(cfg: dict[str, Any]) -> dict[str, str]:
    """What a misaligned access in main memory does: "trap", or "allowed" (within a granule).

    UDB says whether such an access traps but not with which exception, and Sail can express a
    trap either globally or through the main-memory region's attributes, so configurations are
    compared on this summary rather than on the raw keys.
    """
    ram = next(r for r in cfg["memory"]["regions"] if r["attributes"]["mem_type"] == "MainMemory")["attributes"]
    out = {}
    for kind in ("load_store", "vector", "amo", "lrsc"):
        glob = cfg["memory"]["misaligned"]["exceptions"].get(kind, {"None": None})
        region = ram.get("misaligned_exceptions", {}).get(kind)
        if "Some" in glob:
            out[kind] = "trap"
        elif kind in ("amo", "lrsc"):
            granule = ram.get("misaligned_atomicity_granule_size_exp", 0)
            out[kind] = f"allowed within {1 << granule} bytes" if granule and kind == "amo" else "trap"
        else:
            out[kind] = "trap" if isinstance(region, dict) and "Some" in region else "allowed"
    return out


def compare(conv: Converter, new: dict[str, Any], old: dict[str, Any]) -> list[tuple[str, Any, Any]]:
    """Relevant keys whose values differ between a generated and an existing configuration."""
    new, old = copy.deepcopy(new), copy.deepcopy(old)
    for cfg in (new, old):
        cfg["memory"]["misaligned"]["exceptions"] = effective_misaligned(cfg)
    a, b = leaves(new), leaves(old)
    diffs = []
    for k in sorted(set(a) | set(b)):
        if k == "$schema" or k.startswith(LAYOUT) or not conv.relevant(k):
            continue
        va, vb = bits(a.get(k, "<absent>")), bits(b.get(k, "<absent>"))
        if k == "base.writable_hpm_counters" and isinstance(va, int) and isinstance(vb, int):
            va, vb = va & ~7, vb & ~7
        if va != vb:
            diffs.append((k, va, vb))
    return diffs


def validate(path: Path, sim: str = "sail_riscv_sim") -> str:
    r = subprocess.run([sim, "--config", str(path), "--validate-config"], capture_output=True, text=True, check=False)
    return "" if r.returncode == 0 else (r.stdout + r.stderr).strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("udb_yaml", type=Path)
    ap.add_argument("-o", "--output", type=Path, help="sail.json to write (default: stdout)")
    ap.add_argument("--config-dir", type=Path, help="directory with link.ld and rvmodel_macros.h for the memory map")
    ap.add_argument("--sail-extra", type=Path, help="JSON object of dotted Sail keys measured outside UDB")
    ap.add_argument("--compare", type=Path, help="existing sail.json to compare the result with")
    ap.add_argument("--sim", default="sail_riscv_sim")
    ap.add_argument("--cc", default="riscv64-unknown-elf-gcc")
    args = ap.parse_args()

    extra = json.loads(args.sail_extra.read_text()) if args.sail_extra else {}
    text, cfg, conv, _ = convert_file(args.udb_yaml, args.config_dir, extra, args.sim, args.cc)
    if args.output:
        args.output.write_text(text)
        err = validate(args.output, args.sim)
        if err:
            print(f"{args.output}: Sail rejects the configuration:\n{err}", file=sys.stderr)
            sys.exit(1)
    else:
        sys.stdout.write(text)
    if args.compare:
        for k, va, vb in compare(conv, cfg, pyjson5.loads(args.compare.read_text())):
            show = [
                hex(v) if isinstance(v, int) and not isinstance(v, bool) and v > 9 else json.dumps(v)[:100]
                for v in (va, vb)
            ]
            print(f"{k}: generated {show[0]}  existing {show[1]}")


if __name__ == "__main__":
    main()
