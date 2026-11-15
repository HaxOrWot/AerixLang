# The Complete Aerix Language Handbook & Tutorial (`GUIDE.md`)

Welcome to the **Official Aerix Programming Language Handbook**. This handbook is designed as an exhaustive, step-by-step master tutorial for programmers of all backgrounds—from newcomers learning systems programming to experienced engineers transitioning from C, C++, Rust, Go, or Python.

Every chapter is structured with clear conceptual explanations, syntax breakdowns, best practices, and complete runnable code snippets.

---

## 📑 Table of Contents

* [Part I: Language Foundations](#part-i-language-foundations)
  * [Chapter 1: Introduction, Architecture & Toolchain Setup](#chapter-1-introduction-architecture--toolchain-setup)
  * [Chapter 2: Anatomy of an Aerix Program (`fn main()`, Comments & Docs)](#chapter-2-anatomy-of-an-aerix-program-fn-main-comments--docs)
  * [Chapter 3: Variables, Mutability (`let`, `mut`, `const`) & Type Annotations](#chapter-3-variables-mutability-let-mut-const--type-annotations)
  * [Chapter 4: Primitive Types, Sizes & Numeric Precision](#chapter-4-primitive-types-sizes--numeric-precision)
  * [Chapter 5: Strings, UTF-8 Encoding, Interpolation & Slicing](#chapter-5-strings-utf-8-encoding-interpolation--slicing)
  * [Chapter 6: Operators, Bitwise Manipulation & Math Functions](#chapter-6-operators-bitwise-manipulation--math-functions)
  * [Chapter 7: The Pipeline (`|>`) and Fluent Cascade (`~>`) Operators](#chapter-7-the-pipeline--and-fluent-cascade--operators)
* [Part II: Control Flow & Logic](#part-ii-control-flow--logic)
  * [Chapter 8: Conditionals (`if`, `elif`, `else`) & Truthiness](#chapter-8-conditionals-if-elif-else--truthiness)
  * [Chapter 9: Defensive Programming with `guard` Statements](#chapter-9-defensive-programming-with-guard-statements)
  * [Chapter 10: Loops (`while`, Infinite `loop`, Range `for`, `break`, `continue`)](#chapter-10-loops-while-infinite-loop-range-for-break-continue)
  * [Chapter 11: Exhaustive Pattern Matching with `match`](#chapter-11-exhaustive-pattern-matching-with-match)
* [Part III: Functions, Generics & Scopes](#part-iii-functions-generics--scopes)
  * [Chapter 12: Functions, Parameters, Return Types & Expression Bodies (`=>`)](#chapter-12-functions-parameters-return-types--expression-bodies-)
  * [Chapter 13: Generic Functions (`<T>`) & Compile-Time Monomorphization](#chapter-13-generic-functions-t--compile-time-monomorphization)
  * [Chapter 14: Lexical Scopes, Variable Shadowing & Lifetimes](#chapter-14-lexical-scopes-variable-shadowing--lifetimes)
  * [Chapter 15: Module System, Dotted Packages & Scoped Imports](#chapter-15-module-system-dotted-packages--scoped-imports)
* [Part IV: Data Modeling & Object-Oriented Programming](#part-iv-data-modeling--object-oriented-programming)
  * [Chapter 16: Structs: Value Records, Memory Layout & Methods](#chapter-16-structs-value-records-memory-layout--methods)
  * [Chapter 17: Classes: Encapsulation, State & Constructors](#chapter-17-classes-encapsulation-state--constructors)
  * [Chapter 18: Object-Oriented Inheritance (`extends`, `super`, `override`)](#chapter-18-object-oriented-inheritance-extends-super-override)
  * [Chapter 19: Tagged Unions & Enums with Data Payloads](#chapter-19-tagged-unions--enums-with-data-payloads)
  * [Chapter 20: Retroactive Type Extensions (`extend <Type>`)](#chapter-20-retroactive-type-extensions-extend-type)
* [Part V: Memory, Collections & Safety](#part-v-memory-collections--safety)
  * [Chapter 21: Deterministic Scope Cleanup with `defer`](#chapter-21-deterministic-scope-cleanup-with-defer)
  * [Chapter 22: Structured Exception Handling (`try`, `catch`, `finally`, `throw`)](#chapter-22-structured-exception-handling-try-catch-finally-throw)
  * [Chapter 23: Standard Collections: `List<T>`, `Map<K, V>`, `Set<T>`](#chapter-23-standard-collections-listt-mapk-v-sett)
  * [Chapter 24: Specialized Structures: `Stack`, `Queue`, `Deque`, `ByteBuffer`](#chapter-24-specialized-structures-stack-queue-deque-bytebuffer)
  * [Chapter 25: Memory Management: Stack, Linear Arenas & Zero-GC Semantics](#chapter-25-memory-management-stack-linear-arenas--zero-gc-semantics)
* [Part VI: Systems Programming, GUI & Concurrency](#part-vi-systems-programming-gui--concurrency)
  * [Chapter 26: File System Operations (`File`, `Directory`, Streaming I/O)](#chapter-26-file-system-operations-file-directory-streaming-io)
  * [Chapter 27: System Environment, CLI Arguments & Process Control (`Env`, `Process`)](#chapter-27-system-environment-cli-arguments--process-control-env-process)
  * [Chapter 28: Multithreading & Concurrent Channels (`spawn`, `Channel<T>`)](#chapter-28-multithreading--concurrent-channels-spawn-channelt)
  * [Chapter 29: Desktop GUI & Win32 Windowing (`Window.Gui`)](#chapter-29-desktop-gui--win32-windowing-windowgui)
  * [Chapter 30: C Interoperability & Native Windows API Bindings (`#[extern]`)](#chapter-30-c-interoperability--native-windows-api-bindings-extern)
  * [Chapter 31: Advanced Real-World Projects & Idiomatic Patterns](#chapter-31-advanced-real-world-projects--idiomatic-patterns)

---

# Part I: Language Foundations

## Chapter 1: Introduction, Architecture & Toolchain Setup

### 1.1 The Core Philosophy of Aerix
Aerix is designed with three core architectural tenets:
1. **Zero Garbage Collection Overhead:** Predictable, real-time memory behavior with zero GC pauses, deterministic cleanup (`defer`), and cache-friendly linear arenas.
2. **Zero External Compiler Dependencies:** The native PE32+ compiler backend synthesizes AMD64/x86-64 machine instructions and complete Windows `.exe` files directly from memory without invoking external assemblers (MASM/NASM) or linkers (link.exe/ld).
3. **Ergonomic Safety:** Type inference, strict import isolation, algebraic tagged unions, and pattern matching prevent runtime crashes while maintaining the expressiveness of modern languages.

### 1.2 Verifying the Toolchain
Once Aerix is installed, verify your active version from PowerShell or Command Prompt:

```powershell
arx version
```

Expected output:
```text
Aerix Self-Hosting Bootstrap Compiler (arx) v2.2.25
```

---

## Chapter 2: Anatomy of an Aerix Program (`fn main()`, Comments & Docs)

### 2.1 The Program Entry Point
Every executable program begins execution in `fn main()`:

```aerix
fn main() {
    println("Hello, Aerix Systems Programming!")
}
```

### 2.2 Comments & Doc-Comments
Aerix supports three forms of comments:
* **Single-line:** `// Line comment`
* **Multi-line:** `/* Block comment */`
* **Documentation comment:** `/// Doc-comment`

```aerix
/// Computes the linear interpolation between two values.
/// Parameters:
///   `a` - Starting value
///   `b` - Target value
///   `t` - Interpolation factor (0.0 to 1.0)
fn lerp(a: f64, b: f64, t: f64) -> f64 {
    return a + (b - a) * t
}
```

Doc-comments are automatically parsed by the Aerix LSP server (`arx lsp`) and displayed in editor hover tooltips in VS Code and Antigravity IDE.

---

## Chapter 3: Variables, Mutability (`let`, `mut`, `const`) & Type Annotations

### 3.1 Immutability by Default (`let`)
Variables defined with `let` are immutable once assigned:

```aerix
fn main() {
    let app_name = "Aerix Studio"
    // app_name = "Other" // COMPILE ERROR: Cannot reassign immutable variable 'app_name'
}
```

### 3.2 Mutable Bindings (`mut`)
When a value needs to be updated or reassigned, use `mut`:

```aerix
fn main() {
    mut counter = 0
    counter = counter + 1
    println("Counter: {counter}") // 1
}
```

### 3.3 Compile-Time Constants (`const`)
Constants are resolved at compile-time and must specify an explicit type:

```aerix
const MAX_PACKET_SIZE: i64 = 65535
const DEFAULT_TIMEOUT_MS: i64 = 5000
```

---

## Chapter 4: Primitive Types, Sizes & Numeric Precision

Aerix provides fixed-width signed/unsigned integers, IEEE 754 floating-point types, booleans, and characters:

| Primitive | Width | Signed? | Value Range / Description | Literal Example |
| :--- | :--- | :---: | :--- | :--- |
| `i8` | 8 bits | Yes | -128 to 127 | `let a: i8 = -12` |
| `i16` | 16 bits | Yes | -32,768 to 32,767 | `let b: i16 = 1000` |
| `i32` | 32 bits | Yes | -2,147,483,648 to 2,147,483,647 | `let c: i32 = 45000` |
| `i64` | 64 bits | Yes | -9.22e18 to 9.22e18 (Default Integer) | `let d = 42` |
| `u8` | 8 bits | No | 0 to 255 (Byte) | `let byte: u8 = 255` |
| `u16` | 16 bits | No | 0 to 65,535 | `let port: u16 = 8080` |
| `u32` | 32 bits | No | 0 to 4,294,967,295 | `let count: u32 = 100000` |
| `u64` | 64 bits | No | 0 to 18.4e18 | `let mask: u64 = 0xFFFFFFFF` |
| `f32` | 32 bits | Yes | IEEE 754 single precision float | `let speed: f32 = 9.8` |
| `f64` | 64 bits | Yes | IEEE 754 double precision float | `let pi = 3.1415926535` |
| `bool` | 8 bits | N/A | `true` or `false` | `let ok: bool = true` |
| `char` | 32 bits | N/A | 32-bit Unicode scalar value | `let ch: char = 'Z'` |
| `str` | 16 bytes | N/A | UTF-8 pointer + length string slice | `let s: str = "Aerix"` |
| `void` | 0 bytes | N/A | Unit / empty return type | `fn log() -> void` |

---

## Chapter 5: Strings, UTF-8 Encoding, Interpolation & Slicing

Strings in Aerix are immutable, length-prefixed UTF-8 slices:

```aerix
fn main() {
    let lang = "Aerix"
    let year = 2026
    
    // String Interpolation
    let message = "Welcome to {lang} in year {year}!"
    println(message)
    
    // String Slicing: slice(startIndex, endIndex)
    let sample = "High-Performance Systems"
    let prefix = sample.slice(0, 4)
    println(prefix) // "High"
    
    // Common String Utilities
    let text = "   Systems Engineering   "
    println("Trimmed: '{text.trim()}'")
    println("Upper: {text.to_upper()}")
    println("Lower: {text.to_lower()}")
    println("Contains 'Engineering'? {text.contains(\"Engineering\")}")
    println("Replace: {text.replace(\"Systems\", \"Native\")}")
}
```

---

## Chapter 6: Operators, Bitwise Manipulation & Math Functions

### 6.1 Arithmetic & Comparison Operators
* **Arithmetic:** `+`, `-`, `*`, `/`, `%`
* **Comparison:** `==`, `!=`, `<`, `<=`, `>`, `>=`
* **Logical:** `&&`, `||`, `!`

### 6.2 Bitwise Manipulation
```aerix
fn main() {
    let a: i64 = 0b00111100 // 60
    let b: i64 = 0b00001101 // 13
    
    println("AND: {a & b}")   // 12
    println("OR:  {a | b}")   // 61
    println("XOR: {a ^ b}")   // 49
    println("NOT: {~a}")      // -61
    println("SHL: {a << 2}")  // 240
    println("SHR: {a >> 2}")  // 15
}
```

### 6.3 Math Module Functions
```aerix
import Math

fn main() {
    println("Square root: {Math.sqrt(64.0)}")
    println("Power:       {Math.pow(2.0, 8.0)}")
    println("Sine:        {Math.sin(3.14159 / 2.0)}")
    println("Absolute:    {Math.abs(-42)}")
    println("Minimum:     {Math.min(10, 20)}")
    println("Maximum:     {Math.max(10, 20)}")
}
```

---

## Chapter 7: The Pipeline (`|>`) and Fluent Cascade (`~>`) Operators

### 7.1 Pipeline Operator (`|>`)
The pipeline operator forwards the left-hand expression as the first argument of the right-hand function call:

```aerix
fn add_five(n: i64) -> i64  { return n + 5 }
fn double(n: i64) -> i64    { return n * 2 }
fn square(n: i64) -> i64    { return n * n }

fn main() {
    // Equivalent to: square(double(add_five(10)))
    let val = 10 |> add_five() |> double() |> square()
    println("Pipeline Result: {val}") // ((10 + 5) * 2)^2 = 30^2 = 900
}
```

### 7.2 Fluent Cascade Operator (`~>`)
The cascade operator invokes a method on an object while returning the object reference itself, simplifying builder patterns:

```aerix
class HttpConfig {
    pub endpoint: str
    pub retries: i64
    
    init() {
        self.endpoint = "localhost"
        self.retries = 1
    }
    
    pub fn set_endpoint(url: str) { self.endpoint = url }
    pub fn set_retries(r: i64)    { self.retries = r }
}

fn main() {
    let conf = HttpConfig()
        ~>set_endpoint("https://api.aerix.org")
        ~>set_retries(3)
        
    println("Endpoint: {conf.endpoint}, Retries: {conf.retries}")
}
```

---

# Part II: Control Flow & Logic

## Chapter 8: Conditionals (`if`, `elif`, `else`) & Truthiness

Aerix conditional statements require boolean expressions (no implicit integer-to-boolean conversions):

```aerix
fn check_temperature(temp_celsius: f64) {
    if temp_celsius < 0.0 {
        println("Freezing conditions")
    } elif temp_celsius >= 100.0 {
        println("Boiling conditions")
    } else {
        println("Normal liquid range")
    }
}
```

---

## Chapter 9: Defensive Programming with `guard` Statements

The `guard` statement validates preconditions at the top of functions, enforcing early return and eliminating deeply nested `if` blocks:

```aerix
fn authenticate(token: str, user_id: i64) {
    guard token != "" else {
        println("Authentication failed: empty token")
        return
    }
    
    guard user_id > 0 else {
        println("Authentication failed: invalid user ID")
        return
    }
    
    println("Authenticated user #{user_id}")
}
```

---

## Chapter 10: Loops (`while`, Infinite `loop`, Range `for`, `break`, `continue`)

### 10.1 While Loops
```aerix
fn main() {
    mut counter = 0
    while counter < 5 {
        print("{counter} ")
        counter = counter + 1
    }
    println("")
}
```

### 10.2 Numeric Range For Loops
Ranges use the `start..end` syntax (inclusive start, exclusive end):

```aerix
fn main() {
    for i in 0..5 {
        println("Iteration: {i}")
    }
}
```

### 10.3 Break and Continue
```aerix
fn main() {
    for i in 0..10 {
        if i == 3 { continue } // Skip 3
        if i == 7 { break }    // Stop at 7
        print("{i} ")
    }
    println("") // Outputs: 0 1 2 4 5 6
}
```

---

## Chapter 11: Exhaustive Pattern Matching with `match`

The `match` expression provides compile-time exhaustive pattern matching over primitive values and tagged enums:

```aerix
fn describe_http_status(code: i64) -> str {
    match code {
        case 200 => "200 OK"
        case 301 => "301 Moved Permanently"
        case 404 => "404 Not Found"
        case 500 => "500 Internal Server Error"
        case _   => "Unknown Status Code"
    }
}

fn main() {
    println(describe_http_status(200)) // "200 OK"
}
```

---

# Part III: Functions, Generics & Scopes

## Chapter 12: Functions, Parameters, Return Types & Expression Bodies (`=>`)

### 12.1 Standard Block Functions
```aerix
fn add(a: i64, b: i64) -> i64 {
    return a + b
}
```

### 12.2 Expression Body Shorthand (`=>`)
For single-expression functions:

```aerix
fn square(x: i64) -> i64 => x * x
fn is_even(n: i64) -> bool => n % 2 == 0
```

---

## Chapter 13: Generic Functions (`<T>`) & Compile-Time Monomorphization

Aerix functions can be parameterized over types. The compiler monomorphizes each generic call site, generating specialized native machine code without runtime boxing:

```aerix
fn swap<T>(items: List<T>, i: i64, j: i64) {
    let temp = items.get(i)
    items.set(i, items.get(j))
    items.set(j, temp)
}
```

---

## Chapter 14: Lexical Scopes, Variable Shadowing & Lifetimes

Variables exist within their declaring curly-brace `{ ... }` scope:

```aerix
fn main() {
    let x = 10
    {
        let x = 20 // Shadows outer 'x' within this block
        println("Inner: {x}") // 20
    }
    println("Outer: {x}")     // 10
}
```

---

## Chapter 15: Module System, Dotted Packages & Scoped Imports

Aerix strictly isolates imported symbols to prevent namespace pollution:

```aerix
// 1. Selective symbol import (only 'now' is exposed)
from Time import now

// 2. Submodule import (exposes 'Window.Gui' and 'Gui'; 'Window' remains unimported)
import Window.Gui

// 3. Aliased import
import Math as M

fn main() {
    let t0 = now()
    let root = M.sqrt(100.0)
    println("Current time: {t0}, Square root: {root}")
}
```

---

# Part IV: Data Modeling & Object-Oriented Programming

## Chapter 16: Structs: Value Records, Memory Layout & Methods

Structs in Aerix represent contiguous value data:

```aerix
struct Vector2D {
    pub x: f64
    pub y: f64
    
    init(x: f64, y: f64) {
        self.x = x
        self.y = y
    }
    
    pub fn length() -> f64 {
        return Math.sqrt(self.x * self.x + self.y * self.y)
    }
}

fn main() {
    let v = Vector2D(3.0, 4.0)
    println("Vector length: {v.length()}") // 5.0
}
```

---

## Chapter 17: Classes: Encapsulation, State & Constructors

Classes represent heap-allocated reference objects:

```aerix
class BankAccount {
    priv balance: i64
    pub account_id: str
    
    init(id: str, initial_deposit: i64) {
        self.account_id = id
        self.balance = initial_deposit
    }
    
    pub fn deposit(amount: i64) {
        if amount > 0 { self.balance = self.balance + amount }
    }
    
    pub fn get_balance() -> i64 {
        return self.balance
    }
}
```

---

## Chapter 18: Object-Oriented Inheritance (`extends`, `super`, `override`)

Classes support single inheritance with method overriding:

```aerix
class Animal {
    pub name: str
    init(name: str) { self.name = name }
    
    pub fn speak() -> str { return "..." }
}

class Dog extends Animal {
    init(name: str) { super(name) }
    
    pub override fn speak() -> str {
        return "Woof! My name is {self.name}"
    }
}

fn main() {
    let pet = Dog("Rex")
    println(pet.speak()) // "Woof! My name is Rex"
}
```

---

## Chapter 19: Tagged Unions & Enums with Data Payloads

Enums can store payload data variants:

```aerix
enum Command {
    Quit,
    Move(x: i64, y: i64),
    SendMessage(text: str)
}

fn execute_command(cmd: Command) {
    match cmd {
        case Quit => println("Shutting down...")
        case Move(x, y) => println("Moving to ({x}, {y})")
        case SendMessage(msg) => println("Message: {msg}")
    }
}

fn main() {
    execute_command(Command.Move(100, 250))
}
```

---

## Chapter 20: Retroactive Type Extensions (`extend <Type>`)

You can add methods to any struct or class after its definition:

```aerix
extend Vector2D {
    pub fn scale(factor: f64) -> Vector2D {
        return Vector2D(self.x * factor, self.y * factor)
    }
}

fn main() {
    let v1 = Vector2D(2.0, 3.0)
    let v2 = v1.scale(2.0)
    println("Scaled: ({v2.x}, {v2.y})") // (4.0, 6.0)
}
```

---

# Part V: Memory, Collections & Safety

## Chapter 21: Deterministic Scope Cleanup with `defer`

The `defer` statement registers a cleanup statement that executes right before the enclosing block exits, in Last-In First-Out (LIFO) order:

```aerix
fn process_resource() {
    println("1. Opening resource")
    defer println("4. Closed resource")
    defer println("3. Flushed buffer")
    
    println("2. Writing data...")
}

fn main() {
    process_resource()
}
```

---

## Chapter 22: Structured Exception Handling (`try`, `catch`, `finally`, `throw`)

```aerix
fn parse_positive_number(val: i64) -> i64 {
    if val <= 0 {
        throw "Value must be positive!"
    }
    return val
}

fn main() {
    try {
        let n = parse_positive_number(-5)
        println("Parsed: {n}")
    } catch err {
        println("Caught error: {err}")
    } finally {
        println("Cleanup complete.")
    }
}
```

---

## Chapter 23: Standard Collections: `List<T>`, `Map<K, V>`, `Set<T>`

```aerix
fn main() {
    // 1. Dynamic Growable List<T>
    let list = List<str>()
    list.push("Alpha")
    list.push("Beta")
    println("List size: {list.len()}, item: {list.get(0)}")
    
    // 2. Hash Map<K, V>
    let map = Map<str, i64>()
    map.insert("CPU", 8)
    map.insert("RAM", 32)
    println("RAM: {map.get(\"RAM\")} GB")
    
    // 3. Unique Element Set<T>
    let set = Set<str>()
    set.add("admin")
    println("Is admin? {set.contains(\"admin\")}")
}
```

---

## Chapter 24: Specialized Structures: `Stack`, `Queue`, `Deque`, `ByteBuffer`

```aerix
fn main() {
    // LIFO Stack
    let st = Stack<i64>()
    st.push(10)
    st.push(20)
    println("Popped: {st.pop()}") // 20
    
    // Double-Ended Queue (Deque)
    let dq = Deque<str>()
    dq.push_back("End")
    dq.push_front("Start")
    println("Front: {dq.pop_front()}") // "Start"
}
```

---

## Chapter 25: Memory Management: Stack, Linear Arenas & Zero-GC Semantics

Aerix executes without a background garbage collector. Memory is organized into:
1. **Stack Frames:** Local variables and structs are allocated on the fast CPU stack.
2. **Deterministic RAII & Defer:** Destructors and `defer` handlers execute immediately upon scope exit.
3. **Linear Arenas:** Batch allocations for short-lived workloads:
   ```aerix
   let arena = LinearArena(65536) // 64 KB block
   // All arena memory is reclaimed instantly when arena drops
   ```

---

# Part VI: Systems Programming, GUI & Concurrency

## Chapter 26: File System Operations (`File`, `Directory`, Streaming I/O)

```aerix
fn main() {
    let filename = "output.txt"
    File.write_string(filename, "First line of text\nSecond line")
    
    if File.exists(filename) {
        let content = File.read_string(filename)
        println("Read from file:\n{content}")
    }
}
```

---

## Chapter 27: System Environment, CLI Arguments & Process Control (`Env`, `Process`)

```aerix
fn main() {
    // Querying Environment Variables
    let user = Env.get("USERNAME")
    println("Current User: {user}")
    
    // Reading Command-Line Arguments
    let total_args = Env.arg_count()
    println("Total arguments: {total_args}")
    for i in 0..total_args {
        println("Arg #{i}: {Env.arg(i)}")
    }
}
```

---

## Chapter 28: Multithreading & Concurrent Channels (`spawn`, `Channel<T>`)

Native Win32 threads communicate over bounded lock-free channels:

```aerix
fn background_task(id: i64, queue: Channel<str>) {
    queue.send("Task #{id} finished successfully.")
}

fn main() {
    mut queue = Channel<str>(4)
    
    let worker1 = spawn background_task(1, queue)
    let worker2 = spawn background_task(2, queue)
    
    println(queue.recv())
    println(queue.recv())
    
    arx_thread_join(worker1)
    arx_thread_join(worker2)
    queue.close()
}
```

---

## Chapter 29: Desktop GUI & Win32 Windowing (`Window.Gui`)

Create native Windows GUI applications without external dependencies:

```aerix
from Window.Gui import createWindow, AppWindow, Button, TextBox

fn main() {
    let hwnd = createWindow("Aerix Desktop Studio", 800, 600)
    let app = AppWindow(hwnd)
    
    let tb = TextBox(hwnd, 50, 50, 300, 30, "Welcome!")
    let btn = Button(hwnd, 360, 50, 100, 30, "Click Me")
    
    app.show()
    app.run()
}
```

---

## Chapter 30: C Interoperability & Native Windows API Bindings (`#[extern]`)

Directly invoke native DLL exports:

```aerix
#[extern("user32.dll", "MessageBoxA")]
fn MessageBoxA(hwnd: i64, text: str, caption: str, uType: i64) -> i64

fn main() {
    MessageBoxA(0, "Native Dialog Message", "Aerix Systems", 0)
}
```

---

## Chapter 31: Advanced Real-World Projects & Idiomatic Patterns

### Complete Project: High-Performance Multi-Threaded TCP Server
```aerix
import Socket

fn handle_connection(client_fd: i64) {
    defer Socket.close(client_fd)
    
    let request = Socket.recv(client_fd, 1024)
    if request.len() > 0 {
        Socket.send(client_fd, "AERIX_OK: " + request)
    }
}

fn main() {
    let server_fd = Socket.listen(8080)
    println("Aerix Server listening on port 8080...")
    
    while true {
        let client_fd = Socket.accept(server_fd)
        if client_fd >= 0 {
            spawn handle_connection(client_fd)
        }
    }
}
```

---

*You have completed the Complete Aerix Handbook. You are now prepared to build high-performance systems with Aerix!*
