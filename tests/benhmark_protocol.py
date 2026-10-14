import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import socket
import threading
import time

from common.protocol.standard_lrc import StandardLRCProtocol
from common.protocol.line_delim import LineDelimitedProtocol

HOST = "127.0.0.1"
PORT = 9998
NUM_REQUESTS = 2000
PROTOCOLS = {
    'lrc': StandardLRCProtocol,
    'standard': StandardLRCProtocol,
    'standard_lrc': StandardLRCProtocol,
    'line': LineDelimitedProtocol,
    'line_delim': LineDelimitedProtocol,
    'line_delimited': LineDelimitedProtocol,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description='Ejecuta la comparación entre protocolos.',
        usage='python tests/benhmark_protocol.py [lrc|line]'
    )
    parser.add_argument(
        'protocol',
        nargs='?',
        choices=sorted(PROTOCOLS.keys()),
        help='Nombre del protocolo a probar. Si no se indica, compara los dos por defecto.'
    )
    parser.add_argument(
        '--protocol',
        dest='protocol_flag',
        choices=sorted(PROTOCOLS.keys()),
        help='Nombre del protocolo a probar. Si no se indica, compara los dos por defecto.'
    )
    args = parser.parse_args()
    return args.protocol_flag or args.protocol


def test_protocol(protocol_class, name):
    def run_server():
        proto = protocol_class()
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(1)

        conn, _ = srv.accept()
        try:
            for _ in range(NUM_REQUESTS):
                req = proto.receive_request(conn)
                proto.send_response(conn, "AUTH_OK#WS-01#Bienvenido")
        finally:
            conn.close()
            srv.close()

    def run_client(results):
        time.sleep(0.15)
        proto = protocol_class()
        cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cli.connect((HOST, PORT))

        try:
            t_ini = time.perf_counter()
            for i in range(NUM_REQUESTS):
                msg = f"AUTH#WS-{i:03d}#Parque Central"
                _ = proto.send_request(cli, msg)
            t_fin = time.perf_counter()

            total = t_fin - t_ini
            results['time'] = total
            results['latency'] = (total / NUM_REQUESTS) * 1000
            results['throughput'] = NUM_REQUESTS / total
        finally:
            cli.close()

    results = {}
    th_srv = threading.Thread(target=run_server)
    th_cli = threading.Thread(target=run_client, args=(results,))

    th_srv.start()
    th_cli.start()
    th_srv.join()
    th_cli.join()

    time.sleep(0.2)  # Pausa breve para liberar el puerto
    return results

if __name__ == "__main__":
    selected_protocol = parse_args()
    print(f"Iniciando comparativa con {NUM_REQUESTS} peticiones por protocolo...\n")
    print(f"Numero de peticiones: {NUM_REQUESTS}")

    if selected_protocol is None:
        res_lrc = test_protocol(StandardLRCProtocol, "LRC (Estándar)")
        res_line = test_protocol(LineDelimitedProtocol, "Line Delimited")

        print("=" * 68)
        print(f"{'PROTOCOLO':<22} | {'TIEMPO':<10} | {'LATENCIA':<12} | {'THROUGHPUT'}")
        print("=" * 68)
        print(f"{'1. Standard LRC':<22} | {res_lrc['time']:<7.4f} s | {res_lrc['latency']:<9.4f} ms | {res_lrc['throughput']:<8.2f} req/s")
        print(f"{'2. Line Delimited':<22} | {res_line['time']:<7.4f} s | {res_line['latency']:<9.4f} ms | {res_line['throughput']:<8.2f} req/s")
    else:
        protocol_class = PROTOCOLS[selected_protocol]
        res_selected = test_protocol(protocol_class, selected_protocol)
        print("=" * 68)
        print(f"{'PROTOCOLO':<22} | {'TIEMPO':<10} | {'LATENCIA':<12} | {'THROUGHPUT'}")
        print("=" * 68)
        print(f"{selected_protocol:<22} | {res_selected['time']:<7.4f} s | {res_selected['latency']:<9.4f} ms | {res_selected['throughput']:<8.2f} req/s")
    print("=" * 68)