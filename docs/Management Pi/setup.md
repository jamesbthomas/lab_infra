# Setting up the Management Pi

## Components

- Raspberry Pi 4 - I used the CanaKit Raspberry Pi 4 4GB Starter Kit Pro (https://www.amazon.com/dp/B07V5JTMV9?ref=ppx_yo2ov_dt_b_fed_asin_title&th=1)
  - This kit comes with a case, SD Card, power cord, power switch, heat sinks, fan, mini-HDMI cable, and even an adapter to plug your SD Card into another computer to update the OS. It's really everything you need to get started with a Raspberry Pi
- (Optional) USB-C to USB-A Data Cable - I used the Amazon Basics cable rated for 10Gbps data transfer (https://www.amazon.com/dp/B01GGKYR2O?ref=ppx_yo2ov_dt_b_fed_asin_title&th=1
	-  A data-rated cable is useful for a number of things; namely allowing you to pass data from the Pi to a workstation powering it and back. However, I wasn't able to get it to work in my deployment, so this cable became option. I still used it instead of the provided wall plug power supply, so that way everything can run through my tower and I didn't have to get under my desk to plug more stuff in.

## High Level Process:

1. Flash the OS
2. Cable and test
- Includes setting console font size
3. Download dependencies
4. Setup Ansible
5. Ansibilize the Management Node Setup

# Step 1) Flash the OS

The kit comes pre-installed with the latest version of Raspbian Buster - it's a fork of Debian 10 Buster specifically designed for Raspberry Pi. It's compatible with all Raspberry Pi models, but it's not the most recent version. Bullseye (the current legacy OS) and Bookworm (the current recommended OS) are both available for free at https://www.raspberrypi.com/software/operating-systems/

You'll also need the \[Raspberry Pi Imager](https://downloads.raspberrypi.org/imager/imager\_latest.exe) to install the OS.

Follow the prompts and accept the agreement to install the imager, launch it and you'll be able to select your Pi model (4), and your desired OS.

In my deployment, I went with a headless approach to preserve storage, so I scrolled down to "Raspberry Pi OS (other)" and selected the (at the time) top option - Raspberry Pi OS Lite (64-bit). It's really small - only 400Mb - and headless, which is perfect for a use case that doesn't require a graphical interface.

The last option is to choose storage - you should select the SD card that you inserted, and the one that you'll use to run the Pi.

I also recommend setting up a username and password via the OS Settings Customization options. You can also pre-set a hostname, enable SSH, and other things. I didn't enable SSH or Wi-Fi, as those weren't necessary under the console access model and my home lab only uses ethernet for admin functions.

It'll take a few minutes to download and install everything, and then let you know when it's done. Make sure you safely eject the SD card before removing it.

# Step 2) Cable and Test

Make sure that you insert the SD Card first, then plug in the power supply. Pi's don't have an external power button, so they will automatically power on as soon as they get power.
Give it 30-60 seconds to boot, and then once your keyboard and monitor are plugged in you should be presented with the login prompt.

If you're on a monitor with a high resolution (mine are all 27" class and 4K capable) you'll notice that the font size is super tiny.

Log in with the credentials you set in Pi Imager, and then run `sudo nano /etc/default/console-setup` to edit your console settings.

There are two lines here:
- FONTFACE: sets the font; you can find a list of default compatible fonts at `/usr/share/consolefonts`
- FONTSIZE: sets the size of the font; sizes are recorded in WidthxHeight format, where each number represents the number of pixels
	- So 16x32 (my setting), sets each character to be 16 pixels wide and 32 pixels tall. On a 1920/1080p monitor, that comes out to 120 characters across and 33 lines down before stuff starts going over the top.
	

# Step 3) Download dependencies

First and foremost, make sure you have the most up to date patches.
```
## Update local package repositories; ensures the local cache of application versions is up to date with the external repositories
sudo apt update
## Trigger an upgrade for any packages that have newer versions out There
sudo apt full-upgrade -y
```

Next, let's get some of the key dependencies for the management node
`sudo apt install -y python3-pip git curl gnupg software-properties-common`
- python3-pip: Package installer for Python3; used to install ansible later
- git: version control system
- curl: useful for fetching remote scripts, keys, or files; not explicitly necessary but good to have
- gnupg: GNU Privacy Guard; used for encryption, signing, and GPG key management, and required for verifying downloads using Ansible Vault with GPG
- software-properties-common: optional at this stage, but provides the `add-apt-repository` command and other related scripts that manage software sources

# Step 4) Install Ansible

Start by installing ansible for the local user only - this avoids installing the executables for the entire system, nesting nicely with the principle of Least Functionality.
```
python3 -m pip install --user ansible --break-system-packages
# --user keeps Ansible isolated to the current user
# --break-system-packages is an explicit acknowledgement of the risk involved with installing packages to user space or isntalling system-wide packages through the OS's non-default mechanism
## It's known as PEP 668 protection, which prevents pip install from modifying key packages and is standard practice when Python is managed by the OS. It's common on Debian packages (which Raspberry Pi is based on) since 2023.
## Since we're installing to the user space, the risk to the overall system is minimal so we'll just accept the risk here

echo "export PATH=$PATH:~/.local/bin" >> ~/.bashrc
# Ensures Ansible ends up in your path so you can call it directly
## ~/.local/bin is the binary directory in the user's home directory - expected since we installed ansible in user space and not for the system as a whole
source ~/.bashrc
# Applies the new path without you having to log out and back in
ansible --version
# Confirms that ansible was installed correctly
```

# Step 5) Create Initial Ansible Resources

Specifically, a folder structure, initialization play for the management node, and inventory.

Folder Structure:
```
~/ansible/
├── bootstrap/
│   └── mgmt-node-init.yml
│   └── remove-unecessesary-users.yml
├── inventory.ini
```

inventory.ini
```
[local]
localhost ansible_connection=local

```

For the full YAMLs, refer to the git repo.