/**
 * Aerix (arx) — Core Native Runtime Header
 * Standard: ANSI C99 / C11
 * Zero external dependencies. Header-only.
 */

#ifndef AERIX_RT_H
#define AERIX_RT_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdarg.h>
#include <math.h>
#include <ctype.h>

#if defined(_WIN32) || defined(_WIN64)
    #include <windows.h>
    typedef HANDLE arx_thread_t;
#else
    #include <pthread.h>
    #include <unistd.h>
    #include <time.h>
    typedef pthread_t arx_thread_t;
#endif

// --- Fixed-Width Typedefs ---
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

typedef size_t   usize;
typedef const char* str;

// --- Runtime Panic Handler ---
static inline void arx_panic(const char* msg, const char* file, int line) {
    fprintf(stderr, "\n\033[1;31m[AERIX RUNTIME PANIC]\033[0m: %s\n", msg);
    fprintf(stderr, "  --> at %s:%d\n\n", file, line);
    exit(1);
}

#define ARX_ASSERT(cond, msg) \
    do { if (!(cond)) arx_panic(msg, __FILE__, __LINE__); } while(0)

// --- Safe Memory Allocators ---
static inline void* arx_alloc(size_t bytes) {
    void* ptr = malloc(bytes);
    if (!ptr && bytes > 0) {
        arx_panic("Out of memory allocation failure", __FILE__, __LINE__);
    }
    return ptr;
}

static inline void arx_free(void* ptr) {
    if (ptr) {
        free(ptr);
    }
}

// --- High-Resolution Timer ---
static inline f64 arx_time_now(void) {
#if defined(_WIN32) || defined(_WIN64)
    LARGE_INTEGER freq, counter;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&counter);
    return freq.QuadPart > 0 ? (f64)counter.QuadPart / (f64)freq.QuadPart : 0.0;
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (f64)ts.tv_sec + (f64)ts.tv_nsec * 1e-9;
#endif
}

// --- Formatted String Utility ---
static inline char* arx_format_str(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    va_list args_copy;
    va_copy(args_copy, args);
    int len = vsnprintf(NULL, 0, fmt, args_copy);
    va_end(args_copy);
    if (len < 0) {
        va_end(args);
        char* empty_buf = (char*)arx_alloc(1);
        empty_buf[0] = '\0';
        return empty_buf;
    }
    char* buf = (char*)arx_alloc(len + 1);
    vsnprintf(buf, len + 1, fmt, args);
    va_end(args);
    return buf;
}

// --- Formatted Console Printing ---
static inline void arx_print_str(const char* s) {
    fputs(s, stdout);
}

static inline void arx_println_str(const char* s) {
    puts(s);
}

static inline void arx_print_i64(i64 n) {
    printf("%lld", (long long)n);
}

static inline void arx_println_i64(i64 n) {
    printf("%lld\n", (long long)n);
}

static inline void arx_print_f64(f64 n) {
    printf("%g", n);
}

static inline void arx_println_f64(f64 n) {
    printf("%g\n", n);
}

static inline void arx_print_bool(bool b) {
    fputs(b ? "true" : "false", stdout);
}

static inline void arx_println_bool(bool b) {
    puts(b ? "true" : "false");
}

// --- Console User Input ---
static inline char* arx_input(const char* prompt) {
    if (prompt && prompt[0] != '\0') {
        fputs(prompt, stdout);
        fflush(stdout);
    }
    char buffer[4096];
    if (!fgets(buffer, sizeof(buffer), stdin)) {
        char* empty_buf = (char*)arx_alloc(1);
        empty_buf[0] = '\0';
        return empty_buf;
    }
    size_t len = strlen(buffer);
    while (len > 0 && (buffer[len - 1] == '\n' || buffer[len - 1] == '\r')) {
        buffer[--len] = '\0';
    }
    char* result = (char*)arx_alloc(len + 1);
    memcpy(result, buffer, len + 1);
    return result;
}

static inline char* arx_readln(void) {
    return arx_input("");
}

// --- Type Casting Helpers ---
static inline int64_t arx_cast_to_i64(const char* s) {
    if (!s) return 0;
    while (*s == ' ' || *s == '\t' || *s == '\r' || *s == '\n') s++;
    return (int64_t)strtoll(s, NULL, 10);
}

static inline uint64_t arx_cast_to_u64(const char* s) {
    if (!s) return 0;
    while (*s == ' ' || *s == '\t' || *s == '\r' || *s == '\n') s++;
    return (uint64_t)strtoull(s, NULL, 10);
}

static inline double arx_cast_to_f64(const char* s) {
    if (!s) return 0.0;
    while (*s == ' ' || *s == '\t' || *s == '\r' || *s == '\n') s++;
    return strtod(s, NULL);
}

static inline bool arx_cast_to_bool(const char* s) {
    if (!s) return false;
    while (*s == ' ' || *s == '\t' || *s == '\r' || *s == '\n') s++;
    return (strcmp(s, "true") == 0 || strcmp(s, "1") == 0 || strcmp(s, "yes") == 0 || strcmp(s, "t") == 0 || strcmp(s, "y") == 0);
}

static inline const char* arx_cast_i64_to_str(int64_t v) {
    return arx_format_str("%lld", (long long)v);
}

static inline const char* arx_cast_u64_to_str(uint64_t v) {
    return arx_format_str("%llu", (unsigned long long)v);
}

static inline const char* arx_cast_f64_to_str(double v) {
    return arx_format_str("%g", v);
}

static inline const char* arx_cast_bool_to_str(bool v) {
    return v ? "true" : "false";
}

static inline const char* arx_cast_char_to_str(char v) {
    char* s = (char*)arx_alloc(2);
    s[0] = v;
    s[1] = '\0';
    return s;
}

// --- Dynamic Typed Input Helpers ---
static inline int64_t arx_input_int(const char* prompt) {
    char* s = arx_input(prompt);
    return arx_cast_to_i64(s);
}

static inline uint64_t arx_input_uint(const char* prompt) {
    char* s = arx_input(prompt);
    return arx_cast_to_u64(s);
}

static inline double arx_input_float(const char* prompt) {
    char* s = arx_input(prompt);
    return arx_cast_to_f64(s);
}

static inline bool arx_input_bool(const char* prompt) {
    char* s = arx_input(prompt);
    return arx_cast_to_bool(s);
}

static inline char arx_input_char(const char* prompt) {
    char* s = arx_input(prompt);
    return (s && s[0]) ? s[0] : '\0';
}

static inline int64_t arx_readln_int(void) {
    return arx_input_int("");
}

static inline uint64_t arx_readln_uint(void) {
    return arx_input_uint("");
}

static inline double arx_readln_float(void) {
    return arx_input_float("");
}

static inline bool arx_readln_bool(void) {
    return arx_input_bool("");
}

static inline char arx_readln_char(void) {
    return arx_input_char("");
}

// --- Linear Arena Allocator (Phase 14) ---
typedef struct Arx_Arena {
    uint8_t* buffer;
    size_t capacity;
    size_t offset;
} Arx_Arena;

static inline Arx_Arena arx_arena_create(size_t capacity) {
    Arx_Arena arena;
    arena.buffer = (uint8_t*)malloc(capacity);
    if (!arena.buffer && capacity > 0) {
        arx_panic("Arena allocation failed: Out of memory", __FILE__, __LINE__);
    }
    arena.capacity = capacity;
    arena.offset = 0;
    return arena;
}

static inline void* arx_arena_alloc(Arx_Arena* arena, size_t size) {
    if (!arena || !arena->buffer) return NULL;
    // 8-byte natural alignment
    size_t aligned_offset = (arena->offset + 7) & ~((size_t)7);
    if (aligned_offset + size > arena->capacity) {
        arx_panic("Arena overflow: exceeded allocated capacity", __FILE__, __LINE__);
    }
    void* ptr = (void*)(arena->buffer + aligned_offset);
    arena->offset = aligned_offset + size;
    return ptr;
}

static inline void arx_arena_reset(Arx_Arena* arena) {
    if (arena) {
        arena->offset = 0; // O(1) bulk deallocation in a single CPU cycle!
    }
}

