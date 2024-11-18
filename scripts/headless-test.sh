#!/bin/bash

# Check if the script is run as root
if [ "$EUID" -ne 0 ]; then
	echo "This script must be run as root."
	exit 1
fi

SCRIPT_PATH=$(realpath "$0")
SCRIPT_DIR=$(dirname $SCRIPT_PATH)
GNB_CONFIG=$SCRIPT_DIR/../configs/zmq/gnb_zmq.yaml
UE_CONFIG=$SCRIPT_DIR/../configs/zmq/ue_zmq.conf

CORE_SESSION_NAME="5gc"
CORE_SESSION_COMMAND="docker compose -f /opt/srsRAN_Project/docker/docker-compose.yml up --build 5gc"
CORE_SESSION_LOG="/tmp/headless_5gc.log"

GNB_SESSION_NAME="gnb"
GNB_SESSION_COMMAND="gnb -c $SCRIPT_DIR/../configs/zmq/gnb_zmq.yaml"
GNB_SESSION_LOG="/tmp/headless_gnb.log"

UE_SESSION_NAME="ue"
UE_SESSION_COMMAND="srsue $SCRIPT_DIR/../configs/zmq/ue_zmq.conf $@"
UE_SESSION_LOG="/tmp/headless_ue.log"

rm -rf $UE_SESSION_LOG $CORE_SESSION_LOG $GNB_SESSION_LOG

kill_existing_screen() {
	local session_name=$1
	if screen -list | grep -q "$session_name"; then
		screen -S "$session_name" -X quit
		if [ $? -ne 0 ]; then
			echo "Failed to kill existing screen session '$session_name'."
			return 1
		fi
	fi
	return 0
}

stop_script() {
	kill_existing_screen "$UE_SESSION_NAME"
	kill_existing_screen "$GNB_SESSION_NAME"
	kill_existing_screen "$CORE_SESSION_NAME"
	screen -wipe
	ps aux | awk '/open/{print $2}' | while read -r pid; do kill -9 $pid; done
	ps aux | awk '/srsue/{print $2}' | while read -r pid; do kill -9 $pid; done
	ps aux | awk '/gnb/{print $2}' | while read -r pid; do kill -9 $pid; done
}

start_screen_session() {
	local session_name=$1
	local command=$2
	local log_file=$3
	screen -dmS "$session_name" bash -c "$command > $log_file 2>&1"
	if [ $? -ne 0 ]; then
		echo "Failed to start screen session '$session_name'."
		return 1
	fi
	return 0
}

await_log() {
	MAX_RETRIES=$3
	while ((1)); do
		if grep -q "$2" "$1"; then
			break
		fi

		if ((retries > MAX_RETRIES)); then
			echo "log $2 not found in $1"
			stop_script
			exit 1
		fi

		sleep 2
		((retries++))
	done
}

ip netns add ue1 >/dev/null 2>&1

start_screen_session "$CORE_SESSION_NAME" "$CORE_SESSION_COMMAND" "$CORE_SESSION_LOG"
CORE_STATUS=$?

await_log $CORE_SESSION_LOG "NF registered" 30

start_screen_session "$GNB_SESSION_NAME" "$GNB_SESSION_COMMAND" "$GNB_SESSION_LOG"
GNB_STATUS=$?

sleep 1

start_screen_session "$UE_SESSION_NAME" "$UE_SESSION_COMMAND" "$UE_SESSION_LOG"
UE_STATUS=$?

# Check if both sessions were started successfully
if [ $CORE_STATUS -ne 0 ] || [ $GNB_STATUS -ne 0 ] || [ $UE_STATUS -ne 0 ]; then
	echo "Failed to start screens"
	stop_script
	exit 1
fi

screen -ls

await_log "$UE_SESSION_LOG" "PDU Session Establishment successful" 20

stop_script
exit 0
