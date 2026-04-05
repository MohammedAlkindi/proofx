"""
Optimized Collatz Conjecture Computer
Targeting 1+ Billion Integers Per Second 
"""

import gzip
import time
import json
from array import array
import threading
from queue import SimpleQueue, Empty
import os
import mmap
import math
from multiprocessing import shared_memory, Process, Manager, cpu_count
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
from numba import jit, prange, config, types
import psutil
import signal
import sys
from dataclasses import dataclass
from contextlib import contextmanager
import logging

# Configure Numba for maximum performance
config.THREADING_LAYER = 'threadsafe'
config.FASTMATH = True

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PerformanceStats:
    """Track performance metrics"""
    total_processed: int = 0
    instant_speed: float = 0.0
    average_speed: float = 0.0
    peak_speed: float = 0.0
    start_time: float = 0.0
    last_update: float = 0.0

# Standalone Numba-compatible function with enhanced optimizations
@jit(nopython=True, cache=True, fastmath=True, boundscheck=False)
def sequence_length_hyper_fast(n: int, length_cache: np.ndarray) -> int:
    """Numba-accelerated ultra-fast sequence computation with enhanced optimizations"""
    cache_size = len(length_cache)

    # Fast path for cached values
    if n < cache_size and length_cache[n] != 0:
        return length_cache[n]

    # Use fixed-size arrays for stack
    stack = np.zeros(256, dtype=np.uint64)  # Reduced stack size
    stack_size = 0
    current = n
    length = 0

    # Optimized traversal with enhanced pattern recognition
    while current >= cache_size or (current < cache_size and length_cache[current] == 0):
        if stack_size < len(stack):
            stack[stack_size] = current
            stack_size += 1

        # Enhanced Collatz step with multiple optimizations
        if current & 1:
            # For odd numbers: use mathematical shortcut (3n+1)/2
            current = (3 * current + 1) >> 1
            # Check if we can skip multiple steps
            if current < cache_size and length_cache[current] != 0:
                break
        else:
            # For even numbers: use trailing zero count optimization
            # Count trailing zeros for multiple divisions by 2
            temp = current
            shifts = 0
            while (temp & 1) == 0 and shifts < 8:  # Process up to 8 divisions at once
                temp >>= 1
                shifts += 1
                if temp < cache_size and length_cache[temp] != 0:
                    break
            else:
                temp = current >> shifts

            if temp < cache_size and length_cache[temp] != 0:
                # Add the shifts to the length later
                length = length_cache[temp]
                # Process remaining stack with shifts accounted for
                for i in range(stack_size):
                    val = stack[i]
                    if val < cache_size:
                        length_cache[val] = length + (stack_size - i) + shifts
                return length_cache[n]
            current = temp

    length = length_cache[current] if current < cache_size else 0

    # Process stack in reverse with optimized updates
    for i in range(stack_size - 1, -1, -1):
        length += 1
        val = stack[i]
        if val < cache_size:
            length_cache[val] = length

    return length

class HyperOptimizedCollatz:
    """Ultra-optimized Collatz sequence computer with advanced caching"""

    def __init__(self, cache_size: int = 2**24):  # Reduced default cache size
        self.cache_size = cache_size
        self.length_cache = np.zeros(cache_size, dtype=np.uint32)
        self.length_cache[1] = 1
        self.stats = {'hits': 0, 'misses': 0}

    def sequence_length(self, n: int) -> int:
        """Wrapper for the Numba-compiled function"""
        if n < self.cache_size and self.length_cache[n] != 0:
            self.stats['hits'] += 1
            return self.length_cache[n]

        self.stats['misses'] += 1
        return sequence_length_hyper_fast(n, self.length_cache)

