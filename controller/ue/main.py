import argparse
import os
os.environ["KIVY_NO_ARGS"] = "1"
from kivy.config import Config
Config.set('kivy', 'log_enable', 1)
Config.set('kivy', 'log_dir', '.')
Config.set('kivy', 'log_level', 'error')
Config.set('kivy', 'log_name', 'run.log')
Config.set('kivy', 'fullscreen', 1)
Config.write()

import pathlib
import sys
import time
import uuid
import logging
import yaml

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

from kivy.logger import Logger



from MainApp import MainApp
from SharedState import SharedState
from Ue import Ue

from common.utils import send_command


def parse():
    script_dir = pathlib.Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Run an srsRAN gNB and Open5GS, then send metrics to the ue_controller")
    parser.add_argument(
        "--config",
        type=pathlib.Path,
        default=script_dir.parent.parent / "configs" / "basic_ue_zmq.yaml",
        help="Path of the controller config file")
    parser.add_argument(
        "--gnb_config",
        type=pathlib.Path,
        default=script_dir.parent.parent / "configs" / "zmq" / "gnb_zmq.yaml",
        help="Path of the controller config file")
    parser.add_argument('--ip', type=str, help='IP address of the gNB', default="127.0.0.1")
    parser.add_argument('--port', type=int, help='Port of the gNB', default="5000")
    return parser.parse_args()



def main():
    os.system("sudo kill -9 $(ps aux | awk '/srsue/ && !/main/{print $2}') > /dev/null 2>1&")
    args = parse()
    SharedState.cli_args = args


    options = None
    with open(str(args.config), 'r') as file:
        options = yaml.safe_load(file)

    if options.get("gnb", False):
        send_command(args.ip, args.port,
                     {"target": "gnb",
                      "action": "start",
                      "config": options.get('gnb')['config']}
                     )
    else:
        send_command(args.ip, args.port,
                     {"target": "gnb",
                      "action": "start",
                      "config": str(args.gnb_config)}
                     )
    SharedState.ue_index = 1

    for namespace in options.get("namespaces", []):
        os.system(f"sudo ip netns add {namespace['name']} > /dev/null 2>&1")

    time.sleep(0.5)

    for ue in options.get("processes", []):
        if not os.path.exists(ue["config_file"]):
            print(f"Error: File not found {ue['config_file']}")
            return 1
        new_ue = Ue(SharedState.ue_index)
        if ue['type'] == "tester":
            new_ue.start([ue["config_file"]] + ue["args"].split(" "))
        else:
            new_ue.start([ue["config_file"]])
        SharedState.process_list.append({
            'id': str(uuid.uuid4()),
            'type': ue['type'],
            'config': ue['config_file'],
            'handle': new_ue,
            'index': SharedState.ue_index
        })
        SharedState.ue_index += 1


    print(f"Running as: {os.getlogin()}")
    MainApp().run()
    return 0

if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
