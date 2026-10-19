# Aerix (arx) — Real-Time Systems, Game Engines & Embedded Hardware Roadmap

> **Document Version:** 1.0.88-alpha  
> **Status:** 📐 SPECIFICATION & MASTER IMPLEMENTATION BLUEPRINT (Phases 23–28)  
> **Target Domains:** Game Engines, Physics/Simulations, Microcontrollers, Robotics, Edge IoT  
> **Core Compilation Target:** ANSI C99 / GCC / Clang / Bare-Metal Freestanding

---

## 🎯 Executive Vision: The Unified Real-Time Systems Language

Aerix occupies a unique space in modern programming language architecture. While high-level languages (Python, Dart, Swift, Elixir) offer expressive syntax, pipelines, and developer velocity, they require **heavy garbage collectors and runtime engines** that disqualify them from real-time execution. Conversely, low-level languages (C, C++, Rust, Zig) deliver bare-metal speed, but force developers to write **verbose, rigid, and friction-heavy boilerplate**.

**Aerix unites both worlds into a single, cohesive discipline:**
> **"Aerix: The Real-Time Systems Language for Games, Physics, and Physical Hardware."**

### Why Game Engines (Option 2) and Embedded Hardware (Option 3) are the Same Problem:
Game engines and microcontrollers share the **exact same 4 non-negotiable constraints**:
1. **Zero Garbage Collection (Deterministic Latency):**
   - A 10ms GC pause in a game drops frames from 144 FPS to 30 FPS.
   - A 10ms GC pause in a drone or robotics controller causes the PID loop to lag and crashes the vehicle.
2. **Direct Hardware & Memory Layout Control:**
   - Game engines require cache-line-aligned memory (64-byte L1/L2 cache boundaries) and SIMD vector registers.
   - Microcontrollers require bit-exact memory-mapped I/O (MMIO) and packed hardware register structs.
3. **Fixed-Time Real-Time Loops:**
   - Games execute a deterministic 60 Hz / 120 Hz render and physics update loop.
   - Drones, flight controllers, and motor drives execute a 500 Hz / 1000 Hz sensor and PID loop.
4. **ANSI C99 as the Universal Hardware Target:**
   - Every microcontroller (ESP32, STM32, Arduino, Raspberry Pi Pico, RISC-V) and every game console (PlayStation, Nintendo Switch) provides a world-class, ultra-optimized ANSI C99 compiler (GCC/Clang).

---

## 📊 Architectural Gap Matrix: Current (v1.0.88) vs. Real-Time Target

| Dimension | Aerix v1.0.88 (Current) | Real-Time Systems Target (Phases 23–28) | Why Needed for Games & Hardware |
| :--- | :--- | :--- | :--- |
| **Array Allocations** | Dynamic Heap `List<T>` (uses `malloc`) | Fixed Stack Arrays `[T; N]` (zero `malloc`) | Microcontrollers with 8KB RAM cannot allocate heap memory; game loops cannot afford allocator fragmentation. |
| **Struct Alignment** | Default C struct alignment (compiler padded) | First-Class `#[packed]` and `#[align(N)]` | Microcontrollers need packed byte streams for CAN-bus/SPI; games need 64-byte CPU cache-line alignment. |
| **Hardware I/O** | High-level OS stdlib / file I/O | Memory-Mapped I/O (`volatile` register access) | Physical hardware reads and writes directly to hardware addresses (e.g. `0x40021000` for GPIO pins). |
| **Vector Math** | SIMD primitive type exists (`f32x4`) | Direct SIMD Math Operators (`+`, `-`, `*`, `/`, dot) | 3D game physics and robotics inverse kinematics require hardware AVX/NEON vector calculations in 1 CPU cycle. |
| **Runtime Mode** | Hosted (`aerix_rt.h`, OS libc required) | Freestanding (`--freestanding`, zero OS dependencies) | Embedded firmware runs bare-metal without an operating system, dynamic linker, or standard library. |
| **Data Layout** | Object-Oriented Array-of-Structs (AoS) | Struct-of-Arrays (SoA) transforms (`soa class`) | Cache misses waste 70% of CPU cycles in physics loops; SoA enables 4x–8x faster SIMD auto-vectorization. |

---

## 🧱 1. Fixed-Size Stack-Allocated Arrays: `[T; N]`

