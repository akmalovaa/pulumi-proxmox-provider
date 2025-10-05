"""
Virtual Machine resource for Proxmox.
"""

from typing import Any, Dict, Optional
import pulumi
import pulumi.dynamic as dynamic
from .proxmox_api import ProxmoxAPI


class VirtualMachineArgs:
    """Arguments for creating a Virtual Machine."""

    def __init__(
        self,
        node: str,
        vm_id: Optional[int] = None,
        name: Optional[str] = None,
        template: Optional[str] = None,
        cores: Optional[int] = None,
        memory: Optional[int] = None,
        # Disk configuration
        disks: Optional[Dict[str, str]] = None,
        # Network configuration
        networks: Optional[Dict[str, str]] = None,
        # Legacy parameters for compatibility
        disk_size: Optional[str] = None,
        network: Optional[str] = None,
        # Additional parameters
        ssh_keys: Optional[str] = None,
        ip_config: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.node = node
        self.vm_id = vm_id
        self.name = name
        self.template = template
        self.cores = cores or 1
        self.memory = memory or 512

        # Disk configuration
        if disks is not None:
            self.disks = disks
        elif disk_size is not None:
            # Legacy support: create scsi0 by default
            # Remove "G" from size if present, keep only the number
            size = disk_size.replace("G", "").replace("g", "")
            self.disks = {"scsi0": f"local-lvm:{size}"}
        else:
            # By default create 20GB disk
            self.disks = {"scsi0": "local-lvm:20"}

        # Network configuration
        if networks is not None:
            self.networks = networks
        elif network is not None:
            # Legacy support: create net0
            self.networks = {"net0": network}
        else:
            # By default create network interface on vmbr0
            self.networks = {"net0": "virtio,bridge=vmbr0"}

        self.ssh_keys = ssh_keys
        self.ip_config = ip_config
        self.user = user
        self.password = password


class VirtualMachineProvider(dynamic.ResourceProvider):
    """Dynamic provider for Proxmox Virtual Machines."""

    def create(self, props: Dict[str, Any]) -> dynamic.CreateResult:
        """Create a virtual machine."""
        try:
            # Get Proxmox configuration from props
            api = ProxmoxAPI(
                endpoint=props.get("proxmox_endpoint"),
                username=props.get("proxmox_username"),
                password=props.get("proxmox_password"),
                node=props.get("proxmox_node"),
                insecure=props.get("proxmox_insecure", False),
            )
            vm_id = props.get("vm_id") or 100

            # Create VM using Proxmox API
            api.create_vm(
                vm_id=vm_id,
                cores=props.get("cores", 1),
                memory=props.get("memory", 512),
                name=props.get("name", f"vm-{vm_id}"),
                disks=props.get("disks", {}),
                networks=props.get("networks", {}),
            )

            # Don't start VM automatically until we resolve type issues
            # api.start_vm(vm_id)

            # Get VM info after creation
            vm_info = api.get_vm(vm_id)

            outputs = {
                "vm_id": vm_id,
                "node": props["node"],
                "name": props.get("name", f"vm-{vm_id}"),
                "status": vm_info.get("status", "unknown"),
                "cores": props.get("cores", 1),
                "memory": props.get("memory", 512),
                "disks": props.get("disks", {}),
                "networks": props.get("networks", {}),
                # Save Proxmox configuration for update/delete
                "proxmox_endpoint": props.get("proxmox_endpoint"),
                # "proxmox_username": props.get("proxmox_username"),
                # "proxmox_password": props.get("proxmox_password"),
                "proxmox_node": props.get("proxmox_node"),
                "proxmox_insecure": props.get("proxmox_insecure"),
            }

            pulumi.log.info(f"Successfully created VM {vm_id}")
            return dynamic.CreateResult(id_=str(vm_id), outs=outputs)

        except Exception as e:
            pulumi.log.error(f"Failed to create VM: {str(e)}")
            raise

    def update(self, id_: str, old_props: Dict[str, Any], new_props: Dict[str, Any]) -> dynamic.UpdateResult:
        """Update a virtual machine."""
        try:
            # Get Proxmox configuration from props
            api = ProxmoxAPI(
                endpoint=new_props.get("proxmox_endpoint"),
                username=new_props.get("proxmox_username"),
                password=new_props.get("proxmox_password"),
                node=new_props.get("proxmox_node"),
                insecure=new_props.get("proxmox_insecure", False),
            )
            vm_id = int(float(id_))  # Сначала float, потом int

            # Update VM configuration
            update_params = {}
            if new_props.get("cores") != old_props.get("cores"):
                update_params["cores"] = new_props["cores"]
            if new_props.get("memory") != old_props.get("memory"):
                update_params["memory"] = new_props["memory"]
            if new_props.get("name") != old_props.get("name"):
                update_params["name"] = new_props["name"]
            if new_props.get("disks") != old_props.get("disks"):
                update_params["disks"] = new_props["disks"]
            if new_props.get("networks") != old_props.get("networks"):
                update_params["networks"] = new_props["networks"]

            if update_params:
                api.update_vm(vm_id, **update_params)

            # Get updated VM info
            vm_info = api.get_vm(vm_id)

            outputs = old_props.copy()
            outputs.update(new_props)
            outputs["status"] = vm_info.get("status", "unknown")

            pulumi.log.info(f"Successfully updated VM {vm_id}")
            return dynamic.UpdateResult(outs=outputs)

        except Exception as e:
            pulumi.log.error(f"Failed to update VM: {str(e)}")
            raise

    def delete(self, id_: str, props: Dict[str, Any]) -> None:
        """Delete a virtual machine."""
        try:
            # Get Proxmox configuration from props
            api = ProxmoxAPI(
                endpoint=props.get("proxmox_endpoint"),
                username=props.get("proxmox_username"),
                password=props.get("proxmox_password"),
                node=props.get("proxmox_node"),
                insecure=props.get("proxmox_insecure", False),
            )
            vm_id = int(float(id_))

            # Delete VM using Proxmox API
            api.delete_vm(vm_id)

            pulumi.log.info(f"Successfully deleted VM {vm_id}")

        except Exception as e:
            pulumi.log.error(f"Failed to delete VM: {str(e)}")
            raise


class VirtualMachine(dynamic.Resource):
    """A Proxmox Virtual Machine resource."""

    vm_id: pulumi.Output[int]
    node: pulumi.Output[str]
    name: pulumi.Output[str]
    status: pulumi.Output[str]
    ip_address: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        args: VirtualMachineArgs,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        """
        Create a Virtual Machine resource.

        :param resource_name: The name of the resource.
        :param args: The arguments for the virtual machine.
        :param opts: Options for the resource.
        """

        # Get Proxmox configuration
        config = pulumi.Config("proxmox")

        props = {
            # VM configuration
            "node": args.node,
            "vm_id": args.vm_id,
            "name": args.name,
            "template": args.template,
            "cores": args.cores,
            "memory": args.memory,
            "disks": args.disks,
            "networks": args.networks,
            "ssh_keys": args.ssh_keys,
            "ip_config": args.ip_config,
            "user": args.user,
            "password": args.password,
            # Proxmox API configuration
            "proxmox_endpoint": config.require("endpoint"),
            "proxmox_username": config.require("username"),
            "proxmox_password": config.require_secret("password"),
            "proxmox_node": config.get("node", "pve"),
            "proxmox_insecure": config.get_bool("insecure", False),
        }

        # Remove None values
        props = {k: v for k, v in props.items() if v is not None}

        super().__init__(VirtualMachineProvider(), resource_name, props, opts)
