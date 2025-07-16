# This script is called by an Ansible playbook
## It takes a command or set of commands as input, and sends them to the serial device

import serial # For communicating with the switch over serial
import sys # For pulling arguments off the command line
import json # For processing the commands file that ansible generates
import time # To ensure space between commands to match serial behavior

def main():
  if len(sys.argv) != 4:
    print("Usage: send_config.py <serial device> <baud rate> <commands_json>")
    sys.exit(1)

  # Grab the inputs from the command line
  serial_dev = sys.argv[1]
  baud_rate = int(sys.argv[2])
  commands_json = sys.argv[3]

  # Expand the commands to something we can use
  with open(commands_json) as f:
    commands = json.load(f)

  with serial.Serial(serial_dev,baud_rate,timeout=2) as ser:
    # Give the connection time to set and wake the switch
    time.sleep(1)

    ser.write(("\r\n").encode())
    time.sleep(1)
    ser.write(("terminal length 0\n").encode())
    current = ser.readline()
    while current:
      current = ser.readline()

    for command in commands:
      cmd = command["command"]
      expected = command["expect"]
      # Send the command
      ser.write((cmd+"\n").encode())
      time.sleep(0.5)
      # Grab the response
      out = []
      current = ser.readline()
      while current:
        if current.decode().strip() != "":
          out.append(current.decode().strip())
        current = ser.readline()
      print(f"Command: {out[0]}")
      response = "\n".join(out[1:-1])
      print(f"Response: {response}\n")
      if response != expected:
        print(f"FAIL - expected '{expected}' got '{response}'")
      time.sleep(0.5)

if __name__ == "__main__":
  main()