static inline void arx_arena_free(Arx_Arena* arena) {
    if (arena && arena->buffer) {
        free(arena->buffer);
        arena->buffer = NULL;
        arena->capacity = 0;
        arena->offset = 0;
    }
}

static inline size_t arx_arena_used(const Arx_Arena* arena) {
    return arena ? arena->offset : 0;
}

static inline size_t arx_arena_capacity(const Arx_Arena* arena) {
    return arena ? arena->capacity : 0;
}

// --- Hardware SIMD Vector Primitives (Phase 14) ---
typedef struct f32x4 {
    float x, y, z, w;
} f32x4;

static inline f32x4 arx_f32x4_create(float x, float y, float z, float w) {
    f32x4 v = {x, y, z, w};
    return v;
}

static inline f32x4 arx_f32x4_add(f32x4 a, f32x4 b) {
    f32x4 v = {a.x + b.x, a.y + b.y, a.z + b.z, a.w + b.w};
    return v;
}

static inline f32x4 arx_f32x4_sub(f32x4 a, f32x4 b) {
    f32x4 v = {a.x - b.x, a.y - b.y, a.z - b.z, a.w - b.w};
    return v;
}

static inline f32x4 arx_f32x4_mul(f32x4 a, f32x4 b) {
    f32x4 v = {a.x * b.x, a.y * b.y, a.z * b.z, a.w * b.w};
    return v;
}

static inline float arx_f32x4_dot(f32x4 a, f32x4 b) {
    return a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w;
}

// --- Native Threading & Channel Primitives (Phase 19) ---

static inline void arx_sleep_ms(int64_t ms) {
#if defined(_WIN32) || defined(_WIN64)
    Sleep((DWORD)ms);
#else
    usleep((useconds_t)(ms * 1000));
#endif
}

static inline int64_t arx_thread_spawn(void* (*func)(void*), void* arg) {
#if defined(_WIN32) || defined(_WIN64)
    HANDLE h = CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)func, (LPVOID)arg, 0, NULL);
    return (int64_t)(intptr_t)h;
#else
    arx_thread_t t;
    pthread_create(&t, NULL, func, arg);
    return (int64_t)(intptr_t)t;
#endif
}

static inline void arx_thread_join(int64_t handle) {
    arx_thread_t t = (arx_thread_t)(intptr_t)handle;
#if defined(_WIN32) || defined(_WIN64)
    if (t) {
        WaitForSingleObject(t, INFINITE);
        CloseHandle(t);
    }
#else
    if (t) {
        pthread_join(t, NULL);
    }
#endif
}

typedef struct Arx_Channel {
    int64_t* data;
    int64_t capacity;
    int64_t count;
    int64_t head;
    int64_t tail;
    bool is_closed;
#if defined(_WIN32) || defined(_WIN64)
    CRITICAL_SECTION cs;
    CONDITION_VARIABLE not_empty;
    CONDITION_VARIABLE not_full;
#else
    pthread_mutex_t lock;
    pthread_cond_t not_empty;
    pthread_cond_t not_full;
#endif
} Arx_Channel;

static inline int64_t arx_channel_new(int64_t capacity) {
    if (capacity <= 0) capacity = 64;
    Arx_Channel* ch = (Arx_Channel*)arx_alloc(sizeof(Arx_Channel));
    ch->data = (int64_t*)arx_alloc(sizeof(int64_t) * capacity);
    ch->capacity = capacity;
    ch->count = 0;
    ch->head = 0;
    ch->tail = 0;
    ch->is_closed = false;
#if defined(_WIN32) || defined(_WIN64)
    InitializeCriticalSection(&ch->cs);
    InitializeConditionVariable(&ch->not_empty);
    InitializeConditionVariable(&ch->not_full);
#else
    pthread_mutex_init(&ch->lock, NULL);
    pthread_cond_init(&ch->not_empty, NULL);
    pthread_cond_init(&ch->not_full, NULL);
#endif
    return (int64_t)(intptr_t)ch;
}

static inline void arx_channel_send(int64_t ch_handle, int64_t val) {
    Arx_Channel* ch = (Arx_Channel*)(intptr_t)ch_handle;
    if (!ch) return;
#if defined(_WIN32) || defined(_WIN64)
    EnterCriticalSection(&ch->cs);
    while (ch->count == ch->capacity && !ch->is_closed) {
        SleepConditionVariableCS(&ch->not_full, &ch->cs, INFINITE);
    }
    if (ch->is_closed) {
        LeaveCriticalSection(&ch->cs);
        return;
    }
    ch->data[ch->tail] = val;
    ch->tail = (ch->tail + 1) % ch->capacity;
    ch->count++;
    WakeConditionVariable(&ch->not_empty);
    LeaveCriticalSection(&ch->cs);
#else
    pthread_mutex_lock(&ch->lock);
    while (ch->count == ch->capacity && !ch->is_closed) {
        pthread_cond_wait(&ch->not_full, &ch->lock);
    }
    if (ch->is_closed) {
        pthread_mutex_unlock(&ch->lock);
        return;
    }
    ch->data[ch->tail] = val;
    ch->tail = (ch->tail + 1) % ch->capacity;
    ch->count++;
    pthread_cond_signal(&ch->not_empty);
    pthread_mutex_unlock(&ch->lock);
#endif
}

static inline int64_t arx_channel_recv(int64_t ch_handle) {
    Arx_Channel* ch = (Arx_Channel*)(intptr_t)ch_handle;
    if (!ch) return 0;
#if defined(_WIN32) || defined(_WIN64)
    EnterCriticalSection(&ch->cs);
    while (ch->count == 0 && !ch->is_closed) {
        SleepConditionVariableCS(&ch->not_empty, &ch->cs, INFINITE);
    }
    if (ch->count == 0 && ch->is_closed) {
        LeaveCriticalSection(&ch->cs);
        return 0;
    }
    int64_t val = ch->data[ch->head];
    ch->head = (ch->head + 1) % ch->capacity;
    ch->count--;
    WakeConditionVariable(&ch->not_full);
    LeaveCriticalSection(&ch->cs);
    return val;
#else
    pthread_mutex_lock(&ch->lock);
    while (ch->count == 0 && !ch->is_closed) {
        pthread_cond_wait(&ch->not_empty, &ch->lock);
    }
    if (ch->count == 0 && ch->is_closed) {
        pthread_mutex_unlock(&ch->lock);
        return 0;
    }
    int64_t val = ch->data[ch->head];
    ch->head = (ch->head + 1) % ch->capacity;
    ch->count--;
    pthread_cond_signal(&ch->not_full);
    pthread_mutex_unlock(&ch->lock);
    return val;
#endif
}

static inline void arx_channel_close(int64_t ch_handle) {
    Arx_Channel* ch = (Arx_Channel*)(intptr_t)ch_handle;
    if (!ch) return;
#if defined(_WIN32) || defined(_WIN64)
    EnterCriticalSection(&ch->cs);
    ch->is_closed = true;
    WakeAllConditionVariable(&ch->not_empty);
    WakeAllConditionVariable(&ch->not_full);
    LeaveCriticalSection(&ch->cs);
#else
    pthread_mutex_lock(&ch->lock);
    ch->is_closed = true;
    pthread_cond_broadcast(&ch->not_empty);
    pthread_cond_broadcast(&ch->not_full);
    pthread_mutex_unlock(&ch->lock);
#endif
}

static inline void arx_channel_free(int64_t ch_handle) {
    Arx_Channel* ch = (Arx_Channel*)(intptr_t)ch_handle;
    if (!ch) return;
    arx_channel_close(ch_handle);
#if defined(_WIN32) || defined(_WIN64)
    DeleteCriticalSection(&ch->cs);
#else
    pthread_mutex_destroy(&ch->lock);
    pthread_cond_destroy(&ch->not_empty);
    pthread_cond_destroy(&ch->not_full);
#endif
    if (ch->data) arx_free(ch->data);
    arx_free(ch);
}

// ==========================================
// Phase 21: Dynamic Collections (List<T>)
// ==========================================

