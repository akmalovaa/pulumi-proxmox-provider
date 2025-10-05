import pulumi
from pulumi_proxmox_provider import LXCContainer, LXCContainerArgs

config = pulumi.Config("proxmox")
node = config.get("node", "pve1")

lxc = LXCContainer(
    "new-test-lxc",
    LXCContainerArgs(
        node=node,
        vm_id=215,
        hostname="new-test-lxc",
        cores=3,
        memory=1024,
        swap=512,
        ostemplate="local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst",
        password="12345",
        unprivileged=True,
        disks={
            "rootfs": "local-lvm:12",
        },
        networks={
            "net0": "name=eth0,bridge=vmbr0,ip=dhcp",
        },
        features={
            "nesting": "1",
            # "keyctl": "1",
        },
        startup="order=0",  # Startup order of containers
        onboot=True,  # Automatically start the container at boot time
        start_on_create=True,  # Start the container after creation
    ),
)


pulumi.export("lxc_id", lxc.vm_id)
pulumi.export("lxc_hostname", lxc.hostname)
pulumi.export("lxc_node", lxc.node)
pulumi.export("lxc_status", lxc.get_status())
pulumi.export("lxc_cores", lxc.cores)
pulumi.export("lxc_memory", lxc.memory)
pulumi.export("lxc_swap", lxc.swap)