@jit(nopython=True, fastmath=True, parallel=True, boundscheck=False)
def collatz_kernel_optimized(start: int, end: int, output_array: np.ndarray):
    """Enhanced Numba-accelerated parallel kernel with better cache utilization"""
    cache_size = 2**20  # Smaller per-thread cache
    # Thread-local cache for better performance
    local_cache = np.zeros(cache_size, dtype=np.uint32)
    local_cache[1] = 1

    for i in prange(start, end + 1):
        n = i
        stack = np.zeros(128, dtype=np.uint64)  # Smaller stack
        stack_ptr = 0
        length = 0

        # Optimized sequence computation
        while n >= cache_size or (n < cache_size and local_cache[n] == 0):
            if stack_ptr < len(stack):
                stack[stack_ptr] = n
                stack_ptr += 1

            if n & 1:
                n = (3 * n + 1) >> 1
            else:
                n >>= 1

        length = local_cache[n]

        # Reverse stack processing
        for j in range(stack_ptr - 1, -1, -1):
            length += 1
            val = stack[j]
            if val < cache_size:
                local_cache[val] = length

        output_array[i - start] = length

def worker_thread_optimized(worker_id: int, number_ranges: List[Tuple[int, int]],
                           results_queue: SimpleQueue, stats_queue: SimpleQueue,
                           cache_size: int = 2**22):
    """Optimized worker with better cache management and work distribution"""
    computer = HyperOptimizedCollatz(cache_size)
    local_batch = []
    processed = 0
    local_start_time = time.perf_counter()
    last_report_time = local_start_time

    try:
        for start, end in number_ranges:
            # Process entire range at once for better cache locality
            for num in range(start, end + 1):
                length = computer.sequence_length(num)
                local_batch.append((num, length))
                processed += 1

                # Batch submission for efficiency
                if len(local_batch) >= 50000:
                    results_queue.put((worker_id, local_batch))
                    local_batch = []

            # Progress reporting
            current_time = time.perf_counter()
            if current_time - last_report_time >= 2.0:
                elapsed = current_time - local_start_time
                speed = processed / elapsed
                stats_queue.put(('worker_progress', worker_id, speed, processed))
                last_report_time = current_time

    except Exception as e:
        logger.error(f"Worker {worker_id} error: {e}")
    finally:
        # Final batch submission
        if local_batch:
            results_queue.put((worker_id, local_batch))
        stats_queue.put(('worker_complete', worker_id, processed))

def writer_thread_fast(output_file: str, results_queue: SimpleQueue,
                      stats_queue: SimpleQueue, total_numbers: int):
    """Fast writer with efficient batching"""
    buffer = []
    total_written = 0
    start_time = time.perf_counter()

    try:
        with gzip.open(output_file, 'wt', encoding='utf-8', compresslevel=1) as f:  # Faster compression
            f.write('{"metadata":{"version":"4.0","algorithm":"optimized"}}\n')

            while total_written < total_numbers:
                try:
                    worker_id, batch = results_queue.get(timeout=1.0)
                    if batch is None:  # Termination signal
                        break

                    buffer.extend(batch)
                    total_written += len(batch)

                    # Write in larger batches for efficiency
                    if len(buffer) >= 100000 or total_written >= total_numbers:
                        # Use efficient string joining
                        output_str = ''.join(f'{{"n":{num},"l":{length}}}\n' for num, length in buffer)
                        f.write(output_str)
                        buffer.clear()

                    # Progress reporting
                    if total_written % 1000000 == 0:
                        elapsed = time.perf_counter() - start_time
                        speed = total_written / elapsed
                        stats_queue.put(('writer_progress', speed, total_written))

                except Empty:
                    continue

        # Final write
        if buffer:
            output_str = ''.join(f'{{"n":{num},"l":{length}}}\n' for num, length in buffer)
            f.write(output_str)

    except Exception as e:
        logger.error(f"Writer error: {e}")
    finally:
        logger.info(f"Writer completed: {total_written:,} numbers")

