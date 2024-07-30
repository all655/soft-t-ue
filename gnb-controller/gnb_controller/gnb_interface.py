import threading
import time

from utils import kill_subprocess, start_subprocess


class Gnb:
    def __init__(self):
        self.isRunning = False
        self.process = None
        self.output = ""
        self.initialized = False
        self.name = "srsRAN gNB"

    def start(self, args):
        command = ["sudo", "gnb", "-c"] + args
        self.process = start_subprocess(command)
        self.isRunning = True

        self.log_thread = threading.Thread(target=self.collect_logs,
                                           daemon=True)
        self.log_thread.start()
        time.sleep(5)
        self.initialized = True

    def stop(self):
        kill_subprocess(self.process)
        self.isRunning = False

    def collect_logs(self):
        while self.isRunning:
            if self.process:
                line = self.process.stdout.readline()
                if line:
                    self.output += "\n" + line.decode().strip()
            else:
                self.output += "Process Terminated"
                break

    def __repr__(self):
        return f"srsRAN gNB object, running: {self.isRunning}"
