import json
from pathlib import Path
from dataclasses import dataclass
import subprocess
import sys

from loguru import logger
# Configure logger
logger.remove()
logger.add(sys.stderr, format="<level>{level: <5}</level> | <level>{message}</level>", level="INFO")

mandelbrot_program = Path("./mandelbrot")
result_folder = Path("results")

def bootstrap():
    result_folder.mkdir(exist_ok=True)
    if not mandelbrot_program.exists():
        logger.error(f"Program \"{mandelbrot_program.as_posix()}\" not found, please run the Makefile before execute this program")
        exit(1)


@dataclass
class PerfResult:
    counter_value: int
    event: str
    metric_unit: str
    metric_value: float
    variance: float
    unit: str

    @staticmethod
    def from_dict(d: dict):
        return PerfResult(
            counter_value=int(float(d['counter-value'])),
            event=d['event'],
            metric_unit=d['metric-unit'],
            metric_value=float(d['metric-value']),
            variance=float(d['variance']),
            unit=d['unit'],
        )

    @staticmethod
    def parse(s: bytes | str):
        return PerfResult.from_dict(json.loads(s))

    def __repr__(self) -> str:
        return f"{self.counter_value:>12} {self.unit:>4} {self.event:>20} # {self.metric_value:>3.2f} ± {self.variance:>3.2f}% {self.metric_unit}"

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
def run_measure(
    real_min: float,
    real_max: float,
    imag_min: float,
    imag_max: float,
    image_width: int,
    repeat: int,
    threads: int,
    events: list[str] = DEFAULT_MEASURE_EVENTS,
) -> tuple[list[PerfResult], Path]:
    command = [
            "perf", "stat",  # Performance counter statistics
            "-r", repeat, # Multiple samples (generate confidence interval)
            "-e", ",".join(events),
            "-j", # Output JSON, easier to parse
            mandelbrot_program.absolute().as_posix(), real_min, real_max, imag_min, imag_max, image_width # Program executed
            ]
    logger.info(f"Running measure on \"{mandelbrot_program.as_posix()} {real_min} {real_max} {imag_min} {imag_max} {image_width}\" with {threads} threads")
    process = subprocess.run([str(c) for c in command],
        env={"OMP_NUM_THREADS": str(threads)}, # Number of threads used by OpenMP
        capture_output=True,
        check=True, # raise Error if execution fail
    )
    results = [PerfResult.parse(r) 
               for r in process.stderr.split(b'\n') 
               if r != b'']
    logger.info("Results:")
    for r in results:
        logger.info(f"\t{r}")

    # Remove file created
    return results, Path("./mandelbrot.ppm")

def run_measure_cached(
    real_min: float,
    real_max: float,
    imag_min: float,
    imag_max: float,
    image_width: int,
    repeat: int,
    threads: int,
    cache_file: str | Path | None = None,
    force_recompute: bool = False,
    events: list[str] = DEFAULT_MEASURE_EVENTS,
) -> tuple[list[PerfResult], Path]:
    result_file = result_folder / f"mandelbrot_{real_min}_{real_max}_{imag_min}_{imag_max}_{image_width}_{threads}.json" if cache_file is None else Path(cache_file)
    result_image = result_folder / f"mandelbrot_{real_min}_{real_max}_{imag_min}_{imag_max}_{image_width}_{threads}.ppm"

    if (not force_recompute and result_image.exists()):
        logger.info(f"Loading cached result from \"{result_file.as_posix()}\"")
        with result_file.open() as f:
            results = [PerfResult.from_dict(r) for r in json.load(f)]
        return results, result_image
    else:
        logger.info(f"Cache file \"{result_file.as_posix()}\" not found, running measure")

    results, image = run_measure(real_min, real_max, imag_min, imag_max, image_width, repeat, threads, events)

    logger.info(f"Saving results to \"{result_file.as_posix()}\"")
    with result_file.open('w') as f:
        json.dump([r.__dict__ for r in results], f)

    logger.info(f"Saving image to \"{result_image.as_posix()}\"")
    image.rename(result_image)

    return results, image
    


input_sizes = [2**i for i in range(4, 14)]
threads = [2**i for i in range(0, 6)]

def main():
    bootstrap()

    for s in input_sizes:
        for t in range(0, 6):
            run_measure_cached(-2.5, 1.5, -2.0, 2.0, s, 10, t, f"full_picture_{t}.json")
            run_measure_cached(-0.75, -0.737, -0.132, -0.121, s, 10, t, f"seahorse_valley_{t}.json")
            run_measure_cached(0.175, 0.375, -0.1, 0.1, s, 10, t, f"elephant_valley_{t}.json")
            run_measure_cached(-0.188, -0.012, 0.554, 0.754, s, 10, t, f"triple_spiral_valley_{t}.json")

# Run main only if this file is called directly
if __name__ == "__main__":
    main()
