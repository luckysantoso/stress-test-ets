# stress_test_orchestrator.py

"""
Orchestrator to run stress-test scenarios combining server and client pools.
"""

import csv
import logging
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from typing import Optional

logging.basicConfig(level=logging.ERROR, format='[%(levelname)s] %(message)s')


class StressTestOrchestrator:
    """
    Launches server and client pools across various configurations,
    captures results, and writes them to a CSV.
    """

    def __init__(self,
                 server_launcher: str = 'server_pool.py',
                 client_launcher: str = 'client_pool.py') -> None:
        self.server_launcher = server_launcher
        self.client_launcher = client_launcher
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.results_file = f'orchestrator_results_{timestamp}.csv'
        self._init_csv()
        self._print_header_once = False

    def _init_csv(self) -> None:
        """
        Prepare the results CSV with header row.
        """
        os.makedirs('results', exist_ok=True)
        self.results_path = os.path.join('results', self.results_file)
        header = [
            'timestamp', 'mode', 'server_pool', 'operation', 'volume',
            'client_pool', 'avg_time_s', 'throughput_Bps', 'success', 'fail'
        ]
        with open(self.results_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header)

    def run_scenario(self,
                     mode: str,
                     server_pool: int,
                     operation: str,
                     volume: int,
                     client_pool: int) -> None:
        """
        Start server in specified mode and pool size, then run client test.
        Record results in CSV and print formatted table row.
        """
        # Launch server
        server_proc = subprocess.Popen(
            [sys.executable, self.server_launcher,
             '--mode', mode,
             '--pool', str(server_pool),
             '--base-port', '7000'],
            preexec_fn=os.setsid
        )
        try:
            time.sleep(2)
            # Launch client
            cmd = [
                sys.executable, self.client_launcher,
                '--mode', mode,
                '--operation', operation,
                '--volume', str(volume),
                '--client-pool', str(client_pool)
            ]
            client_proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True
            )
            stdout, _ = client_proc.communicate(timeout=300)
        finally:
            # Ensure server is killed
            if server_proc.poll() is None:
                os.killpg(os.getpgid(server_proc.pid), signal.SIGTERM)
                server_proc.wait()

        # Parse client output
        avg_time, throughput, success, fail = self._parse_client_output(stdout)

        # Write to CSV
        with open(self.results_path, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                datetime.now().isoformat(),
                mode,
                server_pool,
                operation,
                volume,
                client_pool,
                avg_time,
                throughput,
                success,
                fail
            ])

        # Print formatted result
        self._print_formatted_result(
            mode, operation, volume, client_pool, server_pool,
            avg_time, throughput, success, fail
        )

    def _print_formatted_result(self,
                                mode: str,
                                operation: str,
                                volume: int,
                                client_pool: int,
                                server_pool: int,
                                avg_time: str,
                                throughput: str,
                                success: str,
                                fail: str) -> None:
        """
        Print a table header once, then each scenario result as a row.
        """
        if not self._print_header_once:
            header = (
                f"{'Mode':<8} | {'Op':<8} | {'Vol(MB)':<8} | "
                f"{'CliPool':<8} | {'SrvPool':<8} | {'Avg(s)':<8} | "
                f"{'Thrpt(Bps)':<12} | {'Suc/Fal':<8}"
            )
            separator = "-" * len(header)
            print("\n" + header)
            print(separator)
            self._print_header_once = True

        row = (
            f"{mode:<8} | {operation:<8} | {volume:<8} | "
            f"{client_pool:<8} | {server_pool:<8} | {avg_time:<8} | "
            f"{throughput:<12} | {success}/{fail:<8}"
        )
        print(row)

    def _parse_client_output(self, output: str):
        """
        Extract average time, throughput, success, and fail counts from client stdout.
        """
        avg_time = throughput = success = fail = '-'
        for line in output.splitlines():
            if 'Average Time/Client:' in line:
                avg_time = line.split(':')[-1].strip().split()[0]
            if 'Throughput/Client:' in line:
                throughput = line.split(':')[-1].strip().split()[0]
            if 'Success/Failure' in line:
                parts = line.split(':')[-1].strip().split('/')
                if len(parts) == 2:
                    success, fail = parts
        return avg_time, throughput, success, fail

    def run_all(self) -> None:
        """
        Iterate through all combinations of modes, operations, volumes,
        client pools, and server pools.
        """
        modes = ['thread', 'process']
        operations = ['upload', 'download', 'list']
        volumes = [10, 50, 100]
        client_pools = [1, 5, 50]
        server_pools = [1, 5, 50]

        total = (len(modes) * len(operations) * len(volumes) *
                 len(client_pools) * len(server_pools))
        count = 0

        try:
            for mode in modes:
                for operation in operations:
                    for volume in volumes:
                        for client_pool in client_pools:
                            for server_pool in server_pools:
                                count += 1
                                print(
                                    f"\nScenario {count}/{total}: "
                                    f"{mode=} {operation=} {volume=} "
                                    f"{client_pool=} {server_pool=}"
                                )
                                self.run_scenario(
                                    mode,
                                    server_pool,
                                    operation,
                                    volume,
                                    client_pool
                                )
        except KeyboardInterrupt:
            print('Exiting orchestrator.')
            sys.exit(0)


if __name__ == '__main__':
    orchestrator = StressTestOrchestrator()
    orchestrator.run_all()
