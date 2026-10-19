# ⚡ Aerix v1.0.88 Release Notes

**Release Date:** October 20, 2026  
**Status:** Stable Production Release (`v1.0.88`)  
**Architecture:** ANSI C99 Native Transpiler & Fast GCC Backend  
**Platform:** Windows 10/11 (AMD64), Linux (POSIX x86_64), macOS (ARM64/x86_64)

---

## 🌟 Executive Summary

Aerix **v1.0.88** represents a major milestone in the evolution of the language: the complete delivery of **Phases 21 and 22 — The Native Data Structures, Collections, and Text Processing Engine**. 

Developers now have access to modern, high-level data structures (Tuples, Robin Hood Hash Maps, Hash Sets, Dynamic Arrays, Linear Buffers, Binary Streams, and Mutable Strings) with **zero-overhead, bare-metal C struct lowering**, deterministic memory management, and complete compile-time type safety.

All 102 automated tests across all compiler subsystems pass with 100% success.

---

## 🚀 What's New in v1.0.88

### 1. Fixed-Size Value Tuples & Pattern Destructuring
- **First-Class Value Tuples:** Construct immutable, stack-allocated heterogeneous tuples:
  ```aerix
  let record = (42, "admin", true)
  ```
- **Positional Indexing:** Direct element access via dot notation (`record.0`, `record.1`, `record.2`).
- **Tuple Return Types:** Return multiple values from functions with zero heap allocation:
  ```aerix
  fn get_window_bounds() -> (i64, i64) {
      return (1920, 1080)
  }
  ```
- **Pattern Destructuring Bindings:** Cleanly unpack tuples directly in variable bindings:
  ```aerix
  let (width, height) = get_window_bounds()
  let (id, name, is_active) = record
  ```

---

### 2. High-Performance Dynamic Arrays (`List<T>`)
- **Dynamic Growth & Direct Indexing:**
  ```aerix
  mut scores = List<i64>()
  scores.push(95)
  scores.push(82)
  let first = scores[0]
  scores[1] = 88
  ```
- **Range Slicing:** Extract sub-lists using range syntax:
  ```aerix
  let sub = scores[0..1]
  ```
- **Algorithmic Suite:**
  - `list.sort()`: In-place ascending sorting.
  - `list.reverse()`: In-place reversal.
  - `list.contains(val) -> bool`: Value presence check.
  - `list.index_of(val) -> i64`: Returns 0-based index or `-1`.
  - `list.swap_remove(idx)`: $O(1)$ fast deletion.
  - `list.remove_at(idx)`: Order-preserving element removal.
  - `list.insert(idx, val)`: Element insertion at specified index.

---

### 3. Text & String Processing Engine (`str` vs `String`)
- **Borrowed Slices (`str`):** Ultra-fast, zero-allocation UTF-8 string pointer (`const char*`) with interpolation:
  ```aerix
  let greeting: str = "Hello, {name}!"
  ```
- **Heavyweight Mutable `String`:** Heap-allocated dynamic UTF-8 string with a fluent method pipeline:
  - `trim()`: Trims leading and trailing whitespace.
  - `to_upper()` / `to_lower()`: ASCII case transformation.
  - `replace(target, replacement)`: Global substring replacement.
  - `split(delimiter)`: Tokenizes into a `List<str>`.
  - `slice(start, end)`: Extracts string substrings.
  - `repeat(count)`: Multiplies strings.
  - `char_at(index)`: Fast indexed character lookup.
  - `contains(sub)` / `starts_with(pre)` / `ends_with(suf)`: Substring validation.

---

### 4. Robin Hood Hash Map (`Map<K, V>`)
- **Dense Open-Addressing Hash Table:** Uses Robin Hood hashing with backward-shift deletion and low variance probing.
- **Keys:** Supports both string (`str`) and integer (`i64`, `u64`) keys powered by 64-bit FNV-1a hashing.
- **Fluent Dictionary Operations:**
  ```aerix
  mut cache = Map<str, i64>()
  cache["max_conns"] = 1000
  let conns = cache["max_conns"]
  guard cache.has_key("max_conns") else { return }
  let keys = cache.keys()       // List<str>
  let vals = cache.values()     // List<i64>
  cache.remove("max_conns")
  cache.clear()
  ```

---

