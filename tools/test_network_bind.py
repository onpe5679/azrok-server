import ipaddress
import tempfile
import unittest

from azrok_network import parse_private_ipv4_bind
from azrok_server import AzrokServer

# Synthetic sample addresses derived from the permitted ranges (not real hosts).
SAMPLE_LAN_IP = str(ipaddress.ip_network('192.168.0.0/16')[300])
SAMPLE_TAILSCALE_IP = str(ipaddress.ip_network('100.64.0.0/10')[300])


class NetworkBindPolicyTests(unittest.TestCase):
    def test_all_supported_local_only_ranges_are_allowed(self):
        cases = {
            '127.0.0.1': '127.0.0.1',
            '10.2.3.4': '10.2.3.4',
            '172.16.0.1': '172.16.0.1',
            '172.31.255.254': '172.31.255.254',
            SAMPLE_LAN_IP: SAMPLE_LAN_IP,
            SAMPLE_TAILSCALE_IP: SAMPLE_TAILSCALE_IP,
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(parse_private_ipv4_bind(raw), expected)

    def test_public_unspecified_and_non_ipv4_values_are_rejected(self):
        for raw in ('0.0.0.0', '203.0.113.10', '169.254.1.1', '::1', 'localhost', ''):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    parse_private_ipv4_bind(raw)

    def test_snapshot_exposes_the_exact_validated_listener(self):
        with tempfile.TemporaryDirectory() as tempdir:
            server = AzrokServer(9207, log_dir=tempdir, bind_host=SAMPLE_TAILSCALE_IP)
            try:
                state = server.snapshot()['server']
                self.assertEqual(state['bind_host'], SAMPLE_TAILSCALE_IP)
                self.assertEqual(state['listen_address'], f'{SAMPLE_TAILSCALE_IP}:9207')
            finally:
                server.stop()


if __name__ == '__main__':
    unittest.main()
