"""
LXC Container resource for Proxmox.
"""

from typing import Any, Dict, Optional
import pulumi
import pulumi.dynamic as dynamic
from .proxmox_api import ProxmoxAPI


class LXCContainerArgs:
    """Arguments for creating an LXC Container."""

    def __init__(
        self,
        node: str,
        vm_id: Optional[int] = None,
        hostname: Optional[str] = None,
        template: Optional[str] = None,
        cores: Optional[int] = None,
        memory: Optional[int] = None,
        swap: Optional[int] = None,
        # Disk configuration
        disks: Optional[Dict[str, str]] = None,
        # Network configuration
        networks: Optional[Dict[str, str]] = None,
        # Legacy parameters for compatibility
        disk_size: Optional[str] = None,
        network: Optional[str] = None,
        # LXC specific parameters
        ostemplate: Optional[str] = None,
        password: Optional[str] = None,
        ssh_public_keys: Optional[str] = None,
        unprivileged: Optional[bool] = None,
        features: Optional[Dict[str, str]] = None,
        startup: Optional[str] = None,
        onboot: Optional[bool] = None,
        start_on_create: Optional[bool] = None,
    ):
        self.node = node
        self.vm_id = vm_id
        self.hostname = hostname
        self.template = template
        self.cores = cores or 1
        self.memory = memory or 512
        self.swap = swap or 512

        # Disk configuration
        if disks is not None:
            self.disks = disks
        elif disk_size is not None:
            # Legacy support: create rootfs by default
            # Remove "G" from size if present, keep only the number
            size = disk_size.replace("G", "").replace("g", "")
            self.disks = {"rootfs": f"local-lvm:{size}"}
        else:
            # By default create 8GB disk for LXC
            self.disks = {"rootfs": "local-lvm:8"}

        # Network configuration
        if networks is not None:
            self.networks = networks
        elif network is not None:
            # Legacy support: create net0
            self.networks = {"net0": network}
        else:
            # By default create network interface on vmbr0 with DHCP
            self.networks = {"net0": "name=eth0,bridge=vmbr0,ip=dhcp"}

        # LXC specific parameters
        self.ostemplate = ostemplate
        self.password = password
        self.ssh_public_keys = ssh_public_keys
        self.unprivileged = unprivileged if unprivileged is not None else True
        self.features = features or {}
        self.startup = startup
        self.onboot = onboot
        self.start_on_create = start_on_create if start_on_create is not None else True


class LXCContainerProvider(dynamic.ResourceProvider):
    """Dynamic provider for Proxmox LXC Containers."""

    def create(self, props: Dict[str, Any]) -> dynamic.CreateResult:
        """Create an LXC container."""
        try:
            # Get Proxmox configuration from props
            api = ProxmoxAPI(
                endpoint=props.get("proxmox_endpoint"),
                username=props.get("proxmox_username"),
                password=props.get("proxmox_password"),
                node=props.get("proxmox_node"),
                insecure=props.get("proxmox_insecure", False),
            )
            vm_id = props.get("vm_id") or 200

            # Create LXC using Proxmox API
            api.create_lxc(
                vm_id=vm_id,
                hostname=props.get("hostname", f"lxc-{vm_id}"),
                cores=props.get("cores", 1),
                memory=props.get("memory", 512),
                swap=props.get("swap", 512),
                disks=props.get("disks", {}),
                networks=props.get("networks", {}),
                ostemplate=props.get("ostemplate"),
                password=props.get("password"),
                ssh_public_keys=props.get("ssh_public_keys"),
                unprivileged=props.get("unprivileged", True),
                features=props.get("features", {}),
                startup=props.get("startup"),
                onboot=props.get("onboot"),
            )

            # Start the container after creation if start_on_create is specified
            if props.get("start_on_create", True):
                try:
                    api.start_lxc(vm_id)
                    pulumi.log.info(f"LXC {vm_id} started automatically after creation")

                    # Wait a moment for the container to start
                    import time

                    time.sleep(3)

                except Exception as e:
                    pulumi.log.error(f"Failed to start LXC {vm_id} after creation: {e}")

            # Get LXC info after creation (and potential start)
            lxc_info = api.get_lxc(vm_id)

            outputs = {
                "vm_id": vm_id,
                "node": props["node"],
                "hostname": props.get("hostname", f"lxc-{vm_id}"),
                "status": lxc_info.get("status", "unknown"),
                "cores": props.get("cores", 1),
                "memory": props.get("memory", 512),
                "swap": props.get("swap", 512),
                "disks": props.get("disks", {}),
                "networks": props.get("networks", {}),
                "unprivileged": props.get("unprivileged", True),
                # Save Proxmox configuration for update/delete
                "proxmox_endpoint": props.get("proxmox_endpoint"),
                # "proxmox_username": props.get("proxmox_username"),
                # "proxmox_password": props.get("proxmox_password"),
                "proxmox_node": props.get("proxmox_node"),
                # "proxmox_insecure": props.get("proxmox_insecure"),
            }

            pulumi.log.info(f"Successfully created LXC {vm_id}")
            return dynamic.CreateResult(id_=str(vm_id), outs=outputs)

        except Exception as e:
            pulumi.log.error(f"Failed to create LXC: {str(e)}")
            raise

    def update(self, id_: str, old_props: Dict[str, Any], new_props: Dict[str, Any]) -> dynamic.UpdateResult:
        """Update an LXC container."""
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

            # Update LXC configuration
            update_params = {}
            if new_props.get("cores") != old_props.get("cores"):
                update_params["cores"] = new_props["cores"]
            if new_props.get("memory") != old_props.get("memory"):
                update_params["memory"] = new_props["memory"]
            if new_props.get("swap") != old_props.get("swap"):
                update_params["swap"] = new_props["swap"]
            if new_props.get("hostname") != old_props.get("hostname"):
                update_params["hostname"] = new_props["hostname"]
            if new_props.get("disks") != old_props.get("disks"):
                update_params["disks"] = new_props["disks"]
            if new_props.get("networks") != old_props.get("networks"):
                update_params["networks"] = new_props["networks"]
            if new_props.get("features") != old_props.get("features"):
                update_params["features"] = new_props["features"]
            if new_props.get("startup") != old_props.get("startup"):
                update_params["startup"] = new_props["startup"]
            if new_props.get("onboot") != old_props.get("onboot"):
                update_params["onboot"] = new_props["onboot"]

            if update_params:
                api.update_lxc(vm_id, **update_params)

            # Get updated LXC info
            lxc_info = api.get_lxc(vm_id)

            outputs = old_props.copy()
            outputs.update(new_props)
            outputs["status"] = lxc_info.get("status", "unknown")

            pulumi.log.info(f"Successfully updated LXC {vm_id}")
            return dynamic.UpdateResult(outs=outputs)

        except Exception as e:
            pulumi.log.error(f"Failed to update LXC: {str(e)}")
            raise

    def delete(self, id_: str, props: Dict[str, Any]) -> None:
        """Delete an LXC container."""
        try:
            # Get Proxmox configuration from props
            api = ProxmoxAPI(
                endpoint=props.get("proxmox_endpoint"),
                username=props.get("proxmox_username"),
                password=props.get("proxmox_password"),
                node=props.get("proxmox_node"),
                insecure=props.get("proxmox_insecure", False),
            )
            vm_id = int(float(id_))  # Сначала float, потом int

            # Delete LXC using Proxmox API
            api.delete_lxc(vm_id)

            pulumi.log.info(f"Successfully deleted LXC {vm_id}")

        except Exception as e:
            pulumi.log.error(f"Failed to delete LXC: {str(e)}")
            raise


