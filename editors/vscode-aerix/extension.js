/**
 * Aerix Language Support — Ultra-Charged IntelliSense Engine
 * Official Extension for Aerix (.arx) Native Systems Language
 * Features:
 *  - 100% Full Type System: Primitives, Unsigned, Floats, SIMD (f32x4), Generics (T), and Channels
 *  - Context-Aware Autocompletions:
 *      * Dot-Access (obj., self.) for fields, methods, properties
 *      * Cascade Operator (~>) completions for fluent mutation chaining
 *      * Spawn completions for thread worker functions
 *      * Trait & Extend completions for classes and interfaces
 *      * Match arms and Enum variant completions
 *  - High-Precision Markdown Hover Documentation:
 *      * Physical struct memory layout, byte offsets, and L1 cache-line density
 *      * Function overloads and constructors
 *      * Operators (~>, |>, ??, ?., op +, op ==)
 *      * Concurrency primitives (spawn, Channel<T>, arx_channel_*)
 *  - Multi-Signature Help with Active Parameter Tracking
 *  - Hierarchical Document Symbols (Classes, Traits, Enums, Extensions, Properties, Methods)
 *  - Real-Time Inlay Hints for inferred variable types and function parameter labels
 *  - On-the-Fly Fast Diagnostic Linter via `arx check`
 */

const vscode = require('vscode');
const cp = require('child_process');
const path = require('path');

/**
 * Aerix Language Keywords & Modifiers
 */
const AERIX_KEYWORDS = [
    { name: 'fn', detail: 'Function Declaration', doc: 'Defines a top-level or method function.\n```aerix\nfn calculate(a: i64, b: i64) -> i64 => a * b\n```' },
    { name: 'let', detail: 'Immutable Variable', doc: 'Binds an immutable variable. Cannot be reassigned once initialized.\n```aerix\nlet max_limit = 100\n```' },
    { name: 'mut', detail: 'Mutable Variable', doc: 'Declares a mutable variable that can be reassigned.\n```aerix\nlet mut counter = 0\ncounter += 1\n```' },
    { name: 'const', detail: 'Compile-Time Constant', doc: 'Defines an immutable constant evaluated at compile-time.\n```aerix\nconst MAX_SIZE: i32 = 1024\n```' },
    { name: 'class', detail: 'Class Declaration', doc: 'Defines an object-oriented class with zero-cost C struct layout, methods, and RAII lifecycle.\n```aerix\nclass Point {\n    pub x: f64\n    pub y: f64\n\n    init(x: f64, y: f64) {\n        self.x = x\n        self.y = y\n    }\n}\n```' },
    { name: 'trait', detail: 'Trait Interface Contract', doc: 'Defines an abstract trait contract of method signatures with compile-time zero-cost conformance.\n```aerix\ntrait Inspectable {\n    fn inspect() -> void\n}\n```' },
    { name: 'implements', detail: 'Trait Implementation', doc: 'Specifies trait contracts fulfilled by a class.\n```aerix\nclass Person implements Inspectable, Serializable {\n```' },
    { name: 'extends', detail: 'Class Inheritance', doc: 'Specifies the base class for single inheritance polymorphism.' },
    { name: 'extend', detail: 'Type Extension', doc: 'Retrofits new methods onto existing classes or types without modification.\n```aerix\nextend Vector2D {\n    pub fn manhattan_distance() -> i64 => self.x + self.y\n}\n```' },
    { name: 'prop', detail: 'Reactive Property', doc: 'Defines a class property with getter and setter accessors and validation.\n```aerix\npub prop clearance: i64 {\n    get => self.raw_clearance\n    set(val) {\n        guard val >= 1 else { return }\n        self.raw_clearance = val\n    }\n}\n```' },
    { name: 'op', detail: 'User-Defined Operator Overloading', doc: 'Overloads standard arithmetic or comparison operators for class types.\n```aerix\npub op +(other: Vector2D) -> Vector2D {\n    return Vector2D(self.x + other.x, self.y + other.y)\n}\n```' },
    { name: 'spawn', detail: 'Native Thread Spawning', doc: 'Asynchronously executes a function call on a native operating system thread with zero runtime overhead.\n```aerix\nlet thread_id = spawn telemetry_worker(1, ch.handle, 50);\narx_thread_join(thread_id);\n```' },
    { name: 'guard', detail: 'Guard Statement (Fail-Fast Flow)', doc: 'Asserts an invariant and requires early exit if false, eliminating deep nesting.\n```aerix\nguard agent.clearance >= 5 else {\n    return false\n}\n```' },
    { name: 'match', detail: 'Exhaustive Pattern Matching', doc: 'Matches enum tagged union variants and destructures payloads with compile-time safety.\n```aerix\nmatch status {\n    Active(bw, peers) => println("Active with {bw} Mbps"),\n    _ => println("Other state")\n}\n```' },
    { name: 'enum', detail: 'Tagged Union Enum', doc: 'Defines an algebraic data type / tagged union with structured payload fields.\n```aerix\nenum NodeStatus {\n    Offline,\n    Standby(battery: i64),\n    Active(bandwidth: i64, peers: i64)\n}\n```' },
    { name: 'defer', detail: 'Scoped Resource Cleanup', doc: 'Schedules statements to execute in deterministic LIFO reverse order upon exiting scope.\n```aerix\ndefer println("Socket disconnected.")\n```' },
    { name: 'pub', detail: 'Public Visibility', doc: 'Grants public visibility to a class field, method, or property.' },
    { name: 'priv', detail: 'Private Visibility', doc: 'Restricts field or method access strictly to the declaring class.' },
    { name: 'static', detail: 'Static Member', doc: 'Declares a class field or method that belongs to the class type itself.' },
    { name: 'virtual', detail: 'Virtual Method', doc: 'Declares a polymorphic method dynamically dispatched via vtable.' },
    { name: 'override', detail: 'Override Method', doc: 'Explicitly overrides a virtual method defined in a base class.' },
    { name: 'init', detail: 'Constructor', doc: 'Defines the constructor method for initializing a class instance.' },
    { name: 'drop', detail: 'Destructor (RAII)', doc: 'Defines deterministic cleanup invoked when a class instance exits scope.' },
    { name: 'if', detail: 'Conditional Branch', doc: 'Executes a block if condition evaluates to true.' },
    { name: 'else', detail: 'Alternative Branch', doc: 'Executes when preceding `if` condition evaluates to false.' },
    { name: 'elif', detail: 'Else-If Branch', doc: 'Chains additional conditional branches.' },
    { name: 'while', detail: 'While Loop', doc: 'Loops repeatedly while condition holds true.' },
    { name: 'for', detail: 'Range Loop', doc: 'Iterates through an inclusive or half-open numeric range.\n```aerix\nfor i in 1..=10 {\n    println(i)\n}\n```' },
    { name: 'in', detail: 'Range Membership', doc: 'Used with `for` loops: `for item in 0..count`' },
    { name: 'loop', detail: 'Infinite Loop', doc: 'Executes an unconditional loop until terminated with `break`.' },
    { name: 'return', detail: 'Return Statement', doc: 'Returns a value or exits from the enclosing function.' },
    { name: 'break', detail: 'Break Loop', doc: 'Immediately terminates the innermost enclosing loop.' },
    { name: 'continue', detail: 'Continue Loop', doc: 'Skips directly to the next iteration of the loop.' },
    { name: 'as', detail: 'Explicit Type Cast', doc: 'Explicitly casts an expression to a target primitive or string type:\n```aerix\nlet val = 42 as str\nlet raw = ch_val as i64\n```' },
    { name: 'cinclude', detail: 'C Header Inclusion', doc: 'Directly includes an ANSI C header without overhead.\n```aerix\ncinclude "<math.h>"\n```' },
    { name: 'cextern', detail: 'C External Binding', doc: 'Declares an external C symbol or library function.' },
    { name: 'get', detail: 'Property Getter', doc: 'Returns the value of a property accessor.' },
    { name: 'set', detail: 'Property Setter', doc: 'Defines the mutation logic and validation for a property accessor.' },
    { name: 'try', detail: 'Try Block (Exception Frame)', doc: 'Encloses fallible code inside an exception frame:\n```aerix\ntry {\n    risky_operation();\n} catch err {\n    println("Caught: {err}");\n} finally {\n    cleanup();\n}\n```' },
    { name: 'catch', detail: 'Catch Handler', doc: 'Catches exceptions thrown in the preceding try block:\n```aerix\ncatch err {\n    println("Error: {err}");\n}\n```' },
    { name: 'finally', detail: 'Finally Block (Optional Guarantee)', doc: 'Guaranteed execution block running on normal completion or after exception handling:\n```aerix\nfinally {\n    db.close();\n}\n```' },
    { name: 'throw', detail: 'Throw Exception', doc: 'Raises an exception and unwinds to the nearest enclosing try-catch block:\n```aerix\nthrow "Invalid parameter value";\n```' },
    { name: 'import', detail: 'Module / Source Import', doc: 'Imports an inbuilt language module or a relative Aerix source file:\n```aerix\nimport Math;\nimport { calculate_percentage, format_stat } from "./helper.arx";\n```' },
    { name: 'from', detail: 'Import Source Clause', doc: 'Specifies the source file path in selective imports:\n```aerix\nimport { a, b } from "./utils.arx";\n```' }
];

/**
 * Aerix Full Type System
 */
