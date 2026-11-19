// aerix_rt.c — compilation unit so clang/LLVM can link runtime functions
#define static
#define inline
#include "aerix_rt.h"

// Built-in class static method wrappers for LLVM backend
int64_t Arx_Env_arg_count(void) { return arx_args_count(); }
const char* Arx_Env_arg(int64_t i) { return arx_args_get(i); }
const char* Arx_Env_get(const char* k) { return arx_env_get(k); }
bool Arx_Env_set(const char* k, const char* v) { return arx_env_set(k, v); }
int64_t Arx_Env_args(void) { return arx_args_list(); }
const char* Arx_Env_cwd(void) { return arx_env_cwd(); }
void Arx_Env_exit(int64_t c) { arx_env_exit(c); }
const char* Arx_Env_os_name(void) { return arx_os_name(); }

bool Arx_Directory_exists(const char* p) { return arx_dir_exists(p); }
bool Arx_Directory_create(const char* p) { return arx_dir_create(p); }
int64_t Arx_Directory_list_files(const char* p) { return arx_dir_list_files(p); }
int64_t Arx_Directory_list_dirs(const char* p) { return arx_dir_list_dirs(p); }

bool Arx_File_exists(const char* p) { return arx_file_exists(p); }
const char* Arx_File_read_to_string(const char* p) { return arx_file_read_to_string(p); }
bool Arx_File_write_string(const char* p, const char* s) { return arx_file_write_string(p, s); }
bool Arx_File_remove(const char* p) { return arx_file_remove(p); }
bool Arx_File_copy(const char* p, const char* d) { return arx_file_copy(p, d); }