class LXCContainer(dynamic.Resource):
    """A Proxmox LXC Container resource."""

    # Declare output properties for IDE support
    vm_id: pulumi.Output[int]
    hostname: pulumi.Output[str]
    node: pulumi.Output[str]
    status: pulumi.Output[str]
    cores: pulumi.Output[int]
    memory: pulumi.Output[int]
    swap: pulumi.Output[int]

    def __init__(
        self,
        resource_name: str,
        args: LXCContainerArgs,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        """
        Create an LXC Container resource.

        :param resource_name: The name of the resource.
        :param args: The arguments for the LXC container.
        :param opts: Options for the resource.
        """

        # Get Proxmox configuration
        config = pulumi.Config("proxmox")

        props = {
            # LXC configuration
            "node": args.node,
            "vm_id": args.vm_id,
            "hostname": args.hostname,
            "template": args.template,
            "cores": args.cores,
            "memory": args.memory,
            "swap": args.swap,
            "disks": args.disks,
            "networks": args.networks,
            "ostemplate": args.ostemplate,
            "password": args.password,
            "ssh_public_keys": args.ssh_public_keys,
            "unprivileged": args.unprivileged,
            "features": args.features,
            "startup": args.startup,
            "onboot": args.onboot,
            "start_on_create": args.start_on_create,
            # Proxmox API configuration
            "proxmox_endpoint": config.require("endpoint"),
            "proxmox_username": config.require("username"),
            "proxmox_password": config.require_secret("password"),
            "proxmox_node": config.get("node", "pve"),
            "proxmox_insecure": config.get_bool("insecure", False),
        }

        # Remove None values
        props = {k: v for k, v in props.items() if v is not None}

        super().__init__(LXCContainerProvider(), resource_name, props, opts)

    def get_status(self) -> pulumi.Output[str]:
        """Get the current status of the LXC container."""

        def _get_status(vm_id_str: str) -> str:
            """Internal function to get LXC status."""
            try:
                # Get Proxmox configuration
                config = pulumi.Config("proxmox")

                # Create API client
                api = ProxmoxAPI(
                    endpoint=config.require("endpoint"),
                    username=config.require("username"),
                    password=config.require("password"),
                    node=config.get("node", "pve"),
                    insecure=config.get_bool("insecure", False),
                )

                # Get LXC status
                vm_id = int(vm_id_str)
                lxc_info = api.get_lxc(vm_id)
                status = lxc_info.get("status")
                return status if status is not None else "unknown"
            except Exception as e:
                pulumi.log.warn(f"Failed to get LXC status: {e}")
                return "unknown"

        return self.vm_id.apply(lambda vm_id: _get_status(str(vm_id)))
