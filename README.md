# Pulumi Proxmox Provider

Proxmox native Pulumi provider written in Python

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository contains a Pulumi Provider for managing Proxmox VE resources. It allows you to define and manage Proxmox VE resources using Pulumi's infrastructure-as-code approach. (Сurrently in early development stage - focused on LXC container management using)

> [!WARNING]
> This is a learning project and experimental repository. The code is under active development and should not be used in production environments. APIs may change without notice.

## Overview

Custom Pulumi provider for Proxmox VE written in Python. Main focus is on LXC containers with features missing in existing providers.

## Why?

Existing Terraform/Pulumi providers have limitations that affect my workflow:

- **LXC disk expansion** requires container recreation instead of using Proxmox API
- Missing advanced LXC configuration options
- Limited Proxmox API coverage

This provider is written in **Python** for easier development and customization.

## 📦 Features

### Current Implementation

- 🚧 **In Development**: Core LXC container management
- 🚧 **In Development**: Enhanced disk operations

### Planned Features

- 📦 **LXC Containers**: Full lifecycle management
- 💾 **Disk Management**: Dynamic expansion and configuration
- 🌐 **Networking**: Advanced networking configuration
- 🔧 **Templates**: Support for LXC templates
- 📊 **Monitoring**: Resource usage and status monitoring

## 🛠️ Getting Started

### Prerequisites

- Python
- Pulumi CLI
- Access to a Proxmox VE cluster

### Installation

#### Option 1: Install from PyPI (when published)

```bash
pip install pulumi-proxmox-provider
```

#### Option 2: Install from GitHub (current)

```bash
# Install directly from GitHub
pip install git+https://github.com/akmalovaa/pulumi-proxmox-provider.git

# Or clone and install in development mode
git clone https://github.com/akmalovaa/pulumi-proxmox-provider.git
cd pulumi-proxmox-provider
pip install -e .
```

#### Option 3: Using uv (recommended for development)

```bash
git clone https://github.com/akmalovaa/pulumi-proxmox-provider.git
cd pulumi-proxmox-provider
uv sync
```

### Usage

```python
# Example Python usage - see examples/example_lxc.py for complete example
import pulumi
from pulumi_proxmox_provider import LXCContainer, LXCContainerArgs

# Configuration
config = pulumi.Config("proxmox")
node = config.get("node", "pve1")

# Create LXC container
lxc = LXCContainer(
    "my-test-container",
    LXCContainerArgs(
        node=node,
        vm_id=210,
        hostname="test-container",
        cores=1,
        memory=512,
        swap=256,
        ostemplate="local:vztmpl/ubuntu-24.10-standard_24.10-1_amd64.tar.zst",
        password="secure-password",
        unprivileged=True,
        disks={
            "rootfs": "local-lvm:8",  # 8GB root filesystem
        },
        networks={
            "net0": "name=eth0,bridge=vmbr0,ip=dhcp",
        },
    ),
)

# Export container information
pulumi.export("container_id", lxc.vm_id)
pulumi.export("container_hostname", lxc.hostname)
```

For more examples, check the [`examples/`](./examples/) directory.

## 🔗 Alternative Proxmox IaC Solutions

### Terraform Providers

- [Telmate/terraform-provider-proxmox](https://github.com/Telmate/terraform-provider-proxmox) - Original Terraform provider
- [BPG/terraform-provider-proxmox](https://github.com/bpg/terraform-provider-proxmox) - Community-maintained fork

### Pulumi Providers

- [muhlba91/pulumi-proxmoxve](https://github.com/muhlba91/pulumi-proxmoxve) - Comprehensive Pulumi provider
- [hctamu/pulumi-pve](https://github.com/hctamu/pulumi-pve) - Alternative Pulumi implementation

### Resources

- [Pulumi Registry](https://www.pulumi.com/registry/) - Official Pulumi provider registry
- [Proxmox VE API Documentation](https://pve.proxmox.com/pve-docs/api-viewer/)

### Development

```sh
uv pip install -e .
# or
uv pip install -e . --force-reinstall
```

Pulumi create stack and select it:

```sh
pulumi stack ls
```

Preview changes:

```sh
uv run pulumi preview --diff
```