### 5. Hash Set (`Set<T>`) & Set Algebra
- **Zero-Payload Dense Table:** $O(1)$ average time complexity for insertion, lookup, and deletion.
- **Set Algebra:**
  ```aerix
  mut set_a = Set<i64>()
  set_a.add(1)
  set_a.add(2)
  set_a.add(3)

  mut set_b = Set<i64>()
  set_b.add(3)
  set_b.add(4)

  let u = set_a.union(set_b)         // {1, 2, 3, 4}
  let i = set_a.intersection(set_b)  // {3}
  let d = set_a.difference(set_b)    // {1, 2}
  ```
- **List Conversion:** `set.to_list()` exports unique elements into an iterable `List<T>`.

---

### 6. Linear Buffers (`Stack<T>`, `Queue<T>`, `Deque<T>`)
- **`Stack<T>` (LIFO):** High-speed pushdown stack with `push(x)`, `pop() -> T`, `peek() -> T`, `len`, and `is_empty()`.
- **`Queue<T>` (FIFO):** First-in, first-out container for task sequencing and event dispatching.
- **`Deque<T>` (Double-Ended Ring Buffer):** Circular ring buffer supporting $O(1)$ operations on both ends:
  - `push_back(x)`, `push_front(x)`
  - `pop_back() -> T`, `pop_front() -> T`
  - `peek_front() -> T`, `peek_back() -> T`

---

### 7. Binary Serialization Stream (`ByteBuffer`)
- **Dynamic Binary Vector:** Low-level, byte-accurate binary packet encoding and parsing for network protocols and file formats.
- **Endian-Aware Read/Write:**
  ```aerix
  mut buf = ByteBuffer()
  buf.write_u8(0xAA)
  buf.write_i32_le(42)
  buf.write_i32_be(42)
  buf.write_f64_le(3.14159)

  buf.seek(0)
  let magic = buf.read_u8()
  let val_le = buf.read_i32_le()
  let val_be = buf.read_i32_be()
  ```

---

### 8. Native Collection Iteration (`for item in coll`)
- **Zero-Cost Loop Lowering:** `for` loops now cleanly iterate over dynamic collections:
  ```aerix
  for item in my_list {
      println(item)
  }
  ```
  Lowers directly to native indexed iteration in ANSI C99 with register variables and zero function-call overhead.

---

### 9. Developer Tooling & Editor Ecosystem
- **Updated TextMate Syntax Grammar:**
  - Added dedicated syntax scopes (`support.class.collection.aerix`) for `List`, `Map`, `Set`, `Stack`, `Queue`, `Deque`, `ByteBuffer`, `String`.
- **VS Code & Google Antigravity IDE Extension (`aerix-1.0.88.vsix`):**
  - Updated manifest to `1.0.88`.
  - Added rich type completions, memory layout documentation, and hover assistance for all collection types.
- **Official One-Click Windows Setup Installer (`AerixSetup-1.0.88.exe`):**
  - Recompiled with Inno Setup using LZMA2 ultra64 solid compression (~2.3 MB).
  - Automatically installs and configures standalone toolchains, stdlib runtime headers, documentation, Explorer file associations, and IDE extensions.
- **Updated Test Suite:**
  - Expanded to **102 automated tests** (`Ran 102 tests ... OK`).
  - Added [examples/29_DATA_STRUCTURES_SHOWCASE.arx](file:///Z:/VSCode/AerixLang/examples/29_DATA_STRUCTURES_SHOWCASE.arx) demonstrating the full collection feature set.

---

## 📦 Distribution Artifacts

| Artifact | Type | Description |
| :--- | :--- | :--- |
| **`AerixSetup-1.0.88.exe`** | Windows Installer | Complete GUI and headless installer for Windows 10/11 |
| **`aerix-1.0.88.vsix`** | IDE Extension | Official extension bundle for VS Code and Google Antigravity IDE |
| **`arx.exe`** | Standalone Binary | PyInstaller + native C dispatcher CLI runner |
| **`arxc.exe`** | Standalone Binary | Dedicated standalone compiler binary |
| **`arx_fast.exe`** | Native Binary | Ultra-low-latency native C dispatcher |
| **`aerix_rt.h`** | Runtime Header | ANSI C99 runtime library header |

---

## 🛠️ Verification & Installation

```powershell
# Run the installer
.\AerixSetup-1.0.88.exe

# Or install extension manually
code --install-extension editors/vscode-aerix/aerix-1.0.88.vsix --force
antigravity --install-extension editors/vscode-aerix/aerix-1.0.88.vsix --force

# Verify toolchain version
arx version
# Output: Aerix (arx) v1.0.88-alpha
```
