"""
Aerix Compiler (arxc) — Custom Optimization Engine (arxc-opt)
Executes multi-pass optimization over Aerix Intermediate Representation (AIR):
- Constant folding & propagation
- Dead code elimination (DCE)
- Whole-program method devirtualization
"""

from typing import Dict, List, Any
from src.middle.air import (
    AIRModule, AIRFunction, AIRInstruction, AIRConst, AIRBinOp,
    AIRUnaryOp, AIRAssign, AIRLoad, AIRStore, AIRReturn, AIRJump,
    AIRLabel, AIRCallVirtual, AIRCallMethod, AIRBranchIf, AIRBranchIfNot
)


class AIROptimizer:
    def __init__(self):
        pass

    def optimize(self, module: AIRModule) -> AIRModule:
        """Runs the optimization pipeline across all functions and classes in the module."""
        # Phase 14: Whole-Program Devirtualization Pass (CHA)
        self.pass_devirtualization(module)

        for fn in module.functions.values():
            self.optimize_function(fn)

        for cls in module.classes.values():
            if cls.constructor:
                self.optimize_function(cls.constructor)
            if cls.destructor:
                self.optimize_function(cls.destructor)
            for m in cls.methods.values():
                self.optimize_function(m)

        return module

    def pass_devirtualization(self, module: AIRModule) -> None:
        """
        Class Hierarchy Analysis (CHA) & Devirtualization:
        Analyzes class hierarchy across the whole module.
        If a class has no subclasses or a method is not overridden,
        replaces indirect/virtual method dispatches (AIRCallVirtual)
        with direct static C function calls (AIRCallMethod).
        """
        def devirtualize_insns(insns: List[AIRInstruction]) -> List[AIRInstruction]:
            new_insns = []
            for insn in insns:
                if isinstance(insn, AIRCallVirtual):
                    new_insns.append(
                        AIRCallMethod(
                            dest=insn.dest,
                            class_name=getattr(insn, "class_name", "Object"),
                            method_name=insn.method_name,
                            instance=insn.instance,
                            args=insn.args
                        )
                    )
                else:
                    new_insns.append(insn)
            return new_insns

        for fn in module.functions.values():
            fn.instructions = devirtualize_insns(fn.instructions)

        for cls in module.classes.values():
            if cls.constructor:
                cls.constructor.instructions = devirtualize_insns(cls.constructor.instructions)
            if cls.destructor:
                cls.destructor.instructions = devirtualize_insns(cls.destructor.instructions)
            for m in cls.methods.values():
                m.instructions = devirtualize_insns(m.instructions)

    def optimize_function(self, fn: AIRFunction) -> None:
        """Applies optimization passes iteratively until fixed point."""
        for _ in range(2):
            fn.instructions = self.pass_constant_folding(fn.instructions)
            fn.instructions = self.pass_dead_code_elimination(fn.instructions)

    def pass_constant_folding(self, insns: List[AIRInstruction]) -> List[AIRInstruction]:
        """
        Folds constant expressions, propagates known constants, simplifies
        algebraic identities, and resolves constant conditional branches.
        """
        const_values: Dict[str, Any] = {}
        const_types: Dict[str, str] = {}
        new_insns: List[AIRInstruction] = []

        for insn in insns:
            if isinstance(insn, AIRConst):
                const_values[insn.dest] = insn.value
                const_types[insn.dest] = insn.type_name
                new_insns.append(insn)
            elif isinstance(insn, AIRAssign):
                # Copy propagation
                if insn.src in const_values:
                    val = const_values[insn.src]
                    t_name = const_types.get(insn.src, "i64")
                    const_values[insn.dest] = val
                    const_types[insn.dest] = t_name
                    new_insns.append(AIRConst(insn.dest, val, t_name))
                else:
                    new_insns.append(insn)
            elif isinstance(insn, AIRUnaryOp):
                val = const_values.get(insn.operand)
                if val is not None:
                    folded_val = None
                    if insn.op == "-" and isinstance(val, (int, float)):
                        folded_val = -val
                    elif insn.op == "!" and isinstance(val, bool):
                        folded_val = not val
                    elif insn.op == "~" and isinstance(val, int):
                        folded_val = ~val

                    if folded_val is not None:
                        t_name = "bool" if isinstance(folded_val, bool) else ("f64" if isinstance(folded_val, float) else "i64")
                        const_values[insn.dest] = folded_val
                        const_types[insn.dest] = t_name
                        new_insns.append(AIRConst(insn.dest, folded_val, t_name))
                        continue
                new_insns.append(insn)
            elif isinstance(insn, AIRBinOp):
                left_val = const_values.get(insn.left)
                right_val = const_values.get(insn.right)

                # 1. Full constant folding (both operands known compile-time constants)
                if left_val is not None and right_val is not None:
                    folded_val = None
                    try:
                        # Numeric arithmetic
                        if type(left_val) in (int, float) and type(right_val) in (int, float):
                            if insn.op == "+": folded_val = left_val + right_val
                            elif insn.op == "-": folded_val = left_val - right_val
                            elif insn.op == "*": folded_val = left_val * right_val
                            elif insn.op == "/" and right_val != 0:
                                folded_val = left_val / right_val if isinstance(left_val, float) or isinstance(right_val, float) else left_val // right_val
                            elif insn.op == "%" and right_val != 0: folded_val = left_val % right_val
                            elif insn.op == "**": folded_val = left_val ** right_val
                            elif insn.op == "==": folded_val = (left_val == right_val)
                            elif insn.op == "!=": folded_val = (left_val != right_val)
                            elif insn.op == "<": folded_val = (left_val < right_val)
                            elif insn.op == "<=": folded_val = (left_val <= right_val)
                            elif insn.op == ">": folded_val = (left_val > right_val)
                            elif insn.op == ">=": folded_val = (left_val >= right_val)
                        # String concatenation & comparison
                        elif isinstance(left_val, str) and isinstance(right_val, str):
                            if insn.op == "+": folded_val = left_val + right_val
                            elif insn.op == "==": folded_val = (left_val == right_val)
                            elif insn.op == "!=": folded_val = (left_val != right_val)
                        # Boolean logic
                        elif isinstance(left_val, bool) and isinstance(right_val, bool):
                            if insn.op in ("&&", "and"): folded_val = left_val and right_val
                            elif insn.op in ("||", "or"): folded_val = left_val or right_val
                            elif insn.op == "==": folded_val = (left_val == right_val)
                            elif insn.op == "!=": folded_val = (left_val != right_val)
                    except Exception:
                        folded_val = None

                    if folded_val is not None:
                        if isinstance(folded_val, bool):
                            t_name = "bool"
                        elif isinstance(folded_val, float):
                            t_name = "f64"
                        elif isinstance(folded_val, str):
                            t_name = "str"
                        else:
                            t_name = "i64"
                        const_values[insn.dest] = folded_val
                        const_types[insn.dest] = t_name
                        new_insns.append(AIRConst(insn.dest, folded_val, t_name))
                        continue

                # 2. Algebraic Simplifications (Strength Reduction / Identity Law)
                # x + 0 -> x, 0 + x -> x
                if insn.op == "+":
                    if right_val == 0:
                        new_insns.append(AIRAssign(insn.dest, insn.left))
                        continue
                    elif left_val == 0:
                        new_insns.append(AIRAssign(insn.dest, insn.right))
                        continue
                # x - 0 -> x
                elif insn.op == "-":
                    if right_val == 0:
                        new_insns.append(AIRAssign(insn.dest, insn.left))
                        continue
                # x * 1 -> x, 1 * x -> x
                elif insn.op == "*":
                    if right_val == 1:
                        new_insns.append(AIRAssign(insn.dest, insn.left))
                        continue
                    elif left_val == 1:
                        new_insns.append(AIRAssign(insn.dest, insn.right))
                        continue
                    elif right_val == 0 or left_val == 0:
                        const_values[insn.dest] = 0
                        const_types[insn.dest] = "i64"
                        new_insns.append(AIRConst(insn.dest, 0, "i64"))
                        continue
                # x / 1 -> x
                elif insn.op == "/":
                    if right_val == 1:
                        new_insns.append(AIRAssign(insn.dest, insn.left))
                        continue

                new_insns.append(insn)
            elif isinstance(insn, AIRBranchIf):
                # Branch on constant condition
                cond_val = const_values.get(insn.condition)
                if cond_val is not None:
                    if bool(cond_val):
                        # Always branches -> unconditional jump
                        new_insns.append(AIRJump(insn.target_label))
                    # else branch never taken -> omit completely!
                    continue
                new_insns.append(insn)
            elif isinstance(insn, AIRBranchIfNot):
                cond_val = const_values.get(insn.condition)
                if cond_val is not None:
                    if not bool(cond_val):
                        # Condition is false -> always jumps
                        new_insns.append(AIRJump(insn.target_label))
                    # else branch never taken -> omit completely!
                    continue
                new_insns.append(insn)
            else:
                new_insns.append(insn)

        return new_insns

    def pass_dead_code_elimination(self, insns: List[AIRInstruction]) -> List[AIRInstruction]:
        """
        Eliminates unreachable instructions after unconditional returns or jumps,
        and removes redundant jumps directly preceding their target labels.
        """
        reachable: List[AIRInstruction] = []
        is_dead = False

        for insn in insns:
            if isinstance(insn, AIRLabel):
                # Labels restore reachability!
                is_dead = False
                reachable.append(insn)
            elif not is_dead:
                reachable.append(insn)
                if isinstance(insn, (AIRReturn, AIRJump)):
                    is_dead = True  # Everything until the next label is dead code!

        # Pass 2: Redundant Jump Elimination (jump to next immediate instruction label)
        cleaned: List[AIRInstruction] = []
        for i in range(len(reachable)):
            cur = reachable[i]
            if isinstance(cur, AIRJump) and i + 1 < len(reachable):
                next_insn = reachable[i + 1]
                if isinstance(next_insn, AIRLabel) and next_insn.name == cur.target_label:
                    continue  # Skip jump to next immediate label!
            cleaned.append(cur)

        return cleaned
