# Aerix (arx) — OOP Architecture & Type System

> **Subsystem:** Object-Oriented Programming (OOP) & Static Type Engine  
> **Philosophy:** *Zero-Cost Object Abstractions over Native C Structs*

---

## 1. Dual-Paradigm Model

Aerix is neither purely object-oriented nor purely procedural; it seamlessly supports both:
- **Procedural ("Normal") Mode:** Functions and state can exist at the top level without class wrappers. Ideal for numerical code, scripts, CLI tools, systems drivers, and games.
- **Object-Oriented (OOP) Mode:** Classes encapsulate data and behavior, support single inheritance, interface implementation (`trait`), access control, and runtime polymorphism.

---

## 2. The Aerix Class Model

### 2.1 Anatomy of a Class
```aerix
class Particle {
    // 1. Fields with explicit access control
    pub x: f64
    pub y: f64
    priv vx: f64
    priv vy: f64

    // 2. Static fields
    pub static count: i32 = 0

    // 3. Constructor
    init(x: f64, y: f64, vx: f64 = 0.0, vy: f64 = 0.0) {
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        Particle.count += 1
    }

    // 4. Instance Methods
    pub fn step(dt: f64) {
        self.x += self.vx * dt
        self.y += self.vy * dt
    }

    // 5. Destructor (Automatic cleanup on scope exit)
    drop() {
        Particle.count -= 1
    }
}
```

---

## 3. How Aerix Compiles OOP into Ultra-Fast C99

To achieve C-level speed, Aerix converts classes into optimized C structures and statically bound functions.

### 3.1 Struct Layout (Zero Overhead)
The `Particle` class generates:
```c
// C99 generated code
typedef struct Arx_Particle {
    double x;
    double y;
    double _priv_vx;
    double _priv_vy;
} Arx_Particle;

int32_t Arx_Particle_count = 0;

// Constructor
void Arx_Particle_init(Arx_Particle* self, double x, double y, double vx, double vy) {
    self->x = x;
    self->y = y;
    self->_priv_vx = vx;
    self->_priv_vy = vy;
    Arx_Particle_count += 1;
}

// Instance method (Static call: ZERO virtual dispatch overhead)
void Arx_Particle_step(Arx_Particle* self, double dt) {
    self->x += self->_priv_vx * dt;
    self->y += self->_priv_vy * dt;
}

// Destructor
void Arx_Particle_drop(Arx_Particle* self) {
    Arx_Particle_count -= 1;
}
```

### 3.2 Stack vs. Heap Allocation
Aerix gives the developer explicit control over memory placement:

```aerix
// 1. Stack Allocation (Instant, zero-allocator overhead)
let p = Particle(0.0, 0.0, 1.5, 2.0)
p.step(0.16)
// Automatically dropped at end of scope!

// 2. Heap Allocation (For long-lived objects or dynamic graphs)
let p_heap = new Particle(10.0, 20.0)
p_heap.step(0.16)
delete p_heap
```

---

## 4. Inheritance & Virtual Method Tables (VTables)

When runtime polymorphism is required, Aerix uses lean virtual tables (vtables).

### 4.1 Base Class and Derived Class
```aerix
class Shape {
    pub name: str

    init(name: str) {
        self.name = name
    }

    pub virtual fn area() -> f64 {
        return 0.0
    }
}

class Rectangle extends Shape {
    pub width: f64
    pub height: f64

    init(width: f64, height: f64) {
        super.init("Rectangle")
        self.width = width
        self.height = height
    }

    pub override fn area() -> f64 {
        return self.width * self.height
    }
}
```

### 4.2 C99 VTable Generation
```c
typedef struct Arx_Shape Arx_Shape;

// VTable struct
typedef struct Arx_Shape_VTable {
    double (*area)(Arx_Shape* self);
} Arx_Shape_VTable;

// Base struct
struct Arx_Shape {
    const Arx_Shape_VTable* vtable;
    const char* name;
};

// Derived struct includes base fields directly at offset 0
typedef struct Arx_Rectangle {
    Arx_Shape base; // Inherited fields & vtable pointer
    double width;
    double height;
} Arx_Rectangle;

// Implementation functions
double Arx_Shape_area(Arx_Shape* self) { return 0.0; }
double Arx_Rectangle_area(Arx_Rectangle* self) { return self->width * self->height; }

// Global static VTables
static const Arx_Shape_VTable Arx_Shape_vtable = { .area = (double(*)(Arx_Shape*))Arx_Shape_area };
static const Arx_Shape_VTable Arx_Rectangle_vtable = { .area = (double(*)(Arx_Shape*))Arx_Rectangle_area };
```

---

## 5. Traits (Interfaces)

Traits provide decoupling and multiple behavior contracts without the complications of multiple inheritance:

```aerix
trait Serializable {
    fn to_json() -> str
}

trait Loggable {
    fn log()
}

class User implements Serializable, Loggable {
    pub username: str
    pub email: str

    init(username: str, email: str) {
        self.username = username
        self.email = email
    }

    pub fn to_json() -> str {
        return "{\"user\": \"{self.username}\"}"
    }

    pub fn log() {
        println("[User]: {self.username} <{self.email}>")
    }
}
```

---

## 6. Access Modifiers & Encapsulation

Aerix strictly checks accessibility at compile time:

