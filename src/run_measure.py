import json
from pathlib import Path
from dataclasses import dataclass
import subprocess
import sys

from loguru import logger
# Configure logger
logger.remove()
logger.add(sys.stderr, format="<level>{level: <5}</level> | <level>{message}</level>", level="DEBUG")

mandelbrot_program = Path("./mandelbrot")
result_folder = Path("results")

def bootstrap():
    result_folder.mkdir(exist_ok=True)
    if not mandelbrot_program.exists():
        logger.error(f"Program \"{mandelbrot_program.as_posix()}\" not found, please run the Makefile before execute this program")
        exit(1)

DEFAULT_MEASURE_EVENTS = [
    "cpu-cycles",
    "ref-cycles",
    "instructions",
    "cpu-clock",
    "duration_time",
    "user_time",
    "system_time",
    "mem-loads",
    "mem-stores",
    "power/energy-cores/",
    "power/energy-ram/",
]

@dataclass
class ProgramInput:
    real_min: float
    real_max: float
    imag_min: float
    imag_max: float
    image_width: int
    repeat: int
    threads: int
    region_label: str
    events: list[str]

    def __init__(
        self,
        real_min: float,
        real_max: float,
        imag_min: float,
        imag_max: float,
        image_width: int,
        repeat: int,
        threads: int,
        region_label: str | None,
        events: list[str] = DEFAULT_MEASURE_EVENTS
    ):
        self.real_min = real_min
        self.real_max = real_max
        self.imag_min = imag_min
        self.imag_max = imag_max
        self.image_width = image_width
        self.repeat = repeat
        self.threads = threads
        self.region_label = region_label if region_label != None else f"{real_min}_{real_max}_{imag_min}_{imag_max}"
        self.events = events


    @staticmethod
    def from_dict(d: dict):
        return ProgramInput(
            real_min=float(d['real_min']),
            real_max=float(d['real_max']),
            imag_min=float(d['imag_min']),
            imag_max=float(d['imag_max']),
            image_width=int(d['image_width']),
            repeat=int(d['repeat']),
            threads=int(d['threads']),
            region_label=d['region_label'],
            events=d['events'],
        )

    def __str__(self) -> str:
        return f"{self.region_label}_{self.image_width}#{self.threads}"


@dataclass
class PerfResult:
    counter_value: int | None
    event: str
    metric_unit: str
    metric_value: float
    variance: float
    unit: str

    @staticmethod
    def from_dict(d: dict):
        return PerfResult(
            counter_value=d['counter_value'],
            event=d['event'],
            metric_unit=d['metric_unit'],
            metric_value=float(d['metric_value']),
            variance=float(d['variance']),
            unit=d['unit'],
        )

    @staticmethod
    def parse(s: bytes | str):
        d = json.loads(s)

        if d['counter-value'] == "<not counted>":
            logger.warning(f'value not counted: {d}')

        return PerfResult(
            counter_value=int(float(d['counter-value'])) if d['counter-value'] != "<not counted>" else None,
            event=d['event'],
            metric_unit=d['metric-unit'],
            metric_value=float(d['metric-value']),
            variance=float(d['variance']),
            unit=d['unit'],
        )

    def __str__(self) -> str:
        counter_value = "" if self.counter_value is None else self.counter_value
        return f"{counter_value:>12} {self.unit:>4} {self.event:>20} # {self.metric_value:>3.2f} ± {self.variance:>3.2f}% {self.metric_unit}"

@dataclass
class PerfExecution:
    input: ProgramInput
    results: list[PerfResult]
    image: Path

    @staticmethod
    def from_dict_and_file(d: dict, image: Path):
        return PerfExecution(
            input=ProgramInput.from_dict(d['input']),
            results=[PerfResult.from_dict(r) for r in d['results']],
            image=image,
        )

def run_measure(
    params: ProgramInput,
) -> PerfExecution:
    logger.info(f"Running measure on {str(params)}")
    command = [
            "perf", "stat",  # Performance counter statistics
            "-r", params.repeat, # Multiple samples (generate confidence interval)
            "-e", ",".join(params.events),
            "-j", # Output JSON, easier to parse
            mandelbrot_program.absolute().as_posix(), params.real_min, params.real_max, params.imag_min, params.imag_max, params.image_width # Program executed
            ]
    process = subprocess.run([str(c) for c in command],
        env={"OMP_NUM_THREADS": str(params.threads)}, # Number of threads used by OpenMP
        capture_output=True,
        check=True, # raise Error if execution fail
    )
    results = [PerfResult.parse(r) 
               for r in process.stderr.split(b'\n') 
               if r != b'']
    logger.info("Results:")
    for r in results:
        logger.info(f"\t{str(r)}")

    # Remove file created
    return PerfExecution(params, results, Path("./mandelbrot.ppm"))

def run_measure_cached(
    params: ProgramInput,
    force_recompute: bool = False,
) -> PerfExecution:
    result_file = result_folder / (str(params) + ".json")
    result_image = result_folder / (str(params) + ".ppm")

    if (not force_recompute and result_image.exists()):
        logger.info(f"Loading cached result from \"{result_file.as_posix()}\"")
        with result_file.open() as f:
            exec = PerfExecution.from_dict_and_file(json.load(f), result_image)
            if exec.input == params:
                return exec
            else:
                logger.warning(f"Cache file \"{result_file.as_posix()}\" does not match input, running measure")
    else:
        logger.info(f"Cache file \"{result_file.as_posix()}\" not found, running measure")

    exec = run_measure(params)
    results = exec.results
    image = exec.image

    logger.info(f"Saving results to \"{result_file.as_posix()}\"")
    with result_file.open('w') as f:
        json.dump({
            'input': exec.input.__dict__,
            'results': [r.__dict__ for r in results],
        }, f)

    logger.info(f"Saving image to \"{result_image.as_posix()}\"")
    image.rename(result_image)

    return PerfExecution(params, results, result_image)

def run_all_measures():
    input_sizes = [2**i for i in range(4, 15)]
    threads = [2**i for i in range(0, 9)]

    for t in threads:
        for s in input_sizes:
            run_measure_cached(
                ProgramInput(
                    real_min=-2.5,
                    real_max=1.5,
                    imag_min=-2.0,
                    imag_max=2.0,
                    image_width=s,
                    repeat=10,
                    threads=t,
                    region_label="full_picture",
                )
            )
            run_measure_cached(
                ProgramInput(
                    real_min=-0.75,
                    real_max=-0.737,
                    imag_min=-0.132,
                    imag_max=-0.121,
                    image_width=s,
                    repeat=10,
                    threads=t,
                    region_label="seahorse_valley",
                )
            )
            run_measure_cached(
                ProgramInput(
                    real_min=0.175,
                    real_max=0.375,
                    imag_min=-0.1,
                    imag_max=0.1,
                    image_width=s,
                    repeat=10,
                    threads=t,
                    region_label="elephant_valley",
                )
            )
            run_measure_cached(
                ProgramInput(
                    real_min=-0.188,
                    real_max=-0.012,
                    imag_min=0.554,
                    imag_max=0.754,
                    image_width=s,
                    repeat=10,
                    threads=t,
                    region_label="triple_spiral_valley",
                )
            )

def main():
    bootstrap()
    run_all_measures()
    #TODO: plot results

# Run main only if this file is called directly
if __name__ == "__main__":
    main()
