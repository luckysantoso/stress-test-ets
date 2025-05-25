"""
Concurrent file server supporting both thread-pool and process-pool modes.
"""

import base64
import logging
import os
import socket
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

from file_protocol import FileProtocol

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

BUFFER_SIZE = 1_048_576
TMP_DIR = tempfile.gettempdir()
protocol = FileProtocol()


def log_handler_start() -> None:
    """
    Log the current process ID and thread ID when a handler starts.
    """
    pid = os.getpid()
    thread_id = threading.get_ident()
    logging.info(f"[HANDLER-START] pid={pid} thread_id={thread_id}")


class ClientHandler(threading.Thread):
    """
    Handle a single client connection in its own thread.
    """

    def __init__(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        super().__init__()
        self.conn = conn
        self.addr = addr

    def run(self) -> None:
        log_handler_start()

        buffer = ''
        uploading = False
        temp_file = None
        temp_path = ''

        try:
            while True:
                data = self.conn.recv(BUFFER_SIZE)
                if not data:
                    break

                buffer += data.decode()
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()

                    if uploading:
                        if line == 'ENDUPLOAD':
                            temp_file.close()
                            response = protocol.proses_string(f'UPLOAD {temp_path}')
                            self._send_response(response)
                            os.remove(temp_path)
                            uploading = False
                            temp_file = None
                            temp_path = ''
                        else:
                            temp_file.write(base64.b64decode(line))
                        continue

                    if line.startswith('UPLOAD'):
                        uploading = True
                        temp_file = tempfile.NamedTemporaryFile(
                            delete=False,
                            dir=TMP_DIR
                        )
                        temp_path = temp_file.name
                        self._send_response('READY TO RECEIVE FILE')
                        continue

                    response = protocol.proses_string(line)
                    self._send_response(response)

        except Exception as err:
            logging.error(f"Error handling client {self.addr}: {err}")
            error_msg = f'{{"status":"ERROR","data":"{err}"}}'
            self._send_response(error_msg)
        finally:
            if temp_file and not temp_file.closed:
                temp_file.close()
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            self.conn.close()

    def _send_response(self, message: str) -> None:
        """
        Append protocol terminator and send the response to the client.
        """
        payload = f"{message}\r\n\r\n"
        self.conn.sendall(payload.encode())


class ThreadedServer:
    """
    File server using a pool of worker threads.
    """

    def __init__(
        self,
        host: str = '0.0.0.0',
        port: int = 7000,
        max_workers: int = 5
    ) -> None:
        self.address = (host, port)
        self.max_workers = max_workers

    def serve_forever(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(self.address)
        sock.listen(100)

        logging.info(
            f"[THREAD-SERVER] pid={os.getpid()} serving at {self.address} "
            f"with {self.max_workers} threads"
        )

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while True:
                conn, addr = sock.accept()
                executor.submit(ClientHandler(conn, addr).run)


class ProcessServer:
    """
    File server that spawns a new thread per client inside its own process.
    """

    def __init__(self, host: str = '0.0.0.0', port: int = 7000) -> None:
        self.address = (host, port)

    def serve_forever(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(self.address)
        sock.listen(100)

        logging.info(
            f"[PROC-SERVER] pid={os.getpid()} serving at {self.address}"
        )

        while True:
            conn, addr = sock.accept()
            logging.info(f"[PROC-ACCEPT] parent_pid={os.getpid()} spawning handler")
            handler = ClientHandler(conn, addr)
            handler.start()
