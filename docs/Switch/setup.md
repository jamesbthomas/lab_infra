# Setting up the Switch

This document describes the manual steps needed to setup the core switch for the lab environment.
It includes the following major steps:
0) Setting up the management pi for console access to the switch
1) Power On and Validate
2) Setup Ansible for serial management
3) Ansible Bootstrap
4) Hardening

See [Upgrade](upgrade.md) for additional details on how to upgrade the iOS on the switch.

## Disclaimer

The current lab hardware is old and does not support some modern crypto implementations, including Ciscoo crypto modules provided via the `k9` IOS images. This guide will be updated to account for cryptographic options and additional remote management possibilities once the hardware supports it. Until then, we'll reduce the switch's attack surface by not enabling any kind of remote management and instead use the serial console for all of the administrative tasks.

# Step 0) Enable console access via the management pi

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

# Step 1) Prep and Setup

This step is pretty self-explanatory, but still important. Before you get too deep into the configurations and cabling, make sure you check the following:
- Do you have a USB to Serial (aka, USB-to-DB9) cable? Is it plugged into the console port on your switch?
- Does the switch have power? Does it POST correctly?

Once your switch is powered on and running, go back to your serial terminal and make sure you get a prompt for your switch (usually indicated by something like `<switch hostname>>`).

Once all of that is good, you can use the command `show version` to check the current version of the OS on your switch, and determine if you need to follow the steps in [this document](upgrade.md) to upgrade to a more recent version.

## Recommendation and Password Recovery

I also recommend running `write erase` and `reload` at this stage - it will wipe any existing configurations from the switch, allowing you to start with a clean slate.

However, you will need to be at an `enable` prompt on your switch - a privileged mode that allows you to change the configuration. Most factory devices will have a default password, or you can check out [this guide](https://www.cisco.com/c/en/us/support/docs/switches/catalyst-4000-series-switches/21229-pswdrec-cat4000-supiii-21229.html?utm_source=chatgpt.com) for more details.

# Step 2) Setup ansible over serial

Since we're using serial instead of ssh for configuration activities, we'll have to be a little creative.

Ansible assumes ssh by default, but we can still configure the Ansible to run the command locally can call a script which integrates better with the serial connection.

This is a little bit backwards - one of the valuable parts of ansible is that it can be used to remotely manage almost anything, and we could just run the other scripts directly - but by forcing everything into ansible constructs, it makes it so that the administrative process remains the same, even if the underlying hardware (or approach) changes.

There are three key pieces:
- An ansible inventory that stays local
- A playbook that uses the "expect" block that can handle the escalation request from the switch
- A Python script that writes the commands to the serial device

# Step 3) Write the bootstrap playbook



# Step 4) Write the ansible hardening playbook