const AERIX_TYPES = [
    { name: 'u8', detail: '8-bit Unsigned Integer (uint8_t)', doc: 'Range: 0 to 255 (1 byte, raw byte buffer).' },
    { name: 'u16', detail: '16-bit Unsigned Integer (uint16_t)', doc: 'Range: 0 to 65,535 (2 bytes).' },
    { name: 'u32', detail: '32-bit Unsigned Integer (uint32_t)', doc: 'Range: 0 to 4,294,967,295 (4 bytes).' },
    { name: 'u64', detail: '64-bit Unsigned Integer (uint64_t)', doc: 'Full 64-bit unsigned integer (8 bytes).' },
    { name: 'uint', detail: 'Word-size Unsigned Integer (uint64_t)', doc: 'Default system word unsigned integer (alias for `u64`).' },
    { name: 'usize', detail: 'Pointer-size Unsigned Integer', doc: 'Word-size unsigned integer matching architecture pointer width.' },
    { name: 'isize', detail: 'Pointer-size Signed Integer', doc: 'Word-size signed integer matching architecture pointer width.' },
    { name: 'i8', detail: '8-bit Signed Integer (int8_t)', doc: 'Range: -128 to 127 (1 byte).' },
    { name: 'i16', detail: '16-bit Signed Integer (int16_t)', doc: 'Range: -32,768 to 32,767 (2 bytes).' },
    { name: 'i32', detail: '32-bit Signed Integer (int32_t)', doc: 'Range: -2,147,483,648 to 2,147,483,647 (4 bytes).' },
    { name: 'i64', detail: '64-bit Signed Integer (int64_t)', doc: 'Full 64-bit signed integer (8 bytes).' },
    { name: 'int', detail: 'Word-size Signed Integer', doc: 'Default system word integer (alias for `i64`).' },
    { name: 'f32', detail: '32-bit Floating Point (float)', doc: 'Single-precision IEEE 754 floating point number (4 bytes).' },
    { name: 'f64', detail: '64-bit Floating Point (double)', doc: 'Double-precision IEEE 754 floating point number (8 bytes).' },
    { name: 'f32x4', detail: '4-Lane SIMD Vector', doc: 'Hardware 128-bit 4-lane single precision float vector (SIMD intrinsics).' },
    { name: 'f64x2', detail: '2-Lane SIMD Vector', doc: 'Hardware 128-bit 2-lane double precision float vector (SIMD intrinsics).' },
    { name: 'float', detail: 'Standard Float', doc: 'Default floating-point type (alias for `f64`).' },
    { name: 'bool', detail: 'Boolean Type', doc: 'Logical truth value (`true` or `false`, 1 byte).' },
    { name: 'char', detail: 'Character Type', doc: '8-bit ASCII character literal (1 byte, e.g. `\'A\'`).' },
    { name: 'str', detail: 'Immutable String Slice', doc: 'UTF-8 string pointer (`const char*`) with interpolation `{var}` support.' },
    { name: 'void', detail: 'Unit / Void Type', doc: 'Represents absence of value or empty function return.' },
    { name: 'null', detail: 'Null Reference', doc: 'Null pointer literal for optional types (`T?`).' },
    { name: 'Channel', detail: 'Generic Thread-Safe Channel<T>', doc: 'Bounded multi-producer multi-consumer thread-safe channel for concurrent data passing.' },
    { name: 'List', detail: 'Generic Dynamic Array List<T>', doc: 'Contiguous growable dynamic array with indexing, slicing [start..end], sort(), reverse(), contains(), and iterator support.' },
    { name: 'Map', detail: 'Robin Hood Hash Table Map<K, V>', doc: 'Dense open-addressing hash map with backward-shift deletion, map[k] = v, map[k], has_key(), remove(), keys(), values().' },
    { name: 'Set', detail: 'Hash Set<T>', doc: 'Zero-payload hash set with add(), has(), remove(), and set algebra: union(), intersection(), difference().' },
    { name: 'Stack', detail: 'LIFO Stack<T>', doc: 'Last-In First-Out container with push(), pop(), peek(), len(), is_empty().' },
    { name: 'Queue', detail: 'FIFO Queue<T>', doc: 'First-In First-Out queue container with push(), pop(), peek(), len(), is_empty().' },
    { name: 'Deque', detail: 'Double-Ended Queue Deque<T>', doc: 'Double-ended ring buffer with push_back(), push_front(), pop_back(), pop_front(), peek_front(), peek_back().' },
    { name: 'ByteBuffer', detail: 'Binary Byte Stream ByteBuffer', doc: 'Dynamic byte vector with little-endian & big-endian serialization: write_u8(), write_i32_le(), write_i32_be(), write_f64_le(), read_u8(), read_i32_le(), read_i32_be(), seek(), reset().' },
    { name: 'String', detail: 'Mutable Owned String', doc: 'Dynamic UTF-8 string with fluent API: trim(), to_upper(), to_lower(), replace(), split(), slice(), repeat(), char_at(), contains(), starts_with(), ends_with().' }
];

/**
 * Aerix Built-In Functions & Runtime APIs
 */
