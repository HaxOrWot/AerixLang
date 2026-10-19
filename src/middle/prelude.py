"""
Aerix Compiler (arxc) — Standard Prelude Declarations (Phase 21)
Defines built-in standard templates and classes: List<T>, String.
"""

from typing import Optional
from src.frontend.lexer import Lexer
from src.frontend.parser import Parser
from src.frontend.ast_nodes import ProgramNode, ClassDefNode

PRELUDE_CODE = """
class List<T> {
    pub data_handle: i64
    pub length: i64
    pub capacity: i64

    init() {
        self.capacity = 4
        self.length = 0
        self.data_handle = arx_list_new(4)
    }

    pub fn push(val: T) {
        arx_list_push(self.data_handle, val as i64)
        self.length = arx_list_len(self.data_handle)
    }

    pub fn pop() -> T {
        let val = arx_list_pop(self.data_handle)
        self.length = arx_list_len(self.data_handle)
        return val as T
    }

    pub fn get(idx: i64) -> T {
        let val = arx_list_get(self.data_handle, idx)
        return val as T
    }

    pub fn set(idx: i64, val: T) {
        arx_list_set(self.data_handle, idx, val as i64)
    }

    pub fn len() -> i64 => self.length

    pub fn clear() {
        arx_list_clear(self.data_handle)
        self.length = 0
    }

    pub fn slice(start: i64, end: i64) -> List<T> {
        let sub_handle = arx_list_slice(self.data_handle, start, end)
        mut sub = List<T>()
        sub.data_handle = sub_handle
        sub.length = arx_list_len(sub_handle)
        return sub
    }

    pub fn free() {
        arx_list_free(self.data_handle)
        self.data_handle = 0
        self.length = 0
    }
}

class String {
    pub buf: str
    pub len: i64

    init(text: str) {
        self.buf = arx_str_copy(text)
        self.len = arx_str_len(self.buf)
    }

    init() {
        self.buf = ""
        self.len = 0
    }

    pub fn trim() -> String {
        return String(arx_str_trim(self.buf))
    }

    pub fn to_upper() -> String {
        return String(arx_str_to_upper(self.buf))
    }

    pub fn to_lower() -> String {
        return String(arx_str_to_lower(self.buf))
    }

    pub fn replace(old_s: str, new_s: str) -> String {
        return String(arx_str_replace(self.buf, old_s, new_s))
    }

    pub fn contains(query: str) -> bool {
        return arx_str_contains(self.buf, query)
    }

    pub fn starts_with(prefix: str) -> bool {
        return arx_str_starts_with(self.buf, prefix)
    }

    pub fn ends_with(suffix: str) -> bool {
        return arx_str_ends_with(self.buf, suffix)
    }

    pub fn split(delim: str) -> List<str> {
        let handle = arx_str_split(self.buf, delim)
        mut list = List<str>()
        list.data_handle = handle
        list.length = arx_list_len(handle)
        return list
    }

    pub fn get(idx: i64) -> str {
        return arx_str_slice(self.buf, idx, idx + 1)
    }

    pub fn slice(start: i64, end: i64) -> String {
        return String(arx_str_slice(self.buf, start, end))
    }

    pub fn as_str() -> str => self.buf
    pub fn length() -> i64 => self.len
}
"""

_PRELUDE_AST: Optional[ProgramNode] = None

def get_prelude_ast() -> ProgramNode:
    global _PRELUDE_AST
    if _PRELUDE_AST is None:
        lexer = Lexer(PRELUDE_CODE, "<prelude>")
        tokens = lexer.tokenize()
        parser = Parser(tokens, PRELUDE_CODE.splitlines(), filename="<prelude>")
        _PRELUDE_AST = parser.parse()
    return _PRELUDE_AST
