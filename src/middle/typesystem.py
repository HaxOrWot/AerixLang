"""
Aerix Compiler (arxc) — Static Type System
Defines static types, primitive aliases, class types, and type inference rules.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple


class Type:
    """Base class for all Aerix types."""
    def __init__(self, name: str):
        self.name = name

    def is_assignable_to(self, target: "Type") -> bool:
        if self.name == target.name:
            return True
        if self.name == "null" and isinstance(target, OptionalType):
            return True
        return False

    def __repr__(self) -> str:
        return self.name

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Type):
            return self.name == other.name
        return False


class PrimitiveType(Type):
    def __init__(self, name: str, size_bytes: int):
        super().__init__(name)
        self.size_bytes = size_bytes

    def is_numeric(self) -> bool:
        return self.name in (
            "i8", "i16", "i32", "i64", "int",
            "u8", "u16", "u32", "u64", "uint",
            "usize", "isize",
            "f32", "f64"
        )

    def is_integer(self) -> bool:
        return self.name in (
            "i8", "i16", "i32", "i64", "int",
            "u8", "u16", "u32", "u64", "uint",
            "usize", "isize"
        )

    def is_float(self) -> bool:
        return self.name in ("f32", "f64")

    def is_assignable_to(self, target: Type) -> bool:
        if self.name == target.name:
            return True
        if isinstance(target, PrimitiveType):
            if self.is_integer() and target.is_integer():
                return True
            if self.is_float() and target.is_float():
                return True
        if isinstance(target, OptionalType):
            return self.is_assignable_to(target.inner)
        return False


class OptionalType(Type):
    def __init__(self, inner: Type):
        super().__init__(f"{inner.name}?")
        self.inner = inner

    def is_assignable_to(self, target: Type) -> bool:
        if isinstance(target, OptionalType):
            return self.inner.is_assignable_to(target.inner)
        return False


class FunctionType(Type):
    def __init__(self, param_types: List[Type], return_type: Type):
        params_str = ", ".join(p.name for p in param_types)
        super().__init__(f"fn({params_str}) -> {return_type.name}")
        self.param_types = param_types
        self.return_type = return_type

    def is_assignable_to(self, target: Type) -> bool:
        if self.name == target.name:
            return True
        if isinstance(target, FunctionType):
            if len(self.param_types) != len(target.param_types):
                return False
            for p1, p2 in zip(self.param_types, target.param_types):
                if not p2.is_assignable_to(p1):
                    return False
            return self.return_type.is_assignable_to(target.return_type)
        return False


class ClassType(Type):
    def __init__(self, name: str, base_class: Optional["ClassType"] = None, is_packed: bool = False, alignment: Optional[int] = None):
        super().__init__(name)
        self.base_class = base_class
        self.is_packed = is_packed
        self.alignment = alignment
        self.fields: Dict[str, Type] = {}
        self.field_access: Dict[str, bool] = {}  # True = pub, False = priv
        self.methods: Dict[str, FunctionType] = {}
        self.method_access: Dict[str, bool] = {}
        self.traits: List[str] = []
        self.constructor_type: Optional[FunctionType] = None
        # Aerix 2.0 Overloading & Named Constructors
        self.method_overloads: Dict[str, List[Tuple[FunctionType, bool, str, Any]]] = {}
        self.constructors: List[Tuple[FunctionType, Optional[str], str, Any]] = []
        # Phase 11: Properties and Operator Overloading
        self.properties: Dict[str, Tuple[Type, bool, bool, bool]] = {} # name -> (type, has_get, has_set, is_pub)
        self.operators: Dict[str, Tuple[Type, Type, str, Any]] = {} # op -> (param_type, return_type, mangled_name, node)

    def resolve_operator(self, op: str, right_type: Type) -> Optional[Tuple[Type, str, Any]]:
        """Resolves an overloaded operator for right_type. Returns (ret_type, mangled_name, node)."""
        if op in self.operators:
            param_t, ret_t, mangled_name, node = self.operators[op]
            if right_type.is_assignable_to(param_t):
                return ret_t, mangled_name, node
        if self.base_class:
            return self.base_class.resolve_operator(op, right_type)
        return None

    def resolve_method(self, name: str, arg_types: List[Type]) -> Optional[Tuple[FunctionType, bool, str, Any]]:
        """Resolves an overloaded method call based on arity and parameter types."""
        candidates = self.method_overloads.get(name, [])
        for fn_type, is_pub, mangled_name, node in candidates:
            if len(fn_type.param_types) == len(arg_types):
                match = True
                for arg_t, param_t in zip(arg_types, fn_type.param_types):
                    if not arg_t.is_assignable_to(param_t):
                        match = False
                        break
                if match:
                    return fn_type, is_pub, mangled_name, node
        if self.base_class:
            return self.base_class.resolve_method(name, arg_types)
        return None

    def resolve_constructor(self, arg_types: List[Type], variant: Optional[str] = None) -> Optional[Tuple[FunctionType, str, Any]]:
        """Resolves a constructor call based on variant, arity and parameter types."""
        for fn_type, v_name, mangled_name, node in self.constructors:
            if v_name == variant and len(fn_type.param_types) == len(arg_types):
                match = True
                for arg_t, param_t in zip(arg_types, fn_type.param_types):
                    if not arg_t.is_assignable_to(param_t):
                        match = False
                        break
                if match:
                    return fn_type, mangled_name, node
        return None

    def is_assignable_to(self, target: Type) -> bool:
        if self.name == target.name:
            return True
        # Check inheritance chain
        current = self.base_class
        while current:
            if current.name == target.name:
                return True
            current = current.base_class
        # Check traits
        if target.name in self.traits:
            return True
        return False


class EnumVariant:
    def __init__(self, name: str, tag: int, fields: List[Tuple[str, Type]]):
        self.name = name
        self.tag = tag
        self.fields = fields # List of (field_name, field_type)


class EnumType(Type):
    def __init__(self, name: str):
        super().__init__(name)
        self.variants: Dict[str, EnumVariant] = {}

    def get_variant(self, name: str) -> Optional[EnumVariant]:
        return self.variants.get(name)

    def is_assignable_to(self, target: Type) -> bool:
        return self.name == target.name



class TraitType(Type):
    def __init__(self, name: str):
        super().__init__(name)
        self.methods: Dict[str, FunctionType] = {}

    def is_assignable_to(self, target: Type) -> bool:
        return self.name == target.name


# --- Phase 23: Fixed-Size Stack Array Type ---
class FixedArrayType(Type):
    """
    Represents a compile-time fixed-size stack array: [T; N].
    Stored as 'FixedArray_<elem_type>_<size>' in the type string system.
    Maps directly to C99: T name[N]  (zero heap allocation).
    """
    def __init__(self, elem_type: Type, size: int):
        super().__init__(f"FixedArray_{elem_type.name}_{size}")
        self.elem_type = elem_type
        self.size = size

    def is_assignable_to(self, target: Type) -> bool:
        if isinstance(target, SliceType):
            return self.elem_type.is_assignable_to(target.elem_type)
        if isinstance(target, FixedArrayType):
            if self.size != target.size:
                return False
            if self.name == target.name:
                return True
            if isinstance(self.elem_type, PrimitiveType) and isinstance(target.elem_type, PrimitiveType):
                if self.elem_type.is_integer() and target.elem_type.is_integer():
                    return True
                if self.elem_type.is_float() and target.elem_type.is_float():
                    return True
            return self.elem_type.is_assignable_to(target.elem_type)
        return False


class SliceType(Type):
    """
    Represents a borrowed slice / view over contiguous memory: &[T] or &mut [T].
    Lowers to a fat pointer struct: { T* data; size_t len; }.
    """
    def __init__(self, elem_type: Type, is_mut: bool = False):
        mut_str = "mut_" if is_mut else ""
        super().__init__(f"Slice_{mut_str}{elem_type.name}")
        self.elem_type = elem_type
        self.is_mut = is_mut

    def is_assignable_to(self, target: Type) -> bool:
        if isinstance(target, SliceType):
            return self.elem_type.is_assignable_to(target.elem_type)
        return False


# --- Standard Primitive Singletons ---
TYPE_I8 = PrimitiveType("i8", 1)
TYPE_I16 = PrimitiveType("i16", 2)
TYPE_I32 = PrimitiveType("i32", 4)
TYPE_I64 = PrimitiveType("i64", 8)
TYPE_U8 = PrimitiveType("u8", 1)
TYPE_U16 = PrimitiveType("u16", 2)
TYPE_U32 = PrimitiveType("u32", 4)
TYPE_U64 = PrimitiveType("u64", 8)
TYPE_F32 = PrimitiveType("f32", 4)
TYPE_F64 = PrimitiveType("f64", 8)
TYPE_BOOL = PrimitiveType("bool", 1)
TYPE_CHAR = PrimitiveType("char", 1)
TYPE_STR = PrimitiveType("str", 8)
TYPE_VOID = PrimitiveType("void", 0)
TYPE_NULL = PrimitiveType("null", 8)
TYPE_USIZE = PrimitiveType("usize", 8)
TYPE_ISIZE = PrimitiveType("isize", 8)

# --- Phase 25: First-Class SIMD Vector Types ---
class SimdType(Type):
    """
    Represents a 128-bit hardware SIMD vector type: f32x4 or f64x2.
    Directly lowers to GCC/Clang vector extensions:
      typedef float  f32x4 __attribute__ ((vector_size (16)));
      typedef double f64x2 __attribute__ ((vector_size (16)));
    """
    def __init__(self, name: str, lane_type: Type, lanes: int):
        super().__init__(name)
        self.lane_type = lane_type
        self.lanes = lanes
        self.size_bytes = 16

    def is_assignable_to(self, target: Type) -> bool:
        if self.name == target.name:
            return True
        if isinstance(target, OptionalType):
            return self.is_assignable_to(target.inner)
        return False


TYPE_F32X4 = SimdType("f32x4", TYPE_F32, 4)
TYPE_F64X2 = SimdType("f64x2", TYPE_F64, 2)

PRIMITIVES: Dict[str, Type] = {
    "i8": TYPE_I8, "i16": TYPE_I16, "i32": TYPE_I32, "i64": TYPE_I64, "int": TYPE_I64,
    "u8": TYPE_U8, "u16": TYPE_U16, "u32": TYPE_U32, "u64": TYPE_U64, "uint": TYPE_U64,
    "usize": TYPE_USIZE, "isize": TYPE_ISIZE,
    "f32": TYPE_F32, "f64": TYPE_F64, "float": TYPE_F64,
    "f32x4": TYPE_F32X4, "f64x2": TYPE_F64X2,
    "bool": TYPE_BOOL, "char": TYPE_CHAR, "str": TYPE_STR,
    "void": TYPE_VOID, "null": TYPE_NULL,
}


def lookup_type(type_name: str, classes: Dict[str, Any], enums: Optional[Dict[str, Any]] = None, traits: Optional[Dict[str, Any]] = None) -> Type:
    """Resolves a type string to its concrete Type object."""
    if type_name.endswith("?"):
        base_name = type_name[:-1]
        inner_type = lookup_type(base_name, classes, enums, traits)
        return OptionalType(inner_type)
    if type_name in PRIMITIVES:
        return PRIMITIVES[type_name]
    # Phase 23: Resolve FixedArray_<elem>_<size> type strings
    if type_name.startswith("FixedArray_"):
        parts = type_name.split("_")  # ["FixedArray", elem, size]
        if len(parts) >= 3:
            try:
                size = int(parts[-1])
                elem_name = "_".join(parts[1:-1])
                elem_t = lookup_type(elem_name, classes, enums, traits)
                return FixedArrayType(elem_t, size)
            except (ValueError, IndexError):
                pass
    # Feature 3: Resolve Slice_[mut_]<elem> type strings
    if type_name.startswith("Slice_"):
        parts = type_name.split("_")
        is_mut = (len(parts) >= 3 and parts[1] == "mut")
        elem_name = "_".join(parts[2:] if is_mut else parts[1:])
        elem_t = lookup_type(elem_name, classes, enums, traits)
        return SliceType(elem_t, is_mut=is_mut)
    # Feature 5: Resolve Fn_<p1>_<p2>_to_<ret> function pointer types
    if type_name.startswith("Fn_"):
        parts = type_name[3:].split("_to_")
        if len(parts) == 2:
            param_part, ret_part = parts
            param_names = [p for p in param_part.split("_") if p]
            param_types = [lookup_type(p, classes, enums, traits) for p in param_names]
            ret_type = lookup_type(ret_part, classes, enums, traits)
            return FunctionType(param_types, ret_type)
    if type_name in classes:
        return classes[type_name]
    if enums and type_name in enums:
        return enums[type_name]
    if type_name.startswith("Tuple_"):
        tuple_cls = ClassType(type_name)
        parts = type_name[6:].split("_")
        for i, p in enumerate(parts):
            f_name = f"f{i}"
            f_type = lookup_type(p, classes, enums, traits)
            tuple_cls.fields[f_name] = f_type
            tuple_cls.field_access[f_name] = True
        classes[type_name] = tuple_cls
        return tuple_cls
    # Return placeholder type if unresolved
    return Type(type_name)