| Modifier | Meaning |
| :--- | :--- |
| `pub` | Public: Accessible anywhere in the program. |
| `priv` | Private: Accessible only within the declaring class methods. (Default for fields). |
| `prot` | Protected: Accessible within the declaring class and derived subclasses. |

---

## 7. Static Type System

### 7.1 Type Inference
The Aerix compiler infers types automatically when a variable is initialized:
```aerix
let a = 100            // Inferred: i64
let b = 3.14           // Inferred: f64
let flag = true        // Inferred: bool
let greeting = "hello" // Inferred: str
```

### 7.2 Explicit Types
When desired or when declaring function signatures, types are explicit:
```aerix
fn distance(x1: f64, y1: f64, x2: f64, y2: f64) -> f64 {
    let dx: f64 = x2 - x1
    let dy: f64 = y2 - y1
    return sqrt(dx * dx + dy * dy)
}
```

### 7.3 Null Safety & Optionals
Aerix prevents null-pointer exceptions at compile time using optional types (`T?`):
```aerix
fn find_user(id: i64) -> User? {
    if id == 1 {
        return User("Admin", "admin@aerix.org")
    }
    return null
}

fn main() {
    let u: User? = find_user(42)
    // Safe access with null coalescing:
    let name = u?.username ?? "Anonymous"
    println("Hello, {name}")
}
```

---

## 8. Memory Layout & Zero-Cost Struct Packing

Aerix maps classes directly to cache-aligned C structures:

```text
Class Instance Memory Map (Example: Player extends Entity):
+-------------------------+--------+---------------------------------------+
| Field                   | Size   | Alignment & Offset                    |
+-------------------------+--------+---------------------------------------+
| vtable_ptr (optional)   | 8 B    | Offset 0  (only if class has virtual) |
| Entity.id               | 8 B    | Offset 8                              |
| Entity.x                | 8 B    | Offset 16                             |
| Entity.y                | 8 B    | Offset 24                             |
| Player.name             | 8 B    | Offset 32 (const char* pointer)       |
| Player.health           | 4 B    | Offset 40 (int32_t)                   |
| [Padding]               | 4 B    | Offset 44 (aligns struct to 8 bytes)  |
+-------------------------+--------+---------------------------------------+
Total Struct Footprint: 48 Bytes (100% Cache-Coherent, Zero Bloat)
```

---

## 9. Devirtualization Optimization

Aerix's semantic analyzer performs whole-module class hierarchy analysis (CHA):
- If a method is marked `virtual` but is **never overridden** in any subclass, the compiler eliminates the virtual table lookup entirely and emits a **direct C function call**.
- Direct function calls allow GCC to **inline** the method body, perform register allocation, and execute vectorization loops.
- Result: **0% CPU penalty for Object-Oriented design**.

---

## 10. Trait Dynamic Dispatch (Fat Pointers)

When an object is passed as a generic trait interface (`fn render(d: &Drawable)`), Aerix compiles it as a 2-word fat pointer:

```c
typedef struct Arx_FatPtr {
    void* data;              // Pointer to the concrete struct instance
    const void* vtable;      // Pointer to the trait's virtual method table
} Arx_FatPtr;
```
This enables decoupled interface polymorphism without needing Java-style virtual machines or multiple inheritance diamond complications.

---

## 11. Aerix 2.0 Polymorphism & Overloading System

### 11.1 Static Method & Constructor Overloading
Aerix supports overloading methods and constructors with identical identifiers via **Static Arity and Type Specialization**:
```aerix
class Person {
    pub name: str, address: str

    // Constructor Overloading
    init(name: str) {
        self.name = name
        self.address = "Unassigned"
    }

    init(name: str, address: str) {
        self.name = name
        self.address = address
    }

    // Method Overloading
    pub fn set_details(name: str, address: str) -> void {
        self.name = name
        self.address = address
    }

    pub fn set_details(address: str) -> void {
        self.address = address
    }
}
```

### 11.2 Name Mangling Convention
At compile time, overloaded symbols are mangled cleanly without C++ ABI bloat:
```c
void Arx_Person_init__str(Arx_Person* self, const char* name);
void Arx_Person_init__str_str(Arx_Person* self, const char* name, const char* address);

void Arx_Person_set_details__str(Arx_Person* self, const char* address);
void Arx_Person_set_details__str_str(Arx_Person* self, const char* name, const char* address);
```

### 11.3 Named Constructor Variants (`init.<name>`)
For constructors with matching parameter types requiring distinct initialisation logic:
```aerix
class Vector3D {
    pub x: f64, y: f64, z: f64

    init(x: f64, y: f64, z: f64) { self.x = x; self.y = y; self.z = z; }
    init.zero() { self.x = 0.0; self.y = 0.0; self.z = 0.0; }
    init.uniform(s: f64) { self.x = s; self.y = s; self.z = s; }
}
```

### 11.4 Operator Overloading
Operators map to inlined static functions with compile-time type verification:
```aerix
class Vector2D {
    pub x: f64, y: f64

    pub op +(other: Vector2D) -> Vector2D {
        return Vector2D(self.x + other.x, self.y + other.y)
    }

    pub op ==(other: Vector2D) -> bool {
        return self.x == other.x && self.y == other.y
    }
}
```
Emitted C code inlines `Arx_Vector2D_op_add(&v1, &v2)` with zero allocation overhead.


