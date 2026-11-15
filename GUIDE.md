# The Complete Aerix Language Handbook & Tutorial (`GUIDE.md`)

Welcome to the **Official Aerix Programming Language Handbook**. This comprehensive tutorial is designed for developers of all backgrounds—from beginners taking their first steps in systems programming to experienced engineers looking for a modern, high-performance alternative to C, C++, Rust, and Go.

Every concept in this guide is accompanied by clear explanations, practical code snippets, and best practices.

---

## 📑 Table of Contents

1. [Introduction & Toolchain Setup](#chapter-1-introduction--toolchain-setup)
2. [Program Structure & Core Syntax](#chapter-2-program-structure--core-syntax)
3. [Variables, Mutability & Primitives](#chapter-3-variables-mutability--primitives)
4. [Strings, Interpolation & Text Operations](#chapter-4-strings-interpolation--text-operations)
5. [Operators, Expressions & Pipelines](#chapter-5-operators-expressions--pipelines)
6. [Control Flow & Pattern Matching](#chapter-6-control-flow--pattern-matching)
7. [Functions & Signatures](#chapter-7-functions--signatures)
8. [Structs & Value Types](#chapter-8-structs--value-types)
9. [Classes & Object-Oriented Programming](#chapter-9-classes--object-oriented-programming)
10. [Enums, Tagged Unions & Exhaustive Matching](#chapter-10-enums-tagged-unions--exhaustive-matching)
11. [Retroactive Type Extensions (`extend`)](#chapter-11-retroactive-type-extensions-extend)
12. [Standard Generic Collections](#chapter-12-standard-generic-collections)
13. [Deterministic Memory Management (`defer`)](#chapter-13-deterministic-memory-management-defer)
14. [Exception Handling (`try` / `catch` / `finally` / `throw`)](#chapter-14-exception-handling)
15. [Modules & Scoped Imports](#chapter-15-modules--scoped-imports)
16. [Concurrency & Thread Channels](#chapter-16-concurrency--thread-channels)
17. [Native Win32 GUI & Desktop Windowing](#chapter-17-native-win32-gui--desktop-windowing)
18. [File I/O & System Environment](#chapter-18-file-io--system-environment)
19. [C Interoperability & External DLLs](#chapter-19-c-interoperability--external-dlls)
20. [Complete Real-World Projects](#chapter-20-complete-real-world-projects)

---

## Chapter 1: Introduction & Toolchain Setup

### What Makes Aerix Special?
Aerix is designed with three core architectural pillars:
1. **Bare-Metal Speed with Zero GC:** Aerix generates direct machine code or standalone ANSI C99. There is no garbage collector running in the background, which means zero GC pauses, minimal memory footprints, and predictable real-time execution.
2. **Zero External Compiler Dependencies:** The native PE32+ backend generates standard Windows `.exe` files directly without needing GCC, Clang, or MSVC installed.
3. **Ergonomic Safety:** Memory safety features like `guard`, `defer`, strong nominal typing, and pattern matching prevent common classes of bugs without the cognitive overhead of complex borrow checkers.

### Verifying Your Toolchain
Once Aerix is installed, verify your installation:
```powershell
arx version
```
Expected output:
```text
Aerix Toolchain v2.2.25 (Stable Channel) - x86_64-windows
```

---

## Chapter 2: Program Structure & Core Syntax

### The Entry Point: `fn main()`
Every executable Aerix program starts execution in `fn main()`:

```aerix
fn main() {
    println("Welcome to Aerix!")
}
```

### Comments & Documentation
Aerix supports single-line comments, multi-line comments, and typed doc-comments:

```aerix
// This is a standard single-line comment

/*
 * This is a multi-line comment block
 */

/// Calculates the euclidean distance between two points.
/// Parameters:
///   `dx` - Horizontal displacement
///   `dy` - Vertical displacement
fn distance(dx: f64, dy: f64) -> f64 {
    return Math.sqrt(dx * dx + dy * dy)
}
```
Doc-comments (`///`) are automatically extracted by the Language Server Protocol (LSP) and displayed when hovering over functions in VS Code / Antigravity IDE.

---

## Chapter 3: Variables, Mutability & Primitives

### Immutability by Default (`let`) vs Mutability (`mut`)
In Aerix, variables are immutable by default:

```aerix
fn main() {
    // Immutable binding (cannot be reassigned)
    let max_retries = 3

    // Mutable variable
    mut counter = 0
    counter = counter + 1
    
    // Compile-time constant
    const BUFFER_SIZE: i64 = 4096
}
```

### Primitive Types
Aerix provides comprehensive fixed-width integer, floating-point, boolean, and character primitives:

| Type | Size | Description | Example |
| :--- | :--- | :--- | :--- |
| `i8`, `i16`, `i32`, `i64` | 1, 2, 4, 8 bytes | Signed two's-complement integers | `let a: i64 = -42` |
| `u8`, `u16`, `u32`, `u64` | 1, 2, 4, 8 bytes | Unsigned integers | `let b: u8 = 255` |
| `f32`, `f64` | 4, 8 bytes | IEEE 754 floating-point numbers | `let pi: f64 = 3.14159265` |
| `bool` | 1 byte | Boolean logical value | `let active: bool = true` |
| `char` | 4 bytes | 32-bit Unicode codepoint | `let symbol: char = 'A'` |
| `str` | Pointer + Len | Immutable UTF-8 string reference | `let msg: str = "Aerix"` |
| `void` | 0 bytes | Unit / empty return type | `fn log() -> void` |

---

## Chapter 4: Strings, Interpolation & Text Operations

Strings in Aerix are UTF-8 encoded and immutable:

```aerix
fn main() {
    let name = "Aerix"
    let version = 2
    
    // String Interpolation with {expression}
    let greeting = "Language: {name}, Major Version: {version + 0}"
    println(greeting)
    
    // String Methods
    let raw = "   Systems Programming   "
    let clean = raw.trim()
    println(clean)                    // "Systems Programming"
    println(clean.to_upper())          // "SYSTEMS PROGRAMMING"
    println(clean.to_lower())          // "systems programming"
    println("Length: {clean.len()}")   // 19
    
    // Substring Slicing
    let word = clean.slice(0, 7)
    println("Slice: {word}")           // "Systems"
    
    // Search & Replacement
    if clean.contains("Programming") {
        let replaced = clean.replace("Systems", "Bare-Metal")
        println(replaced)              // "Bare-Metal Programming"
    }
}
```

---

## Chapter 5: Operators, Expressions & Pipelines

### Standard Operators
* **Arithmetic:** `+`, `-`, `*`, `/`, `%`
* **Comparison:** `==`, `!=`, `<`, `<=`, `>`, `>=`
* **Logical:** `&&`, `||`, `!`
* **Bitwise:** `&`, `|`, `^`, `~`, `<<`, `>>`

### The Pipeline Operator (`|>`)
The pipeline operator forwards the result of the left-hand expression as the first parameter of the right-hand function call:

```aerix
fn double_val(x: i64) -> i64 { return x * 2 }
fn add_ten(x: i64) -> i64    { return x + 10 }
fn square_val(x: i64) -> i64 { return x * x }

fn main() {
    // Equivalent to: square_val(add_ten(double_val(5)))
    let result = 5 |> double_val() |> add_ten() |> square_val()
    println("Pipeline result: {result}") // (5 * 2 + 10)^2 = 400
}
```

### The Fluent Cascade Operator (`~>`)
The cascade operator invokes a method on an object while returning the object itself, enabling clean builder patterns:

```aerix
class RequestBuilder {
    pub url: str
    pub timeout: i64
    
    init() {
        self.url = ""
        self.timeout = 30
    }
    
    pub fn set_url(u: str) { self.url = u }
    pub fn set_timeout(t: i64) { self.timeout = t }
}

fn main() {
    let req = RequestBuilder()
        ~>set_url("https://api.aerix.org")
        ~>set_timeout(60)
    
    println("Configured URL: {req.url}")
}
```

---

## Chapter 6: Control Flow & Pattern Matching

### `if`, `elif`, and `else`
```aerix
fn categorize(score: i64) -> str {
    if score >= 90 {
        return "Distinction"
    } elif score >= 60 {
        return "Pass"
    } else {
        return "Retry"
    }
}
```

### The `guard` Statement
`guard` enforces preconditions early in a function body, reducing nested `if` statements:

```aerix
fn process_account(id: i64, balance: i64) {
    guard id > 0 else {
        println("Invalid ID")
        return
    }
    guard balance >= 0 else {
        println("Overdraft not permitted")
        return
    }
    
    println("Processing valid account {id} with balance ${balance}")
}
```

### Loops: `while` and Range `for`
```aerix
fn main() {
    // While loop
    mut i = 0
    while i < 5 {
        print("{i} ")
        i = i + 1
    }
    println("")

    // For range loop (inclusive..exclusive)
    for index in 0..5 {
        println("Index: {index}")
    }
}
```

---

## Chapter 7: Functions & Signatures

### Standard Functions
```aerix
fn add(a: i64, b: i64) -> i64 {
    return a + b
}

// Expression body shorthand
fn multiply(a: i64, b: i64) -> i64 => a * b
```

### Generic Functions
```aerix
fn identity<T>(val: T) -> T {
    return val
}
```

---

## Chapter 8: Structs & Value Types

Structs represent lightweight, contiguous data records:

```aerix
struct Point {
    pub x: f64
    pub y: f64
    
    init(x: f64, y: f64) {
        self.x = x
        self.y = y
    }
    
    pub fn distance_from_origin() -> f64 {
        return Math.sqrt(self.x * self.x + self.y * self.y)
    }
}

fn main() {
    let pt = Point(3.0, 4.0)
    println("Distance: {pt.distance_from_origin()}") // 5.0
}
```

---

## Chapter 9: Classes & Object-Oriented Programming

Classes support encapsulation, constructors (`init`), and inheritance (`extends`):

```aerix
class Entity {
    pub id: i64
    pub name: str
    
    init(id: i64, name: str) {
        self.id = id
        self.name = name
    }
    
    pub fn describe() -> str {
        return "Entity #{self.id}: {self.name}"
    }
}

class Player extends Entity {
    pub score: i64
    
    init(id: i64, name: str, score: i64) {
        super(id, name)
        self.score = score
    }
    
    pub override fn describe() -> str {
        return "Player {self.name} (ID: {self.id}) - Score: {self.score}"
    }
}

fn main() {
    let p = Player(1, "Alex", 1500)
    println(p.describe())
}
```

---

## Chapter 10: Enums, Tagged Unions & Exhaustive Matching

Enums in Aerix are full-fledged tagged algebraic data types:

```aerix
enum NetworkStatus {
    Disconnected,
    Connecting(attempt: i64),
    Connected(ip: str, ping_ms: i64),
    Failed(reason: str)
}

fn log_status(status: NetworkStatus) {
    match status {
        case Disconnected => println("Status: Offline")
        case Connecting(att) => println("Status: Reconnecting (attempt {att})...")
        case Connected(ip, ping) => println("Status: Online ({ip}) - {ping}ms")
        case Failed(err) => println("Status: Error - {err}")
    }
}

fn main() {
    let state = NetworkStatus.Connected("192.168.1.100", 14)
    log_status(state)
}
```

---

## Chapter 11: Retroactive Type Extensions (`extend`)

You can add methods to any struct or class without modifying its original definition:

```aerix
extend Point {
    pub fn translate(dx: f64, dy: f64) -> Point {
        return Point(self.x + dx, self.y + dy)
    }
}

fn main() {
    let p1 = Point(1.0, 2.0)
    let p2 = p1.translate(4.0, 6.0)
    println("P2: ({p2.x}, {p2.y})") // (5.0, 8.0)
}
```

---

## Chapter 12: Standard Generic Collections

Aerix provides a robust collection of generic data structures:

```aerix
fn main() {
    // 1. Dynamic Growable List<T>
    let nums = List<i64>()
    nums.push(10)
    nums.push(20)
    nums.push(30)
    println("List length: {nums.len()}, first item: {nums.get(0)}")
    
    // 2. Hash Map<K, V>
    let scores = Map<str, i64>()
    scores.insert("Alice", 95)
    scores.insert("Bob", 88)
    if scores.has_key("Alice") {
        println("Alice's Score: {scores.get(\"Alice\")}")
    }
    
    // 3. Unique Element Set<T>
    let tags = Set<str>()
    tags.add("systems")
    tags.add("native")
    println("Has native? {tags.contains(\"native\")}")
    
    // 4. LIFO Stack<T>
    let st = Stack<str>()
    st.push("alpha")
    st.push("beta")
    println("Popped: {st.pop()}") // "beta"
    
    // 5. Double-Ended Queue (Deque<T>)
    let dq = Deque<i64>()
    dq.push_back(100)
    dq.push_front(50)
    println("Front: {dq.pop_front()}") // 50
}
```

---

## Chapter 13: Deterministic Memory Management (`defer`)

The `defer` statement schedules a cleanup expression to run right before the enclosing scope exits, in Last-In First-Out (LIFO) order:

```aerix
fn perform_task() {
    println("1. Starting task")
    defer println("4. Task scope cleanup complete")
    defer println("3. Second cleanup step")
    
    println("2. Performing computation...")
}

fn main() {
    perform_task()
}
```
Output:
```text
1. Starting task
2. Performing computation...
3. Second cleanup step
4. Task scope cleanup complete
```

---

## Chapter 14: Exception Handling

Aerix implements structured exception handling with zero performance penalty on the non-throwing path:

```aerix
fn divide(a: i64, b: i64) -> i64 {
    if b == 0 {
        throw "DivisionByZero: Cannot divide by zero!"
    }
    return a / b
}

fn main() {
    try {
        let result = divide(10, 0)
        println("Result: {result}")
    } catch err {
        println("Caught exception: {err}")
    } finally {
        println("Finally block always executes.")
    }
}
```

---

## Chapter 15: Modules & Scoped Imports

Aerix strictly isolates imported symbols to prevent namespace pollution:

```aerix
// 1. Selective symbol import (only 'now' is accessible)
from Time import now

// 2. Submodule import ('Window.Gui' and 'Gui' are accessible; 'Window' is not)
import Window.Gui

// 3. Full module import ('Math' namespace is accessible)
import Math

fn main() {
    let t0 = now()
    let root = Math.sqrt(144.0)
    println("Timestamp: {t0}, Square root: {root}")
}
```

---

## Chapter 16: Concurrency & Thread Channels

Aerix provides native OS-level thread spawning with typed message queues:

```aerix
fn compute_sum(start: i64, end: i64, out: Channel<i64>) {
    mut sum = 0
    mut i = start
    while i < end {
        sum = sum + i
        i = i + 1
    }
    out.send(sum)
}

fn main() {
    mut ch = Channel<i64>(2)
    
    // Spawn two concurrent threads
    let t1 = spawn compute_sum(0, 500000, ch)
    let t2 = spawn compute_sum(500000, 1000000, ch)
    
    let part1 = ch.recv()
    let part2 = ch.recv()
    
    arx_thread_join(t1)
    arx_thread_join(t2)
    ch.close()
    
    println("Total Sum: {part1 + part2}")
}
```

---

## Chapter 17: Native Win32 GUI & Desktop Windowing

Create native desktop applications with zero third-party dependencies:

```aerix
from Window.Gui import createWindow, AppWindow, Button, TextBox

fn main() {
    // 1. Create a 800x600 centered Win32 window
    let hwnd = createWindow("Aerix Desktop Studio", 800, 600)
    let app = AppWindow(hwnd)
    
    // 2. Add controls
    let input = TextBox(hwnd, 50, 50, 300, 32, "Type here...")
    let btn = Button(hwnd, 360, 50, 120, 32, "Click Me!")
    
    // 3. Show window and enter event loop
    app.show()
    app.run()
}
```

---

## Chapter 18: File I/O & System Environment

```aerix
fn main() {
    let path = "example.txt"
    
    // Write text to file
    File.write_string(path, "Aerix Native File I/O\nLine 2")
    
    // Check file existence
    if File.exists(path) {
        let content = File.read_string(path)
        println("File Content:\n{content}")
    }
    
    // Environment Variables
    let user = Env.get("USERNAME")
    println("Current User: {user}")
    
    // Process Exit
    // Process.exit(0)
}
```

---

## Chapter 19: C Interoperability & External DLLs

Bind existing C libraries or Windows API functions directly:

```aerix
// Direct Win32 API binding
#[extern("user32.dll", "MessageBeep")]
fn MessageBeep(uType: i64) -> bool

fn main() {
    // Plays the default Windows alert sound
    MessageBeep(0)
}
```

---

## Chapter 20: Complete Real-World Projects

### Project 1: High-Performance Multi-Threaded TCP Echo Server
```aerix
import Socket
from Time import now

fn handle_client(client_fd: i64) {
    defer Socket.close(client_fd)
    
    let buf = Socket.recv(client_fd, 1024)
    if buf.len() > 0 {
        Socket.send(client_fd, "ECHO: " + buf)
    }
}

fn main() {
    let server = Socket.listen(8080)
    println("Server listening on port 8080...")
    
    while true {
        let client_fd = Socket.accept(server)
        if client_fd >= 0 {
            spawn handle_client(client_fd)
        }
    }
}
```

---

*End of Handbook. You are now equipped to build production-grade, bare-metal software with Aerix!*