### 1.1 Specification & Design
Currently, Aerix arrays are dynamic heap lists (`List<T>`). In embedded firmware and game physics hot paths, heap allocations are prohibited. Aerix introduces **first-class fixed-size stack arrays** denoted by `[T; N]`, where `T` is any primitive or struct type and `N` is an integer constant expression evaluated at compile time.

### 1.2 Syntax & Examples
```aerix
// 1. Explicit type annotation with array literal
let sensor_pins: [i32; 4] = [2, 4, 12, 14]

// 2. Uniform initialization repeat syntax: [value; count]
mut motor_pwm: [u16; 8] = [0; 8]

// 3. Direct zero-cost indexing and assignment
motor_pwm[0] = 1000
let primary = motor_pwm[0]

// 4. Pass by value or by reference into functions
fn normalize_quaternion(mut q: [f32; 4]) -> [f32; 4] {
    let mag = (q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3]) |> sqrt()
    q[0] /= mag
    q[1] /= mag
    q[2] /= mag
    q[3] /= mag
    return q
}
```

### 1.3 Compiler Pipeline Lowering
* **Lexer:** Recognize `[` and `;` and `]`.
* **AST Node:** 
  ```python
  class FixedArrayTypeNode(ASTNode):
      element_type: TypeNode
      size: int  # Compile-time resolved integer constant

  class FixedArrayLiteralNode(ASTNode):
      elements: List[ASTNode]
      repeat_count: Optional[int]  # For [val; N] repeat initialization
  ```
* **Semantic Analysis:** Verify that `N > 0`, that literal element count matches `N`, and that compile-time indices satisfy `0 <= idx < N`.
* **C99 Emission:**
  ```c
  // Aerix: let sensor_pins: [i32; 4] = [2, 4, 12, 14];
  // Emitted C99:
  int32_t sensor_pins[4] = { 2, 4, 12, 14 };
  
  // Aerix: mut motor_pwm: [u16; 8] = [0; 8];
  // Emitted C99:
  uint16_t motor_pwm[8] = { 0 };
  ```

---

## 📐 2. Physical Memory Layout Attributes: `#[packed]` and `#[align(N)]`

### 2.1 Specification & Design
Hardware communication and cache-conscious game engines require direct control over struct packing and byte alignment. Aerix introduces declarative compiler annotations on class and struct definitions.

### 2.2 Syntax & Examples

#### A. `#[packed]` (Hardware Registers & Serial Packets)
Disables all C compiler struct alignment padding. Fields are placed strictly adjacent in physical memory.
```aerix
#[packed]
class MPU6050TelemetryPacket {
    pub header: u8           // Offset 0 (1 byte)
    pub accel_x: i16         // Offset 1 (2 bytes)
    pub accel_y: i16         // Offset 3 (2 bytes)
    pub accel_z: i16         // Offset 5 (2 bytes)
    pub temp_raw: i16        // Offset 7 (2 bytes)
    pub checksum: u8         // Offset 9 (1 byte)
}
// sizeof(MPU6050TelemetryPacket) == exactly 10 bytes (normally 12 bytes with C padding)
```

#### B. `#[align(N)]` (Cache-Line Boundaries & SIMD Alignment)
Forces the starting memory address of instances to be a multiple of `N` bytes (where `N` is a power of 2: 16, 32, 64, 128).
```aerix
// Aligned to 64 bytes (the physical L1/L2 cache line size of x86 and ARM CPUs)
#[align(64)]
class RigidBodyEntity {
    pub position: f32x4      // 16 bytes
    pub velocity: f32x4      // 16 bytes
    pub mass: f32            // 4 bytes
    pub entity_id: u32       // 4 bytes
    // Remaining bytes to 64 are padded automatically to eliminate false sharing
}
```

### 2.3 Compiler Pipeline Lowering
* **Lexer / Parser:** Support attribute decorator syntax `#[ <identifier> ( <argument>? ) ]` preceding `class` definitions.
* **Semantic Analysis:** Ensure `N` in `#[align(N)]` is a power of two (`16, 32, 64, 128`).
* **C99 Emission:**
  ```c
  // Packed C99 struct:
  typedef struct __attribute__((packed)) {
      uint8_t header;
      int16_t accel_x;
      int16_t accel_y;
      int16_t accel_z;
      int16_t temp_raw;
      uint8_t checksum;
  } Arx_MPU6050TelemetryPacket;

  // Aligned C99 struct:
  typedef struct __attribute__((aligned(64))) {
      v4sf position;
      v4sf velocity;
      float mass;
      uint32_t entity_id;
  } Arx_RigidBodyEntity;
  ```

