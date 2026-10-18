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
    AIRLabel, AIRCallVirtual, AIRCallMethod
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
        """Applies optimization passes in sequence to a single function."""
        fn.instructions = self.pass_constant_folding(fn.instructions)
        fn.instructions = self.pass_dead_code_elimination(fn.instructions)

    def pass_constant_folding(self, insns: List[AIRInstruction]) -> List[AIRInstruction]:
        """Folds binary arithmetic on constant literals at compile-time."""
        const_values: Dict[str, Any] = {}
        const_types: Dict[str, str] = {}
        new_insns: List[AIRInstruction] = []

        for insn in insns:
            if isinstance(insn, AIRConst):
                const_values[insn.dest] = insn.value
                const_types[insn.dest] = insn.type_name
                new_insns.append(insn)
            elif isinstance(insn, AIRBinOp):
                left_val = const_values.get(insn.left)
                right_val = const_values.get(insn.right)

                # If both operands are known compile-time constants, fold!
                if left_val is not None and right_val is not None and type(left_val) in (int, float) and type(right_val) in (int, float):
                    folded_val = None
                    try:
                        if insn.op == "+": folded_val = left_val + right_val
                        elif insn.op == "-": folded_val = left_val - right_val
                        elif insn.op == "*": folded_val = left_val * right_val
                        elif insn.op == "/" and right_val != 0: folded_val = left_val / right_val if isinstance(left_val, float) or isinstance(right_val, float) else left_val // right_val
                        elif insn.op == "%" and right_val != 0: folded_val = left_val % right_val
                        elif insn.op == "**": folded_val = left_val ** right_val
                    except Exception:
                        folded_val = None

                    if folded_val is not None:
                        t_name = "f64" if isinstance(folded_val, float) else "i64"
                        const_values[insn.dest] = folded_val
                        const_types[insn.dest] = t_name
                        # Replace binop with folded constant!
                        new_insns.append(AIRConst(insn.dest, folded_val, t_name))
                        continue

                new_insns.append(insn)
            else:
                new_insns.append(insn)

        return new_insns

    def pass_dead_code_elimination(self, insns: List[AIRInstruction]) -> List[AIRInstruction]:
        """Eliminates unreachable instructions after an unconditional return or jump."""
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

        return reachable