typedef struct {
    int64_t* data;
    size_t len;
    size_t cap;
} Arx_List;

static inline int64_t arx_list_new(int64_t initial_cap) {
    if (initial_cap < 4) initial_cap = 4;
    Arx_List* list = (Arx_List*)arx_alloc(sizeof(Arx_List));
    list->data = (int64_t*)arx_alloc((size_t)initial_cap * sizeof(int64_t));
    list->len = 0;
    list->cap = (size_t)initial_cap;
    return (int64_t)(intptr_t)list;
}

static inline void arx_list_push(int64_t list_handle, int64_t val) {
    Arx_List* list = (Arx_List*)(intptr_t)list_handle;
    if (!list) return;
    if (list->len >= list->cap) {
        size_t new_cap = list->cap + (list->cap >> 1); // 1.5x golden ratio growth
        if (new_cap < 4) new_cap = 4;
        list->data = (int64_t*)realloc(list->data, new_cap * sizeof(int64_t));
        if (!list->data) arx_panic("Out of memory growing List", __FILE__, __LINE__);
        list->cap = new_cap;
    }
    list->data[list->len++] = val;
}

static inline int64_t arx_list_pop(int64_t list_handle) {
    Arx_List* list = (Arx_List*)(intptr_t)list_handle;
    if (!list || list->len == 0) {
        arx_panic("IndexError: pop from empty List", __FILE__, __LINE__);
    }
    return list->data[--list->len];
}

static inline int64_t arx_list_get(int64_t list_handle, int64_t idx) {
    Arx_List* list = (Arx_List*)(intptr_t)list_handle;
    if (!list) arx_panic("NullPointerError: access on null List", __FILE__, __LINE__);
    if (idx < 0 || (size_t)idx >= list->len) {
        arx_panic("IndexOutOfBounds: index out of bounds on List", __FILE__, __LINE__);
    }
    return list->data[idx];
}

static inline void arx_list_set(int64_t list_handle, int64_t idx, int64_t val) {
    Arx_List* list = (Arx_List*)(intptr_t)list_handle;
    if (!list) arx_panic("NullPointerError: access on null List", __FILE__, __LINE__);
    if (idx < 0 || (size_t)idx >= list->len) {
        arx_panic("IndexOutOfBounds: index out of bounds on List", __FILE__, __LINE__);
    }
    list->data[idx] = val;
}

static inline int64_t arx_list_len(int64_t list_handle) {
    Arx_List* list = (Arx_List*)(intptr_t)list_handle;
    return list ? (int64_t)list->len : 0;
}

static inline void arx_list_clear(int64_t list_handle) {
    Arx_List* list = (Arx_List*)(intptr_t)list_handle;
    if (list) list->len = 0;
}

static inline void arx_list_free(int64_t list_handle) {
    Arx_List* list = (Arx_List*)(intptr_t)list_handle;
    if (!list) return;
    if (list->data) arx_free(list->data);
    arx_free(list);
}

static inline int64_t arx_list_slice(int64_t list_handle, int64_t start, int64_t end) {
    Arx_List* list = (Arx_List*)(intptr_t)list_handle;
    if (!list) return arx_list_new(4);
    if (start < 0) start = 0;
    if ((size_t)end > list->len) end = (int64_t)list->len;
    if (start > end) start = end;
    size_t count = (size_t)(end - start);
    int64_t new_handle = arx_list_new(count > 4 ? count : 4);
    Arx_List* new_list = (Arx_List*)(intptr_t)new_handle;
    for (size_t i = 0; i < count; i++) {
        new_list->data[i] = list->data[start + i];
    }
    new_list->len = count;
    return new_handle;
}

// Typed List Helpers
static inline void arx_list_push_i64(int64_t h, int64_t v) { arx_list_push(h, v); }
static inline void arx_list_push_str(int64_t h, const char* s) { arx_list_push(h, (int64_t)(intptr_t)s); }
static inline void arx_list_push_f64(int64_t h, double v) { union { double f; int64_t i; } u; u.f = v; arx_list_push(h, u.i); }

static inline int64_t arx_list_get_i64(int64_t h, int64_t idx) { return arx_list_get(h, idx); }
static inline const char* arx_list_get_str(int64_t h, int64_t idx) { return (const char*)(intptr_t)arx_list_get(h, idx); }
static inline double arx_list_get_f64(int64_t h, int64_t idx) { union { double f; int64_t i; } u; u.i = arx_list_get(h, idx); return u.f; }

static inline void arx_list_set_i64(int64_t h, int64_t idx, int64_t v) { arx_list_set(h, idx, v); }
static inline void arx_list_set_str(int64_t h, int64_t idx, const char* s) { arx_list_set(h, idx, (int64_t)(intptr_t)s); }
static inline void arx_list_set_f64(int64_t h, int64_t idx, double v) { union { double f; int64_t i; } u; u.f = v; arx_list_set(h, idx, u.i); }

static inline int64_t arx_list_pop_i64(int64_t h) { return arx_list_pop(h); }
static inline const char* arx_list_pop_str(int64_t h) { return (const char*)(intptr_t)arx_list_pop(h); }
static inline double arx_list_pop_f64(int64_t h) { union { double f; int64_t i; } u; u.i = arx_list_pop(h); return u.f; }

static inline bool arx_list_contains(int64_t h, int64_t val) {
    Arx_List* list = (Arx_List*)(intptr_t)h;
    if (!list) return false;
    for (size_t i = 0; i < list->len; i++) {
        if (list->data[i] == val) return true;
    }
    return false;
}

static inline int64_t arx_list_index_of(int64_t h, int64_t val) {
    Arx_List* list = (Arx_List*)(intptr_t)h;
    if (!list) return -1;
    for (size_t i = 0; i < list->len; i++) {
        if (list->data[i] == val) return (int64_t)i;
    }
    return -1;
}

static inline void arx_list_reverse(int64_t h) {
    Arx_List* list = (Arx_List*)(intptr_t)h;
    if (!list || list->len < 2) return;
    size_t i = 0, j = list->len - 1;
    while (i < j) {
        int64_t tmp = list->data[i];
        list->data[i] = list->data[j];
        list->data[j] = tmp;
        i++; j--;
    }
}

static int _arx_cmp_i64(const void* a, const void* b) {
    int64_t ia = *(const int64_t*)a;
    int64_t ib = *(const int64_t*)b;
    if (ia < ib) return -1;
    if (ia > ib) return 1;
    return 0;
}

static inline void arx_list_sort(int64_t h) {
    Arx_List* list = (Arx_List*)(intptr_t)h;
    if (!list || list->len < 2) return;
    qsort(list->data, list->len, sizeof(int64_t), _arx_cmp_i64);
}

static inline int64_t arx_list_swap_remove(int64_t h, int64_t idx) {
    Arx_List* list = (Arx_List*)(intptr_t)h;
    if (!list || list->len == 0) arx_panic("IndexError: swap_remove on empty List", __FILE__, __LINE__);
    if (idx < 0 || (size_t)idx >= list->len) arx_panic("IndexOutOfBounds: swap_remove index out of bounds", __FILE__, __LINE__);
    int64_t removed = list->data[idx];
    list->data[idx] = list->data[list->len - 1];
    list->len--;
    return removed;
}

static inline int64_t arx_list_remove_at(int64_t h, int64_t idx) {
    Arx_List* list = (Arx_List*)(intptr_t)h;
    if (!list || list->len == 0) arx_panic("IndexError: remove_at on empty List", __FILE__, __LINE__);
    if (idx < 0 || (size_t)idx >= list->len) arx_panic("IndexOutOfBounds: remove_at index out of bounds", __FILE__, __LINE__);
    int64_t removed = list->data[idx];
    for (size_t i = (size_t)idx; i + 1 < list->len; i++) {
        list->data[i] = list->data[i + 1];
    }
    list->len--;
    return removed;
}

