#include <stdio.h>
#include <stdint.h>
#include <time.h>

int64_t fib(int64_t n) {
    if (n <= 1) return n;
    return fib(n - 1) + fib(n - 2);
}

int main(void) {
    clock_t start = clock();
    int64_t result = fib(38);
    clock_t end = clock();
    double cpu_time = (double)(end - start) / CLOCKS_PER_SEC;
    printf("C Fibonacci(38): %lld in %.4f seconds\n", (long long)result, cpu_time);
    return 0;
}