---

## ⚡ 3. Memory-Mapped I/O (MMIO) & Volatile Hardware Pointers

### 3.1 Specification & Design
In robotics and embedded microcontrollers, physical pins, timers, and hardware peripherals are controlled by reading and writing to dedicated physical memory addresses (e.g. `0x40021000` for STM32 GPIO ports). Because external hardware changes these addresses asynchronously, the compiler optimizer **must never cache or elide these memory reads/writes**.

Aerix introduces intrinsic **volatile memory access functions**:
* `volatile_read_u8(address: usize) -> u8`
* `volatile_read_u16(address: usize) -> u16`
* `volatile_read_u32(address: usize) -> u32`
* `volatile_write_u8(address: usize, value: u8) -> void`
* `volatile_write_u16(address: usize, value: u16) -> void`
* `volatile_write_u32(address: usize, value: u32) -> void`

### 3.2 Syntax & Real-World Example
```aerix
// Microcontroller GPIO Port Configuration
const GPIOA_BASE: usize = 0x40020000
const GPIOA_MODER: usize = GPIOA_BASE + 0x00
const GPIOA_ODR: usize   = GPIOA_BASE + 0x14

fn configure_pin_as_output(pin: i32) {
    let current_mode = volatile_read_u32(GPIOA_MODER)
    let new_mode = current_mode | (1 << (pin * 2))
    volatile_write_u32(GPIOA_MODER, new_mode)
}

fn set_pin_high(pin: i32) {
    let current_output = volatile_read_u32(GPIOA_ODR)
    volatile_write_u32(GPIOA_ODR, current_output | (1 << pin))
}
```

### 3.3 C99 Lowering
```c
#define volatile_read_u32(addr) (*((volatile uint32_t*)(uintptr_t)(addr)))
#define volatile_write_u32(addr, val) (*((volatile uint32_t*)(uintptr_t)(addr)) = (uint32_t)(val))
```

---

## 🚀 4. First-Class SIMD Arithmetic Operators (`f32x4`, `f64x2`)

### 4.1 Specification & Design
Aerix currently recognizes `f32x4` as a 128-bit primitive type. To empower 3D game engines, raytracers, and physics simulations, Aerix elevates `f32x4` to support **direct arithmetic operator overloading** and **standard vector geometric intrinsics** natively.

### 4.2 Syntax & Operations
```aerix
fn update_entity_kinematics(pos: f32x4, vel: f32x4, dt: f32) -> f32x4 {
    // Vector addition and scalar-vector multiplication
    let dt_vec = f32x4(dt, dt, dt, 0.0)
    let next_pos = pos + (vel * dt_vec)
    return next_pos
}

fn calculate_lighting(normal: f32x4, light_dir: f32x4) -> f32 {
    // Hardware-accelerated dot product
    let n_dot_l = normal.dot(light_dir)
    return n_dot_l |> clamp(0.0, 1.0)
}
```

### 4.3 Vector Intrinsics Suite
* `vec.dot(other: f32x4) -> f32`: Vector dot product ($x_1x_2 + y_1y_2 + z_1z_2 + w_1w_2$).
* `vec.cross(other: f32x4) -> f32x4`: 3D cross product ($y_1z_2 - z_1y_2$, etc.).
* `vec.length() -> f32`: Euclidean length / magnitude.
* `vec.normalize() -> f32x4`: Unit vector normalization.
* `vec.min(other: f32x4) -> f32x4`: Per-lane minimum.
* `vec.max(other: f32x4) -> f32x4`: Per-lane maximum.

### 4.4 C99 Lowering
Using GCC / Clang vector extensions (`__attribute__((vector_size(16)))`):
```c
typedef float v4sf __attribute__ ((vector_size (16)));

static inline v4sf arx_vec_add(v4sf a, v4sf b) { return a + b; }
static inline v4sf arx_vec_mul(v4sf a, v4sf b) { return a * b; }
static inline float arx_vec_dot(v4sf a, v4sf b) {
    v4sf p = a * b;
    return p[0] + p[1] + p[2] + p[3];
}
```