static inline void arx_list_insert(int64_t h, int64_t idx, int64_t val) {
    Arx_List* list = (Arx_List*)(intptr_t)h;
    if (!list) return;
    if (idx < 0 || (size_t)idx > list->len) arx_panic("IndexOutOfBounds: insert index out of bounds", __FILE__, __LINE__);
    if (list->len >= list->cap) {
        size_t new_cap = list->cap + (list->cap >> 1);
        if (new_cap < 4) new_cap = 4;
        list->data = (int64_t*)realloc(list->data, new_cap * sizeof(int64_t));
        list->cap = new_cap;
    }
    for (size_t i = list->len; i > (size_t)idx; i--) {
        list->data[i] = list->data[i - 1];
    }
    list->data[idx] = val;
    list->len++;
}

static inline const char* arx_list_swap_remove_str(int64_t h, int64_t idx) { return (const char*)(intptr_t)arx_list_swap_remove(h, idx); }
static inline double arx_list_swap_remove_f64(int64_t h, int64_t idx) { union { double f; int64_t i; } u; u.i = arx_list_swap_remove(h, idx); return u.f; }
static inline int64_t arx_list_swap_remove_i64(int64_t h, int64_t idx) { return arx_list_swap_remove(h, idx); }

static inline const char* arx_list_remove_at_str(int64_t h, int64_t idx) { return (const char*)(intptr_t)arx_list_remove_at(h, idx); }
static inline double arx_list_remove_at_f64(int64_t h, int64_t idx) { union { double f; int64_t i; } u; u.i = arx_list_remove_at(h, idx); return u.f; }
static inline int64_t arx_list_remove_at_i64(int64_t h, int64_t idx) { return arx_list_remove_at(h, idx); }

static inline void arx_list_insert_str(int64_t h, int64_t idx, const char* s) { arx_list_insert(h, idx, (int64_t)(intptr_t)s); }
static inline void arx_list_insert_f64(int64_t h, int64_t idx, double v) { union { double f; int64_t i; } u; u.f = v; arx_list_insert(h, idx, u.i); }
static inline void arx_list_insert_i64(int64_t h, int64_t idx, int64_t v) { arx_list_insert(h, idx, v); }

static inline bool arx_list_contains_str(int64_t h, const char* query) {
    Arx_List* list = (Arx_List*)(intptr_t)h;
    if (!list || !query) return false;
    for (size_t i = 0; i < list->len; i++) {
        const char* s = (const char*)(intptr_t)list->data[i];
        if (s && strcmp(s, query) == 0) return true;
    }
    return false;
}

static inline int64_t arx_list_index_of_str(int64_t h, const char* query) {
    Arx_List* list = (Arx_List*)(intptr_t)h;
    if (!list || !query) return -1;
    for (size_t i = 0; i < list->len; i++) {
        const char* s = (const char*)(intptr_t)list->data[i];
        if (s && strcmp(s, query) == 0) return (int64_t)i;
    }
    return -1;
}


// ==========================================
// Phase 21: Dual-Tier Text Engine (str & String)
// ==========================================

static inline int64_t arx_str_len(const char* s) {
    return s ? (int64_t)strlen(s) : 0;
}

static inline const char* arx_str_copy(const char* s) {
    if (!s) return "";
    size_t len = strlen(s);
    char* copy = (char*)arx_alloc(len + 1);
    memcpy(copy, s, len + 1);
    return copy;
}

static inline const char* arx_str_trim(const char* s) {
    if (!s) return "";
    while (*s && isspace((unsigned char)*s)) s++;
    if (*s == '\0') return "";
    const char* end = s + strlen(s) - 1;
    while (end > s && isspace((unsigned char)*end)) end--;
    size_t len = (size_t)(end - s + 1);
    char* trimmed = (char*)arx_alloc(len + 1);
    memcpy(trimmed, s, len);
    trimmed[len] = '\0';
    return trimmed;
}

static inline const char* arx_str_to_upper(const char* s) {
    if (!s) return "";
    size_t len = strlen(s);
    char* res = (char*)arx_alloc(len + 1);
    for (size_t i = 0; i < len; i++) {
        res[i] = (char)toupper((unsigned char)s[i]);
    }
    res[len] = '\0';
    return res;
}

static inline const char* arx_str_to_lower(const char* s) {
    if (!s) return "";
    size_t len = strlen(s);
    char* res = (char*)arx_alloc(len + 1);
    for (size_t i = 0; i < len; i++) {
        res[i] = (char)tolower((unsigned char)s[i]);
    }
    res[len] = '\0';
    return res;
}

static inline bool arx_str_contains(const char* s, const char* query) {
    if (!s || !query) return false;
    return strstr(s, query) != NULL;
}

static inline bool arx_str_starts_with(const char* s, const char* prefix) {
    if (!s || !prefix) return false;
    size_t len_s = strlen(s);
    size_t len_p = strlen(prefix);
    if (len_p > len_s) return false;
    return strncmp(s, prefix, len_p) == 0;
}

static inline bool arx_str_ends_with(const char* s, const char* suffix) {
    if (!s || !suffix) return false;
    size_t len_s = strlen(s);
    size_t len_suf = strlen(suffix);
    if (len_suf > len_s) return false;
    return strcmp(s + (len_s - len_suf), suffix) == 0;
}

static inline const char* arx_str_replace(const char* s, const char* old_sub, const char* new_sub) {
    if (!s) return "";
    if (!old_sub || old_sub[0] == '\0') return s;
    if (!new_sub) new_sub = "";
    size_t old_len = strlen(old_sub);
    size_t new_len = strlen(new_sub);

    size_t count = 0;
    const char* tmp = s;
    while ((tmp = strstr(tmp, old_sub)) != NULL) {
        count++;
        tmp += old_len;
    }
    if (count == 0) return s;

    size_t result_len = strlen(s) + count * (new_len > old_len ? new_len - old_len : 0);
    char* result = (char*)arx_alloc(result_len + 1);
    char* dst = result;
    const char* src = s;
    while ((tmp = strstr(src, old_sub)) != NULL) {
        size_t chunk_len = (size_t)(tmp - src);
        memcpy(dst, src, chunk_len);
        dst += chunk_len;
        memcpy(dst, new_sub, new_len);
        dst += new_len;
        src = tmp + old_len;
    }
    strcpy(dst, src);
    return result;
}

static inline const char* arx_str_slice(const char* s, int64_t start, int64_t end) {
    if (!s) return "";
    int64_t len = (int64_t)strlen(s);
    if (start < 0) start = 0;
    if (end > len) end = len;
    if (start >= end) return "";
    size_t slice_len = (size_t)(end - start);
    char* res = (char*)arx_alloc(slice_len + 1);
    memcpy(res, s + start, slice_len);
    res[slice_len] = '\0';
    return res;
}

static inline int64_t arx_str_split(const char* s, const char* delim) {
    int64_t list_handle = arx_list_new(4);
    if (!s) return list_handle;
    if (!delim || delim[0] == '\0') delim = " ";
    size_t dlen = strlen(delim);

    const char* cur = s;
    const char* next = NULL;
    while ((next = strstr(cur, delim)) != NULL) {
        size_t part_len = (size_t)(next - cur);
        char* part = (char*)arx_alloc(part_len + 1);
        memcpy(part, cur, part_len);
        part[part_len] = '\0';
        arx_list_push(list_handle, (int64_t)(intptr_t)part);
        cur = next + dlen;
    }
    size_t last_len = strlen(cur);
    char* last_part = (char*)arx_alloc(last_len + 1);
    memcpy(last_part, cur, last_len + 1);
    arx_list_push(list_handle, (int64_t)(intptr_t)last_part);

    return list_handle;
}

static inline const char* arx_str_join(int64_t list_handle, const char* delim) {
    Arx_List* list = (Arx_List*)(intptr_t)list_handle;
    if (!list || list->len == 0) return "";
    if (!delim) delim = "";
    size_t dlen = strlen(delim);

    size_t total_len = 0;
    for (size_t i = 0; i < list->len; i++) {
        const char* piece = (const char*)(intptr_t)list->data[i];
        if (piece) total_len += strlen(piece);
        if (i + 1 < list->len) total_len += dlen;
    }

    char* res = (char*)arx_alloc(total_len + 1);
    res[0] = '\0';
    char* dst = res;
    for (size_t i = 0; i < list->len; i++) {
        const char* piece = (const char*)(intptr_t)list->data[i];
        if (piece) {
            size_t plen = strlen(piece);
            memcpy(dst, piece, plen);
            dst += plen;
        }
        if (i + 1 < list->len) {
            memcpy(dst, delim, dlen);
            dst += dlen;
        }
    }
    *dst = '\0';
    return res;
}

