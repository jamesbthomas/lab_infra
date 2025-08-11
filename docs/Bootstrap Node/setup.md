# Bootstrap Node Setup

This document details the manual setup steps for the bootstrap node. You can find the playbook that enforces idempotency (good for post-install maintenance) [here](..\..\ansible\tasks\bootstrap\init.yml).

We'll follow the below steps:
1) Install ProxMox
2) Configure Networking
3) Create Initial Templates
4) Deploy Services
5) Configure Git

# Step 1) Install ProxMox

This step is self-explanatory - just follow the prompts and you're good to go.

# Step 2) Configure Networking

Self-explanatory here is configure your switch and make sure your bootstrap node is cabled correctly.

This step focuses on configuring the node to accept traffic on the services and management VLANs. The services VLAN will allow it's resources to be accessible to the rest of the compute nodes, while the management vlan will allow management via ansible from the management pi, all from the same interface.

On the switch end, your port should trunk both your services and management VLANs.

On the node end, you need to configure two bridge interfaces anchored by the same physical interface. You'll need to go into /etc/network/interfaces to configure them.

If you did your install correctly, you'll see something that looks like this:
```
auto lo
iface lo inet loopback

iface <interface id> inet manual

auto vmbr0
iface vmbr0 inet static
  address <the IP you set during the install>
  gateway <gateway IP you set during the install>
  bridge-ports <interface id from above>
  bridge-stp off
  bridge-fd 0

source /etc/network/interfaces.d/*
```

Each paragraph specifies the configuration for an interface - lo for loopback, vmbr0 for the default bridge interface that proxmox created when it was installed. You'll want to refactor the existing vmbr0 entry into a bridge that works for a specific VLAN, and add a new entry for any additional VLANs that you want to accept traffic on.

Your management VLAN bridge should look like this:
```
auto vmbr<vlan id>
iface vmbr<Vlan id> inet static
  address <the address for the proxmox management interface on this node>
  gateway <the gateway IP for the management interface>
  bridge-ports <interface ID that will go to the switch>.<vlan id>
  bridge-stp off
  bridge-fd 0
```

Any additional VLANs you want should look like this:
```
auto vmbr<vlan id>
iface vmbr<vlan id> inet static
  bridge-ports <interface ID>.<vlan id>
  bridge-stp off
  bridge-fd 0
```

The two specifications need to be different, so that the management interface isn't exposed on the wrong VLAN, breaking the environment's out-of-band management.

# Step 3) Create Initial Templates

## Step 3.1) Download Images

This will vary based on your setup: you may download them directly to your bootstrap node, or sneakernet them via a mounted USB drive or a disk if your bootstrap node has an optical drive.

These instructions focus on Windows Server 2022 and AlmaLinux9 as the base OS images. Windows Server is a pretty standard enterprise OS, and AlmaLinux provides most of the enterprise-level features you get with from RedHat without the burden or limits of maintaining a RHEL developer license.

You'll also want to download a copy of the virtio drivers for windows. Virtio is paravirtualized driver framework that generates much faster and efficient storage and network I/O than the default approach. Called "emulated hardware", proxmox by default presents hardware that mimics a real physical device. It's a more compatible approach, but it's also slow for high I/O workloads. Virtio bypasses the step where Proxmox tells the guest OS to pretend that it's a real hardware device, and allows it to talk directly to the hypervisor, lowering CPU overhead, achieving better latency, and creating higher throughput for disks and networks.

AlmaLinux includes the virtio drivers by default, so we only need to get the windows drivers.

