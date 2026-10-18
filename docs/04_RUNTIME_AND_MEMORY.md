# Aerix (arx) — Runtime Model, Memory & C Interop

> **Subsystem:** Memory Architecture, Runtime Header (`aerix_rt.h`), and Zero-Cost C FFI  
> **Guiding Axiom:** *Zero Garbage Collector Overhead, Deterministic Lifetimes, Direct Native Access.*

---

## 1. Why Aerix Executes as Fast as C/C++

Most modern languages are slowed down by:
1. **Garbage Collection (GC):** Periodic stop-the-world pauses, memory fragmentation, and cache invalidation (Java, Go, C#, Python).
2. **Dynamic Typing & Boxing:** Allocating integers and floats on the heap, runtime type inspection.
3. **Virtual Machine Interpretation:** Bytecode fetch-decode loops (Python, Lua).

Aerix eliminates all three bottlenecks:
* Aerix compiles directly to **native C99 structs, pointers, and direct function calls**.
* GCC applies aggressive machine optimizations: loop unrolling, auto-vectorization (AVX-512, AVX2, SSE4.2), register allocation, and dead code elimination.
* Memory layout is **100% deterministic and cache-coherent**.

---

## 2. Memory Model & Resource Management

Aerix combines three complementary memory strategies:

### 2.1 Stack Allocation (Default & Fastest)
Whenever an object or variable is declared, it lives on the CPU stack. Allocation costs a single instruction pointer decrement (`sub rsp, N`), and deallocation is completely free (`add rsp, N`).

```aerix
fn process() {
    let p = Point(10.0, 20.0) // Stack allocated
    // Instant stack cleanup when function returns
}
```

### 2.2 Scoped Resource Cleanup (`defer`)
Aerix uses compiler-synthesized `defer` blocks. The compiler collects all `defer` actions in reverse order (LIFO) and inserts them before every `return`, `break`, or scope boundary.

```aerix
fn copy_file(src: str, dst: str) -> bool {
    let in_file = fopen(src, "rb")
    if in_file == null { return false }
    defer fclose(in_file) // 1. Closes second

    let out_file = fopen(dst, "wb")
    if out_file == null { return false }
    defer fclose(out_file) // 2. Closes first

    // Core copy loop...
    return true
}
```

### 2.3 Explicit Heap & Arenas
For objects whose lifetime exceeds the current stack frame:

```aerix
// Manual heap allocation
let buf = arx_alloc(1024)
defer arx_free(buf)

// Class instantiation on heap
let entity = new Player("Hero", 100)
defer delete entity
```

For high-throughput allocations (such as per-frame game logic), Aerix provides **Memory Arenas** in its standard library:

```aerix
let arena = Arena(64 * 1024) // 64 KB scratchpad
defer arena.reset()

let temp_mesh = arena.alloc(sizeof(Mesh))
```

---

## 3. The Aerix Runtime Header (`stdlib/aerix_rt.h`)

The Aerix runtime is a header-only, zero-dependency ANSI C99 library included in every compiled binary.

### 3.1 Key Responsibilities
1. **Platform Abstraction:** Defines fixed-width integer types (`int64_t`, `uint32_t`, etc.) across Windows, Linux, and macOS.
2. **String Utilities:** Fast immutable string slices and formatted string printing (`arx_println`).
3. **Panic & Diagnostics:** Clean crash diagnostics with file, line, and reason if an assertion fails.

### 3.2 Anatomy of `aerix_rt.h` (Specification)
```c
#ifndef AERIX_RT_H
#define AERIX_RT_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdarg.h>

// Core Integer and Float Aliases
typedef int8_t   i8;
typedef int16_t  i16;
typedef int32_t  i32;
typedef int64_t  i64;
typedef uint8_t  u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef float    f32;
typedef double   f64;

// Panic Handler
static inline void arx_panic(const char* msg, const char* file, int line) {
    fprintf(stderr, "\n\033[1;31m[AERIX RUNTIME PANIC]\033[0m %s at %s:%d\n", msg, file, line);
    exit(1);
}

#define ARX_ASSERT(cond, msg) \
    do { if (!(cond)) arx_panic(msg, __FILE__, __LINE__); } while(0)

// Memory Primitives
static inline void* arx_alloc(size_t bytes) {
    void* ptr = malloc(bytes);
    if (!ptr && bytes > 0) arx_panic("Out of memory", __FILE__, __LINE__);
    return ptr;
}

static inline void arx_free(void* ptr) {
    if (ptr) free(ptr);
}

#endif // AERIX_RT_H
```

---

## 4. Zero-Cost C Interoperability (FFI)

Because Aerix targets C99, **any C library in the world can be linked directly with zero wrapper or glue-code overhead**.

### 4.1 Native Header Inclusion
```aerix
// Direct inclusion of system headers
cinclude "<math.h>"
cinclude "<time.h>"

// External function signatures
cextern fn sin(rad: f64) -> f64
cextern fn cos(rad: f64) -> f64
cextern fn time(timer: *void) -> i64
```

### 4.2 Game Development with Raylib (Example)
```aerix
cinclude "raylib.h"

cextern fn InitWindow(width: i32, height: i32, title: str)
cextern fn WindowShouldClose() -> bool
cextern fn CloseWindow()
cextern fn BeginDrawing()
cextern fn EndDrawing()
cextern fn ClearBackground(color: u32)
cextern fn DrawText(text: str, x: i32, y: i32, fontSize: i32, color: u32)

fn main() {
    InitWindow(800, 450, "Aerix + Raylib Native Window")
    defer CloseWindow()

    while !WindowShouldClose() {
        BeginDrawing()
        ClearBackground(0xFF181818) // Dark background
        DrawText("Welcome to Aerix Native Game Loop!", 190, 200, 20, 0xFFFFFFFF)
        EndDrawing()
    }
}
```
**Compilation Command:**
```bash
arx build game.arx -lraylib -lopengl32 -lgdi32 -lwinmm
```
The resulting executable runs at pure 60+ FPS native hardware performance with zero bridge overhead.

---

## 5. Aerix 2.0 High-Performance Memory Architecture

### 5.1 Automatic Cache-Line Struct Packing
The compiler automatically analyzes class fields and orders them in descending alignment ($8 \rightarrow 4 \rightarrow 2 \rightarrow 1$ bytes):
```aerix
class TelemetryData {
    pub id: u8          // 1 byte
    pub timestamp: i64  // 8 bytes
    pub active: bool    // 1 byte
    pub value: f64      // 8 bytes
}
```
*Generated C Struct (Optimized to zero internal padding):*
```c
struct Arx_TelemetryData {
    int64_t timestamp;  // 8 bytes (Offset 0)
    double value;       // 8 bytes (Offset 8)
    uint8_t id;         // 1 byte  (Offset 16)
    bool active;        // 1 byte  (Offset 17)
    char __pad[6];      // 6 bytes tail padding (Total: 24B instead of 32B!)
};
```
Result: **25% reduction in struct size**, increasing L1 CPU cache residency.

### 5.2 Linear Arena Allocators (`stdlib/memory`)
For high-throughput loops (games, simulations, network handlers):
```aerix
use stdlib.memory.Arena

fn run_simulation_tick() {
    let mut arena = Arena.with_capacity(1024 * 1024) // 1 MB bump allocator
    defer arena.reset() // O(1) bulk deallocation in a single cycle!

    let entity1 = arena.alloc(Entity)
    let entity2 = arena.alloc(Entity)
    // 0 malloc/free fragmentation!
}
```

### 5.3 Hardware SIMD Intrinsics
Aerix maps vector types directly to hardware SIMD registers:
```aerix
let a: f32x4 = f32x4(1.0, 2.0, 3.0, 4.0)
let b: f32x4 = f32x4(5.0, 6.0, 7.0, 8.0)
let c = a + b // Compiles directly to Intel AVX `_mm_add_ps` instruction!
```

