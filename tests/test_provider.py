"""
Tests for Pulumi Proxmox Provider
"""

import pytest
import unittest
from unittest.mock import Mock, patch

from pulumi_proxmox_provider import __version__


class TestProxmoxProvider(unittest.TestCase):
    """Test cases for Proxmox Provider."""

    def test_version(self):
        """Test that version is accessible."""
        self.assertEqual(__version__, "0.1.0")

    @patch("pulumi_proxmox_provider.provider.pulumi")
    def test_provider_init(self, mock_pulumi):
        """Test provider initialization."""
        from pulumi_proxmox_provider.provider import ProxmoxProvider

        # Mock the pulumi module
        mock_resource_options = Mock()
        mock_pulumi.ResourceOptions = mock_resource_options

        # This test would need actual pulumi integration
        # For now, just test import works
        self.assertTrue(ProxmoxProvider)


if __name__ == "__main__":
    unittest.main()