def compute_optimized(start: int, end: int, output_file: str,
                     num_threads: Optional[int] = None) -> float:
    """Optimized main computation function with proper work distribution"""

    if num_threads is None:
        num_threads = min(cpu_count(), 8)  # Don't over-subscribe

    total_numbers = end - start + 1

    logger.info(f"OPTIMIZED COLLATZ COMPUTER")
    logger.info(f"Range: {start:,} to {end:,}")
    logger.info(f"Total numbers: {total_numbers:,}")
    logger.info(f"Threads: {num_threads}")

    # Better work distribution - larger chunks for better cache locality
    numbers_per_thread = total_numbers // num_threads
    work_ranges = []

    for i in range(num_threads):
        thread_start = start + i * numbers_per_thread
        if i == num_threads - 1:
            thread_end = end  # Last thread gets remainder
        else:
            thread_end = thread_start + numbers_per_thread - 1
        work_ranges.append([(thread_start, thread_end)])

    # Initialize communication
    results_queue = SimpleQueue()
    stats_queue = SimpleQueue()

    global_start_time = time.perf_counter()

    # Start writer
    writer = threading.Thread(
        target=writer_thread_fast,
        args=(output_file, results_queue, stats_queue, total_numbers),
        name="WriterThread"
    )
    writer.daemon = True
    writer.start()

    # Start workers
    workers = []
    for i in range(num_threads):
        worker = threading.Thread(
            target=worker_thread_optimized,
            args=(i, work_ranges[i], results_queue, stats_queue, 2**22),  # 4MB cache per worker
            name=f"Worker-{i}"
        )
        worker.daemon = True
        worker.start()
        workers.append(worker)

    # Monitoring
    completed_workers = 0
    total_processed = 0
    speeds = []
    last_print_time = global_start_time

    try:
        while completed_workers < len(workers):
            try:
                msg_type, *data = stats_queue.get(timeout=0.5)
                if msg_type == 'worker_progress':
                    worker_id, speed, processed = data
                    speeds.append(speed)
                    total_processed = max(total_processed, processed * num_threads)  # Estimate
                elif msg_type == 'worker_complete':
                    completed_workers += 1
                elif msg_type == 'writer_progress':
                    speed, written = data
                    total_processed = written
            except Empty:
                pass

            # Progress display
            current_time = time.perf_counter()
            if current_time - last_print_time >= 1.0:
                elapsed = current_time - global_start_time
                current_speed = total_processed / elapsed if elapsed > 0 else 0
                progress_pct = (total_processed / total_numbers) * 100
                eta = (total_numbers - total_processed) / current_speed if current_speed > 0 else 0

                print(f"\r⚡ Speed: {current_speed:,.0f} int/sec | "
                      f"Progress: {progress_pct:.1f}% | "
                      f"ETA: {eta:.1f}s | "
                      f"Workers: {len(workers)-completed_workers}/{len(workers)}",
                      end="", flush=True)
                last_print_time = current_time

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return 0

    # Wait for completion
    for worker in workers:
        worker.join(timeout=5)

    # Signal writer to finish
    results_queue.put((0, None))
    writer.join(timeout=10)

    # Final stats
    total_time = time.perf_counter() - global_start_time
    final_speed = total_numbers / total_time

    print(f"\n")  # Clear the progress line
    logger.info(f"COMPUTATION COMPLETE!")
    logger.info(f"Total time: {total_time:.2f} seconds")
    logger.info(f"Final speed: {final_speed:,.0f} integers/sec")

    return final_speed

