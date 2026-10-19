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

#endif // AERIX_RT_H

