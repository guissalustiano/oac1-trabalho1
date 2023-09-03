#import "template.typ": *

#show: project.with(
  title: "Atividade 1 - Org. Arg. 1",
  authors: (
	"Profa. Dra. Cíntia Borges Margi (cintia@usp.br)",
	"Guilherme S. Salustiano (salustiano@usp.br)",
  ),
)
#show link: underline

= Introduction
Esse trabalho busca introduzir alguns dos problemas e desafios relacionados ao conteúdo visto em aula.
Analisaremos o desempenho de um programa variando o número de threads e tamanho da entrada, observando como isso afeta o tempo de execução e o IPC, baseado no EP1 de MAC5742 @ep1-MAC5742.

= Requisitos
Essa atividade depende de funcionalidades únicas do Linux, recomendamos rodar linux nativamente. Caso não seja possível, é recomendado utilizar o #link("https://learn.microsoft.com/en-us/windows/wsl/install")[WSL2 no Windows], ou via #link("https://ubuntu.com/tutorials/how-to-run-ubuntu-desktop-on-a-virtual-machine-using-virtualbox#1-overview")[Máquina Virtual] (com no mínimo 2 cores), em caso de duvidas contate o monitor.

Vamos precisar das seguintes dependências:
```bash
$ Ubuntu
$ sudo apt install build-essential # p/ gcc & make
$ sudo apt install linux-tools-generic # p/ perf
$ sudo apt install hwloc # p/ lstopo (Opcional)
```

Ou você também pode usar o #link("https://docs.docker.com/engine/install/")[docker] com o script `run_by_docker.sh`.

= Conhece quem tu(a CPU) és
Utilizaremos o `lscpu` para observar as especificações do CPU. No terminal rode:
```bash
$ lscpu
```

Observe no `CPU(s)` podemos observar o número de CPU da máquina, guarde esse número pois vamos precisar relacioná-lo a aplicação mais a frente. Também podemos observar outros termos já conhecidos, como a `Architecture`, a ordem dos bits e o tamanho dos caches.

Opcionalmente também podemos gerar uma imagem da arquitetura usando o `lstopo`.
```bash
$ lstopo architecture.png
```

== Entrega
Gere um arquivo json `cpu_info.json` contendo as informações da sua CPU.

// Iremos usar esse arquivo para validar suas análises, utilizando o formato json para facilitar a leitura via script.
```bash
$ # a flag '-J' faz com que a saída seja em JSON
$ # o '>' redireciona a saída do programa para um arquivo
$ lscpu -J > cpu_info.json
```
Esse arquivo será submetido junto com o restante dos arquivos no final da tarefa.

= A aplicação
== Contexto
Você já ouviu falar do Conjunto de Mandelbrot?
Seu descobridor foi Benoit Mandelbrot, que trabalhava na IBM durante a década de 1960 e foi um dos primeiros a usar computação gráfica para mostrar como a complexidade pode surgir a partir de regras simples.
Benoit fez isso criando e visualizando imagens de geometria fractal.

Um desses fractais  foi nomeado _Conjunto de  Mandelbrot_ pelo matemático Adrien Douady.
O Conjunto de Mandelbrot  pode ser informalmente definido como o conjunto dos números complexos $c$ para os quais a função $f_c (z) = z^2 + x$ não diverge quando  é iterada  começando em $z  = 0$. Isto  é, a  sequência $f_c (0), f_c (f_c (0)), f_c (f_c (f_c (0))), dots$   é	sempre	limitada.
Na	@fig:regions abaixo podemos ver algumas regiões do  Conjunto de  Mandelbrot.

/*
#figure(
  image("seahorse.png", width: 82%),
  caption: [
	_Seahorse Valley_
  ],
) <header>
*/
#figure(
grid(
  columns: 2,
  gutter: 2mm,
  figure(
	image("elephant.png"),
	caption: [
  	_Elephant Valley_
	],
  ),
  figure(
	image("seahorse.png"),
	caption: [
  	_Seahorse Valley_
	],
  ),
  figure(
	image("triple_spiral.png"),
	caption: [
  	_Triple Spiral Valley_
	],
  ),
  figure(
	image("full.png"),
	caption: [
  	_Seahorse Valley_
	],
  )
),
  caption: [
	Regiões do Mandelbroat
  ],
) <fig:regions>

== Executando o código
Baixe o #link("https://github.com/guissalustiano/oac1-trabalho1")[código do EP] e entre na pasta com a linha de comando, então basta executar os seguintes comandos

```bash
$ # Compila o código
$ make
$ # Roda o programa
$ OMP_NUM_THREADS=8 ./mandelbrot -2.5 1.5 -2.0 2.0 11500
```
O programa recebe 5 parâmetros, os primeiro quatro se referem a região que será calculada e o último diz respeito ao tamanho da imagem gerada. O número de threads usado é definido pela variável de ambiente `OMP_NUM_THREADS` passada no contexto do shell.

Ao final da execução, o programa gera o arquivo `mandelbrot.ppm` com o seu lindo conjunto de mandelbrot.

== Entrega
Para a entrega dessa secção vamos realizar a medição performance utilizando o comando `perf`. Comece executando o seguinte comando:

```bash
$ OMP_NUM_THREADS=8 perf stat -r 10 -e cycles,instructions,duration_time,power/energy-cores/ ./mandelbrot -2.5 1.5 -2.0 2.0 11500 2048
```

