# Aerix (arx) — Language Feature Gaps & Standard Collections Roadmap

> **Document Version:** 1.0.0  
> **Status:** Architecture Blueprint & Feature Analysis  
> **Target Toolchain:** Aerix 2.0+

---

## 🎯 Executive Overview

Aerix currently excels at **low-level systems architecture**: zero-cost C struct layout, high-performance C99 translation, hardware SIMD intrinsics (`f32x4`), OS thread spawning, mutex/condition-variable channels (`arx_channel_*`), and direct WebAssembly binary emission.

However, in everyday application development (building CLI utilities, web backends, game logic, parsers, and data processors), **80% of human programming revolves around manipulating collections and text:**
- Storing lists of items in growable arrays.
- Trimming, splitting, and replacing strings.
- Looking up data in key-value dictionaries.
- Tracking unique elements in sets.
- Returning multiple values using tuples.
- Iterating through items with clean `for item in collection` loops.

This document details the **critical missing data structures and language features**, specifies their proposed syntax in Aerix, and outlines the phased implementation roadmap.

---

## 📊 Summary of Missing Data Structures & Language Features

| Feature Category | Current State in Aerix | What is Missing | Priority |
| :--- | :--- | :--- | :---: |
| **1. Dynamic Arrays** | Fixed arrays `[i64; 10]` only | Growable `List<T>`, `.push()`, `.pop()`, slicing `[1..4]` | **CRITICAL** |
| **2. Rich Strings** | Raw C string pointer `str` (`const char*`) | Mutable `String` type, `.split()`, `.trim()`, `.replace()` | **CRITICAL** |
| **3. Dictionaries / Maps** | Non-existent | `HashMap<K, V>` or `Map<K, V>` with $O(1)$ key lookup | **HIGH** |
| **4. Sets** | Non-existent | `HashSet<T>` or `Set<T>` for unique collections | **HIGH** |
| **5. Tuples** | Non-existent | `(T1, T2)` anonymous records & destructuring | **HIGH** |
| **6. Collection Iteration** | Only numeric ranges `for i in 0..10` | `for item in list`, `for (k, v) in map` | **HIGH** |
| **7. Queues & Stacks** | Manual ring buffer in channel runtime | `Queue<T>`, `Stack<T>`, `Deque<T>` | **MEDIUM** |
| **8. Multi-File Modules** | Single-file only + `cinclude` | Native `import "./module.arx"` system | **CRITICAL** |
| **9. Error Handling** | `assert`, `panic`, nullable `T?` | `Result<T, E>` with `?` early-return operator | **HIGH** |
| **10. Closures / Lambdas** | Named functions only | Anonymous closures `\|x\| => x * 2` for `\|>` pipeline | **MEDIUM** |

---

## 🧱 1. Dynamic Arrays & Slices (`List<T>`)

### Current Limitation:
Aerix only supports fixed-size stack arrays:
```aerix
let mut numbers: [i64; 5] = [1, 2, 3, 4, 5];
// Cannot push, cannot resize, cannot dynamically append!
```

### Proposed Design:
A monomorphized, heap-allocated dynamic array with amortized $O(1)$ capacity doubling:

```aerix
let mut items = List<i64>();

// Methods
items.push(10);
items.push(20);
items.push(30);

let popped = items.pop();             // 30
let length = items.len();             // 2
let has_item = items.contains(20);    // true

// Indexing with []
items[0] = 99;
let val = items[0];

// Slicing (zero-copy view)
let sub = items[0..1];

// Functional operations
items.sort();
items.reverse();
items.clear();
```

---

## 🔤 2. Rich Strings (`String` vs `str`)

### Current Limitation:
`str` in Aerix is currently an immutable, borrowed C string pointer (`const char*`). While string interpolation works (`"Hello {name}"`), you cannot inspect, mutate, or slice text easily.

### Proposed Design:
Distinguish between **borrowed string slices (`str`)** and **owned dynamic strings (`String`)**:

```aerix
// Creating a dynamic String
let mut s = String("  aerix systems language  ");

// Text Inspection
let length = s.len();
let starts = s.starts_with("  aerix"); // true
let contains_word = s.contains("systems"); // true

// Transformation
let trimmed = s.trim();                     // "aerix systems language"
let upper = trimmed.to_upper();             // "AERIX SYSTEMS LANGUAGE"
let replaced = trimmed.replace(" ", "_");   // "aerix_systems_language"

// Splitting & Joining
let words: List<str> = trimmed.split(" ");
// words = ["aerix", "systems", "language"]

let joined = String.join(words, "-");
// joined = "aerix-systems-language"
```

---

## 🗺️ 3. Dictionaries / Hash Maps (`Map<K, V>`)

### Current Limitation:
To associate keys with values, developers must currently write custom structs or parallel arrays.

### Proposed Design:
A high-performance Robin Hood or open-addressing hash table:

```aerix
let mut user_scores = Map<str, i64>();

// Insertion & Bracket Indexing
user_scores.insert("phoenix", 9850);
user_scores["nova"] = 4320;
user_scores["glitch"] = 8110;

// Lookup
let score = user_scores.get("phoenix"); // Option<i64> or nullable i64?
let exists = user_scores.has_key("guest"); // false

// Removal
user_scores.remove("glitch");

// Key and Value extraction
let all_keys: List<str> = user_scores.keys();
let all_vals: List<i64> = user_scores.values();
```

