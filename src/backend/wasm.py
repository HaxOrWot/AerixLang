"""
Aerix Compiler (arxc) — WebAssembly (WASM) Backend & Browser Target (Phase 20)
Provides direct compilation of Aerix Intermediate Representation (AIR) into:
1. WebAssembly Text Format (.wat)
2. Standalone WebAssembly Binary (.wasm) with zero external tool dependencies
3. Browser JS Interop and HTML5 Canvas / Terminal Runner
"""

import struct
from typing import Dict, List, Optional, Tuple, Any
from src.middle.air import (
    AIRModule, AIRFunction, AIRInstruction, AIRConst, AIRBinOp, AIRUnaryOp,
    AIRAssign, AIRLoad, AIRStore, AIRCast, AIRCall, AIRCallMethod, AIRBranchIf,
    AIRBranchIfNot, AIRJump, AIRLabel, AIRReturn, AIRFormatString
)


# ==============================================================================
# 1. Low-Level WebAssembly Binary Encodings
# ==============================================================================

def encode_uleb128(n: int) -> bytes:
    """Encodes an unsigned integer into LEB128 format."""
    res = bytearray()
    while True:
        byte = n & 0x7F
        n >>= 7
        if n != 0:
            byte |= 0x80
        res.append(byte)
        if n == 0:
            break
    return bytes(res)


def encode_sleb128(n: int) -> bytes:
    """Encodes a signed integer into LEB128 format."""
    res = bytearray()
    while True:
        byte = n & 0x7F
        n >>= 7
        sign = byte & 0x40
        if (n == 0 and sign == 0) or (n == -1 and sign != 0):
            res.append(byte)
            break
        else:
            res.append(byte | 0x80)
    return bytes(res)


def encode_vector(items: List[bytes]) -> bytes:
    """Encodes a vector of byte arrays with its ULEB128 count prefix."""
    return encode_uleb128(len(items)) + b"".join(items)


def encode_string(s: str) -> bytes:
    """Encodes a UTF-8 string with its byte length prefix."""
    data = s.encode("utf-8")
    return encode_uleb128(len(data)) + data


# WASM Type Tags
VAL_I32 = 0x7F
VAL_I64 = 0x7E
VAL_F32 = 0x7D
VAL_F64 = 0x7C
VAL_VOID = 0x40

# Section IDs
SEC_CUSTOM   = 0
SEC_TYPE     = 1
SEC_IMPORT   = 2
SEC_FUNCTION = 3
SEC_TABLE    = 4
SEC_MEMORY   = 5
SEC_GLOBAL   = 6
SEC_EXPORT   = 7
SEC_START    = 8
SEC_ELEMENT  = 9
SEC_CODE     = 10
SEC_DATA     = 11


def infer_function_variable_types(fn: AIRFunction) -> Dict[str, str]:
    """Infers types of all parameters, locals, and temporaries in an AIRFunction."""
    types: Dict[str, str] = dict(fn.var_types)
    for i, p in enumerate(fn.params):
        if i < len(fn.param_types):
            types[p] = fn.param_types[i]
        elif p not in types:
            types[p] = "i64"

    for insn in fn.instructions:
        if isinstance(insn, AIRConst):
            types[insn.dest] = insn.type_name
        elif isinstance(insn, AIRFormatString):
            types[insn.dest] = "str"
        elif isinstance(insn, AIRBinOp):
            l_type = types.get(insn.left, "i64")
            r_type = types.get(insn.right, "i64")
            if l_type in ("f64", "f32") or r_type in ("f64", "f32"):
                types[insn.dest] = "f64"
            elif insn.op in ("==", "!=", "<", "<=", ">", ">=", "&&", "||"):
                types[insn.dest] = "i64"
            else:
                types[insn.dest] = l_type
        elif isinstance(insn, AIRAssign):
            types[insn.dest] = types.get(insn.src, "i64")
        elif isinstance(insn, AIRLoad):
            types[insn.dest] = types.get(insn.var_name, "i64")
        elif isinstance(insn, AIRStore):
            types[insn.var_name] = types.get(insn.src, "i64")
        elif isinstance(insn, AIRCast):
            types[insn.dest] = insn.target_type

    return types


def partition_into_basic_blocks(fn: AIRFunction):
    """Partitions a linear list of AIR instructions into discrete basic blocks."""
    label_to_block: Dict[str, int] = {}
    blocks: List[Tuple[List[AIRInstruction], Optional[AIRInstruction]]] = []
    curr_insns: List[AIRInstruction] = []
    curr_labels: List[str] = []

    for insn in fn.instructions:
        if isinstance(insn, AIRLabel):
            if curr_insns or curr_labels:
                b_idx = len(blocks)
                for lbl in curr_labels:
                    label_to_block[lbl] = b_idx
                blocks.append((curr_insns, None))
                curr_insns = []
                curr_labels = []
            curr_labels.append(insn.name)
        elif isinstance(insn, (AIRBranchIf, AIRBranchIfNot, AIRJump, AIRReturn)):
            curr_insns.append(insn)
            b_idx = len(blocks)
            for lbl in curr_labels:
                label_to_block[lbl] = b_idx
            blocks.append((curr_insns, insn))
            curr_insns = []
            curr_labels = []
        else:
            curr_insns.append(insn)

    if curr_insns or curr_labels:
        b_idx = len(blocks)
        for lbl in curr_labels:
            label_to_block[lbl] = b_idx
        blocks.append((curr_insns, None))

    return blocks, label_to_block


# ==============================================================================
# 2. WebAssembly Text Format (.wat) Emitter
# ==============================================================================

