# server_pool_launcher.py

"""
Launch multiple file-server instances in either thread-pool or process-pool mode.
"""

import argparse
import multiprocessing
import signal
import sys

from file_server import ProcessServer, ThreadedServer


def run_threaded_server(port: int, worker_count: int) -> None:
    """
    Start a ThreadedServer on the given port with a pool of worker threads.
    """
    server = ThreadedServer(host='0.0.0.0', port=port, max_workers=worker_count)
    server.serve_forever()


def run_process_server(port: int) -> None:
    """
    Start a ProcessServer on the given port (in its own process).
    """
    server = ProcessServer(host='0.0.0.0', port=port)
    server.serve_forever()


def main() -> None:
    """
    Parse CLI arguments and launch servers accordingly.
    """
    parser = argparse.ArgumentParser(
        description='Run file-server in thread or process pool mode.'
    )
    parser.add_argument(
        '--mode',
        choices=['thread', 'process'],
        required=True,
        help='Concurrency mode for server.'
    )
    parser.add_argument(
        '--pool',
        type=int,
        required=True,
        help='Number of threads or processes in the pool.'
    )
    parser.add_argument(
        '--base-port',
        type=int,
        default=7000,
        help='Starting port number for servers.'
    )
    args = parser.parse_args()

    def _graceful_shutdown(signum, frame) -> None:
        print('Shutting down gracefully.')
        sys.exit(0)

    signal.signal(signal.SIGINT, _graceful_shutdown)
    signal.signal(signal.SIGTERM, _graceful_shutdown)

    if args.mode == 'thread':
        run_threaded_server(args.base_port, args.pool)
    else:
        processes: list[multiprocessing.Process] = []
        for i in range(args.pool):
            port = args.base_port + i
            process = multiprocessing.Process(
                target=run_process_server,
                args=(port,),
            )
            process.start()
            print(f"[LAUNCHER] Started process server pid={process.pid} on port {port}")
            processes.append(process)

        try:
            for process in processes:
                process.join()
        except KeyboardInterrupt:
            print('Terminating all server processes...')
            for process in processes:
                process.terminate()
            for process in processes:
                process.join()
            sys.exit(0)


if __name__ == '__main__':
    main()
