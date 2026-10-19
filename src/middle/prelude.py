"""
Aerix Compiler (arxc) — Standard Prelude Declarations (Phase 21 & 22)
Defines built-in standard templates and classes:
List<T>, String, Map<K, V>, Set<T>, Stack<T>, Queue<T>, Deque<T>, ByteBuffer.
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

    pub fn is_empty() -> bool => self.length == 0

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

    pub fn contains(val: T) -> bool {
        return arx_list_contains(self.data_handle, val as i64)
    }

    pub fn index_of(val: T) -> i64 {
        return arx_list_index_of(self.data_handle, val as i64)
    }

    pub fn reverse() {
        arx_list_reverse(self.data_handle)
    }

    pub fn sort() {
        arx_list_sort(self.data_handle)
    }

    pub fn swap_remove(idx: i64) -> T {
        let val = arx_list_swap_remove(self.data_handle, idx)
        self.length = arx_list_len(self.data_handle)
        return val as T
    }

    pub fn remove_at(idx: i64) -> T {
        let val = arx_list_remove_at(self.data_handle, idx)
        self.length = arx_list_len(self.data_handle)
        return val as T
    }

    pub fn insert(idx: i64, val: T) {
        arx_list_insert(self.data_handle, idx, val as i64)
        self.length = arx_list_len(self.data_handle)
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

    pub fn repeat(count: i64) -> String {
        return String(arx_str_repeat(self.buf, count))
    }

    pub fn append(extra: str) -> String {
        return String(arx_str_concat(self.buf, extra))
    }

    pub fn index_of(needle: str) -> i64 {
        return arx_str_find(self.buf, needle)
    }

    pub fn char_at(idx: i64) -> str {
        return arx_str_char_at(self.buf, idx)
    }

    pub fn is_empty() -> bool => self.len == 0
    pub fn as_str() -> str => self.buf
    pub fn length() -> i64 => self.len
}

class Map<K, V> {
    pub map_handle: i64
    pub length: i64

    init() {
        self.length = 0
        self.map_handle = arx_map_new(0)
    }

    pub fn insert(key: K, val: V) {
        arx_map_insert(self.map_handle, key as i64, val as i64)
        self.length = arx_map_len(self.map_handle)
    }

    pub fn get(key: K) -> V {
        let val = arx_map_get(self.map_handle, key as i64)
        return val as V
    }

    pub fn set(key: K, val: V) {
        arx_map_insert(self.map_handle, key as i64, val as i64)
        self.length = arx_map_len(self.map_handle)
    }

    pub fn has_key(key: K) -> bool {
        return arx_map_has(self.map_handle, key as i64)
    }

    pub fn remove(key: K) {
        arx_map_remove(self.map_handle, key as i64)
        self.length = arx_map_len(self.map_handle)
    }

    pub fn len() -> i64 => self.length
    pub fn is_empty() -> bool => self.length == 0

    pub fn clear() {
        arx_map_clear(self.map_handle)
        self.length = 0
    }

    pub fn keys() -> List<K> {
        let h = arx_map_keys(self.map_handle)
        mut list = List<K>()
        list.data_handle = h
        list.length = arx_list_len(h)
        return list
    }

    pub fn values() -> List<V> {
        let h = arx_map_values(self.map_handle)
        mut list = List<V>()
        list.data_handle = h
        list.length = arx_list_len(h)
        return list
    }

    pub fn free() {
        arx_map_free(self.map_handle)
        self.map_handle = 0
        self.length = 0
    }
}

class Set<T> {
    pub set_handle: i64
    pub length: i64

    init() {
        self.length = 0
        self.set_handle = arx_set_new(0)
    }

    pub fn add(item: T) -> bool {
        let added = arx_set_add(self.set_handle, item as i64)
        self.length = arx_set_len(self.set_handle)
        return added
    }

    pub fn has(item: T) -> bool {
        return arx_set_has(self.set_handle, item as i64)
    }

    pub fn remove(item: T) -> bool {
        let removed = arx_set_remove(self.set_handle, item as i64)
        self.length = arx_set_len(self.set_handle)
        return removed
    }

    pub fn len() -> i64 => self.length
    pub fn is_empty() -> bool => self.length == 0

    pub fn clear() {
        arx_set_clear(self.set_handle)
        self.length = 0
    }

    pub fn get(idx: i64) -> T {
        let val = arx_set_get(self.set_handle, idx)
        return val as T
    }

    pub fn to_list() -> List<T> {
        let h = arx_set_to_list(self.set_handle)
        mut list = List<T>()
        list.data_handle = h
        list.length = arx_list_len(h)
        return list
    }

    pub fn union(other: Set<T>) -> Set<T> {
        let rh = arx_set_union(self.set_handle, other.set_handle)
        mut res = Set<T>()
        res.set_handle = rh
        res.length = arx_set_len(rh)
        return res
    }

    pub fn intersection(other: Set<T>) -> Set<T> {
        let rh = arx_set_intersection(self.set_handle, other.set_handle)
        mut res = Set<T>()
        res.set_handle = rh
        res.length = arx_set_len(rh)
        return res
    }

    pub fn difference(other: Set<T>) -> Set<T> {
        let rh = arx_set_difference(self.set_handle, other.set_handle)
        mut res = Set<T>()
        res.set_handle = rh
        res.length = arx_set_len(rh)
        return res
    }

    pub fn free() {
        arx_set_free(self.set_handle)
        self.set_handle = 0
        self.length = 0
    }
}

class Stack<T> {
    pub stack_handle: i64
    pub length: i64

    init() {
        self.stack_handle = arx_stack_new()
        self.length = 0
    }

    pub fn push(val: T) {
        arx_stack_push(self.stack_handle, val as i64)
        self.length = arx_stack_len(self.stack_handle)
    }

    pub fn pop() -> T {
        let val = arx_stack_pop(self.stack_handle)
        self.length = arx_stack_len(self.stack_handle)
        return val as T
    }

    pub fn peek() -> T {
        let val = arx_stack_peek(self.stack_handle)
        return val as T
    }

    pub fn len() -> i64 => self.length
    pub fn is_empty() -> bool => self.length == 0

    pub fn clear() {
        arx_stack_clear(self.stack_handle)
        self.length = 0
    }

    pub fn free() {
        arx_stack_free(self.stack_handle)
        self.stack_handle = 0
        self.length = 0
    }
}

class Queue<T> {
    pub queue_handle: i64
    pub length: i64

    init() {
        self.queue_handle = arx_queue_new()
        self.length = 0
    }

    pub fn enqueue(val: T) {
        arx_queue_enqueue(self.queue_handle, val as i64)
        self.length = arx_queue_len(self.queue_handle)
    }

    pub fn dequeue() -> T {
        let val = arx_queue_dequeue(self.queue_handle)
        self.length = arx_queue_len(self.queue_handle)
        return val as T
    }

    pub fn peek() -> T {
        let val = arx_queue_peek_front(self.queue_handle)
        return val as T
    }

    pub fn len() -> i64 => self.length
    pub fn is_empty() -> bool => self.length == 0

    pub fn clear() {
        arx_queue_clear(self.queue_handle)
        self.length = 0
    }

    pub fn free() {
        arx_queue_free(self.queue_handle)
        self.queue_handle = 0
        self.length = 0
    }
}

class Deque<T> {
    pub deque_handle: i64
    pub length: i64

    init() {
        self.deque_handle = arx_deque_new()
        self.length = 0
    }

    pub fn push_back(val: T) {
        arx_deque_push_back(self.deque_handle, val as i64)
        self.length = arx_deque_len(self.deque_handle)
    }

    pub fn push_front(val: T) {
        arx_deque_push_front(self.deque_handle, val as i64)
        self.length = arx_deque_len(self.deque_handle)
    }

    pub fn pop_back() -> T {
        let val = arx_deque_pop_back(self.deque_handle)
        self.length = arx_deque_len(self.deque_handle)
        return val as T
    }

    pub fn pop_front() -> T {
        let val = arx_deque_pop_front(self.deque_handle)
        self.length = arx_deque_len(self.deque_handle)
        return val as T
    }

    pub fn peek_front() -> T {
        let val = arx_deque_peek_front(self.deque_handle)
        return val as T
    }

    pub fn peek_back() -> T {
        let val = arx_deque_peek_back(self.deque_handle)
        return val as T
    }

    pub fn len() -> i64 => self.length
    pub fn is_empty() -> bool => self.length == 0

    pub fn clear() {
        arx_deque_clear(self.deque_handle)
        self.length = 0
    }

    pub fn free() {
        arx_deque_free(self.deque_handle)
        self.deque_handle = 0
        self.length = 0
    }
}

class ByteBuffer {
    pub buf_handle: i64

    init(capacity: i64) {
        self.buf_handle = arx_bytebuf_new(capacity)
    }

    init() {
        self.buf_handle = arx_bytebuf_new(64)
    }

    pub fn write_u8(val: i64) {
        arx_bytebuf_write_u8(self.buf_handle, val)
    }

    pub fn write_i32_le(val: i64) {
        arx_bytebuf_write_i32_le(self.buf_handle, val)
    }

    pub fn write_i32_be(val: i64) {
        arx_bytebuf_write_i32_be(self.buf_handle, val)
    }

    pub fn write_f64_le(val: f64) {
        arx_bytebuf_write_f64_le(self.buf_handle, val as i64)
    }

    pub fn read_u8() -> i64 {
        return arx_bytebuf_read_u8(self.buf_handle)
    }

    pub fn read_i32_le() -> i64 {
        return arx_bytebuf_read_i32_le(self.buf_handle)
    }

    pub fn read_i32_be() -> i64 {
        return arx_bytebuf_read_i32_be(self.buf_handle)
    }

    pub fn seek(offset: i64) {
        arx_bytebuf_seek(self.buf_handle, offset)
    }

    pub fn reset() {
        arx_bytebuf_reset(self.buf_handle)
    }

    pub fn len() -> i64 {
        return arx_bytebuf_len(self.buf_handle)
    }

    pub fn pos() -> i64 {
        return arx_bytebuf_pos(self.buf_handle)
    }

    pub fn free() {
        arx_bytebuf_free(self.buf_handle)
        self.buf_handle = 0
    }
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
