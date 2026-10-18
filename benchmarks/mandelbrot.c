#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <time.h>

int64_t compute_mandelbrot(int64_t width, int64_t height, int64_t max_iter) {
    int64_t total_iterations = 0;
    for (int64_t y = 0; y < height; y++) {
        double ci = ((double)y * 2.0 / (double)height) - 1.0;
        for (int64_t x = 0; x < width; x++) {
            double cr = ((double)x * 3.0 / (double)width) - 2.0;
            double zr = 0.0;
            double zi = 0.0;
            int64_t iter = 0;
            while ((zr * zr + zi * zi <= 4.0) && (iter < max_iter)) {
                double temp = zr * zr - zi * zi + cr;
                zi = 2.0 * zr * zi + ci;
                zr = temp;
                iter++;
            }
            total_iterations += iter;
        }
    }
    return total_iterations;
}

int main(void) {
    clock_t start = clock();
    int64_t total = compute_mandelbrot(1000, 1000, 1000);
    clock_t end = clock();
    double cpu_time = (double)(end - start) / CLOCKS_PER_SEC;
    printf("C Mandelbrot Total: %lld in %.4f seconds\n", (long long)total, cpu_time);
    return 0;
}

