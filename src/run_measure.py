import json
from pathlib import Path
from dataclasses import dataclass
import subprocess
import re

import pandas as pd
import matplotlib.pyplot as plt

from loguru import logger
# Configure logger
logger.remove()
logger.add(sys.stderr, format="<level>{level: <5}</level> | <level>{message}</level>", level="DEBUG")

mandelbrot_program = Path("./mandelbrot")
exec_folder = Path("results")
graph_folder = Path("graphs")

def bootstrap():
    exec_folder.mkdir(exist_ok=True)
    graph_folder.mkdir(exist_ok=True)
    if not mandelbrot_program.exists():
        logger.error(f"Program \"{mandelbrot_program.as_posix()}\" not found, please run the Makefile before execute this program")
        exit(1)

DEFAULT_MEASURE_EVENTS = [
    "cpu-cycles",
    "instructions",
    "duration_time",
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
    counter_value: float | None
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
        fix_perf = re.sub(b'(?<=\\d),(?=\\d)', '.', s) # perf exports json with comma in pt-BR systems
        d = json.loads(fix_perf)

        if d['counter-value'] == "<not counted>":
            logger.warning(f'value not counted: {d}')

        return PerfResult(
            counter_value=float(d['counter-value']) if d['counter-value'] != "<not counted>" else None,
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
            # "sudo", # need high privileges to measure power
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
    result_file = exec_folder / (str(params) + ".json")
    result_image = result_file.with_suffix(".ppm")

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

    # remove image to reduce disk usage
    result_image.unlink()

    return PerfExecution(params, results, result_image)

def run_all_measures():
    input_sizes = [2**i for i in range(4, 14)]
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

def load_results():
    # Read all results from files
    execs = []
    for exec_file in exec_folder.glob("*.json"):
        with exec_file.open() as f:
            execs.append(PerfExecution.from_dict_and_file(json.load(f), exec_file.with_suffix(".ppm")))

    # Convert to DataFrame
    rows = []
    for exec in execs:
        for result in exec.results:
            rows.append({
                'input.real_min': exec.input.real_min,
                'input.real_max': exec.input.real_max,
                'input.imag_min': exec.input.imag_min,
                'input.imag_max': exec.input.imag_max,
                'input.image_width': exec.input.image_width,
                'input.repeat': exec.input.repeat,
                'input.threads': exec.input.threads,
                'input.region_label': exec.input.region_label,
                'result.counter_value': result.counter_value,
                'result.event': result.event,
                'result.metric_unit': result.metric_unit,
                'result.metric_value': result.metric_value,
                'result.variance': result.variance,
                'result.unit': result.unit,
            })
    return pd.DataFrame(rows)

def plot_durationxthreads(df: pd.DataFrame):
    for region_label, group_region in df.groupby('input.region_label'):
        for image_width, group_width in group_region.groupby('input.image_width'):
            df_duration_time = group_width[group_width['result.event'] == "duration_time:u"]

            logger.info(f"Plotting duration_time x threads (region: {region_label}, image_width: {image_width})")
            fig, ax = plt.subplots()
            ax.bar(
                x = [str(x) for x in df_duration_time['input.threads']],
                height = df_duration_time['result.counter_value'],
            )

            ax.set_title(f"Duration time x Threads (region: {region_label}, image_width: {image_width})")
            ax.set_xlabel("Threads")
            ax.set_ylabel("Duration time (s)")

            fig.savefig(graph_folder / f"durationXthreads_{region_label}_{image_width}.png")
            plt.close(fig)

def plot_durationxsize(df: pd.DataFrame):
    for region_label, group_region in df.groupby('input.region_label'):
        for threads, group_threads in group_region.groupby('input.threads'):
            df_duration_time = group_threads[group_threads['result.event'] == "duration_time:u"]

            logger.info(f"Plotting duration_time x image_width (region: {region_label}, threads: {threads})")
            fig, ax = plt.subplots()
            ax.bar(
                x = [str(x) for x in df_duration_time['input.image_width']],
                height = df_duration_time['result.counter_value'],
            )

            ax.set_title(f"Duration time x Image width (region: {region_label}, threads: {threads})")
            ax.set_xlabel("Image width")
            ax.set_ylabel("Duration time (s)")

            fig.savefig(graph_folder / f"durationXsize_{region_label}_{threads}.png")
            plt.close(fig)

def plot_ipcxthreads(df: pd.DataFrame):
    for region_label, group_region in df.groupby('input.region_label'):
        for image_width, group_width in group_region.groupby('input.image_width'):
            df_instructions = group_width[group_width['result.event'] == "instructions:u"]

            logger.info(f"Plotting IPC x threads (region: {region_label}, image_width: {image_width})")
            fig, ax = plt.subplots()
            ax.bar(
                x = [str(x) for x in df_instructions['input.threads']],
                height = df_instructions['result.metric_value'],
            )

            ax.set_title(f"IPC x Threads (region: {region_label}, image_width: {image_width})")
            ax.set_xlabel("Threads")
            ax.set_ylabel("IPC (instructions/cycle)")

            fig.savefig(graph_folder / f"ipcXthreads_{region_label}_{image_width}.png")
            plt.close(fig)

def plot_ipcxxsize(df: pd.DataFrame):
    for region_label, group_region in df.groupby('input.region_label'):
        for threads, group_threads in group_region.groupby('input.threads'):
            df_instructions = group_threads[group_threads['result.event'] == "instructions:u"]
            logger.info(f"Plotting IPC x image_width (region: {region_label}, threads: {threads})")
            fig, ax = plt.subplots()
            ax.bar(
                x = [str(x) for x in df_instructions['input.image_width']],
                height = df_instructions['result.metric_value'],
            )
            ax.set_title(f"IPC x Image width (region: {region_label}, threads: {threads})")
            ax.set_xlabel("Image width")
            ax.set_ylabel("IPC (instructions/cycle)")
            fig.savefig(graph_folder / f"ipcXsize_{region_label}_{threads}.png")
            plt.close(fig)

# Parametros: region, input_size, threads -> IPC, duration_time
# TODO: plot variance
def plot_results():
    df = load_results()

    plot_durationxthreads(df)
    plot_durationxsize(df)
    plot_ipcxthreads(df)
    plot_ipcxxsize(df)


def main():
    bootstrap()
    run_all_measures()
    plot_results()

# Run main only if this file is called directly
if __name__ == "__main__":
    main()
