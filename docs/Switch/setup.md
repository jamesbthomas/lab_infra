# Setting up the Switch

This document describes the manual steps needed to setup the core switch for the lab environment.
It includes the following major steps:
1) Setting up the management pi for console access to the switch
2) Prep and Setup
3) Configure the switch for SSH-based management via Ansible
4) Write the functional configuration playbook
5) Write the security configuration playbook

See [Upgrade](upgrade.md) for additional details on how to upgrade the iOS on the switch.

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

# 3) Configure the switch for SSH-based management via Ansible

This step is completely manual - go ahead and console into the switch using the command from step 1 above and issue the following commands

```
enable
# Short form: en - this command elevates you to super user so you can execute privileged commands
configure terminal
# Short form: conf t - this command sends you to the configuration prompt where you can adjust the switch's configuration
hostname <your hostname>
# this sets the hostname of the device
ip domain-name <your domain name>
# sets the default domain name
crypto key generate rsa modulus 2048
# Creates a new RSA cryptographic key with a size of 2048 bits
## Older IOS versions may have extra details to put in this command, so don't be afraid to use tab completion or the ? option to figure out what it's looking for
ip ssh version 2
# enables SSH version 2
username admin privilege 15 secret <password>
# Creates a user named "admin" with full privileges and the specified password
line vty 0 4
# this sends you into a sub-prompt to configure the authentication settings for the virutal terminal
login local
# Sets the AAA source for the virtual terminal to be the local device, as opposed to a RADIUS or TACACS server
transport input ssh
# Configures the terminal server to accept SSH as the incoming protocol
exit
# return to the configure terminal prompt
vlan <number>
# Creates a descriptive reference for the management VLAN and jumps you into the vlan configuration prompt; you should use your management VLAN for this
name Management
# sets the vlan to have the name Management
exit
# jump back to the configuration terminal prompt
interface vlan <vlan number>
# Creates a new vlan interface with the specific number and jumps you to the vlan interface configuration prompt; you should use your management VLAN for this
ip address <ip address> <subnet mask>
# This should match the VLAN you've designated for the management functions; in our case we're using VLAN 99 and a 10.0.0.0/8 IP space, so we'd assigned 10.0.99.<something> for the ip address and 255.255.255.0 as the subnet mask
no shutdown
# Short form: no shut; turns the interface on so it can switch traffic
exit
# jump out of the interface configuration prompt
interface <interface reference>
# jump into the configuration prompt for the interface your management pi is plugged into
switchport mode access
# Sets this to an access port for an endpoint, as opposed to a trunk port that can carry traffic from multiple hosts
switchport access vlan <number>
# Sets this interface to tag all traffic for a specific VLAN, in this case our management VLAN
no shutdown
# Same as last time, turns the interface on so it can switch packets
end
# Jump out of the configure prompt
copy run start
# copies the running configuration (which we just set) to the startup configuration so if the switch reboots it keeps the same configuration
```

Once you're done, make sure you set an IP address on the management Pi within the same subnet as your management VLAN so you can access it over SSH. I recommend using `sudo nmtui` to set the address on your Pi - my default installation didn't have some of the usual files in /etc/network/ that I look for on other distributions, and nmtui makes sure that the configurations get in the right spot

To test your connection, try pinging the ip address you set on the VLAN interface, and try to SSH to that same IP address using the username and password you set.
Note: If you're on older hardware (like me), you may have to explicitly allow deprecated key exchange, key types, and cipher modes. This is okay in a home lab, but is a serious risk for another production or public-facing components.

# 4) Write the functional configuration playbook

For the first play, create tasks that affirm the configurations we placed in manually. This helps enforce idempotency - a key characteristic of ansible - and helps stabilize the configuration so that if I decide to change something in those configs later I can do it via Ansible and the existing GitOps pipelines.

Check out the current [playbook](../../ansible/playbooks/switch/configure_switch.yml) for the full functional setup.

# 5) Write the security configuration playbook

TBD - will be completed once the full infrastructure is in place

[core_switch]
switch ansible_host=10.0.99.10
