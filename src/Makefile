.PHONY: all
all: mandelbrot

mandelbrot: mandelbrot.c
	gcc -o mandelbrot -std=c11 -lm -O2 -fopenmp mandelbrot.c

.PHONY: clean
clean:
	rm mandelbrot mandelbrot.ppm
