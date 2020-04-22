import socket
import time
import importlib.util
START = int(round(time.time() * 1000))


def run_client():
    with socket.create_connection(('127.0.0.1', 5500)) as server:
        start_mes = f'{{"stamp": {START}, "lang": "Python"}}'
        server.sendall(start_mes.encode())
        while True:
            path = server.recv(1024).decode()
            if path == 'CLOSE_CONNECTION':
                break

            name = path[path.rfind('/') + 1:]
            spec = importlib.util.spec_from_file_location(name, path)
            script = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(script)

            start = int(round(time.time() * 1000))
            start_mes = f'{{"stamp": {start}, "type": "start"}}'
            server.sendall(start_mes.encode())

            result: str = script.run()

            finish = int(round(time.time() * 1000))
            job_mes = f'{{"stamp": {finish}, "type": "finish", "result": "{result}"}}'
            server.sendall(job_mes.encode())
        server.close()


run_client()
