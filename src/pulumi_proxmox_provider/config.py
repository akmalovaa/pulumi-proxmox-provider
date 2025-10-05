"""
Configuration for Proxmox provider.
"""

import pulumi


class Config:
    """Configuration for Proxmox provider."""

    def __init__(self) -> None:
        config = pulumi.Config("proxmox")
        self.endpoint = config.require("endpoint")
        self.username = config.require("username")
        self.password = config.get_secret("password")
        self.token_id = config.get("token_id")
        self.token_secret = config.get_secret("token_secret")
        self.insecure = config.get_bool("insecure", default=False)
        self.debug = config.get_bool("debug", default=False)

    @property
    def use_token_auth(self) -> bool:
        """Check if token authentication should be used."""
        return self.token_id is not None and self.token_secret is not None