static inline const char* arx_str_repeat(const char* s, int64_t count) {
    if (!s || count <= 0) return "";
    size_t slen = strlen(s);
    size_t total = slen * (size_t)count;
    char* buf = (char*)arx_alloc(total + 1);
    char* p = buf;
    for (int64_t i = 0; i < count; i++) {
        memcpy(p, s, slen);
        p += slen;
    }
    *p = '\0';
    return buf;
}

static inline const char* arx_str_concat(const char* a, const char* b) {
    if (!a) a = "";
    if (!b) b = "";
    size_t la = strlen(a);
    size_t lb = strlen(b);
    char* buf = (char*)arx_alloc(la + lb + 1);
    memcpy(buf, a, la);
    memcpy(buf + la, b, lb);
    buf[la + lb] = '\0';
    return buf;
}

static inline const char* arx_str_char_at(const char* s, int64_t idx) {
    if (!s) return "";
    int64_t len = (int64_t)strlen(s);
    if (idx < 0 || idx >= len) return "";
    char* buf = (char*)arx_alloc(2);
    buf[0] = s[idx];
    buf[1] = '\0';
    return buf;
}



// ==========================================
// Phase 22: Map<K, V> — Robin Hood Hash Table
// ==========================================

#define ARX_MAP_EMPTY_SLOT    0
#define ARX_MAP_DELETED_SLOT  1
#define ARX_MAP_FULL_SLOT     2

typedef struct {
    uint8_t   state;    // ARX_MAP_EMPTY/DELETED/FULL
    uint8_t   psl;      // Probe Sequence Length (Robin Hood distance)
    int64_t   key;      // Key stored as i64 (str cast via intptr_t)
    int64_t   value;    // Value stored as i64
} Arx_MapSlot;

typedef struct {
    Arx_MapSlot* slots;
    size_t capacity;   // Always power of 2
    size_t len;
    uint8_t key_is_str; // 1 if key type is str
} Arx_Map;

static inline uint64_t arx_fnv1a(const void* data, size_t len) {
    uint64_t hash = 14695981039346656037ULL;
    const uint8_t* ptr = (const uint8_t*)data;
    for (size_t i = 0; i < len; i++) {
        hash ^= ptr[i];
        hash *= 1099511628211ULL;
    }
    return hash;
}

static inline uint64_t arx_map_hash_i64(int64_t key) {
    uint64_t k = (uint64_t)key;
    k ^= k >> 33;
    k *= 0xff51afd7ed558ccdULL;
    k ^= k >> 33;
    k *= 0xc4ceb9fe1a85ec53ULL;
    k ^= k >> 33;
    return k;
}

static inline uint64_t arx_map_hash_str(const char* s) {
    if (!s) return 0;
    return arx_fnv1a(s, strlen(s));
}

static inline int64_t arx_map_new(int64_t key_is_str) {
    Arx_Map* m = (Arx_Map*)arx_alloc(sizeof(Arx_Map));
    m->capacity = 16;
    m->len = 0;
    m->key_is_str = (uint8_t)key_is_str;
    m->slots = (Arx_MapSlot*)arx_alloc(16 * sizeof(Arx_MapSlot));
    memset(m->slots, 0, 16 * sizeof(Arx_MapSlot));
    return (int64_t)(intptr_t)m;
}

static inline uint64_t arx_map_compute_hash(Arx_Map* m, int64_t key) {
    return m->key_is_str
        ? arx_map_hash_str((const char*)(intptr_t)key)
        : arx_map_hash_i64(key);
}

static inline int arx_map_keys_equal(Arx_Map* m, int64_t a, int64_t b) {
    if (m->key_is_str) {
        const char* sa = (const char*)(intptr_t)a;
        const char* sb = (const char*)(intptr_t)b;
        if (!sa || !sb) return sa == sb;
        return strcmp(sa, sb) == 0;
    }
    return a == b;
}

// Forward declaration for rehash
static void arx_map_insert_raw(Arx_Map* m, int64_t key, int64_t val);

static void arx_map_grow(Arx_Map* m) {
    size_t old_cap = m->capacity;
    Arx_MapSlot* old_slots = m->slots;
    m->capacity = old_cap * 2;
    m->len = 0;
    m->slots = (Arx_MapSlot*)arx_alloc(m->capacity * sizeof(Arx_MapSlot));
    memset(m->slots, 0, m->capacity * sizeof(Arx_MapSlot));
    for (size_t i = 0; i < old_cap; i++) {
        if (old_slots[i].state == ARX_MAP_FULL_SLOT) {
            arx_map_insert_raw(m, old_slots[i].key, old_slots[i].value);
        }
    }
    arx_free(old_slots);
}

static void arx_map_insert_raw(Arx_Map* m, int64_t key, int64_t val) {
    uint64_t hash = arx_map_compute_hash(m, key);
    size_t idx = (size_t)(hash & (m->capacity - 1));
    uint8_t psl = 0;
    int64_t cur_key = key;
    int64_t cur_val = val;

    for (;;) {
        Arx_MapSlot* slot = &m->slots[idx];
        if (slot->state != ARX_MAP_FULL_SLOT) {
            slot->state = ARX_MAP_FULL_SLOT;
            slot->psl = psl;
            slot->key = cur_key;
            slot->value = cur_val;
            m->len++;
            return;
        }
        // Robin Hood: steal from rich
        if (slot->psl < psl) {
            uint8_t tmp_psl = slot->psl;
            int64_t tmp_key = slot->key;
            int64_t tmp_val = slot->value;
            slot->psl = psl;
            slot->key = cur_key;
            slot->value = cur_val;
            psl = tmp_psl;
            cur_key = tmp_key;
            cur_val = tmp_val;
        }
        psl++;
        idx = (idx + 1) & (m->capacity - 1);
    }
}

static inline void arx_map_insert(int64_t map_handle, int64_t key, int64_t val) {
    Arx_Map* m = (Arx_Map*)(intptr_t)map_handle;
    if (!m) return;
    // Check if key already exists and update
    uint64_t hash = arx_map_compute_hash(m, key);
    size_t idx = (size_t)(hash & (m->capacity - 1));
    uint8_t psl = 0;
    while (m->slots[idx].state == ARX_MAP_FULL_SLOT) {
        if (m->slots[idx].psl < psl) break;
        if (arx_map_keys_equal(m, m->slots[idx].key, key)) {
            m->slots[idx].value = val;
            return;
        }
        psl++;
        idx = (idx + 1) & (m->capacity - 1);
    }
    // Load factor 75%: grow before inserting
    if ((m->len + 1) * 4 > m->capacity * 3) {
        arx_map_grow(m);
    }
    if (m->key_is_str) {
        key = (int64_t)(intptr_t)arx_str_copy((const char*)(intptr_t)key);
    }
    arx_map_insert_raw(m, key, val);
}

static inline int64_t arx_map_get(int64_t map_handle, int64_t key) {
    Arx_Map* m = (Arx_Map*)(intptr_t)map_handle;
    if (!m) return 0;
    uint64_t hash = arx_map_compute_hash(m, key);
    size_t idx = (size_t)(hash & (m->capacity - 1));
    uint8_t psl = 0;
    while (m->slots[idx].state == ARX_MAP_FULL_SLOT) {
        if (m->slots[idx].psl < psl) break;
        if (arx_map_keys_equal(m, m->slots[idx].key, key)) {
            return m->slots[idx].value;
        }
        psl++;
        idx = (idx + 1) & (m->capacity - 1);
    }
    return 0; // Key not found
}

