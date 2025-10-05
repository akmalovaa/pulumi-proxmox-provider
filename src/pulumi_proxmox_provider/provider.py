"""
Base provider class for Proxmox.
"""

from typing import Any, Dict, Optional
import pulumi


class Provider(pulumi.ProviderResource):
    """
    The provider type for the Proxmox package.
    """

    def __init__(
        self,
        resource_name: str,
        endpoint: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[pulumi.Input[str]] = None,
        token_id: Optional[str] = None,
        token_secret: Optional[pulumi.Input[str]] = None,
        insecure: Optional[bool] = None,
        debug: Optional[bool] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        """
        Create a Proxmox provider resource.

        :param resource_name: The name of the provider resource.
        :param endpoint: The endpoint URL for the Proxmox server.
        :param username: The username for authentication.
        :param password: The password for authentication.
        :param token_id: The API token ID for authentication.
        :param token_secret: The API token secret for authentication.
        :param insecure: Whether to skip TLS verification.
        :param debug: Whether to enable debug logging.
        :param opts: Options for the resource.
        """

        args: Dict[str, Any] = {}

        if endpoint is not None:
            args["endpoint"] = endpoint
        if username is not None:
            args["username"] = username
        if password is not None:
            args["password"] = password
        if token_id is not None:
            args["tokenId"] = token_id
        if token_secret is not None:
            args["tokenSecret"] = token_secret
        if insecure is not None:
            args["insecure"] = insecure
        if debug is not None:
            args["debug"] = debug

        super().__init__("proxmox", resource_name, args, opts)