class WasmTextEmitter:
    """Translates an AIRModule into clean, standard WebAssembly Text format (.wat)."""

    def __init__(self, air_module: AIRModule):
        self.air = air_module
        self.data_segments: List[Tuple[int, bytes]] = []
        self.data_offset = 1024

    def emit(self) -> str:
        lines: List[str] = [
            ";; =====================================================================",
            ";; Aerix WebAssembly (WASM) Text Format Module",
            ";; Generated by the Aerix Compiler (arxc) — Phase 20 Target",
            ";; =====================================================================",
            "(module",
            '  ;; Host Browser Runtime Imports',
            '  (import "env" "print_i64" (func $print_i64 (param i64)))',
            '  (import "env" "print_f64" (func $print_f64 (param f64)))',
            '  (import "env" "print_str" (func $print_str (param i32 i32)))',
            '  (import "env" "arx_canvas_set_pixel" (func $arx_canvas_set_pixel (param i32 i32 i32 i32 i32)))',
            '  (import "env" "arx_canvas_fill_rect" (func $arx_canvas_fill_rect (param i32 i32 i32 i32 i32 i32 i32)))',
            '  (import "env" "arx_canvas_clear" (func $arx_canvas_clear (param i32 i32 i32)))',
            '  (import "env" "arx_now_ms" (func $arx_now_ms (result f64)))',
            '',
            '  ;; Linear Memory (1 page = 64KB)',
            '  (memory (export "memory") 1)',
            ''
        ]

        # Scan for string constants
        string_constants: Dict[str, Tuple[int, int]] = {}
        for fn in self.air.functions.values():
            for insn in fn.instructions:
                if isinstance(insn, AIRConst) and insn.type_name in ("str", "string") and isinstance(insn.value, str):
                    if insn.value not in string_constants:
                        encoded = insn.value.encode("utf-8")
                        offset = self.data_offset
                        string_constants[insn.value] = (offset, len(encoded))
                        self.data_segments.append((offset, encoded))
                        self.data_offset += len(encoded) + 1

        # Emit Data Segments
        for offset, data in self.data_segments:
            escaped = "".join(f"\\{b:02x}" if b < 32 or b >= 127 or b in (34, 92) else chr(b) for b in data)
            lines.append(f'  (data (i32.const {offset}) "{escaped}")')
        lines.append('')

        # Emit Functions
        for fn_name, fn in self.air.functions.items():
            lines.extend(self._emit_function(fn, string_constants))
            lines.append('')

        lines.append(")")
        return "\n".join(lines)

    def _emit_instruction(self, insn: AIRInstruction, fn: AIRFunction, var_types: Dict[str, str], string_constants: Dict[str, Tuple[int, int]], is_main: bool) -> List[str]:
        out = []
        if isinstance(insn, AIRConst):
            dest = insn.dest.replace("$", "_")
            if insn.type_name in ("f64", "f32"):
                out.append(f"      f64.const {float(insn.value)}")
                out.append(f"      local.set ${dest}")
            elif insn.type_name in ("str", "string") and isinstance(insn.value, str):
                offset, length = string_constants.get(insn.value, (1024, len(insn.value)))
                packed = (length << 32) | offset
                out.append(f"      i64.const {packed}")
                out.append(f"      local.set ${dest}")
            else:
                val = 1 if insn.value is True else (0 if insn.value is False else int(insn.value))
                out.append(f"      i64.const {val}")
                out.append(f"      local.set ${dest}")

        elif isinstance(insn, AIRAssign):
            dest = insn.dest.replace("$", "_")
            src = insn.src.replace("$", "_")
            out.append(f"      local.get ${src}")
            out.append(f"      local.set ${dest}")

        elif isinstance(insn, AIRLoad):
            dest = insn.dest.replace("$", "_")
            var = insn.var_name.replace("$", "_")
            out.append(f"      local.get ${var}")
            out.append(f"      local.set ${dest}")

        elif isinstance(insn, AIRStore):
            var = insn.var_name.replace("$", "_")
            src = insn.src.replace("$", "_")
            out.append(f"      local.get ${src}")
            out.append(f"      local.set ${var}")

        elif isinstance(insn, AIRBinOp):
            dest = insn.dest.replace("$", "_")
            l = insn.left.replace("$", "_")
            r = insn.right.replace("$", "_")
            is_f64 = var_types.get(insn.dest) in ("f64", "f32")
            prefix = "f64" if is_f64 else "i64"
            
            op_map = {
                "+": f"{prefix}.add",
                "-": f"{prefix}.sub",
                "*": f"{prefix}.mul",
                "/": f"{prefix}.div" if is_f64 else f"{prefix}.div_s",
                "%": f"{prefix}.rem_s",
                "==": f"{prefix}.eq",
                "!=": f"{prefix}.ne",
                "<": f"{prefix}.lt" if is_f64 else f"{prefix}.lt_s",
                "<=": f"{prefix}.le" if is_f64 else f"{prefix}.le_s",
                ">": f"{prefix}.gt" if is_f64 else f"{prefix}.gt_s",
                ">=": f"{prefix}.ge" if is_f64 else f"{prefix}.ge_s",
                "&&": f"{prefix}.and",
                "||": f"{prefix}.or",
            }
            wasm_op = op_map.get(insn.op, f"{prefix}.add")
            out.append(f"      local.get ${l}")
            out.append(f"      local.get ${r}")
            out.append(f"      {wasm_op}")
            if insn.op in ("==", "!=", "<", "<=", ">", ">="):
                dest_type = var_types.get(insn.dest, "i64")
                if dest_type in ("i64", "int"):
                    out.append("      i64.extend_i32_u")
            out.append(f"      local.set ${dest}")

        elif isinstance(insn, AIRCall):
            target = insn.fn_name
            if target in ("print", "println"):
                for arg in insn.args:
                    arg_clean = arg.replace("$", "_")
                    arg_type = var_types.get(arg, "i64")
                    if arg_type in ("str", "string"):
                        out.append(f"      local.get ${arg_clean}")
                        out.append("      i32.wrap_i64")
                        out.append(f"      local.get ${arg_clean}")
                        out.append("      i64.const 32")
                        out.append("      i64.shr_u")
                        out.append("      i32.wrap_i64")
                        out.append("      call $print_str")
                    elif arg_type in ("f64", "f32"):
                        out.append(f"      local.get ${arg_clean}")
                        out.append("      call $print_f64")
                    else:
                        out.append(f"      local.get ${arg_clean}")
                        out.append("      call $print_i64")
            elif target.startswith("arx_canvas_"):
                for arg in insn.args:
                    arg_clean = arg.replace("$", "_")
                    out.append(f"      local.get ${arg_clean}")
                    out.append("      i32.wrap_i64")
                out.append(f"      call ${target}")
            else:
                for arg in insn.args:
                    arg_clean = arg.replace("$", "_")
                    out.append(f"      local.get ${arg_clean}")
                out.append(f"      call ${target}")
                if insn.dest:
                    dest = insn.dest.replace("$", "_")
                    out.append(f"      local.set ${dest}")

        elif isinstance(insn, AIRReturn):
            if insn.value:
                val = insn.value.replace("$", "_")
                out.append(f"      local.get ${val}")
            elif is_main:
                out.append("      i32.const 0")
            out.append("      return")

        return out

    def _emit_function(self, fn: AIRFunction, string_constants: Dict[str, Tuple[int, int]]) -> List[str]:
        out = []
        is_main = fn.name == "main"
        export_clause = f' (export "{fn.name}")' if is_main or fn.is_pub else ""
        var_types = infer_function_variable_types(fn)

        # Build params
        params_wat = ""
        for i, p in enumerate(fn.params):
            ptype = var_types.get(p, "i64")
            wtype = "f64" if ptype in ("f64", "f32") else "i64"
            params_wat += f" (param ${p} {wtype})"

        # Result type
        ret_wat = ""
        if fn.return_type and fn.return_type != "void":
            wtype = "f64" if fn.return_type in ("f64", "f32") else "i64"
            ret_wat = f" (result {wtype})"
        elif is_main:
            ret_wat = " (result i32)"

        out.append(f"  (func ${fn.name}{export_clause}{params_wat}{ret_wat}")

        # Collect local variables
        locals_map: Dict[str, str] = {}
        for insn in fn.instructions:
            if hasattr(insn, "dest") and insn.dest and insn.dest not in fn.params:
                vtype = var_types.get(insn.dest, "i64")
                wtype = "f64" if vtype in ("f64", "f32") else "i64"
                locals_map[insn.dest] = wtype
            if isinstance(insn, (AIRStore, AIRLoad)):
                name = insn.var_name
                if name not in fn.params:
                    vtype = var_types.get(name, "i64")
                    wtype = "f64" if vtype in ("f64", "f32") else "i64"
                    locals_map[name] = wtype

        blocks, label_to_block = partition_into_basic_blocks(fn)
        has_branches = len(blocks) > 1

        if has_branches:
            locals_map["_pc"] = "i32"

        # Emit local declarations
        for loc_name, wtype in locals_map.items():
            clean_name = loc_name.replace("$", "_")
            out.append(f"    (local ${clean_name} {wtype})")

        if not has_branches:
            # Straight-line code
            for insn in fn.instructions:
                out.extend(self._emit_instruction(insn, fn, var_types, string_constants, is_main))
            if is_main and not any(isinstance(i, AIRReturn) for i in fn.instructions):
                out.append("    i32.const 0")
                out.append("    return")
        else:
            # Multi-block state machine dispatcher
            out.append("    (block $exit")
            out.append("      (loop $dispatch")
            for b_idx, (b_insns, term) in enumerate(blocks):
                out.append(f"        (if (i32.eq (local.get $_pc) (i32.const {b_idx}))")
                out.append("          (then")
                for insn in b_insns:
                    if not isinstance(insn, (AIRBranchIf, AIRBranchIfNot, AIRJump, AIRReturn)):
                        out.extend(self._emit_instruction(insn, fn, var_types, string_constants, is_main))

                # Handle block terminator
                if isinstance(term, AIRReturn):
                    out.extend(self._emit_instruction(term, fn, var_types, string_constants, is_main))
                elif isinstance(term, AIRJump):
                    target_idx = label_to_block.get(term.target_label, b_idx + 1)
                    out.append(f"            i32.const {target_idx}")
                    out.append("            local.set $_pc")
                    out.append("            br $dispatch")
                elif isinstance(term, AIRBranchIf):
                    cond = term.condition.replace("$", "_")
                    target_idx = label_to_block.get(term.target_label, b_idx + 1)
                    fallthrough_idx = b_idx + 1
                    out.append(f"            local.get ${cond}")
                    out.append("            i64.eqz")
                    out.append("            (if")
                    out.append("              (then")
                    out.append(f"                i32.const {fallthrough_idx}")
                    out.append("                local.set $_pc")
                    out.append("                br $dispatch")
                    out.append("              )")
                    out.append("              (else")
                    out.append(f"                i32.const {target_idx}")
                    out.append("                local.set $_pc")
                    out.append("                br $dispatch")
                    out.append("              )")
                    out.append("            )")
                elif isinstance(term, AIRBranchIfNot):
                    cond = term.condition.replace("$", "_")
                    target_idx = label_to_block.get(term.target_label, b_idx + 1)
                    fallthrough_idx = b_idx + 1
                    out.append(f"            local.get ${cond}")
                    out.append("            i64.eqz")
                    out.append("            (if")
                    out.append("              (then")
                    out.append(f"                i32.const {target_idx}")
                    out.append("                local.set $_pc")
                    out.append("                br $dispatch")
                    out.append("              )")
                    out.append("              (else")
                    out.append(f"                i32.const {fallthrough_idx}")
                    out.append("                local.set $_pc")
                    out.append("                br $dispatch")
                    out.append("              )")
                    out.append("            )")
                else:
                    if b_idx + 1 < len(blocks):
                        out.append(f"            i32.const {b_idx + 1}")
                        out.append("            local.set $_pc")
                        out.append("            br $dispatch")
                    else:
                        out.append("            br $exit")
                out.append("          )")
                out.append("        )")
            out.append("      )")
            out.append("    )")

            ret_t = fn.return_type
            if ret_t in ("f64", "f32"):
                out.append("    f64.const 0.0")
                out.append("    return")
            elif ret_t and ret_t != "void":
                out.append("    i64.const 0")
                out.append("    return")
            elif is_main:
                out.append("    i32.const 0")
                out.append("    return")

        out.append("  )")
        return out