const AERIX_BUILTINS = [
    {
        name: 'println',
        detail: 'println(val?: any) -> void',
        doc: 'Prints formatted values to standard output followed by a newline.\n' +
             'Supports string interpolation with variable substitution:\n' +
             '```aerix\n' +
             'println("User: {self.name}, Clearance: {self.clearance}")\n' +
             '```'
    },
    {
        name: 'print',
        detail: 'print(val: any) -> void',
        doc: 'Prints formatted values to standard output without appending a newline.'
    },
    {
        name: 'eprintln',
        detail: 'eprintln(val: any) -> void',
        doc: 'Prints formatted values directly to stderr followed by a newline.'
    },
    {
        name: 'arx_channel_new',
        detail: 'arx_channel_new(capacity: i64) -> i64',
        doc: 'Creates a new thread-safe bounded channel ring-buffer protected by condition variables.\nReturns an integer handle.'
    },
    {
        name: 'arx_channel_send',
        detail: 'arx_channel_send(ch_handle: i64, val: i64) -> void',
        doc: 'Pushes an integer or pointer payload into a bounded channel, blocking synchronously if full.'
    },
    {
        name: 'arx_channel_recv',
        detail: 'arx_channel_recv(ch_handle: i64) -> i64',
        doc: 'Pulls an item from a bounded channel, blocking until an item is pushed or the channel closes.'
    },
    {
        name: 'arx_channel_close',
        detail: 'arx_channel_close(ch_handle: i64) -> void',
        doc: 'Closes a channel and wakes all pending consumer or producer worker threads.'
    },
    {
        name: 'arx_channel_free',
        detail: 'arx_channel_free(ch_handle: i64) -> void',
        doc: 'Closes the channel, destroys synchronization mutexes, and frees underlying ring buffer memory.'
    },
    {
        name: 'arx_thread_join',
        detail: 'arx_thread_join(handle: i64) -> void',
        doc: 'Waits synchronously for a spawned worker thread to terminate and reclaims OS thread resources.'
    },
    {
        name: 'arx_sleep_ms',
        detail: 'arx_sleep_ms(ms: i64) -> void',
        doc: 'Suspends the calling thread for the specified duration in milliseconds.'
    },
    {
        name: 'arx_time_now_ns',
        detail: 'arx_time_now_ns() -> i64',
        doc: 'Returns high-resolution hardware monotonic clock timestamp in nanoseconds.'
    },
    {
        name: 'arx_time_now',
        detail: 'arx_time_now() -> f64',
        doc: 'Returns high-resolution timestamp in seconds with sub-microsecond precision.'
    },
    {
        name: 'input',
        detail: 'input(prompt?: str) -> T (Dynamic)',
        doc: 'Reads user input from the console with target-typed parsing.'
    },
    {
        name: 'readln',
        detail: 'readln() -> T (Dynamic)',
        doc: 'Reads a line from standard input without a prompt.'
    },
    {
        name: 'typeof',
        detail: 'typeof(expr: any) -> str',
        doc: 'Returns the compile-time type name of any expression as a string.'
    },
    {
        name: 'assert',
        detail: 'assert(cond: bool, msg?: str) -> void',
        doc: 'Asserts a boolean condition; halts with panic if false.'
    },
    {
        name: 'panic',
        detail: 'panic(msg: str) -> void',
        doc: 'Immediately halts program execution and outputs formatted panic backtrace to stderr.'
    },
    {
        name: 'len',
        detail: 'len(arr: any) -> i64',
        doc: 'Returns the element count of an array, buffer, or string.'
    },
    {
        name: 'sizeof',
        detail: 'sizeof(type: any) -> i64',
        doc: 'Returns the physical memory byte size of a type or instance.'
    },
    {
        name: 'arx_canvas_set_pixel',
        detail: 'arx_canvas_set_pixel(x: i64, y: i64, r: i64, g: i64, b: i64, a: i64) -> void',
        doc: 'Draws a single pixel onto the HTML5 / WebAssembly canvas at `(x, y)` with RGBA color channels (0-255).\n' +
             '```aerix\n' +
             'arx_canvas_set_pixel(100, 50, 0, 220, 255, 255);\n' +
             '```'
    },
    {
        name: 'arx_canvas_fill_rect',
        detail: 'arx_canvas_fill_rect(x: i64, y: i64, w: i64, h: i64, r: i64, g: i64, b: i64, a: i64) -> void',
        doc: 'Fills a rectangular region on the HTML5 / WebAssembly canvas with RGBA color channels (0-255).\n' +
             '```aerix\n' +
             'arx_canvas_fill_rect(10, 10, 80, 40, 30, 144, 255, 255);\n' +
             '```'
    },
    {
        name: 'arx_canvas_clear',
        detail: 'arx_canvas_clear(r: i64, g: i64, b: i64, a: i64) -> void',
        doc: 'Clears the entire HTML5 / WebAssembly canvas with a solid RGBA color background.\n' +
             '```aerix\n' +
             'arx_canvas_clear(13, 17, 23, 255); // Dark GitHub Slate\n' +
             '```'
    },
    {
        name: 'arx_now_ms',
        detail: 'arx_now_ms() -> i64',
        doc: 'Returns monotonic timestamp in milliseconds from `performance.now()` in WebAssembly runtime or system clock.'
    },
    {
        name: 'volatile_read_u32',
        detail: 'volatile_read_u32(addr: u64) -> u32',
        doc: 'Reads a 32-bit unsigned word directly from a memory-mapped hardware peripheral register without compiler caching.'
    },
    {
        name: 'volatile_write_u32',
        detail: 'volatile_write_u32(addr: u64, val: u32) -> void',
        doc: 'Writes a 32-bit unsigned word directly to a memory-mapped hardware peripheral register with volatile semantics.'
    },
    {
        name: 'volatile_load_u32',
        detail: 'volatile_load_u32(addr: u64) -> u32',
        doc: 'Reads a 32-bit word from a volatile hardware register (alias for `volatile_read_u32`).'
    },
    {
        name: 'volatile_store_u32',
        detail: 'volatile_store_u32(addr: u64, val: u32) -> void',
        doc: 'Writes a 32-bit word to a volatile hardware register (alias for `volatile_write_u32`).'
    },
    {
        name: 'address_of',
        detail: 'address_of(val: any) -> u64',
        doc: 'Returns the direct physical memory address (`uintptr_t`) of a variable or struct instance.'
    },
    {
        name: 'f32x4',
        detail: 'f32x4(x: f32, y: f32, z: f32, w: f32) -> f32x4',
        doc: 'Constructs a 128-bit 4-lane single precision float SIMD vector. Supports overloaded operators `+`, `-`, `*`, `/` and dot(), cross(), length(), normalize(), min(), max().'
    },
    {
        name: 'f64x2',
        detail: 'f64x2(x: f64, y: f64) -> f64x2',
        doc: 'Constructs a 128-bit 2-lane double precision float SIMD vector. Supports overloaded operators `+`, `-`, `*`, `/` and dot(), length(), normalize(), min(), max().'
    },
    // Standard Math Functions (Math module exports)
    { name: 'abs', detail: 'abs(x: f64) -> f64', doc: 'Returns the absolute value of $x$.' },
    { name: 'min', detail: 'min(a: f64, b: f64) -> f64', doc: 'Returns the smaller of two floating-point numbers $a$ and $b$.' },
    { name: 'max', detail: 'max(a: f64, b: f64) -> f64', doc: 'Returns the larger of two floating-point numbers $a$ and $b$.' },
    { name: 'clamp', detail: 'clamp(val: f64, low: f64, high: f64) -> f64', doc: 'Clamps $val$ within the closed interval $[low, high]$.' },
    { name: 'sign', detail: 'sign(x: f64) -> f64', doc: 'Returns $1.0$ if $x > 0$, $-1.0$ if $x < 0$, or $0.0$.' },
    { name: 'is_even', detail: 'is_even(n: i64) -> bool', doc: 'Returns true if integer $n$ is divisible by 2.' },
    { name: 'is_odd', detail: 'is_odd(n: i64) -> bool', doc: 'Returns true if integer $n$ is not divisible by 2.' },
    { name: 'floor', detail: 'floor(x: f64) -> f64', doc: 'Returns the largest integer less than or equal to $x$.' },
    { name: 'ceil', detail: 'ceil(x: f64) -> f64', doc: 'Returns the smallest integer greater than or equal to $x$.' },
    { name: 'round', detail: 'round(x: f64) -> f64', doc: 'Rounds $x$ to the nearest whole integer.' },
    { name: 'trunc', detail: 'trunc(x: f64) -> f64', doc: 'Truncates $x$ toward zero.' },
    { name: 'fract', detail: 'fract(x: f64) -> f64', doc: 'Returns the fractional part of $x$ ($x - \\text{floor}(x)$).' },
    { name: 'lerp', detail: 'lerp(a: f64, b: f64, t: f64) -> f64', doc: 'Performs linear interpolation between $a$ and $b$ using parameter $t$.' },
    { name: 'smoothstep', detail: 'smoothstep(edge0: f64, edge1: f64, x: f64) -> f64', doc: 'Performs Hermite smooth interpolation between $edge0$ and $edge1$.' },
    { name: 'sqrt', detail: 'sqrt(x: f64) -> f64', doc: 'Calculates the square root $\\sqrt{x}$ with high-precision convergence.' },
    { name: 'cbrt', detail: 'cbrt(x: f64) -> f64', doc: 'Calculates the cube root $\\sqrt[3]{x}$.' },
    { name: 'hypot', detail: 'hypot(a: f64, b: f64) -> f64', doc: 'Calculates Euclidean distance / hypotenuse $\\sqrt{a^2 + b^2}$.' },
    { name: 'pow', detail: 'pow(base: f64, exp: i64) -> f64', doc: 'Raises floating-point $base$ to integer exponent $exp$.' },
    { name: 'factorial', detail: 'factorial(n: i64) -> i64', doc: 'Calculates factorial $n! = n \\times (n-1) \\times \\dots \\times 1$.' },
    { name: 'nPr', detail: 'nPr(n: i64, r: i64) -> i64', doc: 'Calculates permutations $P(n, r) = \\frac{n!}{(n-r)!}$.' },
    { name: 'nCr', detail: 'nCr(n: i64, r: i64) -> i64', doc: 'Calculates combinations / binomial coefficient $C(n, r) = \\frac{n!}{r!(n-r)!}$.' },
    { name: 'gcd', detail: 'gcd(a: i64, b: i64) -> i64', doc: 'Calculates the Greatest Common Divisor of $a$ and $b$ using Euclidean algorithm.' },
    { name: 'lcm', detail: 'lcm(a: i64, b: i64) -> i64', doc: 'Calculates the Least Common Multiple of $a$ and $b$.' },
    { name: 'is_prime', detail: 'is_prime(n: i64) -> bool', doc: 'Determines whether $n$ is a prime number.' },
    { name: 'next_prime', detail: 'next_prime(n: i64) -> i64', doc: 'Finds the smallest prime number strictly greater than $n$.' },
    { name: 'deg_to_rad', detail: 'deg_to_rad(deg: f64) -> f64', doc: 'Converts angles from degrees to radians ($deg \\times \\frac{\\pi}{180}$).' },
    { name: 'rad_to_deg', detail: 'rad_to_deg(rad: f64) -> f64', doc: 'Converts angles from radians to degrees ($rad \\times \\frac{180}{\\pi}$).' },
    { name: 'sin', detail: 'sin(x: f64) -> f64', doc: 'Calculates the trigonometric sine $\\sin(x)$ using Taylor series polynomial reduction.' },
    { name: 'cos', detail: 'cos(x: f64) -> f64', doc: 'Calculates the trigonometric cosine $\\cos(x)$ using Taylor series polynomial reduction.' },
    { name: 'tan', detail: 'tan(x: f64) -> f64', doc: 'Calculates trigonometric tangent $\\tan(x) = \\frac{\\sin(x)}{\\cos(x)}$.' },
    { name: 'cot', detail: 'cot(x: f64) -> f64', doc: 'Calculates trigonometric cotangent $\\cot(x) = \\frac{1}{\\tan(x)}$.' },
    { name: 'sec', detail: 'sec(x: f64) -> f64', doc: 'Calculates trigonometric secant $\\sec(x) = \\frac{1}{\\cos(x)}$.' },
    { name: 'csc', detail: 'csc(x: f64) -> f64', doc: 'Calculates trigonometric cosecant $\\csc(x) = \\frac{1}{\\sin(x)}$.' },
    { name: 'exp', detail: 'exp(x: f64) -> f64', doc: 'Calculates the natural exponential $e^x$.' },
    { name: 'ln', detail: 'ln(x: f64) -> f64', doc: 'Calculates the natural logarithm $\\ln(x)$ for $x > 0$.' },
    { name: 'log10', detail: 'log10(x: f64) -> f64', doc: 'Calculates the base-10 common logarithm $\\log_{10}(x)$.' },
    { name: 'log2', detail: 'log2(x: f64) -> f64', doc: 'Calculates the binary logarithm $\\log_2(x)$.' },
    { name: 'pow_f64', detail: 'pow_f64(base: f64, exp: f64) -> f64', doc: 'Calculates generalized real power $base^{exp} = \\exp(exp \\times \\ln(base))$.' },
    // Standard Random Functions (Random module exports)
    { name: 'seed', detail: 'seed(s: i64) -> void', doc: 'Initializes the internal PRNG state. If s is 0, auto-seeds from high-resolution OS monotonic performance counters.' },
    { name: 'getstate', detail: 'getstate() -> i64', doc: 'Returns the current 64-bit internal integer state of the PRNG generator.' },
    { name: 'setstate', detail: 'setstate(state: i64) -> void', doc: 'Restores the internal PRNG generator state from a previously saved state.' },
    { name: 'random', detail: 'random() -> f64', doc: 'Returns the next random floating point number in the range [0.0, 1.0).' },
    { name: 'uniform', detail: 'uniform(a: f64, b: f64) -> f64', doc: 'Returns a random floating point number N such that a <= N <= b.' },
    { name: 'randint', detail: 'randint(a: i64, b: i64) -> i64', doc: 'Returns a random integer N such that a <= N <= b (inclusive on both ends).' },
    { name: 'randrange', detail: 'randrange(start: i64, stop: i64) -> i64', doc: 'Returns a randomly selected element from range(start, stop).' },
    { name: 'randrange_step', detail: 'randrange_step(start: i64, stop: i64, step: i64) -> i64', doc: 'Returns a randomly selected element from range(start, stop, step).' },
    { name: 'getrandbits', detail: 'getrandbits(k: i64) -> i64', doc: 'Generates a non-negative integer with k random bits.' },
    { name: 'triangular', detail: 'triangular(low: f64, high: f64, mode: f64) -> f64', doc: 'Returns a random floating point number from a triangular distribution.' },
    { name: 'normalvariate', detail: 'normalvariate(mu: f64, sigma: f64) -> f64', doc: 'Normal distribution with mean mu and standard deviation sigma.' },
    { name: 'gauss', detail: 'gauss(mu: f64, sigma: f64) -> f64', doc: 'Gaussian distribution (identical to normalvariate).' },
    { name: 'lognormvariate', detail: 'lognormvariate(mu: f64, sigma: f64) -> f64', doc: 'Log normal distribution.' },
    { name: 'expovariate', detail: 'expovariate(lambd: f64) -> f64', doc: 'Exponential distribution with rate parameter lambd.' },
    { name: 'paretovariate', detail: 'paretovariate(alpha: f64) -> f64', doc: 'Pareto distribution with shape parameter alpha.' },
    { name: 'weibullvariate', detail: 'weibullvariate(alpha: f64, beta: f64) -> f64', doc: 'Weibull distribution with scale parameter alpha and shape parameter beta.' },
    { name: 'betavariate', detail: 'betavariate(alpha: f64, beta: f64) -> f64', doc: 'Beta distribution using Johnk algorithm.' },
    { name: 'gammavariate', detail: 'gammavariate(alpha: f64, beta: f64) -> f64', doc: 'Gamma distribution using Marsaglia and Tsang method.' },
    { name: 'vonmisesvariate', detail: 'vonmisesvariate(mu: f64, kappa: f64) -> f64', doc: 'Circular von Mises distribution.' },
    { name: 'choice', detail: 'choice(s: &[i64]) -> i64', doc: 'Returns a random element from non-empty slice or fixed array.' },
    { name: 'choice_f64', detail: 'choice_f64(s: &[f64]) -> f64', doc: 'Returns a random f64 element from non-empty slice or fixed array.' },
    { name: 'choice_str', detail: 'choice_str(s: &[str]) -> str', doc: 'Returns a random string element from non-empty slice or fixed array.' },
    { name: 'shuffle', detail: 'shuffle(s: &mut [i64]) -> void', doc: 'Shuffles slice or fixed array in-place using Fisher-Yates algorithm.' },
    { name: 'shuffle_f64', detail: 'shuffle_f64(s: &mut [f64]) -> void', doc: 'Shuffles f64 slice or fixed array in-place.' },
    { name: 'shuffle_str', detail: 'shuffle_str(s: &mut [str]) -> void', doc: 'Shuffles string slice or fixed array in-place.' },
    { name: 'sample', detail: 'sample(src: &[i64], dest: &mut [i64]) -> void', doc: 'Copies elements from src to dest with partial shuffle without replacement.' }
];

/**
 * Aerix Inbuilt Modules Catalog
 */