static inline bool arx_map_has(int64_t map_handle, int64_t key) {
    Arx_Map* m = (Arx_Map*)(intptr_t)map_handle;
    if (!m) return false;
    uint64_t hash = arx_map_compute_hash(m, key);
    size_t idx = (size_t)(hash & (m->capacity - 1));
    uint8_t psl = 0;
    while (m->slots[idx].state == ARX_MAP_FULL_SLOT) {
        if (m->slots[idx].psl < psl) break;
        if (arx_map_keys_equal(m, m->slots[idx].key, key)) {
            return true;
        }
        psl++;
        idx = (idx + 1) & (m->capacity - 1);
    }
    return false;
}

static inline void arx_map_remove(int64_t map_handle, int64_t key) {
    Arx_Map* m = (Arx_Map*)(intptr_t)map_handle;
    if (!m) return;
    uint64_t hash = arx_map_compute_hash(m, key);
    size_t idx = (size_t)(hash & (m->capacity - 1));
    uint8_t psl = 0;
    size_t found = (size_t)-1;
    while (m->slots[idx].state == ARX_MAP_FULL_SLOT) {
        if (m->slots[idx].psl < psl) break;
        if (arx_map_keys_equal(m, m->slots[idx].key, key)) {
            found = idx;
            break;
        }
        psl++;
        idx = (idx + 1) & (m->capacity - 1);
    }
    if (found == (size_t)-1) return;
    // Backward shift deletion
    size_t cur = found;
    for (;;) {
        size_t next = (cur + 1) & (m->capacity - 1);
        if (m->slots[next].state != ARX_MAP_FULL_SLOT || m->slots[next].psl == 0) {
            m->slots[cur].state = ARX_MAP_EMPTY_SLOT;
            m->slots[cur].psl = 0;
            break;
        }
        m->slots[cur] = m->slots[next];
        m->slots[cur].psl--;
        cur = next;
    }
    m->len--;
}

static inline int64_t arx_map_len(int64_t map_handle) {
    Arx_Map* m = (Arx_Map*)(intptr_t)map_handle;
    return m ? (int64_t)m->len : 0;
}

static inline void arx_map_clear(int64_t map_handle) {
    Arx_Map* m = (Arx_Map*)(intptr_t)map_handle;
    if (!m) return;
    memset(m->slots, 0, m->capacity * sizeof(Arx_MapSlot));
    m->len = 0;
}

static inline void arx_map_free(int64_t map_handle) {
    Arx_Map* m = (Arx_Map*)(intptr_t)map_handle;
    if (!m) return;
    if (m->slots) arx_free(m->slots);
    arx_free(m);
}

// Returns a List handle containing all keys
static inline int64_t arx_map_keys(int64_t map_handle) {
    Arx_Map* m = (Arx_Map*)(intptr_t)map_handle;
    int64_t list_h = arx_list_new(m ? (int64_t)m->len : 4);
    if (!m) return list_h;
    for (size_t i = 0; i < m->capacity; i++) {
        if (m->slots[i].state == ARX_MAP_FULL_SLOT) {
            arx_list_push(list_h, m->slots[i].key);
        }
    }
    return list_h;
}

// Returns a List handle containing all values
static inline int64_t arx_map_values(int64_t map_handle) {
    Arx_Map* m = (Arx_Map*)(intptr_t)map_handle;
    int64_t list_h = arx_list_new(m ? (int64_t)m->len : 4);
    if (!m) return list_h;
    for (size_t i = 0; i < m->capacity; i++) {
        if (m->slots[i].state == ARX_MAP_FULL_SLOT) {
            arx_list_push(list_h, m->slots[i].value);
        }
    }
    return list_h;
}

// ==========================================
// Phase 22: Set<T> — Zero-Value Hash Set
// ==========================================

// Reuses Arx_Map with value always 1
static inline int64_t arx_set_new(int64_t key_is_str) {
    return arx_map_new(key_is_str);
}

static inline bool arx_set_add(int64_t set_handle, int64_t item) {
    bool already = arx_map_has(set_handle, item);
    arx_map_insert(set_handle, item, 1);
    return !already;
}

static inline bool arx_set_has(int64_t set_handle, int64_t item) {
    return arx_map_has(set_handle, item);
}

static inline bool arx_set_remove(int64_t set_handle, int64_t item) {
    bool had = arx_map_has(set_handle, item);
    arx_map_remove(set_handle, item);
    return had;
}

static inline int64_t arx_set_len(int64_t set_handle) {
    return arx_map_len(set_handle);
}

static inline void arx_set_clear(int64_t set_handle) {
    arx_map_clear(set_handle);
}

static inline void arx_set_free(int64_t set_handle) {
    arx_map_free(set_handle);
}

static inline int64_t arx_set_to_list(int64_t set_handle) {
    return arx_map_keys(set_handle);
}

static inline int64_t arx_set_get(int64_t set_handle, int64_t idx) {
    Arx_Map* m = (Arx_Map*)(intptr_t)set_handle;
    if (!m) return 0;
    size_t count = 0;
    for (size_t i = 0; i < m->capacity; i++) {
        if (m->slots[i].state == ARX_MAP_FULL_SLOT) {
            if ((int64_t)count == idx) return m->slots[i].key;
            count++;
        }
    }
    return 0;
}

static inline const char* arx_set_get_str(int64_t set_handle, int64_t idx) {
    return (const char*)(intptr_t)arx_set_get(set_handle, idx);
}

// Set algebra helpers
static inline int64_t arx_set_union(int64_t a, int64_t b) {
    Arx_Map* ma = (Arx_Map*)(intptr_t)a;
    int64_t result = arx_set_new(ma ? ma->key_is_str : 0);
    Arx_Map* mr = (Arx_Map*)(intptr_t)result;
    Arx_Map* mb = (Arx_Map*)(intptr_t)b;
    if (ma) for (size_t i = 0; i < ma->capacity; i++)
        if (ma->slots[i].state == ARX_MAP_FULL_SLOT)
            arx_map_insert_raw(mr, ma->slots[i].key, 1);
    if (mb) for (size_t i = 0; i < mb->capacity; i++)
        if (mb->slots[i].state == ARX_MAP_FULL_SLOT)
            if (!arx_map_has(result, mb->slots[i].key))
                arx_map_insert_raw(mr, mb->slots[i].key, 1);
    return result;
}

static inline int64_t arx_set_intersection(int64_t a, int64_t b) {
    Arx_Map* ma = (Arx_Map*)(intptr_t)a;
    int64_t result = arx_set_new(ma ? ma->key_is_str : 0);
    Arx_Map* mr = (Arx_Map*)(intptr_t)result;
    if (!ma) return result;
    for (size_t i = 0; i < ma->capacity; i++) {
        if (ma->slots[i].state == ARX_MAP_FULL_SLOT) {
            if (arx_map_has(b, ma->slots[i].key))
                arx_map_insert_raw(mr, ma->slots[i].key, 1);
        }
    }
    return result;
}

static inline int64_t arx_set_difference(int64_t a, int64_t b) {
    Arx_Map* ma = (Arx_Map*)(intptr_t)a;
    int64_t result = arx_set_new(ma ? ma->key_is_str : 0);
    Arx_Map* mr = (Arx_Map*)(intptr_t)result;
    if (!ma) return result;
    for (size_t i = 0; i < ma->capacity; i++) {
        if (ma->slots[i].state == ARX_MAP_FULL_SLOT) {
            if (!arx_map_has(b, ma->slots[i].key))
                arx_map_insert_raw(mr, ma->slots[i].key, 1);
        }
    }
    return result;
}

// Typed Map and Set Helpers
static inline void arx_map_insert_i64_i64(int64_t h, int64_t k, int64_t v) { arx_map_insert(h, k, v); }
static inline void arx_map_insert_str_i64(int64_t h, const char* k, int64_t v) { arx_map_insert(h, (int64_t)(intptr_t)k, v); }
static inline void arx_map_insert_str_str(int64_t h, const char* k, const char* v) { arx_map_insert(h, (int64_t)(intptr_t)k, (int64_t)(intptr_t)v); }
static inline void arx_map_insert_i64_str(int64_t h, int64_t k, const char* v) { arx_map_insert(h, k, (int64_t)(intptr_t)v); }

