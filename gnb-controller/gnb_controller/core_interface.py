from utils import start_subprocess, kill_subprocess
import threading
import time

class CoreNetwork:
    def __init__(self):
        self.isRunning = False
        self.process = None
        self.output = ""

    def start(self):
        command = ["sudo", "docker","compose","-f", "/opt/srsRAN_Project/docker/docker-compose.yml","up", "--build", "5gc"]
        self.process = start_subprocess(command)
        self.isRunning = True

        self.log_thread = threading.Thread(target=self.collect_logs, daemon=True)
        self.log_thread.start()

    def stop(self):
        kill_subprocess(self.process)
        self.isRunning = False

    def collect_logs(self):
        while self.isRunning:
            if self.process:
                line = self.process.stdout.readline()
                if line:
                    self.output += '\n' + line.decode().strip()
            else:
                self.output += "Process Terminated"
                break

    def __repr__(self):
        return f"srsRAN gNB object, running: {self.isRunning}"