const AERIX_MODULES = [
    {
        name: 'Math',
        detail: 'Aerix Standard Math Module',
        doc: 'Comprehensive pure-Aerix high-performance mathematical functions, constants, trigonometry, exponentials, combinatorics, and algorithms.\n\n```aerix\nimport Math;\nlet val: f64 = Math.PI;\nlet s: f64 = Math.sin(0.0);\n```',
        constants: [
            { name: 'PI', type: 'f64', value: '3.141592653589793', doc: 'Archimedes constant $\\pi$ (ratio of circumference to diameter).' },
            { name: 'E', type: 'f64', value: '2.718281828459045', doc: 'Euler\'s number $e$ (base of natural logarithms).' },
            { name: 'TAU', type: 'f64', value: '6.283185307179586', doc: 'Circle constant $\\tau = 2\\pi$.' },
            { name: 'SQRT2', type: 'f64', value: '1.4142135623730951', doc: 'Square root of 2 $\\sqrt{2}$.' },
            { name: 'LN2', type: 'f64', value: '0.6931471805599453', doc: 'Natural logarithm of 2.' },
            { name: 'LN10', type: 'f64', value: '2.302585092994046', doc: 'Natural logarithm of 10.' },
            { name: 'INF', type: 'f64', value: '1.0e308', doc: 'Positive infinity approximation.' }
        ],
        functions: [
            { name: 'abs', sig: 'abs(x: f64) -> f64', doc: 'Returns the absolute value of $x$.' },
            { name: 'min', sig: 'min(a: f64, b: f64) -> f64', doc: 'Returns the smaller of two numbers.' },
            { name: 'max', sig: 'max(a: f64, b: f64) -> f64', doc: 'Returns the larger of two numbers.' },
            { name: 'clamp', sig: 'clamp(val: f64, low: f64, high: f64) -> f64', doc: 'Clamps $val$ between $low$ and $high$.' },
            { name: 'sign', sig: 'sign(x: f64) -> f64', doc: 'Returns $1.0$ if $x > 0$, $-1.0$ if $x < 0$, or $0.0$.' },
            { name: 'is_even', sig: 'is_even(n: i64) -> bool', doc: 'Checks if $n$ is even.' },
            { name: 'is_odd', sig: 'is_odd(n: i64) -> bool', doc: 'Checks if $n$ is odd.' },
            { name: 'floor', sig: 'floor(x: f64) -> f64', doc: 'Floor rounding.' },
            { name: 'ceil', sig: 'ceil(x: f64) -> f64', doc: 'Ceil rounding.' },
            { name: 'round', sig: 'round(x: f64) -> f64', doc: 'Nearest integer rounding.' },
            { name: 'trunc', sig: 'trunc(x: f64) -> f64', doc: 'Truncation toward zero.' },
            { name: 'fract', sig: 'fract(x: f64) -> f64', doc: 'Fractional part.' },
            { name: 'lerp', sig: 'lerp(a: f64, b: f64, t: f64) -> f64', doc: 'Linear interpolation.' },
            { name: 'smoothstep', sig: 'smoothstep(edge0: f64, edge1: f64, x: f64) -> f64', doc: 'Hermite smoothstep.' },
            { name: 'sqrt', sig: 'sqrt(x: f64) -> f64', doc: 'High-precision square root.' },
            { name: 'cbrt', sig: 'cbrt(x: f64) -> f64', doc: 'Cube root.' },
            { name: 'hypot', sig: 'hypot(a: f64, b: f64) -> f64', doc: 'Hypotenuse $\\sqrt{a^2 + b^2}$.' },
            { name: 'pow', sig: 'pow(base: f64, exp: i64) -> f64', doc: 'Integer power exponentiation.' },
            { name: 'factorial', sig: 'factorial(n: i64) -> i64', doc: 'Factorial $n!$.' },
            { name: 'nPr', sig: 'nPr(n: i64, r: i64) -> i64', doc: 'Permutations $P(n, r)$.' },
            { name: 'nCr', sig: 'nCr(n: i64, r: i64) -> i64', doc: 'Combinations $C(n, r)$.' },
            { name: 'gcd', sig: 'gcd(a: i64, b: i64) -> i64', doc: 'Greatest common divisor.' },
            { name: 'lcm', sig: 'lcm(a: i64, b: i64) -> i64', doc: 'Least common multiple.' },
            { name: 'is_prime', sig: 'is_prime(n: i64) -> bool', doc: 'Prime check.' },
            { name: 'next_prime', sig: 'next_prime(n: i64) -> i64', doc: 'Next prime search.' },
            { name: 'deg_to_rad', sig: 'deg_to_rad(deg: f64) -> f64', doc: 'Degrees to radians.' },
            { name: 'rad_to_deg', sig: 'rad_to_deg(rad: f64) -> f64', doc: 'Radians to degrees.' },
            { name: 'sin', sig: 'sin(x: f64) -> f64', doc: 'Trigonometric sine.' },
            { name: 'cos', sig: 'cos(x: f64) -> f64', doc: 'Trigonometric cosine.' },
            { name: 'tan', sig: 'tan(x: f64) -> f64', doc: 'Trigonometric tangent.' },
            { name: 'cot', sig: 'cot(x: f64) -> f64', doc: 'Trigonometric cotangent.' },
            { name: 'sec', sig: 'sec(x: f64) -> f64', doc: 'Trigonometric secant.' },
            { name: 'csc', sig: 'csc(x: f64) -> f64', doc: 'Trigonometric cosecant.' },
            { name: 'exp', sig: 'exp(x: f64) -> f64', doc: 'Natural exponential $e^x$.' },
            { name: 'ln', sig: 'ln(x: f64) -> f64', doc: 'Natural logarithm $\\ln(x)$.' },
            { name: 'log10', sig: 'log10(x: f64) -> f64', doc: 'Base-10 logarithm.' },
            { name: 'log2', sig: 'log2(x: f64) -> f64', doc: 'Base-2 logarithm.' },
            { name: 'pow_f64', sig: 'pow_f64(base: f64, exp: f64) -> f64', doc: 'Real power $base^{exp}$.' }
        ]
    },
    {
        name: 'Random',
        detail: 'Aerix Standard Random Module',
        doc: 'Pseudo-random number generator module powered by high-performance SplitMix64 engine.\n\n```aerix\nimport Random;\nRandom.seed(42);\nlet r: i64 = Random.randint(1, 100);\nlet f: f64 = Random.uniform(0.0, 1.0);\n```',
        constants: [],
        functions: [
            { name: 'seed', sig: 'seed(s: i64)', doc: 'Initializes internal PRNG state. If s is 0, auto-seeds from high-resolution OS monotonic performance counters.' },
            { name: 'getstate', sig: 'getstate() -> i64', doc: 'Returns the current 64-bit internal integer state of the PRNG generator.' },
            { name: 'setstate', sig: 'setstate(state: i64)', doc: 'Restores the internal PRNG generator state from a previously saved state.' },
            { name: 'random', sig: 'random() -> f64', doc: 'Returns the next random floating point number in the range [0.0, 1.0).' },
            { name: 'uniform', sig: 'uniform(a: f64, b: f64) -> f64', doc: 'Returns a random floating point number N such that a <= N <= b.' },
            { name: 'randint', sig: 'randint(a: i64, b: i64) -> i64', doc: 'Returns a random integer N such that a <= N <= b (inclusive on both ends).' },
            { name: 'randrange', sig: 'randrange(start: i64, stop: i64) -> i64', doc: 'Returns a randomly selected element from range(start, stop).' },
            { name: 'randrange_step', sig: 'randrange_step(start: i64, stop: i64, step: i64) -> i64', doc: 'Returns a randomly selected element from range(start, stop, step).' },
            { name: 'getrandbits', sig: 'getrandbits(k: i64) -> i64', doc: 'Generates a non-negative integer with k random bits.' },
            { name: 'triangular', sig: 'triangular(low: f64, high: f64, mode: f64) -> f64', doc: 'Returns a random floating point number from a triangular distribution.' },
            { name: 'normalvariate', sig: 'normalvariate(mu: f64, sigma: f64) -> f64', doc: 'Normal distribution with mean mu and standard deviation sigma.' },
            { name: 'gauss', sig: 'gauss(mu: f64, sigma: f64) -> f64', doc: 'Gaussian distribution (identical to normalvariate).' },
            { name: 'lognormvariate', sig: 'lognormvariate(mu: f64, sigma: f64) -> f64', doc: 'Log normal distribution.' },
            { name: 'expovariate', sig: 'expovariate(lambd: f64) -> f64', doc: 'Exponential distribution with rate parameter lambd.' },
            { name: 'paretovariate', sig: 'paretovariate(alpha: f64) -> f64', doc: 'Pareto distribution with shape parameter alpha.' },
            { name: 'weibullvariate', sig: 'weibullvariate(alpha: f64, beta: f64) -> f64', doc: 'Weibull distribution with scale parameter alpha and shape parameter beta.' },
            { name: 'betavariate', sig: 'betavariate(alpha: f64, beta: f64) -> f64', doc: 'Beta distribution using Johnk algorithm.' },
            { name: 'gammavariate', sig: 'gammavariate(alpha: f64, beta: f64) -> f64', doc: 'Gamma distribution using Marsaglia and Tsang method.' },
            { name: 'vonmisesvariate', sig: 'vonmisesvariate(mu: f64, kappa: f64) -> f64', doc: 'Circular von Mises distribution.' },
            { name: 'choice', sig: 'choice(s: &[i64]) -> i64', doc: 'Returns a random element from non-empty slice or fixed array.' },
            { name: 'choice_f64', sig: 'choice_f64(s: &[f64]) -> f64', doc: 'Returns a random f64 element from non-empty slice or fixed array.' },
            { name: 'choice_str', sig: 'choice_str(s: &[str]) -> str', doc: 'Returns a random string element from non-empty slice or fixed array.' },
            { name: 'shuffle', sig: 'shuffle(s: &mut [i64])', doc: 'Shuffles slice or fixed array in-place using Fisher-Yates algorithm.' },
            { name: 'shuffle_f64', sig: 'shuffle_f64(s: &mut [f64])', doc: 'Shuffles f64 slice or fixed array in-place.' },
            { name: 'shuffle_str', sig: 'shuffle_str(s: &mut [str])', doc: 'Shuffles string slice or fixed array in-place.' },
            { name: 'sample', sig: 'sample(src: &[i64], dest: &mut [i64])', doc: 'Copies elements from src to dest with partial shuffle without replacement.' }
        ]
    }
];

/**
 * Extracts all classes, traits, enums, extensions, functions, properties, and variables.
 */