static inline int64_t arx_map_get_i64(int64_t h, int64_t k) { return arx_map_get(h, k); }
static inline int64_t arx_map_get_str_i64(int64_t h, const char* k) { return arx_map_get(h, (int64_t)(intptr_t)k); }
static inline const char* arx_map_get_str_str(int64_t h, const char* k) { return (const char*)(intptr_t)arx_map_get(h, (int64_t)(intptr_t)k); }
static inline const char* arx_map_get_i64_str(int64_t h, int64_t k) { return (const char*)(intptr_t)arx_map_get(h, k); }

static inline bool arx_map_has_i64(int64_t h, int64_t k) { return arx_map_has(h, k); }
static inline bool arx_map_has_str(int64_t h, const char* k) { return arx_map_has(h, (int64_t)(intptr_t)k); }

static inline void arx_map_remove_i64(int64_t h, int64_t k) { arx_map_remove(h, k); }
static inline void arx_map_remove_str(int64_t h, const char* k) { arx_map_remove(h, (int64_t)(intptr_t)k); }

static inline bool arx_set_add_i64(int64_t h, int64_t v) { return arx_set_add(h, v); }
static inline bool arx_set_add_str(int64_t h, const char* v) { return arx_set_add(h, (int64_t)(intptr_t)v); }
static inline bool arx_set_has_i64(int64_t h, int64_t v) { return arx_set_has(h, v); }
static inline bool arx_set_has_str(int64_t h, const char* v) { return arx_set_has(h, (int64_t)(intptr_t)v); }
static inline bool arx_set_remove_i64(int64_t h, int64_t v) { return arx_set_remove(h, v); }
static inline bool arx_set_remove_str(int64_t h, const char* v) { return arx_set_remove(h, (int64_t)(intptr_t)v); }



// ==========================================
// Phase 22: Stack<T> — LIFO Contiguous Buffer
// ==========================================

// Stack reuses Arx_List entirely — push/pop from back
static inline int64_t arx_stack_new(void) {
    return arx_list_new(8);
}

static inline void arx_stack_push(int64_t h, int64_t val) {
    arx_list_push(h, val);
}

static inline int64_t arx_stack_pop(int64_t h) {
    return arx_list_pop(h);
}

static inline int64_t arx_stack_peek(int64_t h) {
    Arx_List* s = (Arx_List*)(intptr_t)h;
    if (!s || s->len == 0) arx_panic("PeekError: Stack is empty", __FILE__, __LINE__);
    return s->data[s->len - 1];
}

static inline int64_t arx_stack_len(int64_t h) {
    return arx_list_len(h);
}

static inline bool arx_stack_is_empty(int64_t h) {
    return arx_list_len(h) == 0;
}

static inline void arx_stack_clear(int64_t h) {
    arx_list_clear(h);
}

static inline void arx_stack_free(int64_t h) {
    arx_list_free(h);
}

// ==========================================
// Phase 22: Queue<T> — FIFO Ring Buffer
// ==========================================

typedef struct {
    int64_t* data;
    size_t   head; // Read position
    size_t   tail; // Write position
    size_t   len;
    size_t   cap;  // Always power of 2
} Arx_Queue;

static inline int64_t arx_queue_new(void) {
    Arx_Queue* q = (Arx_Queue*)arx_alloc(sizeof(Arx_Queue));
    q->cap  = 8;
    q->len  = 0;
    q->head = 0;
    q->tail = 0;
    q->data = (int64_t*)arx_alloc(8 * sizeof(int64_t));
    return (int64_t)(intptr_t)q;
}

static inline void arx_queue_enqueue(int64_t qh, int64_t val) {
    Arx_Queue* q = (Arx_Queue*)(intptr_t)qh;
    if (!q) return;
    if (q->len == q->cap) {
        // Grow: double capacity
        size_t new_cap = q->cap * 2;
        int64_t* new_data = (int64_t*)arx_alloc(new_cap * sizeof(int64_t));
        for (size_t i = 0; i < q->len; i++) {
            new_data[i] = q->data[(q->head + i) & (q->cap - 1)];
        }
        arx_free(q->data);
        q->data = new_data;
        q->head = 0;
        q->tail = q->len;
        q->cap  = new_cap;
    }
    q->data[q->tail & (q->cap - 1)] = val;
    q->tail = (q->tail + 1) & (q->cap - 1);
    q->len++;
}

static inline int64_t arx_queue_dequeue(int64_t qh) {
    Arx_Queue* q = (Arx_Queue*)(intptr_t)qh;
    if (!q || q->len == 0) arx_panic("DequeueError: Queue is empty", __FILE__, __LINE__);
    int64_t val = q->data[q->head & (q->cap - 1)];
    q->head = (q->head + 1) & (q->cap - 1);
    q->len--;
    return val;
}

static inline int64_t arx_queue_peek_front(int64_t qh) {
    Arx_Queue* q = (Arx_Queue*)(intptr_t)qh;
    if (!q || q->len == 0) arx_panic("PeekError: Queue is empty", __FILE__, __LINE__);
    return q->data[q->head & (q->cap - 1)];
}

static inline int64_t arx_queue_len(int64_t qh) {
    Arx_Queue* q = (Arx_Queue*)(intptr_t)qh;
    return q ? (int64_t)q->len : 0;
}

static inline bool arx_queue_is_empty(int64_t qh) {
    Arx_Queue* q = (Arx_Queue*)(intptr_t)qh;
    return !q || q->len == 0;
}

static inline void arx_queue_clear(int64_t qh) {
    Arx_Queue* q = (Arx_Queue*)(intptr_t)qh;
    if (q) { q->len = 0; q->head = 0; q->tail = 0; }
}

static inline void arx_queue_free(int64_t qh) {
    Arx_Queue* q = (Arx_Queue*)(intptr_t)qh;
    if (!q) return;
    if (q->data) arx_free(q->data);
    arx_free(q);
}

// ==========================================
// Phase 22: Deque<T> — Double-Ended Ring Buffer
// ==========================================

// Deque reuses the same Arx_Queue struct; we expose both front+back operations
static inline int64_t arx_deque_new(void) {
    return arx_queue_new();
}

static inline void arx_deque_push_back(int64_t dh, int64_t val) {
    arx_queue_enqueue(dh, val);
}

static inline void arx_deque_push_front(int64_t dh, int64_t val) {
    Arx_Queue* q = (Arx_Queue*)(intptr_t)dh;
    if (!q) return;
    if (q->len == q->cap) {
        size_t new_cap = q->cap * 2;
        int64_t* new_data = (int64_t*)arx_alloc(new_cap * sizeof(int64_t));
        for (size_t i = 0; i < q->len; i++) {
            new_data[i + 1] = q->data[(q->head + i) & (q->cap - 1)];
        }
        arx_free(q->data);
        q->data = new_data;
        q->head = 0;
        q->tail = q->len;
        q->cap  = new_cap;
    }
    q->head = (q->head - 1 + q->cap) & (q->cap - 1);
    q->data[q->head] = val;
    q->len++;
}

static inline int64_t arx_deque_pop_back(int64_t dh) {
    Arx_Queue* q = (Arx_Queue*)(intptr_t)dh;
    if (!q || q->len == 0) arx_panic("PopError: Deque is empty", __FILE__, __LINE__);
    q->tail = (q->tail - 1 + q->cap) & (q->cap - 1);
    int64_t val = q->data[q->tail];
    q->len--;
    return val;
}

static inline int64_t arx_deque_pop_front(int64_t dh) {
    return arx_queue_dequeue(dh);
}

static inline int64_t arx_deque_peek_front(int64_t dh) {
    return arx_queue_peek_front(dh);
}

static inline int64_t arx_deque_peek_back(int64_t dh) {
    Arx_Queue* q = (Arx_Queue*)(intptr_t)dh;
    if (!q || q->len == 0) arx_panic("PeekError: Deque is empty", __FILE__, __LINE__);
    return q->data[(q->tail - 1 + q->cap) & (q->cap - 1)];
}

