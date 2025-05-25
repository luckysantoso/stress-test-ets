# stress_test_client.py

"""
Stress-test client pool launcher for the file server.

Supports both thread- and process-based concurrency.
"""

import argparse
import logging
import os
import time
from concurrent.futures import (ThreadPoolExecutor, ProcessPoolExecutor,
                                as_completed)
from typing import Tuple, List

from file_client_cli import remote_get, remote_list, remote_upload


def human_readable_bytes(num: float) -> str:
    """
    Convert a byte rate into a human-readable string.
    """
    for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s', 'TB/s']:
        if abs(num) < 1024.0:
            return f"{num:3.2f} {unit}"
        num /= 1024.0
    return f"{num:.2f} PB/s"


def run_task(operation: str,
             volume: int,
             filename: str) -> Tuple[bool, float, str]:
    """
    Perform a single file operation and measure its duration.
    Returns (success, elapsed_time, error_message).
    """
    start_time = time.time()
    error_message = ""
    success = False

    try:
        if operation == 'upload':
            success = remote_upload(f"test_files/{filename}")
        elif operation == 'download':
            success = remote_get(filename)
        elif operation == 'list':
            success = remote_list()
        else:
            error_message = f"Unknown operation: {operation}"
    except Exception as exc:
        error_message = str(exc)
    elapsed = time.time() - start_time

    return success, elapsed, error_message


def run_client_pool(mode: str,
                    operation: str,
                    volume: int,
                    client_pool: int) -> None:
    """
    Launch a pool of client workers to perform the given operation.
    """
    filename = f"file_{volume}MB.bin" if operation in ('upload', 'download') else ''
    error_log_dir = 'results'
    error_log_path = os.path.join(error_log_dir, 'error_log.txt')
    os.makedirs(error_log_dir, exist_ok=True)

    # Prepare test files or directories
    if operation == 'upload':
        os.makedirs('test_files', exist_ok=True)
        file_path = os.path.join('test_files', filename)
        if volume > 0 and not os.path.isfile(file_path):
            print(f"Generating test file {filename} ({volume} MB)")
            with open(file_path, 'wb') as f:
                f.write(os.urandom(volume * 1024 * 1024))

    if operation == 'download':
        os.makedirs('downloads', exist_ok=True)

    Executor = (ThreadPoolExecutor
                if mode == 'thread'
                else ProcessPoolExecutor)

    start_time = time.time()
    results: List[Tuple[bool, float, str]] = []

    with Executor(max_workers=client_pool) as executor:
        futures = [
            executor.submit(run_task, operation, volume, filename)
            for _ in range(client_pool)
        ]

        for idx, future in enumerate(as_completed(futures), start=1):
            success, duration, error = future.result()
            results.append((success, duration, error))

            if error:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                with open(error_log_path, 'a') as elog:
                    elog.write(
                        f"[{timestamp}] Mode={mode} "
                        f"Op={operation} Volume={volume}MB "
                        f"Client={idx} Error={error}\n"
                    )

    total_time = time.time() - start_time
    durations = [r[1] for r in results]
    avg_time = sum(durations) / len(durations) if durations else 0.0
    successes = sum(1 for r in results if r[0])
    failures = client_pool - successes

    throughput = 0.0
    if operation in ('upload', 'download') and avg_time > 0:
        throughput = (volume * 1024 * 1024) / avg_time

    # Print summary
    print("\nTest Results")
    print(f"  Mode               : {mode}")
    print(f"  Operation          : {operation.upper()}")
    print(f"  Client Pool Size   : {client_pool}")
    print(f"  Volume per Client  : {volume} MB")
    print(f"  Average Time/Client: {avg_time:.2f} s")
    print(f"  Throughput/Client  : {human_readable_bytes(throughput)}")
    print(f"  Success/Failure     : {successes}/{failures}")
    print(f"  Total Test Duration: {total_time:.2f} s")


def main() -> None:
    """
    Command-line entry point.
    """
    parser = argparse.ArgumentParser(
        description="File Server Stress Test Client Pool Launcher"
    )
    parser.add_argument(
        '--mode',
        choices=['thread', 'process'],
        required=True,
        help='Concurrency mode (thread or process).'
    )
    parser.add_argument(
        '--operation',
        choices=['upload', 'download', 'list'],
        required=True,
        help='File operation to perform.'
    )
    parser.add_argument(
        '--volume',
        type=int,
        choices=[10, 50, 100],
        default=10,
        help='File size in MB for upload/download.'
    )
    parser.add_argument(
        '--client-pool',
        type=int,
        choices=[1, 5, 50],
        required=True,
        help='Number of concurrent client workers.'
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.ERROR, format='[%(levelname)s] %(message)s')

    run_client_pool(
        mode=args.mode,
        operation=args.operation,
        volume=args.volume,
        client_pool=args.client_pool
    )


if __name__ == '__main__':
    main()