---

## 🛠️ 5. Freestanding Bare-Metal Compilation Mode (`--freestanding`)

### 5.1 Specification & Design
When compiling firmware for an Arduino, ESP32, STM32, or a custom game engine launcher, the host OS standard C library (`libc`) is absent. Aerix introduces the `--freestanding` flag in the CLI:

```powershell
# Compile Aerix source directly to freestanding C99
arx build firmware.arx --freestanding -o firmware.c
```

### 5.2 Architectural Rules of Freestanding Mode
1. **Zero Standard Library Headers:** Excludes `<stdio.h>`, `<stdlib.h>`, `<pthread.h>`, and `<windows.h>`.
2. **Zero Dynamic Memory Allocation:** The compiler flags dynamic heap types (`List<T>`, `String`, `Map<K, V>`) as compile-time errors in freestanding mode, guaranteeing **zero runtime allocator failures**.
3. **Embedded Entry Point:** Permits custom microcontroller entry points (`fn setup()`, `fn loop()`) without enforcing an OS-level `fn main() -> int`.
4. **Direct Header Compatibility:** Emitted `.c` files can be included or compiled directly with:
   - `arm-none-eabi-gcc` (STM32, Raspberry Pi Pico, ARM Cortex-M)
   - `xtensa-esp32-elf-gcc` (ESP32, ESP8266)
   - `avr-gcc` (Arduino Uno, Mega, ATmega328p)

---

## 🎮 6. Struct-of-Arrays (SoA) for Game Engines

### 6.1 The "Memory Wall" & Cache Lines
In traditional OOP, an entity is stored as an **Array of Structures (AoS)**:
```text
[ {x, y, vx, vy, hp, name}, {x, y, vx, vy, hp, name}, ... ]
```
When updating positions, the CPU loads useless fields (`hp`, `name`) into the 64-byte L1 cache line, wasting 75% of memory bandwidth.

**Struct-of-Arrays (SoA)** rearranges the memory layout into parallel contiguous arrays:
```text
x:  [ x0,  x1,  x2,  x3,  x4, ... ]
y:  [ y0,  y1,  y2,  y3,  y4, ... ]
vx: [ vx0, vx1, vx2, vx3, vx4, ... ]
vy: [ vy0, vy1, vy2, vy3, vy4, ... ]
```
Every single byte loaded into the L1 cache is consumed by the CPU, enabling **instant hardware auto-vectorization** and a **4x–8x performance boost**.

### 6.2 Aerix `soa class` Syntax
```aerix
soa class Bullet {
    pub x: f32
    pub y: f32
    pub vx: f32
    pub vy: f32
    pub lifetime: f32
}

fn update_bullets(mut bullets: SoA<Bullet, 1024>, dt: f32) {
    for b in bullets {
        b.x += b.vx * dt
        b.y += b.vy * dt
        b.lifetime -= dt
    }
}
```

---

## 🚀 7. Two Flagship Real-World Showcases

### Showcase A: 60 FPS Particle Gravity Simulation (Game / Physics)
File: `examples/30_REALTIME_PARTICLE_PHYSICS.arx`
```aerix
// Real-Time Particle Physics Engine in Aerix
// Compiles to WebAssembly (Canvas Live Preview) or Native 144 FPS Binary

#[align(64)]
class ParticleSystem {
    pub positions: [f32x4; 1000]
    pub velocities: [f32x4; 1000]
    pub count: i32

    init(count: i32) {
        self.count = count
        mut i = 0
        while i < count {
            self.positions[i] = f32x4(0.0, 0.0, 0.0, 1.0)
            self.velocities[i] = f32x4(0.1, 0.2, 0.0, 0.0)
            i += 1
        }
    }

    pub fn step(dt: f32) {
        let gravity = f32x4(0.0, -9.81 * dt, 0.0, 0.0)
        let dt_step = f32x4(dt, dt, dt, 0.0)
        mut i = 0
        while i < self.count {
            self.velocities[i] += gravity
            self.positions[i] += self.velocities[i] * dt_step
            i += 1
        }
    }
}
```

---