# ==============================================================================
# 3. Direct Pure-Python Binary WebAssembly (.wasm) Emitter
# ==============================================================================

class WasmBinaryEncoder:
    """
    Self-contained WebAssembly binary bytecode generator.
    Translates an AIRModule directly into valid W3C .wasm binary bytes.
    """

    def __init__(self, air_module: AIRModule):
        self.air = air_module
        self.type_entries: List[bytes] = []
        self.type_map: Dict[Tuple[Tuple[int, ...], Tuple[int, ...]], int] = {}
        self.import_entries: List[bytes] = []
        self.imported_func_count = 0
        self.function_types: List[int] = []
        self.export_entries: List[bytes] = []
        self.code_entries: List[bytes] = []
        self.data_entries: List[bytes] = []
        self.data_offset = 1024

    def _get_or_add_type(self, params: Tuple[int, ...], results: Tuple[int, ...]) -> int:
        key = (params, results)
        if key in self.type_map:
            return self.type_map[key]
        idx = len(self.type_entries)
        entry = bytearray([0x60])
        entry.extend(encode_vector([bytes([p]) for p in params]))
        entry.extend(encode_vector([bytes([r]) for r in results]))
        self.type_entries.append(bytes(entry))
        self.type_map[key] = idx
        return idx

    def _add_import(self, mod: str, field_name: str, params: Tuple[int, ...], results: Tuple[int, ...]) -> int:
        type_idx = self._get_or_add_type(params, results)
        imp = bytearray()
        imp.extend(encode_string(mod))
        imp.extend(encode_string(field_name))
        imp.append(0x00)  # import kind: func
        imp.extend(encode_uleb128(type_idx))
        self.import_entries.append(bytes(imp))
        idx = self.imported_func_count
        self.imported_func_count += 1
        return idx

    def encode(self) -> bytes:
        # 1. Register Host Browser Runtime Imports
        import_map = {
            "print_i64": self._add_import("env", "print_i64", (VAL_I64,), ()),
            "print_f64": self._add_import("env", "print_f64", (VAL_F64,), ()),
            "print_str": self._add_import("env", "print_str", (VAL_I32, VAL_I32), ()),
            "arx_canvas_set_pixel": self._add_import("env", "arx_canvas_set_pixel", (VAL_I32, VAL_I32, VAL_I32, VAL_I32, VAL_I32), ()),
            "arx_canvas_fill_rect": self._add_import("env", "arx_canvas_fill_rect", (VAL_I32, VAL_I32, VAL_I32, VAL_I32, VAL_I32, VAL_I32, VAL_I32), ()),
            "arx_canvas_clear": self._add_import("env", "arx_canvas_clear", (VAL_I32, VAL_I32, VAL_I32), ()),
            "arx_now_ms": self._add_import("env", "arx_now_ms", (), (VAL_F64,)),
        }

        # 2. Extract Data Segments (String Literals)
        string_constants: Dict[str, Tuple[int, int]] = {}
        for fn in self.air.functions.values():
            for insn in fn.instructions:
                if isinstance(insn, AIRConst) and insn.type_name in ("str", "string") and isinstance(insn.value, str):
                    if insn.value not in string_constants:
                        encoded = insn.value.encode("utf-8")
                        offset = self.data_offset
                        string_constants[insn.value] = (offset, len(encoded))
                        
                        # WASM Data Segment
                        data_seg = bytearray([0x00])  # active segment, memory 0
                        data_seg.extend([0x41] + list(encode_sleb128(offset)) + [0x0B])  # i32.const offset, end
                        data_seg.extend(encode_string(insn.value))
                        self.data_entries.append(bytes(data_seg))
                        self.data_offset += len(encoded) + 1

        # 3. Index Defined Functions
        fn_indices: Dict[str, int] = {}
        for fn_name, fn in self.air.functions.items():
            func_idx = self.imported_func_count + len(self.function_types)
            fn_indices[fn_name] = func_idx

            # Build signature
            params = tuple(VAL_F64 if p in ("f64", "f32") else VAL_I64 for p in fn.param_types)
            if fn.return_type and fn.return_type != "void":
                results = (VAL_F64 if fn.return_type in ("f64", "f32") else VAL_I64,)
            elif fn_name == "main":
                results = (VAL_I32,)
            else:
                results = ()

            t_idx = self._get_or_add_type(params, results)
            self.function_types.append(t_idx)

            # Export main or public functions
            if fn_name == "main" or fn.is_pub:
                exp = bytearray()
                exp.extend(encode_string(fn_name))
                exp.append(0x00)  # Export kind: func
                exp.extend(encode_uleb128(func_idx))
                self.export_entries.append(bytes(exp))

        # Export memory
        mem_exp = bytearray()
        mem_exp.extend(encode_string("memory"))
        mem_exp.append(0x02)  # Export kind: memory
        mem_exp.extend(encode_uleb128(0))  # memory index 0
        self.export_entries.append(bytes(mem_exp))

        # 4. Generate Function Bodies
        for fn_name, fn in self.air.functions.items():
            code_bytes = self._encode_function(fn, fn_indices, import_map, string_constants)
            self.code_entries.append(code_bytes)

        # 5. Assemble Sections into Final WASM Module
        out = bytearray(b"\x00asm\x01\x00\x00\x00")  # WASM Magic & Version 1

        # Section 1: Types
        if self.type_entries:
            sec_payload = encode_vector(self.type_entries)
            out.append(SEC_TYPE)
            out.extend(encode_uleb128(len(sec_payload)))
            out.extend(sec_payload)

        # Section 2: Imports
        if self.import_entries:
            sec_payload = encode_vector(self.import_entries)
            out.append(SEC_IMPORT)
            out.extend(encode_uleb128(len(sec_payload)))
            out.extend(sec_payload)

        # Section 3: Functions
        if self.function_types:
            sec_payload = encode_vector([encode_uleb128(t) for t in self.function_types])
            out.append(SEC_FUNCTION)
            out.extend(encode_uleb128(len(sec_payload)))
            out.extend(sec_payload)

        # Section 5: Memory (1 initial page = 64KB)
        mem_payload = encode_vector([bytes([0x00, 0x01])])  # flags=0 (no max), initial=1
        out.append(SEC_MEMORY)
        out.extend(encode_uleb128(len(mem_payload)))
        out.extend(mem_payload)

        # Section 7: Exports
        if self.export_entries:
            sec_payload = encode_vector(self.export_entries)
            out.append(SEC_EXPORT)
            out.extend(encode_uleb128(len(sec_payload)))
            out.extend(sec_payload)

        # Section 10: Code
        if self.code_entries:
            sec_payload = encode_vector(self.code_entries)
            out.append(SEC_CODE)
            out.extend(encode_uleb128(len(sec_payload)))
            out.extend(sec_payload)

        # Section 11: Data
        if self.data_entries:
            sec_payload = encode_vector(self.data_entries)
            out.append(SEC_DATA)
            out.extend(encode_uleb128(len(sec_payload)))
            out.extend(sec_payload)

        return bytes(out)

    def _encode_instruction(
        self,
        insn: AIRInstruction,
        body: bytearray,
        local_indices: Dict[str, int],
        var_types: Dict[str, str],
        string_constants: Dict[str, Tuple[int, int]],
        fn_indices: Dict[str, int],
        import_map: Dict[str, int],
        is_main: bool
    ) -> None:
        if isinstance(insn, AIRConst):
            dest_idx = local_indices[insn.dest]
            if insn.type_name in ("f64", "f32"):
                body.append(0x44)  # f64.const
                body.extend(struct.pack("<d", float(insn.value)))
            elif insn.type_name in ("str", "string") and isinstance(insn.value, str):
                offset, length = string_constants.get(insn.value, (1024, len(insn.value)))
                packed = (length << 32) | offset
                body.append(0x42)  # i64.const
                body.extend(encode_sleb128(packed))
            else:
                val = 1 if insn.value is True else (0 if insn.value is False else int(insn.value))
                body.append(0x42)  # i64.const
                body.extend(encode_sleb128(val))
            body.append(0x21)  # local.set
            body.extend(encode_uleb128(dest_idx))

        elif isinstance(insn, AIRAssign):
            body.append(0x20)  # local.get
            body.extend(encode_uleb128(local_indices[insn.src]))
            body.append(0x21)  # local.set
            body.extend(encode_uleb128(local_indices[insn.dest]))

        elif isinstance(insn, AIRLoad):
            body.append(0x20)  # local.get
            body.extend(encode_uleb128(local_indices[insn.var_name]))
            body.append(0x21)  # local.set
            body.extend(encode_uleb128(local_indices[insn.dest]))

        elif isinstance(insn, AIRStore):
            body.append(0x20)  # local.get
            body.extend(encode_uleb128(local_indices[insn.src]))
            body.append(0x21)  # local.set
            body.extend(encode_uleb128(local_indices[insn.var_name]))

        elif isinstance(insn, AIRBinOp):
            is_f64 = var_types.get(insn.dest) in ("f64", "f32")
            body.append(0x20)  # local.get left
            body.extend(encode_uleb128(local_indices[insn.left]))
            body.append(0x20)  # local.get right
            body.extend(encode_uleb128(local_indices[insn.right]))
            
            # Opcode
            if is_f64:
                f64_ops = {
                    "+": 0xA0, "-": 0xA1, "*": 0xA2, "/": 0xA3,
                    "==": 0x61, "!=": 0x62, "<": 0x63, "<=": 0x65,
                    ">": 0x64, ">=": 0x66
                }
                body.append(f64_ops.get(insn.op, 0xA0))
            else:
                i64_ops = {
                    "+": 0x7C, "-": 0x7D, "*": 0x7E, "/": 0x7F, "%": 0x81,
                    "==": 0x51, "!=": 0x52, "<": 0x53, "<=": 0x57,
                    ">": 0x55, ">=": 0x59, "&&": 0x83, "||": 0x84
                }
                body.append(i64_ops.get(insn.op, 0x7C))
            
            if insn.op in ("==", "!=", "<", "<=", ">", ">="):
                dest_type = var_types.get(insn.dest, "i64")
                if dest_type in ("i64", "int"):
                    body.append(0xAD)  # i64.extend_i32_u
            
            body.append(0x21)  # local.set dest
            body.extend(encode_uleb128(local_indices[insn.dest]))

        elif isinstance(insn, AIRCall):
            target = insn.fn_name
            if target in ("print", "println"):
                for arg in insn.args:
                    arg_idx = local_indices[arg]
                    arg_type = var_types.get(arg, "i64")
                    if arg_type in ("str", "string"):
                        body.append(0x20)  # local.get
                        body.extend(encode_uleb128(arg_idx))
                        body.append(0xA7)  # i32.wrap_i64
                        body.append(0x20)  # local.get
                        body.extend(encode_uleb128(arg_idx))
                        body.append(0x42)  # i64.const 32
                        body.extend(encode_sleb128(32))
                        body.append(0x88)  # i64.shr_u
                        body.append(0xA7)  # i32.wrap_i64
                        body.append(0x10)  # call print_str
                        body.extend(encode_uleb128(import_map["print_str"]))
                    elif arg_type in ("f64", "f32"):
                        body.append(0x20)  # local.get
                        body.extend(encode_uleb128(arg_idx))
                        body.append(0x10)  # call print_f64
                        body.extend(encode_uleb128(import_map["print_f64"]))
                    else:
                        body.append(0x20)  # local.get
                        body.extend(encode_uleb128(arg_idx))
                        body.append(0x10)  # call print_i64
                        body.extend(encode_uleb128(import_map["print_i64"]))

            elif target.startswith("arx_canvas_") and target in import_map:
                for arg in insn.args:
                    body.append(0x20)  # local.get
                    body.extend(encode_uleb128(local_indices[arg]))
                    body.append(0xA7)  # i32.wrap_i64
                body.append(0x10)  # call import
                body.extend(encode_uleb128(import_map[target]))

            elif target in fn_indices:
                for arg in insn.args:
                    body.append(0x20)  # local.get
                    body.extend(encode_uleb128(local_indices[arg]))
                body.append(0x10)  # call
                body.extend(encode_uleb128(fn_indices[target]))
                if insn.dest:
                    body.append(0x21)  # local.set
                    body.extend(encode_uleb128(local_indices[insn.dest]))

        elif isinstance(insn, AIRReturn):
            if insn.value:
                body.append(0x20)  # local.get
                body.extend(encode_uleb128(local_indices[insn.value]))
            elif is_main:
                body.append(0x41)  # i32.const 0
                body.extend(encode_sleb128(0))
            body.append(0x0F)  # return

    def _encode_function(
        self,
        fn: AIRFunction,
        fn_indices: Dict[str, int],
        import_map: Dict[str, int],
        string_constants: Dict[str, Tuple[int, int]]
    ) -> bytes:
        is_main = fn.name == "main"
        var_types = infer_function_variable_types(fn)
        blocks, label_to_block = partition_into_basic_blocks(fn)
        has_branches = len(blocks) > 1
        
        # Build local index mapping
        local_indices: Dict[str, int] = {}
        for i, p in enumerate(fn.params):
            local_indices[p] = i

        declared_locals: List[Tuple[str, int]] = []
        for insn in fn.instructions:
            if hasattr(insn, "dest") and insn.dest and insn.dest not in local_indices:
                vtype = var_types.get(insn.dest, "i64")
                wtype = VAL_F64 if vtype in ("f64", "f32") else VAL_I64
                local_indices[insn.dest] = len(local_indices)
                declared_locals.append((insn.dest, wtype))
            if isinstance(insn, (AIRStore, AIRLoad)):
                name = insn.var_name
                if name not in local_indices:
                    vtype = var_types.get(name, "i64")
                    wtype = VAL_F64 if vtype in ("f64", "f32") else VAL_I64
                    local_indices[name] = len(local_indices)
                    declared_locals.append((name, wtype))

        pc_idx = None
        if has_branches:
            pc_idx = len(local_indices)
            local_indices["_pc"] = pc_idx
            declared_locals.append(("_pc", VAL_I32))

        body = bytearray()

        # Locals header
        locals_vec = encode_vector([encode_uleb128(1) + bytes([wtype]) for _, wtype in declared_locals])
        body.extend(locals_vec)

        if not has_branches:
            # Straight-line code
            for insn in fn.instructions:
                self._encode_instruction(insn, body, local_indices, var_types, string_constants, fn_indices, import_map, is_main)
            if is_main and not any(isinstance(i, AIRReturn) for i in fn.instructions):
                body.append(0x41)  # i32.const 0
                body.extend(encode_sleb128(0))
                body.append(0x0F)  # return
        else:
            # Block dispatcher loop
            body.append(0x02)  # block $exit
            body.append(VAL_VOID)
            body.append(0x03)  # loop $dispatch
            body.append(VAL_VOID)

            for b_idx, (b_insns, term) in enumerate(blocks):
                # if ($pc == b_idx)
                body.append(0x20)  # local.get $pc
                body.extend(encode_uleb128(pc_idx))
                body.append(0x41)  # i32.const b_idx
                body.extend(encode_sleb128(b_idx))
                body.append(0x46)  # i32.eq
                body.append(0x04)  # if
                body.append(VAL_VOID)

                for insn in b_insns:
                    if not isinstance(insn, (AIRBranchIf, AIRBranchIfNot, AIRJump, AIRReturn)):
                        self._encode_instruction(insn, body, local_indices, var_types, string_constants, fn_indices, import_map, is_main)

                # Terminator
                if isinstance(term, AIRReturn):
                    self._encode_instruction(term, body, local_indices, var_types, string_constants, fn_indices, import_map, is_main)
                elif isinstance(term, AIRJump):
                    target_idx = label_to_block.get(term.target_label, b_idx + 1)
                    body.append(0x41)  # i32.const target_idx
                    body.extend(encode_sleb128(target_idx))
                    body.append(0x21)  # local.set $pc
                    body.extend(encode_uleb128(pc_idx))
                    body.append(0x0C)  # br $dispatch (depth 1)
                    body.extend(encode_uleb128(1))
                elif isinstance(term, AIRBranchIf):
                    cond_idx = local_indices[term.condition]
                    target_idx = label_to_block.get(term.target_label, b_idx + 1)
                    fallthrough_idx = b_idx + 1
                    body.append(0x20)  # local.get cond
                    body.extend(encode_uleb128(cond_idx))
                    body.append(0x50)  # i64.eqz
                    body.append(0x04)  # if
                    body.append(VAL_VOID)
                    # then (cond == 0 -> fallthrough)
                    body.append(0x41)  # i32.const fallthrough_idx
                    body.extend(encode_sleb128(fallthrough_idx))
                    body.append(0x21)  # local.set $pc
                    body.extend(encode_uleb128(pc_idx))
                    body.append(0x0C)  # br $dispatch (depth 2)
                    body.extend(encode_uleb128(2))
                    body.append(0x05)  # else (cond != 0 -> target)
                    body.append(0x41)  # i32.const target_idx
                    body.extend(encode_sleb128(target_idx))
                    body.append(0x21)  # local.set $pc
                    body.extend(encode_uleb128(pc_idx))
                    body.append(0x0C)  # br $dispatch (depth 2)
                    body.extend(encode_uleb128(2))
                    body.append(0x0B)  # end if
                elif isinstance(term, AIRBranchIfNot):
                    cond_idx = local_indices[term.condition]
                    target_idx = label_to_block.get(term.target_label, b_idx + 1)
                    fallthrough_idx = b_idx + 1
                    body.append(0x20)  # local.get cond
                    body.extend(encode_uleb128(cond_idx))
                    body.append(0x50)  # i64.eqz
                    body.append(0x04)  # if
                    body.append(VAL_VOID)
                    # then (cond == 0 -> target)
                    body.append(0x41)  # i32.const target_idx
                    body.extend(encode_sleb128(target_idx))
                    body.append(0x21)  # local.set $pc
                    body.extend(encode_uleb128(pc_idx))
                    body.append(0x0C)  # br $dispatch (depth 2)
                    body.extend(encode_uleb128(2))
                    body.append(0x05)  # else (cond != 0 -> fallthrough)
                    body.append(0x41)  # i32.const fallthrough_idx
                    body.extend(encode_sleb128(fallthrough_idx))
                    body.append(0x21)  # local.set $pc
                    body.extend(encode_uleb128(pc_idx))
                    body.append(0x0C)  # br $dispatch (depth 2)
                    body.extend(encode_uleb128(2))
                    body.append(0x0B)  # end if
                else:
                    if b_idx + 1 < len(blocks):
                        body.append(0x41)  # i32.const b_idx + 1
                        body.extend(encode_sleb128(b_idx + 1))
                        body.append(0x21)  # local.set $pc
                        body.extend(encode_uleb128(pc_idx))
                        body.append(0x0C)  # br $dispatch (depth 1)
                        body.extend(encode_uleb128(1))
                    else:
                        body.append(0x0C)  # br $exit (depth 2)
                        body.extend(encode_uleb128(2))

                body.append(0x0B)  # end if

            body.append(0x0B)  # end loop $dispatch
            body.append(0x0B)  # end block $exit

            ret_t = fn.return_type
            if ret_t in ("f64", "f32"):
                body.append(0x44)  # f64.const 0.0
                body.extend(struct.pack("<d", 0.0))
                body.append(0x0F)  # return
            elif ret_t and ret_t != "void":
                body.append(0x42)  # i64.const 0
                body.extend(encode_sleb128(0))
                body.append(0x0F)  # return
            elif is_main:
                body.append(0x41)  # i32.const 0
                body.extend(encode_sleb128(0))
                body.append(0x0F)  # return

        body.append(0x0B)  # end opcode of function

        # Return length-prefixed function body
        return encode_uleb128(len(body)) + body