Estamos usando o `perf-stat` que junta estatísticas sobre a execução do programa. O parâmetro `-r` significa o número de repetições da execução, utilizado para calcular o intervalo de confiança. No parâmetro `-e` passamos a lista de eventos que queremos contar, podemos observar a lista inteira com o comando `perf list`. Por fim temos efetivamente o programa a ser executado.

Agora vamos rodar novamente o programa para uma entrada maior e salvar seu resultado para submissão.
```bash
$ OMP_NUM_THREADS=8 perf stat -r 10 -e cycles,instructions,duration_time,power/energy-cores/ ./mandelbrot -2.5 1.5 -2.0 2.0 11500 2> perf.txt
$ cat perf.txt
```

= Brenchmark
Para cada uma  das três versões do programa, vocês  deverão realizar medições do tempo de execução para diferentes tamanhos de entrada.
Nas versões paralelizadas vocês deverão  também medir, para cada  tamanho de entrada, o  tempo de execução para diferentes números de _threads_.

Vocês  devem fazer  um número  de  medições e  analisar a  variação dos  valores obtidos.
Sugerimos $10$ medições para cada experimento, e também que vocês usem a média  e o intervalo  de confiança das $10$  medições nos seus  gráficos.
Caso observem variabilidade  muito grande nas  medições, resultando num  intervalo de confiança muito grande, vocês podem  realizar mais medições, sempre apresentando a média e  o intervalo de confiança.  
*Não é  recomendado* fazer menos de $10$ medições.


A  @tab:exp lista os experimentos  que devem ser feitos:  os valores
para o  número de  _threads_ e  de execuções, e  os tamanhos  de entrada.
Cada  experimento  deverá  ser  repetido nas  quatro  regiões  especificadas  na @fig:regions.  As coordenadas  para  cada região  podem ser  obtidas
executando no diretório `src`:

```bash
$ make mandelbrot_seq
gcc -o mandelbrot_seq -std=c11 mandelbrot_seq.c
$ ./mandelbrot_seq
usage: ./mandelbrot_seq c_x_min c_x_max c_y_min c_y_max image_size
examples with image_size = 11500:
  	Full Picture:     	./mandelbrot_seq -2.5 1.5 -2.0 2.0 11500
  	Seahorse Valley:  	./mandelbrot_seq -0.8 -0.7 0.05 0.15 11500
  	Elephant Valley:  	./mandelbrot_seq 0.175 0.375 -0.1 0.1 11500
  	Triple Spiral Valley: ./mandelbrot_seq -0.188 -0.012 0.554 0.754 11500
```

O número de iterações para o critério de convergência foi escolhido\ #link("https://goo.gl/WpL9hS")[de forma a produzir uma imagem interessante em diferentes níveis de magnificação], mas ter um tempo de execução razoável para tamanhos grandes de entrada.

#align(center)[
  #figure(
  	table(
  	columns: (auto, auto),
  	inset: 10pt,
  	align: center + horizon,
  	[*Regiões*], [
    	- _Triple Spiral_
    	- _Elephant_
    	- _Seahorse_
    	- _Full_
  	],
  	[*Núm. de Threads*], $2^0 dots 2^8$,
  	[*Tamanho da Entrada*], $2^4 dots 2^13$,
  	[*Núm de Execuções*], $10$
	),
	caption: [Experimentos]
  ) <tab:exp>
]

== Entrega
De forma a facilitar a execução dos parâmetros fornecemos o script `run_measure.py` que realiza a execução do programa (#link("https://docs.python.org/3/library/subprocess.html#subprocess.run")[utilizando o `subprocess.run`]), varia os parâmetros conforme o especificado e salva seus resultados na pasta `results` em formato JSON.

Para executar entre no diretório `src/` e execute o comando abaixo:
```bash
python run_measure.py
```
*Atenção* o script demora várias horas para ser executado.
Você pode interromper o script, se necessário, e ele voltará a executar do experimento que parou. Evite rodar coisas pesadas junto do experimento, como jogos, e em caso de notebook prefira rodar sempre enquanto estiver na tomada.

Após o término da execução você deverá submeter a pasta `results/` com os arquivos `json` criados.

= Análise dos resultados
O script `run_measure.py` também gera gráficos na pasta `graphs/` (utilizando pandas e mathplotlib). Você pode alterá-los ou incrementá-los. se quiser.

== Entrega
Vocês deverão analisar os resultados obtidos e tentar responder a algumas perguntas:
- Como e por que as três versões do programa se comportam com a variação:
  - Do tamanho da entrada?
  - Das regiões do Conjunto de Mandelbrot?
  - Do número de _threads_?
- Qual é o número de _threads_ ideal teorico? Oque podemos observar nesse ponto?
- Porque um IPC maior não necessariamente corresponde a uma menor duração

Vocês conseguem pensar em mais perguntas interessantes?

Crie um documento `relatorio.pdf` com suas respostas e considerações, ele deverá ser submetido ao final com os demais arquivos.


= Entrega final
Ao final gere um zip `atv1.zip` com os arquivos solicitados ao longo da atividade e submeta no tidia.
```bash
atv1.zip
├── cpu_info.json
├── perf.txt
├── results/*.json
└── relatorio.pdf
```


#bibliography("references.bib")