You can find the most recent ISOs for each at the following links:
- [Windows Server](https://www.microsoft.com/en-us/evalcenter/download-windows-server-2022)
- [AlmaLinux](https://almalinux.org/get-almalinux/)
- [VirtIO Windows Drivers](github.com/virtio-win/kvm-guest-drivers-windows/wiki/Driver-installation)
  - [Alternate](https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/latest-virtio/virtio-win.iso)

Note on the Windows Server images: the ISO linked above comes pre-built with an evaluation license good for 180 days. After 180 days, that image will start asking for a full license. Buying from Microsoft directly is the safest, but also most expensive. You can generally find spare licenses on resellers or other marketplaces like eBay for significantly cheaper.

Note on AlmaLinux images: there are three options.
- Boot is the bare minimum needed to install the OS, and requires internet access to get the rest of the necessary packages.
- DVD is the full set of packages and repositories; great for offline installs or air-gapped environments, but may introduce unnecessary packages.
- Minimal (the version used in this environment) is just enough to get the OS running and functioning correctly, with the assumptrion that anything more detailed will be downloaded separately via `dnf`.

Once you've got all of the ISOs on your bootstrap node, move them to /var/lib/vs/template/iso - this will make sure your ISOs are available through the UI as well.
- If you want to use a different path, go to /etc/pve/storage.cfg and change the `path` variable under the `dir: local` block.

## Step 3.2) Create the Linux image

Since we're focusing on Infrastructure as Code, these instructions will focus on CLI or text-based configurations that can easily be converted to ansible plays later.

The main binary we'll be using here is `qm` - Proxmox's native CLI for managing QEMU/KVM virtual machines.

To create the image, follow the below general steps:
1) Create the VM Shell
2) Attach devices and prepare for boot
3) Start
4) Configure
5) Seal as a template

Use the following command to create the VM shell: `qm create <vm id> -- name <vm name> --memory 4096 --cores 2 --sockets 1 --cpu kvm64 --machine q35 --scsihw virtio-scsi-pci --net0 virtio,bridge=<management bridge interface> --serial0 socket --vga serial0`
- `<vm id>` - a quick numeric reference; must be unique across all VMs in the cluster
- `<vm name>` - the human-readable name for this VM
- `--cpu kvm64` - configures the set of CPU features to offer to the guest OS; can significant impact image portability and efficiency. `kvm64` is a generic option that favors portability within CPU architectures (i.e, x86 to x86) at the cost of some speed; alternatively, the `host` option offers all features of the proxmox host's CPU to the guest, favoring speed at the cost of portability.
- `--net0 virtio,bridge=<management bridge interface>` - configures the VM to use the virtio NIC and to connect via the management bridge we configured earlier.
- `--scsihw virtio-scsi-pci` - makes sure the VM uses the virtio hardware controller
- `--serial0 socket --vga serial0` - configures a text-based terminal for accessing this VM

You'll notice the shell is missing a few things, like storage specifications or the ISO that we want to install into the template. You'll set those using the commands below.

```
# Creates a new thin-provisioned logical volume at the specified size; 32GB is fine, but size based on your availability
qm set <vm id> --scsi0 local-lvm:32
# Sets the new volume at the start of the boot order
qm set <vm id> --boot order=scsi0

# Mounts the OS ISO
qm set <vm id> --cdrom local:iso/AlmaLinux-9.6-x86_64-minimal.iso

# Configure text-based install
qm set <vm id> --args "console=ttyS0,115200n8 inst.text"
# Powers on the VM
qm start <vm id>

# Accesses the terminal on the VM
qm terminal <vm id>
```

Once inside the VM, we need to enable a few things before templating it.
```
# Update packages
sudo dnf -y update
sudo dnf -y install qemu-guest-agent cloud-init

# Enable template services
sudo systemctl enable --now qemu-guest-agent
sudo systemctl enable cloud-init

# Ensure the terminal is available; should be default on Alma images, but good for idempotency
sudo systemctl enable --now serial-getty@ttyS0.service

# (Optional) Configure networking


# Remove any packages that come with the ISO but that aren't installed
sudo dnf -y clean all
# Remove logs to reduce the storage requirements
sudo rm -f /var/log/*/* /var/log/* 2> /dev/null

# Shutdown cleanly for sealing
sudo shutdown -h now
```

Once back on the proxmox prompt, do some cleanup and seal the VM as a template
```
# Unmount the OS installation media
qm set <vm id> --cdrom none
# Seal the VM
qm template <vm id>
```

# Step 4) Deploy Services



# Step 5) Configure Git
