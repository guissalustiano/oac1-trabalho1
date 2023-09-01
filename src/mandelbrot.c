#include <complex.h>
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

const size_t MAX_ITERATIONS = 200;

/*
 * Armazena as cores de cada pixel da imagem
 */
typedef struct {
  uint8_t red;
  uint8_t green;
  uint8_t blue;
} pixel_t;

/*
 * Armazena as informações da imagem, com um array de pixels que devera ser alocado na criação
 */
typedef struct {
  pixel_t *pixels;
  const size_t width;
  const size_t height;
} image_t;

/*
 * Area do conjunto de mandelbrot que será gerada
 */
typedef struct {
  double real_min;
  double real_max;
  double imag_min;
  double imag_max;
} frame_t;

/*
 * Paleta de cores
 * Será dada cores diferentes para o numero de iterações que demorou para o ponto divergir
 */
const size_t PALLET_SIZE = 17;
pixel_t pallet[] = {
    {66, 30, 15},    {25, 7, 26},     {9, 1, 47},      {4, 4, 73},
    {0, 7, 100},     {12, 44, 138},   {24, 82, 177},   {57, 125, 209},
    {134, 181, 229}, {211, 236, 248}, {241, 233, 191}, {248, 201, 95},
    {255, 170, 0},   {204, 128, 0},   {153, 87, 0},    {106, 52, 3},
    {16, 16, 16},
};

/*
 * Função usada para calcular o proximo ponto da sequencia
 */
double complex fc(const double complex z, const double complex c) {
  return z * z + c;
}

/*
 * Iteramos a partir de um ponto multiplas vezes com a função fc
 * Se o ponto divergir, retornamos o numero de iterações que demorou para divergir
 */
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

/*
 * Gera a cor do pixel a partir do numero de iterações que demorou para divergir
 */
pixel_t iteration2pixel(size_t iterations) {
  // Se o ponto "não divergiu", ele é preto
  if (iterations >= MAX_ITERATIONS) {
    return pallet[PALLET_SIZE - 1];
  }

  // Se não é alguma outra cor da paleta
  return pallet[iterations % PALLET_SIZE];
}

/*
 * A partir do frame (com o retangulo que deve ser gerado)
 * calcula o passo de cada pixel.
 * Então percorre os pixels aplicando a função multiplas vezes e observando quando diverge.
 */
void create_mandelbrot(const frame_t *frame, image_t *image) {
  // Calcula o espaço entre cada pixel
  double real_step = (frame->real_max - frame->real_min) / image->width;
  double imag_step = (frame->imag_max - frame->imag_min) / image->height;

  // Ultiliza o OpemMP para paralelizar o for, ou seja, cada linha do programa é calculada em uma thread diferente
  #pragma omp parallel for
  for (int y = 0; y < image->height; y++) {
    // A partir do step e do ponto inicial, calcula o valor da parte imaginaria referente ao ponto (https://pt.wikipedia.org/wiki/Interpola%C3%A7%C3%A3o_linear)
    double imag = frame->imag_min + y * imag_step;

    // Garante que o ponto seja 0 caso esteja muito proximo de 0
    if (fabs(imag) < imag_step / 2) {
      imag = 0.0;
    };

    for (int x = 0; x < image->width; x++) {
      // Calcula a parte real referente ao ponto
      double real = frame->real_min + x * real_step;

      // Itera multiplas vezes sobre o ponto para ver quado diverge
      int iteration = iterate_point(real + imag * I);

      // Prenche a imagem com a cor referente ao numero de iterações
      image->pixels[x + y * image->width] = iteration2pixel(iteration);
    };
  };
};


// Escreve o arquivo usando o formato ppm P6 (binario)
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

// Parceia os parametros e chama a função principal
int main(int argc, char *argv[]) {
  if(argc < 6){
        printf("usage: ./mandelbrot real_min real_max imag_min imag_max image_width\n");
        printf("examples with image_width = 11500:\n");
        printf("    Full Picture:         ./mandelbrot -2.5 1.5 -2.0 2.0 11500\n");
        printf("    Seahorse Valley:      ./mandelbrot -0.75 -0.737 -0.132 -0.121 11500\n");
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
