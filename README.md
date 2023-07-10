# EP 1 - OAC 1
Brenchmarks com ma

# How to run
### Compile
```bash
gcc mandelbrot.c -o mandelbrot -lm -O2 -std=c99
```

### Run
```bash
# Seahorse
OMP_NUM_THREADS=8 ./mandelbrot -0.75 -0.737 -0.132 -0.121 3840
```
