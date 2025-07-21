# Setting up the Switch

This document describes the manual steps needed to setup the core switch for the lab environment.
It includes the following major steps:
1) Setting up the management pi for console access to the switch
2) Power On and Validate
3) Setup Ansible for serial management
4) Ansible Bootstrap
5) Hardening

See [Upgrade](upgrade.md) for additional details on how to upgrade the iOS on the switch.

## Disclaimer

The current lab hardware is old and does not support some modern crypto implementations, including Ciscoo crypto modules provided via the `k9` IOS images. This guide will be updated to account for cryptographic options and additional remote management possibilities once the hardware supports it. Until then, we'll reduce the switch's attack surface by not enabling any kind of remote management and instead use the serial console for all of the administrative tasks.

# Step 1) Enable console access via the management pi

First and foremost - make sure you have a serial terminal softare installed. Common examples include `screen` and `minicom` - if you used the init script in this repository, then you should have already installed `minicom`.

Next, identify the serial device that you're using with the following command:
```
dmesg | grep ttyUSB
```

You should get output that includes something like `/dev/ttyUSB<some number>`. The command searches your system logs to find a message that has to do with the `ttyUSB` device class, which (ideally) will only pull up the log message indicating that a serial controller was attached, and which device location it's available at.

My message looked like this:
```
[<relative timestamp>] usb 1-1.1.3: FTDI USB Serial Device Converter now attached to ttyUSB<number>
```

The `<number>` in the output is the key value we're looking for. We need to pass that value to the serial terminal software so that we can connect to the switch.

If you're using minicom, your command will look like this:
```
sudo minicom -D /dev/ttyUSB<the number you saw> -b 9600
```
-D tells minicom to use the specific device to connect, and -b tells minicom the bitrate to use for the serial connection. 9600 is generally the default, but it's an important setting. Also known as the baud rate, if this number is wrong between your terminal (the management pi and the serial terminal software) and the device (the switch), you'll see garbled data, complete communication failure, system instability, or even buffer overflows. This is because serial communications rely on precise timing to synchronize data transfer: each end of the connection needs to send and receive bits at the same rate.

For the hardware-inclined folks reading this, you can check out [this article](https://www.botasys.com/post/baud-rate-guide) for more details on the baud rate, how to calculate it, how to select or evaluate a baud rate, troubleshooting steps, and best practices.

# Step 2) Prep and Setup

This step is pretty self-explanatory, but still important. Before you get too deep into the configurations and cabling, make sure you check the following:
- Do you have a USB to Serial (aka, USB-to-DB9) cable? Is it plugged into the console port on your switch?
- Does the switch have power? Does it POST correctly?

Once your switch is powered on and running, go back to your serial terminal and make sure you get a prompt for your switch (usually indicated by something like `<switch hostname>>`).

Once all of that is good, you can use the command `show version` to check the current version of the OS on your switch, and determine if you need to follow the steps in [this document](upgrade.md) to upgrade to a more recent version.

## Recommendation and Password Recovery

I also recommend running `write erase` and `reload` at this stage - it will wipe any existing configurations from the switch, allowing you to start with a clean slate.

However, you will need to be at an `enable` prompt on your switch - a privileged mode that allows you to change the configuration. Most factory devices will have a default password, or you can check out [this guide](https://www.cisco.com/c/en/us/support/docs/switches/catalyst-4000-series-switches/21229-pswdrec-cat4000-supiii-21229.html?utm_source=chatgpt.com) for more details.

# Step 3) Setup ansible over serial

Since we're using serial instead of ssh for configuration activities, we'll have to be a little creative.

Ansible assumes ssh by default, but we can still configure the Ansible to run the command locally can call a script which integrates better with the serial connection.

This is a little bit backwards - one of the valuable parts of ansible is that it can be used to remotely manage almost anything, and we could just run the other scripts directly - but by forcing everything into ansible constructs, it makes it so that the administrative process remains the same, even if the underlying hardware (or approach) changes.

There are three key pieces:
- An ansible inventory that stays local
- A playbook that uses the "expect" block that can handle the escalation request from the switch
- A Python script that writes the commands to the serial device

For simplicity, we're going to focus on the ansible inventory and Python script, plus a simplified version of the playbook that validates everything works correctly. The swtch does not issue an authentication request at this stage, since it hasn't been configured to do so, so we'll focus on getting the framework setup to run the configuration via ansible.

## Inventory

The inventory entry for the switch will be pretty simple; it's just one line that tell ansible to run the playbook locally.

```
[switch_console]  ## This should match what you want to put in your playbooks under the host item
local_console ansible_connection=local
```

## Python Script

For a full version of the script, see [Send_Config.py](../../ansible/playbooks/switch/send_config.py).

The script takes 3 arguments as input:
- serial_dev - the serial device to send the commands through
- baud_rate - the baud rate to use with the serial device
- commands_json - a path to a file containinig the commands and expected responses from each command in JSON format

A couple of important foot stomps on this script:
- Sleep is important: Serial connections aren't as state-aware as, say, a TCP connection. There's reading a serial response doesn't necessarily wait for a response, it just reads and moves on, so ensuring there's enough time between commands helps stabilize the entire playbook.
- Wake and Set the Terminal Length: the first thing to do once the serial connection is opened is wake up the device at the other end, usually by sending a new line character (`serial.write("\r\n").encode())`). Next, especially so for Cisco devices, you'll want to set the terminal length to 0 (`terminal length 0`), telling the device at the other end to return output immediately, instead of waiting for an entire page to become available.
- Filtering the return values: The script reads every line until it hit a blank line, which includes the command that was run, the response to the command (if there is one), and the prompt for the next command. You can see my implementation of logic to filter the content read from the serial link in the `while` loop of the script.

## Simplified Playbook

As discussed above, we also need a simplified playbook that can show that everything is working end-to-end. This also works as a template for future playbooks that need to use the serial connection, as it includes all of the major functionality minus the `expect` item for the escalation challenge.

See [serial_config_template.yaml](../../ansible/playbooks/switch/serial_config_template.yaml).

A couple of footstomps here:
- The `hosts` entry - this shoul match what you put between the square brackets in your inventory, otherwise you'll end up running the playbook on a device that you don't want to.
- The `vars` section - this section, and specifically the `switch_commands` variable, sets the commands and expected return values.
  - A couple of notes here:
    - If the command does not generate any output, you still have to put `''` for the script to evaluate correctly.
    - Especially when changing context (like with the `end` or `exit` commands), be sure you check your output manually first. Responses might come out of order, and the current logic does not do a very good job of handling these edge cases.
- Creating the json file - this **must** always be the first task in the playbook, as it creates the file that gets passed into the script that tells it what commands to run
- The `{{ playbook_dir }}` variable - this is a special variable that ansible generates at run time that's really useful for calling something in the same directory as the playbook. It includes the absolute path to the playbook being run, which is conveniently also the same directory as the `send_config.py` script.

# Step 4) Write the bootstrap playbook

Now that we've got a template playbook and validated that we can send configuraton commands to the switch over serial, let's go ahead and write the bootstrap playbook that sets up the initial configurations for the switch.

# Step 5) Write the ansible hardening playbook