function analyzeDocument(document) {
    const text = document.getText();
    const lines = text.split('\n');

    const classes = new Map();    // name -> { name, kind, base, traits, line, fields: Map, methods: Map, properties: Map, operators: Map }
    const traits = new Map();     // name -> { name, line, methods: Map }
    const enums = new Map();      // name -> { name, line, variants: Map }
    const functions = new Map();  // name -> [ { name, params, rawParams, returnType, line, isMethod, className } ]
    const variables = new Map();  // name -> { name, type, isMut, line }

    let currentClass = null;
    let currentEnum = null;

    for (let l = 0; l < lines.length; l++) {
        const line = lines[l];
        const trimmed = line.trim();

        // Match from ... import ...
        const fromMatch = trimmed.match(/^from\s+(?:["']([^"']+)["']|([A-Z][a-zA-Z0-9_]*))\s+import\s+(?:\{([^}]+)\}|([*])|([^;]+))\s*;?/);
        if (fromMatch) {
            const modTarget = fromMatch[2];
            const symList = fromMatch[3] || fromMatch[5];
            if (fromMatch[4] === '*' && modTarget) {
                const foundMod = AERIX_MODULES.find(m => m.name === modTarget);
                if (foundMod) {
                    for (const f of foundMod.functions) {
                        if (!functions.has(f.name)) functions.set(f.name, []);
                        functions.get(f.name).push({
                            name: f.name,
                            params: [],
                            rawParams: f.sig,
                            returnType: 'any',
                            doc: f.doc,
                            module: modTarget,
                            line: l,
                            isMethod: false,
                            className: null
                        });
                    }
                }
            } else if (symList) {
                const importedNames = symList.split(',').map(s => s.trim()).filter(Boolean);
                for (const name of importedNames) {
                    if (!functions.has(name)) functions.set(name, []);
                    functions.get(name).push({ name: name, params: [], rawParams: '...', returnType: 'any', line: l, isMethod: false, className: null });
                }
            }
            continue;
        }

        // Match Import: import Math; or import "./path.arx"; or import { a, b } from "..."; or import Math, Random;
        const importMatch = trimmed.match(/^import\s+(?:\{([^}]+)\}\s+from\s+["']([^"']+)["']|((?:[A-Z][a-zA-Z0-9_]*)(?:\s*,\s*[A-Z][a-zA-Z0-9_]*)*)|["']([^"']+)["'])\s*;?/);
        if (importMatch) {
            if (importMatch[1]) {
                const importedNames = importMatch[1].split(',').map(s => s.trim()).filter(Boolean);
                for (const name of importedNames) {
                    if (!functions.has(name)) {
                        functions.set(name, []);
                    }
                    functions.get(name).push({
                        name: name,
                        params: [],
                        rawParams: '...',
                        returnType: 'any',
                        line: l,
                        isMethod: false,
                        className: null
                    });
                }
            } else if (importMatch[3]) {
                const modNames = importMatch[3].split(',').map(s => s.trim()).filter(Boolean);
                for (const modName of modNames) {
                    const foundMod = AERIX_MODULES.find(m => m.name === modName);
                    if (foundMod) {
                        for (const f of foundMod.functions) {
                            if (!functions.has(f.name)) functions.set(f.name, []);
                            functions.get(f.name).push({
                                name: f.name,
                                params: [],
                                rawParams: f.sig,
                                returnType: 'any',
                                doc: f.doc,
                                module: modName,
                                line: l,
                                isMethod: false,
                                className: null
                            });
                        }
                    }
                }
            }
            continue;
        }

        // Check Enum Declaration: enum <Name> {
        const enumMatch = trimmed.match(/^enum\s+([a-zA-Z_][a-zA-Z0-9_]*)/);
        if (enumMatch) {
            currentEnum = {
                name: enumMatch[1],
                line: l,
                variants: new Map()
            };
            enums.set(enumMatch[1], currentEnum);
            currentClass = null;
            continue;
        }

        // Check Enum Variants inside enum block
        if (currentEnum) {
            if (/^}/.test(trimmed)) {
                currentEnum = null;
                continue;
            }
            const variantMatch = trimmed.match(/^([A-Z][a-zA-Z0-9_]*)(?:\(([^)]*)\))?/);
            if (variantMatch) {
                currentEnum.variants.set(variantMatch[1], {
                    name: variantMatch[1],
                    payload: variantMatch[2] ? variantMatch[2].trim() : null,
                    line: l
                });
            }
            continue;
        }

        // Match Class, Trait, or Extend:
        // class Name<T> [extends Base] [implements Trait1, Trait2]
        // trait Name
        // extend Name
        const classMatch = trimmed.match(/^(class|trait|extend)\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:<[^>]+>)?(?:\s+(?:extends|:)\s+([a-zA-Z_][a-zA-Z0-9_]*))?(?:\s+implements\s+([a-zA-Z0-9_,\s]+))?/);
        if (classMatch) {
            const kind = classMatch[1];
            const name = classMatch[2];
            const base = classMatch[3] || null;
            const traitsList = classMatch[4] ? classMatch[4].split(',').map(t => t.trim()) : [];

            if (kind === 'extend' && classes.has(name)) {
                currentClass = classes.get(name);
            } else {
                currentClass = {
                    name: name,
                    kind: kind,
                    base: base,
                    traits: traitsList,
                    line: l,
                    fields: new Map(),
                    methods: new Map(),
                    properties: new Map(),
                    operators: new Map()
                };
                if (kind === 'trait') {
                    traits.set(name, currentClass);
                } else {
                    classes.set(name, currentClass);
                }
            }
            continue;
        }

        // Close class/trait on closing brace at column 0 or alone
        if (currentClass && /^}/.test(trimmed)) {
            currentClass = null;
        }

        // Inside Class/Trait Body
        if (currentClass) {
            // Match Property: [pub|priv] prop <name>: <type>
            const propMatch = trimmed.match(/^(?:(pub|priv)\s+)?prop\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([a-zA-Z0-9_<>]+)/);
            if (propMatch) {
                currentClass.properties.set(propMatch[2], {
                    name: propMatch[2],
                    type: propMatch[3],
                    visibility: propMatch[1] || 'pub',
                    line: l
                });
                continue;
            }

            // Match Operator Overloading: [pub|priv] op <operator>(<params>) [-> <ret>]
            const opMatch = trimmed.match(/^(?:(pub|priv)\s+)?op\s+([+\-*/%^&|~!<>=]+|==|!=|<=|>=)\s*\(([^)]*)\)(?:\s*->\s*([a-zA-Z0-9_<>]+))?/);
            if (opMatch) {
                currentClass.operators.set(opMatch[2], {
                    symbol: opMatch[2],
                    params: opMatch[3],
                    returnType: opMatch[4] || 'void',
                    line: l
                });
                continue;
            }

            // Match Class Field: [pub|priv] [static] <name>: <type>
            if (!trimmed.startsWith('fn') && !trimmed.startsWith('init') && !trimmed.startsWith('drop') && !trimmed.startsWith('prop') && !trimmed.startsWith('op')) {
                const prefixMatch = trimmed.match(/^(?:(pub|priv)\s+)?(?:(static)\s+)?/);
                const vis = prefixMatch ? (prefixMatch[1] || 'priv') : 'priv';
                const isStat = prefixMatch ? !!prefixMatch[2] : false;
                const afterPrefix = trimmed.slice(prefixMatch ? prefixMatch[0].length : 0);

                const fieldPairs = afterPrefix.matchAll(/([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*([a-zA-Z0-9_?<>]+)/g);
                for (const fp of fieldPairs) {
                    currentClass.fields.set(fp[1], {
                        name: fp[1],
                        type: fp[2],
                        visibility: vis,
                        isStatic: isStat,
                        line: l
                    });
                }
            }
        }

        // Match Function (top-level or method):
        // [pub|priv] [static|virtual|override] fn <name>[<T>](<params>) [-> <ret>]
        const fnMatch = trimmed.match(/^(?:(pub|priv)\s+)?(?:(static|virtual|override)\s+)?fn\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:<[^>]+>)?\s*\(([^)]*)\)(?:\s*->\s*([a-zA-Z0-9_<>]+))?/);
        if (fnMatch) {
            const fnName = fnMatch[3];
            const paramsStr = fnMatch[4];
            const retType = fnMatch[5] || 'void';

            const params = paramsStr.split(',').map(p => p.trim()).filter(Boolean).map(p => {
                const parts = p.split(':').map(x => x.trim());
                return { name: parts[0], type: parts[1] || 'any' };
            });

            const fnInfo = {
                name: fnName,
                params: params,
                rawParams: paramsStr,
                returnType: retType,
                line: l,
                isMethod: !!currentClass,
                className: currentClass ? currentClass.name : null
            };

            if (currentClass) {
                if (!currentClass.methods.has(fnName)) {
                    currentClass.methods.set(fnName, []);
                }
                currentClass.methods.get(fnName).push(fnInfo);
            } else {
                if (!functions.has(fnName)) {
                    functions.set(fnName, []);
                }
                functions.get(fnName).push(fnInfo);
            }
            continue;
        }

        // Match Constructor Overloads: init(<params>)
        const initMatch = trimmed.match(/^init\s*\(([^)]*)\)/);
        if (initMatch && currentClass) {
            const paramsStr = initMatch[1];
            const params = paramsStr.split(',').map(p => p.trim()).filter(Boolean).map(p => {
                const parts = p.split(':').map(x => x.trim());
                return { name: parts[0], type: parts[1] || 'any' };
            });
            const initInfo = {
                name: 'init',
                params: params,
                rawParams: paramsStr,
                returnType: currentClass.name,
                line: l,
                isMethod: true,
                className: currentClass.name
            };
            if (!currentClass.methods.has('init')) {
                currentClass.methods.set('init', []);
            }
            currentClass.methods.get('init').push(initInfo);
            continue;
        }

        // Match Variables: let [mut] <name> [: <type>] [= <val>]
        const varMatch = line.match(/\b(let)\s+(?:(mut)\s+)?([a-zA-Z_][a-zA-Z0-9_]*)(?:\s*:\s*([a-zA-Z0-9_?<>]+))?(?:\s*=\s*(.+))?/);
        if (varMatch) {
            const varName = varMatch[3];
            let typeName = varMatch[4] || null;
            const initVal = varMatch[5] ? varMatch[5].trim() : '';

            if (!typeName && initVal) {
                if (initVal.startsWith('"')) typeName = 'str';
                else if (/^\d+\.\d+/.test(initVal)) typeName = 'f64';
                else if (/^\d+/.test(initVal)) typeName = 'i64';
                else if (initVal === 'true' || initVal === 'false') typeName = 'bool';
                else if (initVal.startsWith("'")) typeName = 'char';
                else if (initVal.startsWith('Channel<') || initVal.startsWith('arx_channel_new(')) typeName = 'Channel<i64>';
                else if (/^([A-Z][a-zA-Z0-9_]*)\(/.test(initVal)) {
                    const m = initVal.match(/^([A-Z][a-zA-Z0-9_]*)\(/);
                    typeName = m[1];
                }
            }

            variables.set(varName, {
                name: varName,
                type: typeName || 'inferred',
                isMut: !!varMatch[2],
                line: l
            });
        }
    }

    return { classes, traits, enums, functions, variables };
}

/**
 * Physical struct memory layout, alignment, and cache-line footprint.
 */
const TYPE_SIZES = {
    'u8': 1, 'i8': 1, 'bool': 1, 'char': 1,
    'u16': 2, 'i16': 2,
    'u32': 4, 'i32': 4, 'f32': 4,
    'u64': 8, 'i64': 8, 'uint': 8, 'int': 8, 'usize': 8, 'isize': 8, 'f64': 8, 'float': 8,
    'str': 8
};

function calculateStructLayout(cls) {
    let offset = 0;
    let maxAlign = 8;
    const fields = [];
    for (const f of cls.fields.values()) {
        const size = TYPE_SIZES[f.type] || 8;
        const align = size >= 8 ? 8 : (size <= 2 ? size : 4);
        const pad = (align - (offset % align)) % align;
        offset += pad;
        fields.push({
            name: f.name,
            type: f.type,
            visibility: f.visibility,
            offset: offset,
            size: size,
            paddingBefore: pad
        });
        offset += size;
    }
    const tailPad = offset > 0 ? (maxAlign - (offset % maxAlign)) % maxAlign : 0;
    const totalSize = offset + tailPad;
    return {
        totalSize: totalSize || 8,
        alignment: maxAlign,
        fields,
        cacheLines: Math.max(1, Math.ceil((totalSize || 8) / 64))
    };
}

/**
 * Activates the Supercharged Aerix IntelliSense extension.
 */
