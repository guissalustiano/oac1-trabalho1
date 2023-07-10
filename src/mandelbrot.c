#include <complex.h>
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

const size_t MAX_ITERATIONS = 255;

typedef struct {
  uint8_t red;
  uint8_t green;
  uint8_t blue;
} pixel_t;

typedef struct {
  pixel_t *pixels;
  const size_t width;
  const size_t height;
} image_t;

typedef struct {
  double real_max;
  double real_min;
  double imag_max;
  double imag_min;
} frame_t;

const size_t PALLET_SIZE = 17;
pixel_t pallet[] = {
    {66, 30, 15},    {25, 7, 26},     {9, 1, 47},      {4, 4, 73},
    {0, 7, 100},     {12, 44, 138},   {24, 82, 177},   {57, 125, 209},
    {134, 181, 229}, {211, 236, 248}, {241, 233, 191}, {248, 201, 95},
    {255, 170, 0},   {204, 128, 0},   {153, 87, 0},    {106, 52, 3},
    {16, 16, 16},
};

double complex fc(const double complex z, const double complex c) {
  return z * z + c;
}

size_t iterate_point(const double complex z0) {
  double complex z = z0;
  for (size_t i = 0; i < MAX_ITERATIONS; i++) {
    z = fc(z, z0);

    if (cabs(z) > 2) {
      return i;
    }
  }
  return MAX_ITERATIONS;
}

pixel_t iteration2pixel(size_t iterations) {
  if (iterations >= MAX_ITERATIONS) {
    return pallet[PALLET_SIZE - 1];
  }
  return pallet[iterations % PALLET_SIZE];
}

void create_mandelbrot(const frame_t *frame, image_t *image) {
  double real_step = (frame->real_max - frame->real_min) / image->width;
  double imag_step = (frame->imag_max - frame->imag_min) / image->height;

  #pragma omp parallel for
  for (int y = 0; y < image->height; y++) {
    double imag = frame->imag_min + y * imag_step;

    if (fabs(imag) < imag_step / 2) {
      imag = 0.0;
    };

    for (int x = 0; x < image->width; x++) {
      double real = frame->real_min + x * real_step;

      int iteration = iterate_point(real + imag * I);
      image->pixels[x + y * image->width] = iteration2pixel(iteration);
    };
  };
};

void write_image(const image_t *image, const char *filename) {
  FILE *file = fopen(filename, "wb");

  char *comment = "# Mandelbrot set";
  fprintf(file, "P6\n %s\n %zu\n %zu\n %d\n", comment, image->width,
          image->height, 255);

  for (int i = 0; i < image->width * image->height; i++) {
    fwrite(&image->pixels[i], 1, 3, file);
  };

  fclose(file);
}

int main(int argc, char *argv[]) {
  if(argc < 6){
        printf("usage: ./mandelbrot real_min real_max imag_min imag_max image_width\n");
        printf("examples with image_width = 11500:\n");
        printf("    Full Picture:         ./mandelbrot -2.5 1.5 -2.0 2.0 11500\n");
        printf("    Seahorse Valley:      ./mandelbrot -0.8 -0.7 0.05 0.15 11500\n");
        printf("    Elephant Valley:      ./mandelbrot 0.175 0.375 -0.1 0.1 11500\n");
        printf("    Triple Spiral Valley: ./mandelbrot -0.188 -0.012 0.554 0.754 11500\n");
        exit(0);
  }

  const frame_t frame = {
      .real_min = atof(argv[1]),
      .real_max = atof(argv[2]),
      .imag_min = atof(argv[3]),
      .imag_max = atof(argv[4]),
  };

  const size_t width = atoi(argv[5]); // 16K image width
  const size_t height = width * (frame.imag_max - frame.imag_min) /
                        (frame.real_max - frame.real_min);

  image_t image = {
      .width = width,
      .height = height,
      .pixels = malloc(width * height * sizeof(pixel_t)),
  };

  create_mandelbrot(&frame, &image);
  write_image(&image, "mandelbrot.ppm");

  return EXIT_SUCCESS;
}