static inline int64_t arx_deque_len(int64_t dh) {
    return arx_queue_len(dh);
}

static inline bool arx_deque_is_empty(int64_t dh) {
    return arx_queue_is_empty(dh);
}

static inline void arx_deque_clear(int64_t dh) {
    arx_queue_clear(dh);
}

static inline void arx_deque_free(int64_t dh) {
    arx_queue_free(dh);
}

// ==========================================
// Phase 22: ByteBuffer — Aligned Binary Stream
// ==========================================

typedef struct {
    uint8_t* data;
    size_t   len;
    size_t   cap;
    size_t   pos; // Current read/write cursor
} Arx_ByteBuf;

static inline int64_t arx_bytebuf_new(int64_t capacity) {
    if (capacity < 64) capacity = 64;
    Arx_ByteBuf* buf = (Arx_ByteBuf*)arx_alloc(sizeof(Arx_ByteBuf));
    buf->data = (uint8_t*)arx_alloc((size_t)capacity);
    buf->len  = 0;
    buf->cap  = (size_t)capacity;
    buf->pos  = 0;
    return (int64_t)(intptr_t)buf;
}

static inline void arx_bytebuf_ensure(Arx_ByteBuf* buf, size_t extra) {
    if (buf->len + extra <= buf->cap) return;
    size_t new_cap = buf->cap + (buf->cap >> 1);
    if (new_cap < buf->cap + extra) new_cap = buf->cap + extra + 64;
    buf->data = (uint8_t*)realloc(buf->data, new_cap);
    if (!buf->data) arx_panic("OOM: ByteBuffer growth failed", __FILE__, __LINE__);
    buf->cap = new_cap;
}

static inline void arx_bytebuf_write_u8(int64_t bh, int64_t val) {
    Arx_ByteBuf* buf = (Arx_ByteBuf*)(intptr_t)bh;
    if (!buf) return;
    arx_bytebuf_ensure(buf, 1);
    buf->data[buf->len++] = (uint8_t)(val & 0xFF);
}

static inline void arx_bytebuf_write_i32_le(int64_t bh, int64_t val) {
    Arx_ByteBuf* buf = (Arx_ByteBuf*)(intptr_t)bh;
    if (!buf) return;
    arx_bytebuf_ensure(buf, 4);
    int32_t v = (int32_t)val;
    memcpy(buf->data + buf->len, &v, 4);
    buf->len += 4;
}

static inline void arx_bytebuf_write_i32_be(int64_t bh, int64_t val) {
    Arx_ByteBuf* buf = (Arx_ByteBuf*)(intptr_t)bh;
    if (!buf) return;
    arx_bytebuf_ensure(buf, 4);
    int32_t v = (int32_t)val;
    buf->data[buf->len + 0] = (uint8_t)((v >> 24) & 0xFF);
    buf->data[buf->len + 1] = (uint8_t)((v >> 16) & 0xFF);
    buf->data[buf->len + 2] = (uint8_t)((v >>  8) & 0xFF);
    buf->data[buf->len + 3] = (uint8_t)( v        & 0xFF);
    buf->len += 4;
}

static inline void arx_bytebuf_write_f64_le(int64_t bh, int64_t val_bits) {
    Arx_ByteBuf* buf = (Arx_ByteBuf*)(intptr_t)bh;
    if (!buf) return;
    arx_bytebuf_ensure(buf, 8);
    memcpy(buf->data + buf->len, &val_bits, 8);
    buf->len += 8;
}

static inline int64_t arx_bytebuf_read_u8(int64_t bh) {
    Arx_ByteBuf* buf = (Arx_ByteBuf*)(intptr_t)bh;
    if (!buf || buf->pos >= buf->len)
        arx_panic("ReadError: ByteBuffer underrun on read_u8", __FILE__, __LINE__);
    return (int64_t)buf->data[buf->pos++];
}

static inline int64_t arx_bytebuf_read_i32_le(int64_t bh) {
    Arx_ByteBuf* buf = (Arx_ByteBuf*)(intptr_t)bh;
    if (!buf || buf->pos + 4 > buf->len)
        arx_panic("ReadError: ByteBuffer underrun on read_i32_le", __FILE__, __LINE__);
    int32_t v;
    memcpy(&v, buf->data + buf->pos, 4);
    buf->pos += 4;
    return (int64_t)v;
}

static inline int64_t arx_bytebuf_read_i32_be(int64_t bh) {
    Arx_ByteBuf* buf = (Arx_ByteBuf*)(intptr_t)bh;
    if (!buf || buf->pos + 4 > buf->len)
        arx_panic("ReadError: ByteBuffer underrun on read_i32_be", __FILE__, __LINE__);
    int32_t v = ((int32_t)buf->data[buf->pos + 0] << 24)
              | ((int32_t)buf->data[buf->pos + 1] << 16)
              | ((int32_t)buf->data[buf->pos + 2] <<  8)
              | ((int32_t)buf->data[buf->pos + 3]);
    buf->pos += 4;
    return (int64_t)v;
}

static inline void arx_bytebuf_seek(int64_t bh, int64_t offset) {
    Arx_ByteBuf* buf = (Arx_ByteBuf*)(intptr_t)bh;
    if (!buf) return;
    if ((size_t)offset > buf->len) offset = (int64_t)buf->len;
    buf->pos = (size_t)offset;
}

static inline void arx_bytebuf_reset(int64_t bh) {
    Arx_ByteBuf* buf = (Arx_ByteBuf*)(intptr_t)bh;
    if (buf) buf->pos = 0;
}

static inline int64_t arx_bytebuf_len(int64_t bh) {
    Arx_ByteBuf* buf = (Arx_ByteBuf*)(intptr_t)bh;
    return buf ? (int64_t)buf->len : 0;
}

static inline int64_t arx_bytebuf_pos(int64_t bh) {
    Arx_ByteBuf* buf = (Arx_ByteBuf*)(intptr_t)bh;
    return buf ? (int64_t)buf->pos : 0;
}

static inline void arx_bytebuf_free(int64_t bh) {
    Arx_ByteBuf* buf = (Arx_ByteBuf*)(intptr_t)bh;
    if (!buf) return;
    if (buf->data) arx_free(buf->data);
    arx_free(buf);
}

// ==========================================
// Phase 22: str helper — arx_str_find
// ==========================================

static inline int64_t arx_str_find(const char* s, const char* needle) {
    if (!s || !needle) return -1;
    const char* found = strstr(s, needle);
    return found ? (int64_t)(found - s) : -1;
}

static inline int64_t arx_str_compare(const char* a, const char* b) {
    if (!a && !b) return 0;
    if (!a) return -1;
    if (!b) return 1;
    return (int64_t)strcmp(a, b);
}

// ==========================================
// Phase 22: for..in List iterator helper
// ==========================================

// arx_list_iter_next: stateless helper for for-in codegen
// iter_state is a mutable int64 holding current index (starts at 0)
// returns 1 if valid, 0 if exhausted; writes element into *out_elem
static inline bool arx_list_iter_next(int64_t list_handle, int64_t* iter_idx, int64_t* out_elem) {
    Arx_List* list = (Arx_List*)(intptr_t)list_handle;
    if (!list || (size_t)(*iter_idx) >= list->len) return false;
    *out_elem = list->data[(*iter_idx)++];
    return true;
}

// arx_map_iter_next: iterates over key-value pairs
// iter_state = current slot index in map->slots
static inline bool arx_map_iter_next(int64_t map_handle, int64_t* iter_idx, int64_t* out_key, int64_t* out_val) {
    Arx_Map* m = (Arx_Map*)(intptr_t)map_handle;
    if (!m) return false;
    while ((size_t)(*iter_idx) < m->capacity) {
        size_t i = (size_t)(*iter_idx)++;
        if (m->slots[i].state == ARX_MAP_FULL_SLOT) {
            *out_key = m->slots[i].key;
            *out_val = m->slots[i].value;
            return true;
        }
    }
    return false;
}

#endif // AERIX_RT_H