---

## 🔢 4. Sets (`Set<T>`)

### Current Limitation:
No built-in way to filter duplicates or verify unique membership in $O(1)$ time.

### Proposed Design:
Hash set with mathematical set operations:

```aerix
let mut tags = Set<str>();

tags.add("game");
tags.add("graphics");
tags.add("game"); // Duplicate ignored!

println("Unique tags: {tags.len()}"); // 2
println("Has game tag: {tags.has(\"game\")}"); // true

// Set Algebra
let other_tags = Set<str>();
other_tags.add("physics");
other_tags.add("game");

let common = tags.intersection(other_tags); // {"game"}
let combined = tags.union(other_tags);       // {"game", "graphics", "physics"}
```

---

## 📦 5. Tuples & Destructuring

### Current Limitation:
To return two values from a function, you currently have to define an entire `class` or pass pointers:
```aerix
// Today: Requires dedicated class boilerplate
class Point2D { pub x: f64, pub y: f64 ... }
```

### Proposed Design:
Zero-overhead lightweight anonymous tuples:

```aerix
fn get_user_stats() -> (str, i64, bool) {
    return ("HaxOrWot", 42, true);
}

fn main() {
    // Destructuring assignment
    let (name, level, is_admin) = get_user_stats();
    println("User: {name}, Level: {level}");

    // Direct tuple index access
    let pair = (10, "alpha");
    let first = pair.0;
    let second = pair.1;
}
```

---

## 🔁 6. Collection Iteration (`for .. in`)

### Current Limitation:
Aerix only iterates over numeric ranges:
```aerix
for i in 0..10 { ... }
```

### Proposed Design:
Extend `for .. in` to iterate over any collection or data structure:

```aerix
let fruits = ["Apple", "Banana", "Cherry"];

// 1. Iterate over elements
for fruit in fruits {
    println("Fruit: {fruit}");
}

// 2. Iterate with index (enumerate)
for (index, fruit) in fruits.enumerate() {
    println("#{index}: {fruit}");
}

// 3. Iterate over Map key-value pairs
for (user, score) in user_scores {
    println("{user} -> {score}");
}
```

---

## ⚡ 7. Queues, Stacks & Deques

### Proposed Design:
Fast FIFO (First-In, First-Out) and LIFO (Last-In, First-Out) structures for game loops, pathfinding, and task dispatch:

```aerix
let mut queue = Queue<str>();
queue.enqueue("Task1");
queue.enqueue("Task2");
let next_task = queue.dequeue(); // "Task1"

let mut stack = Stack<i64>();
stack.push(1);
stack.push(2);
let top = stack.pop(); // 2
```

---

## 🛡️ 8. Error Handling: `Result<T, E>` & `?` Operator

### Current Limitation:
Panicking crashes the entire program. Errors in network, file, and math operations cannot be recovered cleanly.

### Proposed Design:
```aerix
enum Result<T, E> {
    Ok(val: T),
    Err(err: E)
}

fn read_config(path: str) -> Result<str, str> {
    guard file_exists(path) else {
        return Result.Err("Configuration file not found")
    }
    return Result.Ok(read_file(path))
}

fn boot() -> Result<void, str> {
    // '?' unwraps Ok or immediately returns Err up the call stack!
    let content = read_config("settings.toml")?;
    println("Booting with: {content}");
    return Result.Ok(())
}
```

---

## 🗺️ 9. The Implementation Roadmap

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                  AERIX DATA STRUCTURES IMPLEMENTATION PLAN                   │
├─────────────┬───────────────────────────┬────────────────────────────────────┤
│ Phase 21    │ 📚 Standard Collections   │ • List<T> (Growable Array)         │
│             │                           │ • String API (split, trim, replace)│
│             │                           │ • Bracket indexing (arr[i], s[i])  │
├─────────────┼───────────────────────────┼────────────────────────────────────┤
│ Phase 22    │ 🗺️ Key-Value & Sets       │ • Map<K, V> / HashMap<K, V>        │
│             │                           │ • Set<T> / HashSet<T>              │
│             │                           │ • Collection iteration (for in)    │
├─────────────┼───────────────────────────┼────────────────────────────────────┤
│ Phase 23    │ 📦 Tuples & Destructuring │ • (T1, T2) Tuple literals          │
│             │                           │ • Destructuring (let (x, y) = ...) │
│             │                           │ • Queue<T> and Stack<T>            │
├─────────────┼───────────────────────────┼────────────────────────────────────┤
│ Phase 24    │ 🛡️ Robust Error Handling  │ • Result<T, E> and Option<T>       │
│             │                           │ • The '?' operator for propagation │
├─────────────┼───────────────────────────┼────────────────────────────────────┤
│ Phase 25    │ 🌐 Multi-File Modules     │ • import "./module.arx"            │
│             │                           │ • Integration with `arx pm`        │
└─────────────┴───────────────────────────┴────────────────────────────────────┘
```

---

<div align="center">

*Aerix Language Architecture Specification Suite*  
**Speed of C • Safety of Rust • Elegance of Modern Scripting**

</div>