function activate(context) {
    console.log('[Aerix] Ultra-Charged IntelliSense Engine activated!');

    const diagnosticCollection = vscode.languages.createDiagnosticCollection('aerix');
    context.subscriptions.push(diagnosticCollection);

    // ==========================================
    // 1. Context-Aware Autocompletion Provider
    // ==========================================
    const completionProvider = vscode.languages.registerCompletionItemProvider('aerix', {
        provideCompletionItems(document, position, token, completionContext) {
            const line = document.lineAt(position).text;
            const linePrefix = line.substr(0, position.character);
            const items = [];

            const docData = analyzeDocument(document);

            // A. Cascade Operator Completion: obj ~> <methods>
            const cascadeMatch = linePrefix.match(/([a-zA-Z_][a-zA-Z0-9_]*)\s*~>\s*([a-zA-Z0-9_]*)$/);
            if (cascadeMatch) {
                const targetIdent = cascadeMatch[1];
                let targetClass = null;

                if (targetIdent === 'self') {
                    for (const cls of docData.classes.values()) {
                        if (position.line >= cls.line) { targetClass = cls; break; }
                    }
                } else if (docData.variables.has(targetIdent)) {
                    const varInfo = docData.variables.get(targetIdent);
                    if (docData.classes.has(varInfo.type)) {
                        targetClass = docData.classes.get(varInfo.type);
                    }
                }

                if (targetClass) {
                    for (const [mName, mList] of targetClass.methods.entries()) {
                        if (mName === 'init' || mName === 'drop') continue;
                        for (const m of mList) {
                            const item = new vscode.CompletionItem(m.name, vscode.CompletionItemKind.Method);
                            item.detail = `(~> cascade) ${targetClass.name}.${m.name}(${m.rawParams})`;
                            item.documentation = new vscode.MarkdownString(`Mutates \`${targetIdent}\` in-place and passes instance forward.`);
                            item.insertText = new vscode.SnippetString(`${m.name}($0)`);
                            items.push(item);
                        }
                    }
                    return items;
                }
            }

            // B. Spawn Completion: spawn <workers>
            if (/\bspawn\s+[a-zA-Z0-9_]*$/.test(linePrefix)) {
                for (const [fnName, fnList] of docData.functions.entries()) {
                    if (fnName === 'main') continue;
                    for (const fn of fnList) {
                        const item = new vscode.CompletionItem(fn.name, vscode.CompletionItemKind.Function);
                        item.detail = `(spawn thread) fn ${fn.name}(${fn.rawParams})`;
                        item.documentation = new vscode.MarkdownString('Spawns this function asynchronously on a dedicated OS worker thread.');
                        item.insertText = new vscode.SnippetString(`${fn.name}($0)`);
                        items.push(item);
                    }
                }
                return items;
            }

            // C. Implements Completion: implements <traits>
            if (/\bimplements\s+[a-zA-Z0-9_,\s]*$/.test(linePrefix)) {
                for (const trait of docData.traits.values()) {
                    const item = new vscode.CompletionItem(trait.name, vscode.CompletionItemKind.Interface);
                    item.detail = `trait ${trait.name}`;
                    items.push(item);
                }
                return items;
            }

            // D. Extend Completion: extend <classes>
            if (/\bextend\s+[a-zA-Z0-9_]*$/.test(linePrefix)) {
                for (const cls of docData.classes.values()) {
                    const item = new vscode.CompletionItem(cls.name, vscode.CompletionItemKind.Class);
                    item.detail = `class ${cls.name}`;
                    items.push(item);
                }
                return items;
            }

            // E. Import Completion: import <modules>
            if (/\bimport\s+(?:[A-Z][a-zA-Z0-9_]*\s*,\s*)*[a-zA-Z0-9_]*$/.test(linePrefix) || /\bfrom\s+[a-zA-Z0-9_]*$/.test(linePrefix)) {
                for (const mod of AERIX_MODULES) {
                    const item = new vscode.CompletionItem(mod.name, vscode.CompletionItemKind.Module);
                    item.detail = `Inbuilt Module '${mod.name}'`;
                    item.documentation = new vscode.MarkdownString(mod.doc);
                    item.insertText = /,\s*[a-zA-Z0-9_]*$/.test(linePrefix) ? mod.name : `${mod.name};`;
                    items.push(item);
                }
                return items;
            }

            // F. Dot Access: obj., self., or Module. (e.g. Math.)
            const dotMatch = linePrefix.match(/([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z0-9_]*)$/);
            if (dotMatch) {
                const targetIdent = dotMatch[1];

                // Inbuilt Module Access: Math.<constant|function>
                const mod = AERIX_MODULES.find(m => m.name === targetIdent);
                if (mod) {
                    for (const c of mod.constants) {
                        const item = new vscode.CompletionItem(c.name, vscode.CompletionItemKind.Constant);
                        item.detail = `(constant) ${mod.name}.${c.name}: ${c.type} = ${c.value}`;
                        item.documentation = new vscode.MarkdownString(c.doc);
                        items.push(item);
                    }
                    for (const f of mod.functions) {
                        const item = new vscode.CompletionItem(f.name, vscode.CompletionItemKind.Function);
                        item.detail = `(function) ${mod.name}.${f.sig}`;
                        item.documentation = new vscode.MarkdownString(f.doc);
                        item.insertText = new vscode.SnippetString(`${f.name}($0)`);
                        item.sortText = '0_' + f.name;
                        items.push(item);
                    }
                    return items;
                }

                // self.
                if (targetIdent === 'self') {
                    for (const cls of docData.classes.values()) {
                        if (position.line >= cls.line) {
                            for (const f of cls.fields.values()) {
                                const item = new vscode.CompletionItem(f.name, vscode.CompletionItemKind.Field);
                                item.detail = `(field) self.${f.name}: ${f.type}`;
                                items.push(item);
                            }
                            for (const p of cls.properties.values()) {
                                const item = new vscode.CompletionItem(p.name, vscode.CompletionItemKind.Property);
                                item.detail = `(property) self.${p.name}: ${p.type}`;
                                items.push(item);
                            }
                            for (const [mName, mList] of cls.methods.entries()) {
                                for (const m of mList) {
                                    const item = new vscode.CompletionItem(m.name, vscode.CompletionItemKind.Method);
                                    item.detail = `(method) self.${m.name}(${m.rawParams}) -> ${m.returnType}`;
                                    item.insertText = new vscode.SnippetString(`${m.name}($0)`);
                                    items.push(item);
                                }
                            }
                            return items;
                        }
                    }
                }

                // Enum Variants: NodeStatus.<Variant>
                if (docData.enums.has(targetIdent)) {
                    const en = docData.enums.get(targetIdent);
                    for (const v of en.variants.values()) {
                        const item = new vscode.CompletionItem(v.name, vscode.CompletionItemKind.EnumMember);
                        item.detail = v.payload ? `variant ${en.name}.${v.name}(${v.payload})` : `variant ${en.name}.${v.name}`;
                        if (v.payload) {
                            item.insertText = new vscode.SnippetString(`${v.name}($0)`);
                        }
                        items.push(item);
                    }
                    return items;
                }

                // Known Class Variable Instance
                const varInfo = docData.variables.get(targetIdent);
                if (varInfo && docData.classes.has(varInfo.type)) {
                    const cls = docData.classes.get(varInfo.type);
                    for (const f of cls.fields.values()) {
                        if (f.visibility === 'pub') {
                            const item = new vscode.CompletionItem(f.name, vscode.CompletionItemKind.Field);
                            item.detail = `(field) ${cls.name}.${f.name}: ${f.type}`;
                            items.push(item);
                        }
                    }
                    for (const p of cls.properties.values()) {
                        if (p.visibility === 'pub') {
                            const item = new vscode.CompletionItem(p.name, vscode.CompletionItemKind.Property);
                            item.detail = `(property) ${cls.name}.${p.name}: ${p.type}`;
                            items.push(item);
                        }
                    }
                    for (const [mName, mList] of cls.methods.entries()) {
                        for (const m of mList) {
                            const item = new vscode.CompletionItem(m.name, vscode.CompletionItemKind.Method);
                            item.detail = `(method) ${cls.name}.${m.name}(${m.rawParams}) -> ${m.returnType}`;
                            item.insertText = new vscode.SnippetString(`${m.name}($0)`);
                            items.push(item);
                        }
                    }
                    return items;
                }
            }

            // F. Type Position: after ':', '->', 'as', '<'
            const isTypePosition = /(?::\s*|->\s*|\bas\s+|<)[a-zA-Z0-9_]*$/.test(linePrefix);
            if (isTypePosition) {
                for (let i = 0; i < AERIX_TYPES.length; i++) {
                    const t = AERIX_TYPES[i];
                    const item = new vscode.CompletionItem(t.name, vscode.CompletionItemKind.TypeParameter);
                    item.detail = t.detail;
                    item.documentation = new vscode.MarkdownString(t.doc);
                    item.sortText = '0_' + String(i).padStart(2, '0') + '_' + t.name;
                    items.push(item);
                }
                for (const cls of docData.classes.values()) {
                    const item = new vscode.CompletionItem(cls.name, vscode.CompletionItemKind.Class);
                    item.detail = `class ${cls.name}`;
                    item.sortText = '1_' + cls.name;
                    items.push(item);
                }
                for (const en of docData.enums.values()) {
                    const item = new vscode.CompletionItem(en.name, vscode.CompletionItemKind.Enum);
                    item.detail = `enum ${en.name}`;
                    item.sortText = '1_' + en.name;
                    items.push(item);
                }
                return items;
            }

            // G. General Completions: Keywords
            for (const kw of AERIX_KEYWORDS) {
                const item = new vscode.CompletionItem(kw.name, vscode.CompletionItemKind.Keyword);
                item.detail = kw.detail;
                item.documentation = new vscode.MarkdownString(kw.doc);
                item.sortText = '2_' + kw.name;
                items.push(item);
            }

            // General Completions: Builtins
            for (const b of AERIX_BUILTINS) {
                const item = new vscode.CompletionItem(b.name, vscode.CompletionItemKind.Function);
                item.detail = b.detail;
                item.documentation = new vscode.MarkdownString(b.doc);
                item.insertText = new vscode.SnippetString(`${b.name}($0)`);
                item.sortText = '3_' + b.name;
                items.push(item);
            }

            // General Completions: Document Variables
            for (const v of docData.variables.values()) {
                const item = new vscode.CompletionItem(v.name, vscode.CompletionItemKind.Variable);
                item.detail = `(${v.isMut ? 'mut ' : ''}variable) ${v.name}: ${v.type}`;
                item.sortText = '0_' + v.name;
                items.push(item);
            }

            // General Completions: Top-Level Functions
            for (const [fnName, fnList] of docData.functions.entries()) {
                if (fnName !== 'main') {
                    for (const fn of fnList) {
                        const item = new vscode.CompletionItem(fn.name, vscode.CompletionItemKind.Function);
                        item.detail = fn.module ? `(${fn.module}) ${fn.rawParams}` : `fn ${fn.name}(${fn.rawParams}) -> ${fn.returnType}`;
                        if (fn.doc) {
                            item.documentation = new vscode.MarkdownString(fn.doc);
                        }
                        item.insertText = new vscode.SnippetString(`${fn.name}($0)`);
                        item.sortText = '0_' + fn.name;
                        items.push(item);
                    }
                }
            }

            // General Completions: Classes & Enums
            for (const cls of docData.classes.values()) {
                const item = new vscode.CompletionItem(cls.name, vscode.CompletionItemKind.Class);
                item.detail = `class ${cls.name}`;
                item.sortText = '1_' + cls.name;
                items.push(item);
            }
            for (const en of docData.enums.values()) {
                const item = new vscode.CompletionItem(en.name, vscode.CompletionItemKind.Enum);
                item.detail = `enum ${en.name}`;
                item.sortText = '1_' + en.name;
                items.push(item);
            }

            return items;
        }
    }, '.', ':', ' ', '>', '|', '~', '<');

    context.subscriptions.push(completionProvider);

    // ==========================================
    // 2. High-Precision Hover Provider
    // ==========================================
    const hoverProvider = vscode.languages.registerHoverProvider('aerix', {
        provideHover(document, position, token) {
            const lineText = document.lineAt(position.line).text;

            // Hover over Cascade ~>
            if (lineText.includes('~>')) {
                const idx = lineText.indexOf('~>');
                if (position.character >= idx && position.character <= idx + 2) {
                    const md = new vscode.MarkdownString();
                    md.appendMarkdown('### Fluent Cascade Operator (`~>`)\n\n' +
                                      'Mutates the target instance in-place and passes the object forward down the pipeline.\n\n' +
                                      '```aerix\n' +
                                      'phoenix ~> promote(2)\n' +
                                      '        ~> set_clearance(8);\n' +
                                      '```');
                    return new vscode.Hover(md);
                }
            }

            // Hover over Pipeline |>
            if (lineText.includes('|>')) {
                const idx = lineText.indexOf('|>');
                if (position.character >= idx && position.character <= idx + 2) {
                    const md = new vscode.MarkdownString();
                    md.appendMarkdown('### Functional Pipeline Operator (`|>`) — Zero Overhead Dataflow\n\n' +
                                      'Passes the left-hand result as the first argument to the right-hand function call.\n\n' +
                                      '```aerix\n' +
                                      'let val = 15 |> scale_signal() |> normalize();\n' +
                                      '```');
                    return new vscode.Hover(md);
                }
            }

            const range = document.getWordRangeAtPosition(position);
            if (!range) return null;
            const word = document.getText(range);

            const docData = analyzeDocument(document);

            // 1. Local Variables
            if (docData.variables.has(word)) {
                const v = docData.variables.get(word);
                const md = new vscode.MarkdownString();
                md.appendCodeblock(`let ${v.isMut ? 'mut ' : ''}${v.name}: ${v.type}`, 'aerix');
                md.appendMarkdown(`*Declared at line ${v.line + 1}*`);
                return new vscode.Hover(md);
            }

            // 2. Functions (including Overloads)
            if (docData.functions.has(word)) {
                const fns = docData.functions.get(word);
                const md = new vscode.MarkdownString();
                for (const fn of fns) {
                    md.appendCodeblock(`fn ${fn.name}(${fn.rawParams}) -> ${fn.returnType}`, 'aerix');
                }
                md.appendMarkdown(`*User-defined function with ${fns.length} overload(s) at line ${fns[0].line + 1}*`);
                return new vscode.Hover(md);
            }

            // 3. Classes (Physical Memory Layout & Struct Footprint)
            if (docData.classes.has(word)) {
                const cls = docData.classes.get(word);
                const layout = calculateStructLayout(cls);
                const md = new vscode.MarkdownString();
                const traitDesc = cls.traits && cls.traits.length > 0 ? ` implements ${cls.traits.join(', ')}` : '';
                md.appendCodeblock(`class ${cls.name}${cls.base ? ' extends ' + cls.base : ''}${traitDesc}`, 'aerix');
                md.appendMarkdown(`### 📦 Physical Struct Layout & Offsets\n\n` +
                                  `* **Total Size:** \`${layout.totalSize} bytes\`\n` +
                                  `* **Alignment:** \`${layout.alignment} bytes\`\n` +
                                  `* **L1 Cache Line:** \`${layout.cacheLines}\` (${layout.cacheLines === 1 ? '✨ Fits within single 64B cache line' : 'Spans multiple cache lines'})\n\n` +
                                  `| Offset | Field | Type | Vis | Size |\n` +
                                  `| :--- | :--- | :--- | :--- | :--- |\n`);
                for (const f of layout.fields) {
                    md.appendMarkdown(`| \`[${f.offset}..${f.offset + f.size - 1}]\` | \`${f.name}\` | \`${f.type}\` | \`${f.visibility}\` | ${f.size}B |\n`);
                }
                md.appendMarkdown(`\n**Properties:** ${cls.properties.size} | **Methods:** ${cls.methods.size} | **Operators:** ${cls.operators.size}`);
                return new vscode.Hover(md);
            }

            // 4. Enums
            if (docData.enums.has(word)) {
                const en = docData.enums.get(word);
                const md = new vscode.MarkdownString();
                md.appendCodeblock(`enum ${en.name}`, 'aerix');
                md.appendMarkdown(`### Tagged Union Enum\nContains **${en.variants.size}** variant(s):\n`);
                for (const v of en.variants.values()) {
                    md.appendMarkdown(`- \`${v.name}\`${v.payload ? ` (${v.payload})` : ''}\n`);
                }
                return new vscode.Hover(md);
            }

            // 5. Traits
            if (docData.traits.has(word)) {
                const tr = docData.traits.get(word);
                const md = new vscode.MarkdownString();
                md.appendCodeblock(`trait ${tr.name}`, 'aerix');
                md.appendMarkdown(`### Abstract Interface Trait Contract\nZero-overhead compile-time behavior specification.`);
                return new vscode.Hover(md);
            }

            // Inbuilt Module Hover: Math
            const mod = AERIX_MODULES.find(m => m.name === word);
            if (mod) {
                const md = new vscode.MarkdownString();
                md.appendMarkdown(`### Inbuilt Module: \`${mod.name}\`\n*${mod.detail}*\n\n${mod.doc}\n\n` +
                    `**Constants:** ` + mod.constants.map(c => `\`${c.name}\``).join(', ') + `\n\n` +
                    `**Functions:** ` + mod.functions.map(f => `\`${f.name}()\``).join(', '));
                return new vscode.Hover(md);
            }

            // Inbuilt Module Constants Hover (e.g. PI, E, TAU, SQRT2, LN2, LN10, INF)
            for (const m of AERIX_MODULES) {
                const c = m.constants.find(con => con.name === word);
                if (c) {
                    const md = new vscode.MarkdownString();
                    md.appendCodeblock(`${m.name}.${c.name}: ${c.type} = ${c.value}`, 'aerix');
                    md.appendMarkdown(c.doc);
                    return new vscode.Hover(md);
                }
            }

            // 6. Built-ins
            const builtin = AERIX_BUILTINS.find(b => b.name === word);
            if (builtin) {
                const md = new vscode.MarkdownString();
                md.appendCodeblock(builtin.detail, 'aerix');
                md.appendMarkdown(builtin.doc);
                return new vscode.Hover(md);
            }

            // 7. Keywords
            const kw = AERIX_KEYWORDS.find(k => k.name === word);
            if (kw) {
                const md = new vscode.MarkdownString();
                md.appendMarkdown(`### Keyword: \`${kw.name}\`\n*${kw.detail}*\n\n${kw.doc}`);
                return new vscode.Hover(md);
            }

            // 8. Types
            const t = AERIX_TYPES.find(typ => typ.name === word);
            if (t) {
                const md = new vscode.MarkdownString();
                md.appendMarkdown(`### Aerix Type: \`${t.name}\`\n*${t.detail}*\n\n${t.doc}`);
                return new vscode.Hover(md);
            }

            return null;
        }
    });

    context.subscriptions.push(hoverProvider);

    // ==========================================
    // 3. Signature Help Provider
    // ==========================================
    const signatureProvider = vscode.languages.registerSignatureHelpProvider('aerix', {
        provideSignatureHelp(document, position, token) {
            const line = document.lineAt(position.line).text.substr(0, position.character);
            const callMatch = line.match(/(?:spawn\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)$/);
            if (!callMatch) return null;

            const fnName = callMatch[1];
            const argsStr = callMatch[2];
            const activeParam = argsStr.split(',').length - 1;

            const sigHelp = new vscode.SignatureHelp();

            // Built-ins
            const builtin = AERIX_BUILTINS.find(b => b.name === fnName);
            if (builtin) {
                const sig = new vscode.SignatureInformation(builtin.detail, new vscode.MarkdownString(builtin.doc));
                sigHelp.signatures = [sig];
                sigHelp.activeSignature = 0;
                sigHelp.activeParameter = Math.max(0, activeParam);
                return sigHelp;
            }

            const docData = analyzeDocument(document);

            // User Functions
            if (docData.functions.has(fnName)) {
                const fns = docData.functions.get(fnName);
                sigHelp.signatures = fns.map(fn => {
                    const sig = new vscode.SignatureInformation(`fn ${fn.name}(${fn.rawParams}) -> ${fn.returnType}`);
                    sig.parameters = fn.params.map(p => new vscode.ParameterInformation(`${p.name}: ${p.type}`));
                    return sig;
                });
                sigHelp.activeSignature = 0;
                sigHelp.activeParameter = Math.max(0, activeParam);
                return sigHelp;
            }

            // Class Constructor
            if (docData.classes.has(fnName)) {
                const cls = docData.classes.get(fnName);
                if (cls.methods.has('init')) {
                    const inits = cls.methods.get('init');
                    sigHelp.signatures = inits.map(i => {
                        const sig = new vscode.SignatureInformation(`init(${i.rawParams}) -> ${cls.name}`);
                        sig.parameters = i.params.map(p => new vscode.ParameterInformation(`${p.name}: ${p.type}`));
                        return sig;
                    });
                    sigHelp.activeSignature = 0;
                    sigHelp.activeParameter = Math.max(0, activeParam);
                    return sigHelp;
                }
            }

            return null;
        }
    }, '(', ',');

    context.subscriptions.push(signatureProvider);

    // ==========================================
    // 4. Go to Definition Provider (F12)
    // ==========================================
    const definitionProvider = vscode.languages.registerDefinitionProvider('aerix', {
        provideDefinition(document, position, token) {
            const range = document.getWordRangeAtPosition(position);
            if (!range) return null;
            const word = document.getText(range);

            const docData = analyzeDocument(document);

            if (docData.functions.has(word)) {
                const fn = docData.functions.get(word)[0];
                return new vscode.Location(document.uri, new vscode.Position(fn.line, 0));
            }
            if (docData.classes.has(word)) {
                const cls = docData.classes.get(word);
                return new vscode.Location(document.uri, new vscode.Position(cls.line, 0));
            }
            if (docData.traits.has(word)) {
                const tr = docData.traits.get(word);
                return new vscode.Location(document.uri, new vscode.Position(tr.line, 0));
            }
            if (docData.enums.has(word)) {
                const en = docData.enums.get(word);
                return new vscode.Location(document.uri, new vscode.Position(en.line, 0));
            }
            if (docData.variables.has(word)) {
                const v = docData.variables.get(word);
                return new vscode.Location(document.uri, new vscode.Position(v.line, 0));
            }

            return null;
        }
    });

    context.subscriptions.push(definitionProvider);

    // ==========================================
    // 5. Hierarchical Document Symbols (Outline Tree)
    // ==========================================
    const symbolProvider = vscode.languages.registerDocumentSymbolProvider('aerix', {
        provideDocumentSymbols(document, token) {
            const symbols = [];
            const docData = analyzeDocument(document);

            // Classes & Traits
            for (const cls of docData.classes.values()) {
                const line = document.lineAt(cls.line);
                const clsSym = new vscode.DocumentSymbol(
                    cls.name,
                    cls.kind === 'extend' ? 'extend' : (cls.base ? `extends ${cls.base}` : 'class'),
                    cls.kind === 'trait' ? vscode.SymbolKind.Interface : vscode.SymbolKind.Class,
                    line.range,
                    line.range
                );

                for (const f of cls.fields.values()) {
                    const fLine = document.lineAt(f.line);
                    clsSym.children.push(new vscode.DocumentSymbol(f.name, f.type, vscode.SymbolKind.Field, fLine.range, fLine.range));
                }

                for (const p of cls.properties.values()) {
                    const pLine = document.lineAt(p.line);
                    clsSym.children.push(new vscode.DocumentSymbol(p.name, p.type, vscode.SymbolKind.Property, pLine.range, pLine.range));
                }

                for (const op of cls.operators.values()) {
                    const opLine = document.lineAt(op.line);
                    clsSym.children.push(new vscode.DocumentSymbol(`op ${op.symbol}`, `(${op.params}) -> ${op.returnType}`, vscode.SymbolKind.Operator, opLine.range, opLine.range));
                }

                for (const [mName, mList] of cls.methods.entries()) {
                    for (const m of mList) {
                        const mLine = document.lineAt(m.line);
                        clsSym.children.push(new vscode.DocumentSymbol(m.name, `(${m.rawParams}) -> ${m.returnType}`, m.name === 'init' ? vscode.SymbolKind.Constructor : vscode.SymbolKind.Method, mLine.range, mLine.range));
                    }
                }

                symbols.push(clsSym);
            }

            // Enums
            for (const en of docData.enums.values()) {
                const line = document.lineAt(en.line);
                const enSym = new vscode.DocumentSymbol(en.name, 'enum', vscode.SymbolKind.Enum, line.range, line.range);
                for (const v of en.variants.values()) {
                    const vLine = document.lineAt(v.line);
                    enSym.children.push(new vscode.DocumentSymbol(v.name, v.payload || '', vscode.SymbolKind.EnumMember, vLine.range, vLine.range));
                }
                symbols.push(enSym);
            }

            // Top-Level Functions
            for (const [fnName, fns] of docData.functions.entries()) {
                for (const fn of fns) {
                    const line = document.lineAt(fn.line);
                    symbols.push(new vscode.DocumentSymbol(fn.name, `(${fn.rawParams}) -> ${fn.returnType}`, fn.name === 'main' ? vscode.SymbolKind.Interface : vscode.SymbolKind.Function, line.range, line.range));
                }
            }

            // Variables
            for (const v of docData.variables.values()) {
                const line = document.lineAt(v.line);
                symbols.push(new vscode.DocumentSymbol(v.name, v.type, v.isMut ? vscode.SymbolKind.Variable : vscode.SymbolKind.Constant, line.range, line.range));
            }

            return symbols;
        }
    });

    context.subscriptions.push(symbolProvider);

    // ==========================================
    // 6. Live Diagnostic Linter via `arx check`
    // ==========================================
    let lintTimeout = null;

    function runLinter(doc) {
        if (!doc || doc.languageId !== 'aerix') return;
        const filePath = doc.fileName;
        if (!filePath || !filePath.endsWith('.arx')) return;

        cp.exec(`arx check "${filePath}"`, { timeout: 3500 }, (err, stdout, stderr) => {
            const diagnostics = [];
            const output = (stdout || '') + '\n' + (stderr || '');
            if (err && output) {
                const match = output.match(/-->\s*.*?:(\d+):(\d+)/);
                if (match) {
                    const line = Math.max(0, parseInt(match[1], 10) - 1);
                    const col = Math.max(0, parseInt(match[2], 10) - 1);
                    const errMsg = output.split('\n')[1] || 'Aerix Syntax / Semantic Error';
                    const range = new vscode.Range(line, col, line, col + 12);
                    const diag = new vscode.Diagnostic(range, errMsg, vscode.DiagnosticSeverity.Error);
                    diagnostics.push(diag);
                }
            }
            diagnosticCollection.set(doc.uri, diagnostics);
        });
    }

    function scheduleLinter(doc) {
        if (lintTimeout) clearTimeout(lintTimeout);
        lintTimeout = setTimeout(() => runLinter(doc), 500);
    }

    vscode.workspace.onDidChangeTextDocument(e => scheduleLinter(e.document));
    vscode.workspace.onDidSaveTextDocument(runLinter);
    vscode.workspace.onDidOpenTextDocument(runLinter);
    if (vscode.window.activeTextEditor) {
        runLinter(vscode.window.activeTextEditor.document);
    }

    // ==========================================
    // 7. Real-Time Inlay Hints Provider
    // ==========================================
    const inlayHintsProvider = vscode.languages.registerInlayHintsProvider('aerix', {
        provideInlayHints(document, range, token) {
            const hints = [];
            const docData = analyzeDocument(document);
            const lines = document.getText().split('\n');

            const startLine = range.start.line;
            const endLine = Math.min(lines.length - 1, range.end.line);

            for (let l = startLine; l <= endLine; l++) {
                const line = lines[l];
                if (/^\s*\/\//.test(line)) continue;

                // 1. Variable Inferred Types: let [mut] name = val
                const letMatch = line.match(/\b(let)\s+(?:mut\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(.+)/);
                if (letMatch) {
                    const prefix = line.slice(0, line.indexOf('='));
                    if (!prefix.includes(':')) {
                        const varName = letMatch[2];
                        const vInfo = docData.variables.get(varName);
                        if (vInfo && vInfo.type && vInfo.type !== 'inferred') {
                            const nameIndex = line.indexOf(varName);
                            if (nameIndex !== -1) {
                                const pos = new vscode.Position(l, nameIndex + varName.length);
                                const hint = new vscode.InlayHint(pos, `: ${vInfo.type}`, vscode.InlayHintKind.Type);
                                hint.paddingLeft = true;
                                hints.push(hint);
                            }
                        }
                    }
                }

                // 2. Function & Constructor Parameter Names
                const callMatches = line.matchAll(/\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]+)\)/g);
                for (const cm of callMatches) {
                    const callee = cm[1];
                    const argsStr = cm[2];
                    if (['fn', 'if', 'while', 'for', 'println', 'print', 'eprintln', 'input', 'readln', 'assert', 'panic'].includes(callee)) continue;

                    let targetParams = null;
                    if (docData.functions.has(callee)) {
                        targetParams = docData.functions.get(callee)[0].params;
                    } else if (docData.classes.has(callee)) {
                        const cls = docData.classes.get(callee);
                        if (cls.methods.has('init')) {
                            targetParams = cls.methods.get('init')[0].params;
                        } else {
                            targetParams = Array.from(cls.fields.values()).map(f => ({ name: f.name, type: f.type }));
                        }
                    }

                    if (targetParams && targetParams.length > 0) {
                        const args = [];
                        let curArg = '';
                        let inStr = false;
                        let parenDepth = 0;
                        const argOffsets = [];
                        let baseOffset = cm.index + cm[0].indexOf('(') + 1;

                        for (let c = 0; c < argsStr.length; c++) {
                            const ch = argsStr[c];
                            if (ch === '"' && (c === 0 || argsStr[c - 1] !== '\\')) inStr = !inStr;
                            else if (!inStr && ch === '(') parenDepth++;
                            else if (!inStr && ch === ')') parenDepth--;
                            else if (!inStr && ch === ',' && parenDepth === 0) {
                                args.push(curArg);
                                argOffsets.push(baseOffset);
                                curArg = '';
                                baseOffset = cm.index + cm[0].indexOf('(') + 1 + c + 1;
                                continue;
                            }
                            curArg += ch;
                        }
                        if (curArg.trim()) {
                            args.push(curArg);
                            argOffsets.push(baseOffset);
                        }

                        for (let a = 0; a < Math.min(args.length, targetParams.length); a++) {
                            const argText = args[a];
                            const leadingSpaces = argText.length - argText.trimStart().length;
                            const pos = new vscode.Position(l, argOffsets[a] + leadingSpaces);
                            const hint = new vscode.InlayHint(pos, `${targetParams[a].name}:`, vscode.InlayHintKind.Parameter);
                            hint.paddingRight = true;
                            hints.push(hint);
                        }
                    }
                }
            }

            return hints;
        }
    });
    context.subscriptions.push(inlayHintsProvider);

    // ==========================================
    // 8. CodeLens Provider: Run Button & Struct Sizing
    // ==========================================
    const codeLensProvider = vscode.languages.registerCodeLensProvider('aerix', {
        provideCodeLenses(document, token) {
            const lenses = [];
            const docData = analyzeDocument(document);

            if (docData.functions.has('main')) {
                const mainFn = docData.functions.get('main')[0];
                const range = new vscode.Range(mainFn.line, 0, mainFn.line, 0);
                lenses.push(new vscode.CodeLens(range, {
                    title: '▶ Run Program',
                    command: 'aerix.runFile',
                    arguments: [document.uri]
                }));
            }

            return lenses;
        }
    });
    context.subscriptions.push(codeLensProvider);

    // ==========================================
    // 9. Document Formatting Provider
    // ==========================================
    const formatProvider = vscode.languages.registerDocumentFormattingEditProvider('aerix', {
        provideDocumentFormattingEdits(document, options, token) {
            const text = document.getText();
            const lines = text.split('\n');

            let indentLevel = 0;
            const formattedLines = [];

            for (let l = 0; l < lines.length; l++) {
                let line = lines[l].trim();

                if (line === '') {
                    formattedLines.push('');
                    continue;
                }

                if (line.startsWith('}') || line.startsWith(')')) {
                    indentLevel = Math.max(0, indentLevel - 1);
                }

                if (!line.startsWith('//')) {
                    line = line
                        .replace(/\s*\|\>\s*/g, ' |> ')
                        .replace(/\s*~\>\s*/g, ' ~> ')
                        .replace(/\s*\?\?\s*/g, ' ?? ')
                        .replace(/\s*->\s*/g, ' -> ')
                        .replace(/\s*=>\s*/g, ' => ')
                        .replace(/,\s*/g, ', ');
                }

                const indentStr = '    '.repeat(indentLevel);
                formattedLines.push(indentStr + line);

                if (line.endsWith('{') || (line.endsWith('(') && !line.includes(')'))) {
                    indentLevel++;
                }
            }

            const fullRange = new vscode.Range(0, 0, lines.length, 0);
            return [vscode.TextEdit.replace(fullRange, formattedLines.join('\n') + '\n')];
        }
    });
    context.subscriptions.push(formatProvider);

    // ==========================================
    // 10. Aerix Commands
    // ==========================================
    const runFileCmd = vscode.commands.registerCommand('aerix.runFile', (uri) => {
        const editor = vscode.window.activeTextEditor;
        const filePath = uri ? uri.fsPath : (editor ? editor.document.fileName : null);
        if (!filePath) return;

        let terminal = vscode.window.terminals.find(t => t.name === 'Aerix Terminal');
        if (!terminal) {
            terminal = vscode.window.createTerminal('Aerix Terminal');
        }
        terminal.show();
        terminal.sendText(`arx run "${filePath}"`);
    });
    context.subscriptions.push(runFileCmd);

    const checkFileCmd = vscode.commands.registerCommand('aerix.checkFile', (uri) => {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            runLinter(editor.document);
            vscode.window.showInformationMessage(`Aerix: Verified syntax & types for ${path.basename(editor.document.fileName)}`);
        }
    });
    context.subscriptions.push(checkFileCmd);

    const buildWasmCmd = vscode.commands.registerCommand('aerix.buildWasm', (uri) => {
        const editor = vscode.window.activeTextEditor;
        const filePath = uri ? uri.fsPath : (editor ? editor.document.fileName : null);
        if (!filePath) return;

        let terminal = vscode.window.terminals.find(t => t.name === 'Aerix Terminal');
        if (!terminal) {
            terminal = vscode.window.createTerminal('Aerix Terminal');
        }
        terminal.show();
        terminal.sendText(`arx wasm "${filePath}" --wat --html`);
    });
    context.subscriptions.push(buildWasmCmd);

    const serveWasmCmd = vscode.commands.registerCommand('aerix.serveWasm', (uri) => {
        const editor = vscode.window.activeTextEditor;
        const filePath = uri ? uri.fsPath : (editor ? editor.document.fileName : null);
        if (!filePath) return;

        let terminal = vscode.window.terminals.find(t => t.name === 'Aerix Terminal');
        if (!terminal) {
            terminal = vscode.window.createTerminal('Aerix Terminal');
        }
        terminal.show();
        terminal.sendText(`arx wasm "${filePath}" --serve`);
    });
    context.subscriptions.push(serveWasmCmd);
}

function deactivate() {
    console.log('[Aerix] Extension deactivated.');
}

module.exports = {
    activate,
    deactivate
};
