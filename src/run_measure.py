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

def run_measure(
    real_min: float,
    real_max: float,
    imag_min: float,
    imag_max: float,
    image_width: int =15360,
    repeat: int =10,
    threads: int =8,
):
    command = [
            "perf", "stat",  # Performance counter statistics
            "-r", repeat, # Multiple samples (generate confidence interval)
            "-j", # Output JSON, easier to parse
            mandelbrot_program.absolute().as_posix(), real_min, real_max, imag_min, imag_max, image_width # Program executed
            ]
    logger.info(f"Running measure on \"{mandelbrot_program.as_posix()} {real_min} {real_max} {imag_min} {imag_max} {image_width}\"")
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
    return results

def main():
    run_measure(-0.75, -0.737, -0.132, -0.121, 256, 10, 1)

# Run main only if this file is called directly
if __name__ == "__main__":
    main()
