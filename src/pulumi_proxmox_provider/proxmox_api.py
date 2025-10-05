"""
Proxmox API client for communicating with Proxmox VE.
"""

import requests
import urllib3
from typing import Dict, Any, Optional
import pulumi


class ProxmoxAPI:
    """Client for Proxmox VE API."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        node: Optional[str] = None,
        insecure: bool = False,
    ):
        """Initialize Proxmox API client with configuration."""
        if endpoint is None:
            # Fallback to config if not provided directly
            config = pulumi.Config("proxmox")
            self.endpoint = config.require("endpoint")
            self.username = config.require("username")
            self.password = config.require_secret("password")
            self.node = config.get("node", "pve")
            self.insecure = config.get_bool("insecure", False)
        else:
            self.endpoint = endpoint
            self.username = username
            self.password = password
            self.node = node or "pve"
            self.insecure = insecure

        # Disable SSL warnings if insecure mode
        if self.insecure:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.session = requests.Session()
        self.ticket = None
        self.csrf_token = None

    def _authenticate(self) -> bool:
        """Authenticate with Proxmox and get ticket."""
        auth_url = f"{self.endpoint}/access/ticket"

        # Get the actual password value
        password_value = self.password

        auth_data = {"username": self.username, "password": password_value}

        try:
            response = self.session.post(auth_url, data=auth_data, verify=not self.insecure, timeout=30)
            response.raise_for_status()

            result = response.json()
            if result.get("data"):
                self.ticket = result["data"]["ticket"]
                self.csrf_token = result["data"]["CSRFPreventionToken"]

                # Set authentication headers
                self.session.headers.update({"CSRFPreventionToken": self.csrf_token})
                self.session.cookies.set("PVEAuthCookie", self.ticket)
                return True

        except Exception as e:
            pulumi.log.error(f"Authentication failed: {str(e)}")
            return False

        return False

    def _make_request(self, method: str, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to Proxmox API."""
        if not self.ticket:
            if not self._authenticate():
                raise Exception("Failed to authenticate with Proxmox")

        url = f"{self.endpoint}/{path.lstrip('/')}"

        try:
            if method.upper() == "GET":
                response = self.session.get(url, verify=not self.insecure, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, data=data, verify=not self.insecure, timeout=30)
            elif method.upper() == "PUT":
                response = self.session.put(url, data=data, verify=not self.insecure, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, verify=not self.insecure, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            pulumi.log.error(f"API request failed: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_details = e.response.json()
                    pulumi.log.error(f"Error details: {error_details}")
                except Exception:
                    pulumi.log.error(f"Response text: {e.response.text}")
            raise

    def create_vm(self, vm_id: int, **params) -> Dict[str, Any]:
        """Create a new virtual machine."""
        pulumi.log.info(f"Creating VM {vm_id} on node {self.node}")

        vm_params = {
            "vmid": int(vm_id),
            "cores": int(params.get("cores", 1)),
            "memory": int(params.get("memory", 512)),
            "name": params.get("name", f"vm-{vm_id}"),
        }

        disks = params.get("disks", {})
        for disk_name, disk_config in disks.items():
            vm_params[disk_name] = disk_config

        networks = params.get("networks", {})
        for net_name, net_config in networks.items():
            vm_params[net_name] = net_config

        pulumi.log.info(f"VM params: {vm_params}")
        result = self._make_request("POST", f"nodes/{self.node}/qemu", vm_params)
        pulumi.log.info(f"VM creation initiated: {result}")
        return result

    def get_vm(self, vm_id: int) -> Dict[str, Any]:
        """Get virtual machine information."""
        try:
            vm_id = int(vm_id)  # Ensure this is an integer
            result = self._make_request("GET", f"nodes/{self.node}/qemu/{vm_id}/status/current")
            return result.get("data", {})
        except Exception as e:
            pulumi.log.warn(f"Failed to get VM {vm_id}: {str(e)}")
            return {}

    def update_vm(self, vm_id: int, **params) -> Dict[str, Any]:
        """Update virtual machine configuration."""
        pulumi.log.info(f"Updating VM {vm_id}")

        vm_params = {}
        if "cores" in params:
            vm_params["cores"] = int(params["cores"])
        if "memory" in params:
            vm_params["memory"] = int(params["memory"])
        if "name" in params:
            vm_params["name"] = params["name"]

        if "disks" in params:
            disks = params["disks"]
            for disk_name, disk_config in disks.items():
                vm_params[disk_name] = disk_config

        if "networks" in params:
            networks = params["networks"]
            for net_name, net_config in networks.items():
                vm_params[net_name] = net_config

        pulumi.log.info(f"VM update params: {vm_params}")
        result = self._make_request("PUT", f"nodes/{self.node}/qemu/{vm_id}/config", vm_params)
        pulumi.log.info(f"VM update completed: {result}")
        return result

    def delete_vm(self, vm_id: int) -> Dict[str, Any]:
        """Delete virtual machine."""
        pulumi.log.info(f"Deleting VM {vm_id}")

        try:
            self._make_request("POST", f"nodes/{self.node}/qemu/{vm_id}/status/stop")
            pulumi.log.info(f"VM {vm_id} stopped")
        except Exception as e:
            pulumi.log.warn(f"Failed to stop VM {vm_id}: {str(e)}")

        result = self._make_request("DELETE", f"nodes/{self.node}/qemu/{vm_id}")
        pulumi.log.info(f"VM deletion completed: {result}")
        return result

    def start_vm(self, vm_id: int) -> Dict[str, Any]:
        """Start virtual machine."""
        pulumi.log.info(f"Starting VM {vm_id}")
        result = self._make_request("POST", f"nodes/{self.node}/qemu/{int(vm_id)}/status/start")
        return result

    def create_lxc(self, vm_id: int, **params) -> Dict[str, Any]:
        """Create a new LXC container."""
        pulumi.log.info(f"Creating LXC {vm_id} on node {self.node}")

        # Base parameters for LXC creation
        lxc_params = {
            "vmid": int(vm_id),
            "cores": int(params.get("cores", 1)),
            "memory": int(params.get("memory", 512)),
            "swap": int(params.get("swap", 512)),
            "hostname": params.get("hostname", f"lxc-{vm_id}"),
            "unprivileged": int(params.get("unprivileged", True)),
        }

        if params.get("ostemplate"):
            lxc_params["ostemplate"] = params["ostemplate"]

        if params.get("password"):
            lxc_params["password"] = params["password"]

        if params.get("ssh_public_keys"):
            lxc_params["ssh-public-keys"] = params["ssh_public_keys"]

        disks = params.get("disks", {})
        for disk_name, disk_config in disks.items():
            lxc_params[disk_name] = disk_config

        networks = params.get("networks", {})
        for net_name, net_config in networks.items():
            lxc_params[net_name] = net_config

        features = params.get("features", {})
        if features:
            # Convert features dictionary to string format "key1=value1,key2=value2"
            features_str = ",".join([f"{k}={v}" for k, v in features.items()])
            lxc_params["features"] = features_str

        if params.get("startup"):
            lxc_params["startup"] = params["startup"]

        if params.get("onboot") is not None:
            lxc_params["onboot"] = 1 if params["onboot"] else 0
            pulumi.log.info(f"Added onboot: {params['onboot']} -> {lxc_params['onboot']}")
        else:
            pulumi.log.info(f"onboot not found in params: {list(params.keys())}")

        pulumi.log.info(f"LXC params: {lxc_params}")
        result = self._make_request("POST", f"nodes/{self.node}/lxc", lxc_params)
        pulumi.log.info(f"LXC creation initiated: {result}")
        return result

    def get_lxc(self, vm_id: int) -> Dict[str, Any]:
        """Get LXC container information."""
        try:
            vm_id = int(vm_id)  # Ensure this is an integer
            result = self._make_request("GET", f"nodes/{self.node}/lxc/{vm_id}/status/current")
            return result.get("data", {})
        except Exception as e:
            pulumi.log.warn(f"Failed to get LXC {vm_id}: {str(e)}")
            return {}

    def _resize_lxc_disk(self, vm_id: int, disk_name: str, disk_config: str) -> Dict[str, Any]:
        """
        Resize LXC container disk.

        For LXC usage API: PUT /nodes/{node}/lxc/{vmid}/resize
        """
        if not disk_config or not isinstance(disk_config, str):
            return {}

        # Parsing disk_config like "local-lvm:10"
        if ":" not in disk_config:
            pulumi.log.warn(f"Invalid disk config format: {disk_config}")
            return {}

        storage, size_part = disk_config.split(":", 1)

        # Extract size (must be a number)
        if not size_part.isdigit():
            pulumi.log.warn(f"Invalid disk size format: {size_part}")
            return {}

        new_size_gb = int(size_part)

        pulumi.log.info(f"Resizing LXC {vm_id} disk {disk_name} to {new_size_gb}G")

        # Use API to resize disk
        resize_params = {"disk": disk_name, "size": f"{new_size_gb}G"}

        try:
            result = self._make_request("PUT", f"nodes/{self.node}/lxc/{vm_id}/resize", resize_params)
            pulumi.log.info(f"Disk resize completed: {result}")
            return result
        except Exception as e:
            pulumi.log.error(f"Failed to resize disk: {e}")
            raise

    def update_lxc(self, vm_id: int, **params) -> Dict[str, Any]:
        """Update LXC container configuration."""
        pulumi.log.info(f"Updating LXC {vm_id}")

        lxc_params: Dict[str, Any] = {}
        if "cores" in params:
            lxc_params["cores"] = int(params["cores"])
        if "memory" in params:
            lxc_params["memory"] = int(params["memory"])
        if "swap" in params:
            lxc_params["swap"] = int(params["swap"])
        if "hostname" in params:
            lxc_params["hostname"] = params["hostname"]

        # Update disks - use special API for resizing
        if "disks" in params:
            disks = params["disks"]
            for disk_name, disk_config in disks.items():
                try:
                    self._resize_lxc_disk(vm_id, disk_name, disk_config)
                except Exception as e:
                    pulumi.log.warn(f"Failed to resize disk {disk_name}: {e}")
                    # Continue with other disks

        # Update network interfaces
        if "networks" in params:
            networks = params["networks"]
            for net_name, net_config in networks.items():
                lxc_params[net_name] = net_config

        # Update features
        if "features" in params:
            features = params["features"]
            if features:
                # Convert features dictionary to string format "key1=value1,key2=value2"
                features_str = ",".join([f"{k}={v}" for k, v in features.items()])
                lxc_params["features"] = features_str

        # Update startup parameters
        if "startup" in params:
            lxc_params["startup"] = params["startup"]

        # Update onboot parameter
        if "onboot" in params:
            lxc_params["onboot"] = 1 if params["onboot"] else 0

        pulumi.log.info(f"LXC update params: {lxc_params}")

        # If there are no parameters to update, skip the request
        if lxc_params:
            result = self._make_request("PUT", f"nodes/{self.node}/lxc/{vm_id}/config", lxc_params)
            pulumi.log.info(f"LXC update completed: {result}")
            return result
        else:
            pulumi.log.info("No configuration parameters to update")
            return {"data": None}

    def _wait_for_lxc_unlock(self, vm_id: int, max_retries: int = 30) -> bool:
        """
        Wait for the LXC container to be unlocked.

        Sometimes after resize operations, the container remains locked.
        Wait up to max_retries seconds.
        """
        import time

        for attempt in range(max_retries):
            try:
                # Check the current status of the container
                result = self._make_request("GET", f"nodes/{self.node}/lxc/{vm_id}/status/current")

                # If we can get the status without errors, the container is unlocked
                pulumi.log.info(f"LXC {vm_id} is unlocked (attempt {attempt + 1})")
                return True

            except Exception as e:
                if "timeout" in str(e).lower() or "lock" in str(e).lower():
                    pulumi.log.info(f"LXC {vm_id} still locked, waiting... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(1)
                    continue
                else:
                    # Другая ошибка - не связанная с блокировкой
                    pulumi.log.warn(f"Unexpected error checking LXC {vm_id}: {e}")
                    return True

        pulumi.log.warn(f"LXC {vm_id} is still locked after {max_retries} seconds")
        return False

    def _wait_for_lxc_stop(self, vm_id: int, max_retries: int = 30) -> bool:
        """
        Ожидает полной остановки LXC контейнера.
        """
        import time

        for attempt in range(max_retries):
            try:
                # Check the current status of the container
                result = self._make_request("GET", f"nodes/{self.node}/lxc/{vm_id}/status/current")

                status = result.get("data", {}).get("status", "unknown")
                pulumi.log.info(f"LXC {vm_id} status: {status} (attempt {attempt + 1})")

                if status == "stopped":
                    pulumi.log.info(f"LXC {vm_id} successfully stopped")
                    return True

                # Wait a second before the next check
                time.sleep(1)

            except Exception as e:
                pulumi.log.warn(f"Error checking LXC {vm_id} status: {e}")
                time.sleep(1)

        pulumi.log.warn(f"LXC {vm_id} did not stop after {max_retries} seconds")
        return False

    def delete_lxc(self, vm_id: int) -> Dict[str, Any]:
        """Delete LXC container with improved stop and delete logic."""
        pulumi.log.info(f"Deleting LXC {vm_id}")

        # First, wait for the container to be unlocked
        self._wait_for_lxc_unlock(vm_id)

        # Check the current status of the container
        try:
            current_status = self.get_lxc(vm_id)
            status = current_status.get("status", "unknown")
            pulumi.log.info(f"LXC {vm_id} current status: {status}")

            if status == "running":
                # Stop the container gracefully
                pulumi.log.info(f"Stopping LXC {vm_id}")
                try:
                    self._make_request("POST", f"nodes/{self.node}/lxc/{vm_id}/status/stop")
                    pulumi.log.info(f"Stop command sent to LXC {vm_id}")
                except Exception as e:
                    pulumi.log.error(f"Failed to send stop command to LXC {vm_id}: {str(e)}")

                # Wait for the container to stop
                if not self._wait_for_lxc_stop(vm_id, 60):  # Wait up to 60 seconds
                    # If it didn't stop, try forcing the shutdown
                    pulumi.log.warn(f"LXC {vm_id} did not stop gracefully, forcing shutdown")
                    try:
                        self._make_request("POST", f"nodes/{self.node}/lxc/{vm_id}/status/shutdown")
                        self._wait_for_lxc_stop(vm_id, 30)  # Wait another 30 seconds
                    except Exception as e:
                        pulumi.log.error(f"Failed to force shutdown LXC {vm_id}: {str(e)}")

        except Exception as e:
            pulumi.log.warn(f"Could not check LXC {vm_id} status: {str(e)}")

        # Wait again for unlock before deletion
        self._wait_for_lxc_unlock(vm_id)

        # Retry logic for deletion
        max_delete_retries = 10  # Count of retries for deletion
        for attempt in range(max_delete_retries):
            try:
                result = self._make_request("DELETE", f"nodes/{self.node}/lxc/{vm_id}")
                pulumi.log.info(f"LXC deletion completed: {result}")
                return result
            except Exception as e:
                error_msg = str(e).lower()
                if (
                    "container is running" in error_msg or "timeout" in error_msg or "lock" in error_msg
                ) and attempt < max_delete_retries - 1:
                    import time

                    wait_time = (attempt + 1) * 3  # Up to: 3, 6, 9, 12... seconds
                    pulumi.log.warn(
                        f"Delete failed ({str(e)}), retrying in {wait_time}s... (attempt {attempt + 1}/{max_delete_retries})"
                    )

                    # Additional status check before retry
                    try:
                        current_status = self.get_lxc(vm_id)
                        status = current_status.get("status", "unknown")
                        pulumi.log.info(f"LXC {vm_id} status before retry: {status}")

                        if status == "running":
                            # Attempt to stop again
                            pulumi.log.warn(f"LXC {vm_id} still running, attempting to stop again")
                            self._make_request("POST", f"nodes/{self.node}/lxc/{vm_id}/status/shutdown")
                            self._wait_for_lxc_stop(vm_id, 15)
                    except Exception:
                        pass

                    time.sleep(wait_time)
                    continue
                else:
                    pulumi.log.error(f"Failed to delete LXC {vm_id} after {max_delete_retries} attempts: {e}")
                    raise

        # Fallback return (must not be executed
        return {"data": None}

    def start_lxc(self, vm_id: int) -> Dict[str, Any]:
        """Start LXC container."""
        pulumi.log.info(f"Starting LXC {vm_id}")
        result = self._make_request("POST", f"nodes/{self.node}/lxc/{int(vm_id)}/status/start")
        return result

    def list_lxc_templates(self, storage: str = "local") -> Dict[str, Any]:
        """List available LXC templates."""
        pulumi.log.info(f"Listing LXC templates on storage {storage}")
        try:
            result = self._make_request(
                "GET",
                f"nodes/{self.node}/storage/{storage}/content",
                {"content": "vztmpl"},
            )
            templates = result.get("data", [])
            pulumi.log.info(f"Available templates: {[t.get('volid') for t in templates]}")
            return result
        except Exception as e:
            pulumi.log.error(f"Failed to list templates: {str(e)}")
            return {"data": []}

    def list_lxc_containers(self) -> Dict[str, Any]:
        """List all LXC containers on the node."""
        pulumi.log.info(f"Listing LXC containers on node {self.node}")
        try:
            result = self._make_request("GET", f"nodes/{self.node}/lxc")
            containers = result.get("data", [])
            pulumi.log.info(f"Found {len(containers)} LXC containers")
            return result
        except Exception as e:
            pulumi.log.error(f"Failed to list LXC containers: {str(e)}")
            return {"data": []}
