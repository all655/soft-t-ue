import threading
import time
import os
import sys
import select
import socket


parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

from common.utils import start_subprocess, kill_subprocess, send_command
from common.Iperf import Iperf
from common.Ping import Ping


class Ue:
    def __init__(self, ue_index):
        self.ue_index = ue_index
        self.isRunning = False
        self.isConnected = False
        self.process = None
        self.iperf_client = Iperf()
        self.ping_client = Ping()
        self.output = ""

    def start(self, args):
        command = ["sudo", "srsue"] + args
        self.process = start_subprocess(command)
        self.isRunning = True
        self.stop_thread = threading.Event()
        self.log_thread = threading.Thread(target=self.collect_logs, daemon=True)
        self.log_thread.start()
    
    def start_metrics(self):
        print(f"Starting UE {self.ue_index} metrics")
        send_command("127.0.0.1", 5000, "iperf:" + str(5000 + self.ue_index))
        os.system(f"sudo ip netns add ue{self.ue_index}")
        os.system("sudo ip ro add 10.45.0.0/16 via 10.53.1.2")
        os.system(f"sudo ip netns exec ue{self.ue_index} ip ro add default via 10.45.1.1 dev tun_srsue")
        self.iperf_client.start(['-c', '10.53.1.1','-i', '1', '-t', '3000', '-u', '-b', '100M', '-R', '-p', str(5000 + self.ue_index)], process_type='client', ue_index=self.ue_index)
        self.ping_client.start(['10.53.1.1'])


    def stop(self):
        self.stop_thread.set()
        kill_subprocess(self.process)
        self.iperf_client.stop()
        self.isRunning = False

    def collect_logs(self):
        while self.isRunning and not self.stop_thread.is_set():
            if self.process:
                line = self.process.stdout.readline()
                if line:
                    self.output += line
                    if "PDU" in line:
                        self.start_metrics()
                        self.isConnected = True
            else:
                self.output += "Process Terminated"
                self.isRunning = False
                break

    def __repr__(self):
        return f"srsRAN UE{self.ue_index} object, running: {self.isRunning}"
