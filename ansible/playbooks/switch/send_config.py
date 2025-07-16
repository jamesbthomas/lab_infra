# This script is called by an Ansible playbook
## It takes a command or set of commands as input, and sends them to the serial device

import serial
import time


def send_config(commands):
  with serial.Serial('/dev/ttyUSB0',9600,timeout=1) as ser:
    # Set the commands you want to run in this playbook
    cmds = [
      "enable\n",
      "configure terminal\n",
      # Insert commands here
      "exit\n"
    ]

    for cmd in cmds:
      ser.write(cmd.encode())
      time.sleep(1)

if __name__ == "__main__":
  # How to get the commands from ansible?
