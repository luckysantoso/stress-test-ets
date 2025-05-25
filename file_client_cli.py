# file_client_cli.py

"""
Client-side utilities for sending commands to the file server.
"""

import base64
import json
import logging
import os
import socket

from typing import Any, Dict, Tuple

# Server configuration
SERVER_HOST = '172.16.16.101'
SERVER_PORT = 7000
SERVER_ADDRESS: Tuple[str, int] = (SERVER_HOST, SERVER_PORT)

# Networking constants
BUFFER_SIZE = 1_048_576
SOCKET_TIMEOUT = 60

# Logging configuration
logging.basicConfig(level=logging.ERROR, format='[%(levelname)s] %(message)s')


def send_command(command: str = '') -> Dict[str, Any]:
    """
    Send a raw command string to the server and return the parsed JSON response.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(SOCKET_TIMEOUT)

    try:
        sock.connect(SERVER_ADDRESS)
        logging.warning(f'Connecting to {SERVER_ADDRESS}')
        sock.sendall(command.encode())

        data_buffer = ''
        while True:
            try:
                chunk = sock.recv(BUFFER_SIZE)
            except socket.timeout:
                logging.error('Receive timeout')
                return {'status': 'ERROR', 'data': 'timeout during receive'}

            if not chunk:
                break

            decoded = chunk.decode()
            data_buffer += decoded

            if '\r\n\r\n' in decoded:
                data_buffer = data_buffer.split('\r\n\r\n', 1)[0]
                break

        return json.loads(data_buffer)

    except socket.timeout:
        logging.error('Socket operation timed out')
        return {'status': 'ERROR', 'data': 'timeout during connect/send'}
    except Exception as err:
        logging.warning(f'Error during communication: {err}')
        return {'status': 'ERROR', 'data': str(err)}
    finally:
        sock.close()


def remote_list() -> bool:
    """
    Request the list of files from the server and log them.
    """
    response = send_command('LIST\n')
    if response.get('status') == 'OK':
        logging.info('Files on server:')
        for filename in response.get('data', []):
            logging.info(f'- {filename}')
        return True

    logging.error(f"Error listing files: {response.get('data')}")
    raise RuntimeError(response.get('data', 'Unknown error'))


def remote_get(filename: str) -> bool:
    """
    Download a file from the server by name.
    """
    response = send_command(f'GET {filename}\n')
    if response.get('status') != 'OK':
        logging.error(f"Error getting file: {response.get('data')}")
        raise RuntimeError(response.get('data', 'Unknown error'))

    file_name = response.get('data_namafile', filename)
    file_data_b64 = response.get('data_file', '')
    file_bytes = base64.b64decode(file_data_b64)

    try:
        # Write to disk if needed:
        # with open(file_name, 'wb') as f:
        #     f.write(file_bytes)
        pass
    except Exception as err:
        logging.error(f'Error writing file: {err}')
        return False

    return True


def remote_upload(filepath: str) -> bool:
    """
    Upload a local file to the server.
    """
    if not os.path.isfile(filepath):
        logging.error(f'File not found: {filepath}')
        raise FileNotFoundError(f'File not found: {filepath}')

    with open(filepath, 'rb') as f:
        encoded_data = base64.b64encode(f.read()).decode()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(SOCKET_TIMEOUT)

    try:
        sock.connect(SERVER_ADDRESS)
        sock.sendall('UPLOAD\n'.encode())

        try:
            handshake = sock.recv(BUFFER_SIZE).decode().strip()
        except socket.timeout:
            logging.error('Handshake receive timeout')
            raise RuntimeError('Timeout during upload handshake')

        if 'READY' not in handshake:
            logging.error('Server not ready for upload')
            raise RuntimeError('Server not ready for upload')

        # Send data in chunks
        for i in range(0, len(encoded_data), BUFFER_SIZE):
            chunk = encoded_data[i:i + BUFFER_SIZE]
            try:
                sock.sendall((chunk + '\n').encode())
            except socket.timeout:
                logging.error('Upload send timeout')
                raise RuntimeError('Timeout during file upload')

        # Signal end of upload
        sock.sendall('ENDUPLOAD\n'.encode())

        try:
            final_resp = sock.recv(BUFFER_SIZE).decode().strip()
        except socket.timeout:
            logging.error('Final response timeout')
            raise RuntimeError('Timeout during upload final response')

        logging.info(f'Final response: {final_resp}')
        return True

    except Exception as err:
        logging.error(f'Error during upload: {err}')
        raise
    finally:
        sock.close()


def remote_delete(filename: str) -> bool:
    """
    Delete a file on the server by name.
    """
    response = send_command(f'DELETE {filename}\n')
    if response.get('status') == 'OK':
        logging.warning('File deleted successfully')
        return True

    logging.warning('Failed to delete file')
    return False


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    remote_list()
    remote_get('file_100mb.bin')