# ==============================================================================
# 4. Interactive Browser Runner Page Generator
# ==============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Aerix (__MODULE_NAME__) — WebAssembly Browser Runtime</title>
  <style>
    :root {
      --bg-primary: #0a0e17;
      --bg-card: #131c2e;
      --accent: #00dcff;
      --accent-glow: rgba(0, 220, 255, 0.3);
      --text-main: #f0f6fc;
      --text-dim: #8b949e;
      --terminal-bg: #050811;
      --border-color: #212c42;
      --success: #00e676;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg-primary);
      color: var(--text-main);
      padding: 24px;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 100vh;
    }
    .header {
      text-align: center;
      margin-bottom: 24px;
    }
    .header h1 {
      font-size: 2.2rem;
      font-weight: 800;
      background: linear-gradient(135deg, #00dcff, #7c4dff);
      -webkit-background-clip: text;
      background-clip: text;
      -webkit-text-fill-color: transparent;
      letter-spacing: -0.5px;
    }
    .badge {
      display: inline-block;
      margin-top: 8px;
      padding: 4px 12px;
      border-radius: 999px;
      background: rgba(0, 220, 255, 0.15);
      border: 1px solid var(--accent);
      color: var(--accent);
      font-size: 0.85rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .container {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      width: 100%;
      max-width: 1200px;
    }
    @media (max-width: 900px) {
      .container { grid-template-columns: 1fr; }
    }
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
      display: flex;
      flex-direction: column;
    }
    .card h2 {
      font-size: 1.15rem;
      margin-bottom: 14px;
      color: var(--accent);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    #canvas-container {
      display: flex;
      justify-content: center;
      align-items: center;
      background: #000;
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid var(--border-color);
    }
    canvas {
      display: block;
      background-color: #000;
    }
    #terminal {
      background: var(--terminal-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      font-family: "Cascadia Code", "Fira Code", Consolas, monospace;
      font-size: 0.9rem;
      color: #7ee787;
      padding: 16px;
      height: 380px;
      overflow-y: auto;
      white-space: pre-wrap;
      line-height: 1.5;
    }
    .status-bar {
      margin-top: 14px;
      display: flex;
      justify-content: space-between;
      color: var(--text-dim);
      font-size: 0.85rem;
    }
    .btn {
      margin-top: 14px;
      padding: 10px 20px;
      background: linear-gradient(135deg, #00dcff, #00a0dc);
      border: none;
      border-radius: 6px;
      color: #000;
      font-weight: 700;
      font-size: 0.95rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn:hover {
      transform: translateY(-1px);
      box-shadow: 0 4px 16px var(--accent-glow);
    }
  </style>
</head>
<body>

  <div class="header">
    <h1>Aerix WebAssembly Browser Runtime</h1>
    <span class="badge">WASM Target • Phase 20 • 60 FPS Native Web Speed</span>
  </div>

  <div class="container">
    <!-- Left Panel: Interactive Canvas -->
    <div class="card">
      <h2>🎨 Hardware-Accelerated 2D Canvas</h2>
      <div id="canvas-container">
        <canvas id="aerix-canvas" width="480" height="380"></canvas>
      </div>
      <div class="status-bar">
        <span>Target: <b>__WASM_FILENAME__</b></span>
        <span id="canvas-status">Resolution: 480x380</span>
      </div>
      <button class="btn" onclick="runAerix()">⚡ Re-Run WebAssembly Module</button>
    </div>

    <!-- Right Panel: Standard Output Terminal -->
    <div class="card">
      <h2>💻 Console Output (stdout)</h2>
      <div id="terminal">Initializing Aerix WebAssembly engine...\n</div>
      <div class="status-bar">
        <span id="exec-time">Execution: 0.00 ms</span>
        <span style="color: var(--success);" id="engine-status">● Engine Standby</span>
      </div>
    </div>
  </div>

  <script>
    const term = document.getElementById("terminal");
    const canvas = document.getElementById("aerix-canvas");
    const ctx = canvas.getContext("2d");
    let wasmInstance = null;

    function log(msg) {
      term.textContent += msg + "\\n";
      term.scrollTop = term.scrollHeight;
    }

    function createImportObject() {
      return {
        env: {
          print_i64: (val) => log(val.toString()),
          print_f64: (val) => log(val.toFixed(6)),
          print_str: (offset, length) => {
            if (!wasmInstance) return;
            const bytes = new Uint8Array(wasmInstance.exports.memory.buffer, offset, length);
            const str = new TextDecoder("utf-8").decode(bytes);
            log(str);
          },
          arx_canvas_set_pixel: (x, y, r, g, b) => {
            ctx.fillStyle = `rgb(${r},${g},${b})`;
            ctx.fillRect(x, y, 1, 1);
          },
          arx_canvas_fill_rect: (x, y, w, h, r, g, b) => {
            ctx.fillStyle = `rgb(${r},${g},${b})`;
            ctx.fillRect(x, y, w, h);
          },
          arx_canvas_clear: (r, g, b) => {
            ctx.fillStyle = `rgb(${r},${g},${b})`;
            ctx.fillRect(0, 0, canvas.width, canvas.height);
          },
          arx_now_ms: () => performance.now()
        }
      };
    }

    async function runAerix() {
      term.textContent = "";
      log("[AERIX RUNNER] Loading WebAssembly binary '__WASM_FILENAME__'...");
      const t0 = performance.now();
      try {
        const response = await fetch("__WASM_FILENAME__");
        if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        const bytes = await response.arrayBuffer();
        
        let importObj = createImportObject();
        const results = await WebAssembly.instantiate(bytes, importObj);
        wasmInstance = results.instance;

        log("[AERIX RUNNER] Module instantiated successfully!");
        log("--------------------------------------------------");

        if (wasmInstance.exports.main) {
          const ret = wasmInstance.exports.main();
          log("--------------------------------------------------");
          log(`[EXIT CODE]: ${ret}`);
        }

        const t1 = performance.now();
        document.getElementById("exec-time").textContent = `Execution: ${(t1 - t0).toFixed(2)} ms`;
        document.getElementById("engine-status").textContent = "● Completed OK";
        document.getElementById("engine-status").style.color = "var(--success)";
      } catch (err) {
        log(`\\n[FATAL ERROR]: ${err.message}`);
        document.getElementById("engine-status").textContent = "● Failed";
        document.getElementById("engine-status").style.color = "#ff5252";
      }
    }

    window.addEventListener("DOMContentLoaded", runAerix);
  </script>
</body>
</html>
"""

def generate_browser_runner_html(module_name: str, wasm_filename: str) -> str:
    """Generates the interactive HTML5 browser runner page for WebAssembly execution."""
    return HTML_TEMPLATE.replace("__MODULE_NAME__", module_name).replace("__WASM_FILENAME__", wasm_filename)