def compute_numba_parallel_fast(start: int, end: int) -> float:
    """Fast Numba parallel computation for best performance"""
    total_numbers = end - start + 1
    logger.info(f"NUMBA PARALLEL MODE - MAXIMUM PERFORMANCE")

    # Use smaller chunks for better cache behavior
    chunk_size = min(10_000_000, total_numbers)
    results = np.zeros(total_numbers, dtype=np.uint32)

    start_time = time.perf_counter()

    # Process in chunks if too large
    if total_numbers > chunk_size:
        chunks = (total_numbers + chunk_size - 1) // chunk_size
        for i in range(chunks):
            chunk_start = start + i * chunk_size
            chunk_end = min(chunk_start + chunk_size - 1, end)
            chunk_size_actual = chunk_end - chunk_start + 1
            chunk_results = np.zeros(chunk_size_actual, dtype=np.uint32)
            collatz_kernel_optimized(chunk_start, chunk_end, chunk_results)
            results[i*chunk_size:(i*chunk_size + chunk_size_actual)] = chunk_results
    else:
        collatz_kernel_optimized(start, end, results)

    total_time = time.perf_counter() - start_time
    speed = total_numbers / total_time

    logger.info(f"NUMBA PARALLEL: {speed:,.0f} integers/sec")

    # Save results efficiently
    with gzip.open('collatz_numba_fast.json.gz', 'wt') as f:
        f.write('{"numba_results":[\n')
        for i, length in enumerate(results):
            f.write(f'{{"n":{start + i},"l":{length}}}')
            if i < len(results) - 1:
                f.write(',\n')
        f.write('\n]}')

    return speed

def benchmark_system_accurate() -> Dict[str, Any]:
    """Accurate system benchmarking"""
    logger.info("🔬 ACCURATE SYSTEM BENCHMARK")

    cpu_cores = cpu_count()
    memory = psutil.virtual_memory()

    # More accurate performance test
    test_size = 1_000_000
    test_cache = np.zeros(2**22, dtype=np.uint32)  # 4MB cache
    test_cache[1] = 1

    # Warm up
    for i in range(1, 1000):
        sequence_length_hyper_fast(i, test_cache)

    # Actual benchmark
    start_time = time.perf_counter()
    for i in range(1, test_size + 1):
        sequence_length_hyper_fast(i, test_cache)
    test_time = time.perf_counter() - start_time
    test_speed = test_size / test_time

    logger.info(f"CPU Cores: {cpu_cores}")
    logger.info(f"Available Memory: {memory.available / 1024**3:.1f} GB")
    logger.info(f"Single-thread speed: {test_speed:,.0f} int/sec")

    # Realistic multi-thread projection
    projected_speed = test_speed * cpu_cores * 0.7  # 70% efficiency
    logger.info(f"Projected multi-thread: {projected_speed:,.0f} int/sec")

    return {
        'cpu_cores': cpu_cores,
        'single_thread_speed': test_speed,
        'projected_speed': projected_speed
    }

if __name__ == "__main__":
    # Realistic configuration for 2-core system
    START = 1
    END = 10_000_000

    logger.info(" OPTIMIZED COLLATZ COMPUTER - REALISTIC TARGETS")
    logger.info("=" * 50)

    system_info = benchmark_system_accurate()

    print("\nSelect computation mode:")
    print("1. Multi-threaded (recommended)")
    print("2. Numba parallel (fastest)")
    print("3. Quick test (1M numbers)")

    try:
        choice = input("Choice (1-3): ").strip()

        if choice == "2":
            speed = compute_numba_parallel_fast(START, END)
        elif choice == "3":
            speed = compute_optimized(START, 1_000_000, "collatz_quick.json.gz")
        else:
            speed = compute_optimized(START, END, "collatz_optimized.json.gz")

        # Realistic projections
        if speed > 0:
            million_per_sec = speed / 1_000_000
            logger.info(f"\nPERFORMANCE ANALYSIS:")
            logger.info(f"Speed: {million_per_sec:.2f} million integers/sec")

            if million_per_sec >= 100:
                logger.info("WORLD-CLASS PERFORMANCE!")
            elif million_per_sec >= 10:
                logger.info("EXCELLENT PERFORMANCE")
            elif million_per_sec >= 1:
                logger.info("GOOD PERFORMANCE")
            else:
                logger.info("MODERATE PERFORMANCE")

            # Projection to 1 billion
            billion_time = 1_000_000_000 / speed
            logger.info(f"Time for 1 billion: {billion_time/60:.1f} minutes")

    except KeyboardInterrupt:
        logger.info("\nOperation cancelled")
    except Exception as e:
        logger.error(f"Error: {e}")
