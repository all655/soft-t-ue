import itertools
import sys
import threading
import time
import os
import pathlib
import argparse
import socket

import tailer


# add the common directory to the import path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

from core_interface import CoreNetwork
from gnb_interface import Gnb
from common.iperf_interface import Iperf


class gnb_controller:
    def start(self, gnb_config_str):
        # connect to ue controller

        # recieve configuration

        # start gnb and core
        self.core_handle = CoreNetwork()
        self.core_handle.start()
        self.spinner_loading(self.core_handle)

        print("\n\nCore Started Successfully!")
        print("Starting gNB...")

        self.gnb_handle = Gnb()
        self.gnb_handle.start([gnb_config_str])

        # sending metrics
        self.gnb_logs_process = threading.Thread(
            target=self.get_gnb_logs).start()
        # stop gnb, core, metrics, etc
        # run a variation of main without calling ue_controller

    def get_gnb_logs(self):
        for line in tailer.follow(open("/tmp/gnb.log")):
            # TODO: Fix this poor handling of the output.
            print(line)

    def spinner_loading(self, handle, verbose=True):
        spinner = itertools.cycle(["|", "/", "-", "\\"])
        while not handle.initialized:
            if verbose:
                sys.stdout.write(handle.output + "\n\n" + 50 * "=" + "\n")
            sys.stdout.write(f"{handle.name} " + next(spinner))
            sys.stdout.flush()
            sys.stdout.write("\b")
            time.sleep(0.1)

def parse():
    current_script_path = pathlib.Path(__file__).resolve()
    repo_root = current_script_path.parent.parent.parent
    code_root = repo_root.parent
    parser = argparse.ArgumentParser(
        description="Run an srsRAN gNB and Open5GS, then send metrics to the ue_controller")
    parser.add_argument(
        "--gnb_config",
        type=pathlib.Path,
        default=repo_root / "configs" / "zmq" / "gnb_zmq.yaml",
        help="Path of the gNB config file")
    parser.add_argument('--ip', type=str, help='IP address to listen for commands', default="127.0.0.1")
    parser.add_argument('--port', type=int, help='Port to listen for commands', default="5000")
    return parser.parse_args()

def create_iperf_handles(server_socket, add_callback):
    while True:
        client_socket, _ = server_socket.accept()
        command = client_socket.recv(1024).decode('utf-8').strip()
        client_socket.close()

        iperf_process = Iperf()
        if int(command):
            iperf_process.start(["-s", "-i", "1", "-p", command], process_type="server")
            add_callback(iperf_process)


def main():
    args = parse()
    print(args)
    os.system("sudo kill -9 $(ps aux | awk '!/gnb_controller\.py/ && /gnb/{print $2}')")
    os.system("sudo kill -9 $(ps aux | awk '/open5gs/{print $2}')")
    time.sleep(0.1)
    controller = gnb_controller()
    controller.start(str(args.gnb_config))

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((args.ip, args.port))
    server_socket.listen(1)

    iperf_servers = []

    handle_thread = threading.Thread(target=create_iperf_handles, args=(server_socket, lambda x: iperf_servers.append(x)), daemon=True)
    handle_thread.start()

    while controller.gnb_handle.isRunning and controller.core_handle.isRunning:
        time.sleep(0.5)
        print(f"\n\n{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}\n")
        # Core Network Logs
        print(f"✨ {controller.core_handle}")
        core_end = '\n\t'.join(controller.core_handle.output.split('\n')[-5:])
        print(f"\t{core_end}\n\n")
        # GNB Logs
        print(f"✨ {controller.gnb_handle}")
        #  Iperf Server Logs
        for proc in iperf_servers:
            print(f"✨ {proc}")
            print('\t' + '\t'.join(proc.output[-5:]))

    return 0

if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
