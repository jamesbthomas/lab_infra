# Bootstrap Node

This directory covers the documentation for the bootstrap node, and the manual steps necessary to set it up.

## Architecture

The Bootstrap Node is a key component of the architecture - together with the Management Pi, it provides a the resources for configuring the remainder of the environment, primarily the Compute Nodes.

It also provides recoverability: if the Compute Nodes fail, the Bootstrap Node will retain key features (like Identity) that will continue to support administrative recovery without losing the current state of the domain.

The bootstrap node is still managed via the Management Pi, but it is smaller and more manageable than a full compute node.

## Features

1) Identity - to ensure centralized, federated identities from the start
2) PXE - to install bare-metal OSes
3) Packer - to build base images (only booted on demand)