### Showcase B: Drone 1000 Hz PID Motor Controller (Embedded Firmware)
File: `examples/31_EMBEDDED_DRONE_PID_CONTROLLER.arx`
```aerix
// Autonomous Drone Flight Controller Firmware (Freestanding Bare-Metal)
// Executed at 1000 Hz (1 millisecond control loop) on an STM32F4 processor

#[packed]
class MPU6050RawData {
    pub accel_x: i16
    pub accel_y: i16
    pub accel_z: i16
    pub gyro_pitch: i16
    pub gyro_roll: i16
    pub gyro_yaw: i16
}

class PIDController {
    pub kp: f32
    pub ki: f32
    pub kd: f32
    pub integral: f32
    pub prev_error: f32

    pub fn compute(setpoint: f32, current: f32, dt: f32) -> f32 {
        let error = setpoint - current
        self.integral += error * dt
        let derivative = (error - self.prev_error) / dt
        self.prev_error = error

        return (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)
    }
}

// 1000 Hz Real-Time Tick Entry Point
fn flight_loop_step(mut pid: PIDController, gyro_reading: f32, dt: f32) -> u16 {
    let desired_pitch: f32 = 0.0  // Keep level
    let correction = pid.compute(desired_pitch, gyro_reading, dt)

    let base_throttle: f32 = 1400.0
    let motor_output = (base_throttle + correction) |> clamp(1000.0, 2000.0)
    return motor_output as u16
}
```

---

## 📅 8. Phased Implementation Roadmap & Verification Plan

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PHASED EXECUTION PIPELINE                       │
├────────────────────────────────────────────────────────────────────────┤
│  PHASE 23: Fixed-Size Stack Arrays ([T; N])                           │
│    - Grammar, AST nodes, semantic bounds validation                    │
│    - Stack C99 array lowering, array indexing, repeat [0; N] syntax    │
│    - Automated Test: test_phase23_fixed_arrays.py                     │
├────────────────────────────────────────────────────────────────────────┤
│  PHASE 24: Memory Layout Attributes (#[packed] & #[align(N)])         │
│    - Attribute parsing on class definitions                            │
│    - C99 __attribute__((packed)) & __attribute__((aligned(N)))         │
│    - Volatile MMIO intrinsics (volatile_read_*, volatile_write_*)      │
│    - Automated Test: test_phase24_layout_and_mmio.py                   │
├────────────────────────────────────────────────────────────────────────┤
│  PHASE 25: First-Class SIMD Arithmetic Operators                      │
│    - Overloaded +, -, *, / for f32x4 and f64x2                         │
│    - Intrinsics: dot(), cross(), length(), normalize()                │
│    - Automated Test: test_phase25_simd_vectors.py                      │
├────────────────────────────────────────────────────────────────────────┤
│  PHASE 26: Freestanding Bare-Metal Compilation Mode                   │
│    - CLI --freestanding flag integration in src/arx.py                │
│    - Libc exclusion, heap error validation, embedded setup/loop hooks  │
│    - Automated Test: test_phase26_freestanding.py                      │
├────────────────────────────────────────────────────────────────────────┤
│  PHASE 27: Struct-of-Arrays (SoA) Engine for Games                    │
│    - soa class syntax and compiler layout decomposition                │
│    - Auto-vectorized SIMD batch iteration                              │
│    - Automated Test: test_phase27_soa_engine.py                        │
├────────────────────────────────────────────────────────────────────────┤
│  PHASE 28: Flagship Real-World Demos & Tooling Delivery               │
│    - examples/30_REALTIME_PARTICLE_PHYSICS.arx (WASM/Native 60 FPS)   │
│    - examples/31_EMBEDDED_DRONE_PID_CONTROLLER.arx (Freestanding C)   │
│    - Documentation update, VSIX release v1.0.89, installer compilation │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Verification Criteria & Quality Standards

1. **Deterministic Test Execution:** Every phase must add automated unit tests executed via `python -m unittest` with 100% pass rate.
2. **Zero-Allocation Invariant:** In `--freestanding` mode, emitted C code must contain **0 calls** to `malloc`, `calloc`, `realloc`, or `free`.
3. **Exact Memory Layout Alignment:** Verified using `sizeof()` and `offsetof()` assertions compiled natively with GCC.
4. **Examples Integrity:** Code samples in `examples/` must remain clean, runnable demonstrations, never targeted by build outputs.
5. **Toolchain Uniformity:** All compiler versions, installer configurations, and VS Code extensions must track identically across every milestone.
