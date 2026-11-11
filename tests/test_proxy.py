"""Proxy selection and real HTTPS tunneling regression tests."""

import base64
import contextlib
import http.server
import json
import os
from pathlib import Path
import select
import shutil
import socket
import socketserver
import ssl
import subprocess
import tempfile
import threading
import time
from typing import Any, ClassVar, Dict, Iterator, List, Tuple
import unittest
from unittest.mock import Mock, patch

import urllib3

from vastpy import RESTFailure, VASTClient


class ProxySelectionTests(unittest.TestCase):
    """Exercise environment selection without opening a connection."""

    def setUp(self) -> None:
        """Isolate proxy configuration from the developer's environment."""
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.response = Mock(status=200, data=b"[]", headers={})
        self.direct = Mock(return_value=Mock(request=Mock(return_value=self.response)))
        self.proxy = Mock(return_value=Mock(request=Mock(return_value=self.response)))
        direct_patch = patch("vastpy.urllib3.PoolManager", self.direct)
        proxy_patch = patch("vastpy.urllib3.ProxyManager", self.proxy)
        direct_patch.start()
        proxy_patch.start()
        self.addCleanup(direct_patch.stop)
        self.addCleanup(proxy_patch.stop)

    def test_environment_selection(self) -> None:
        """Use stdlib casing rules, HTTPS precedence, and HTTP fallback."""
        cases = [
            ({}, None),
            ({"HTTPS_PROXY": "http://secure:8080"}, "http://secure:8080"),
            ({"HTTP_PROXY": "http://fallback:8080"}, "http://fallback:8080"),
            ({"https_proxy": "https://secure:8443"}, "https://secure:8443"),
            ({"http_proxy": "http://fallback:8080"}, "http://fallback:8080"),
            (
                {"HTTPS_PROXY": "http://secure", "HTTP_PROXY": "http://fallback"},
                "http://secure",
            ),
            (
                {"HTTPS_PROXY": "http://upper", "https_proxy": "http://lower"},
                "http://lower",
            ),
            ({"HTTPS_PROXY": "http://upper", "https_proxy": ""}, None),
            ({"HTTP_PROXY": "http://upper", "http_proxy": ""}, None),
            (
                {
                    "HTTPS_PROXY": "http://upper",
                    "https_proxy": "",
                    "HTTP_PROXY": "http://fallback",
                },
                "http://fallback",
            ),
            ({"ALL_PROXY": "http://unused"}, None),
            ({"REQUEST_METHOD": "GET", "HTTP_PROXY": "http://untrusted"}, None),
            (
                {"REQUEST_METHOD": "GET", "http_proxy": "http://trusted"},
                "http://trusted",
            ),
        ]
        for environment, expected in cases:
            with self.subTest(environment=environment):
                self.direct.reset_mock()
                self.proxy.reset_mock()
                with patch.dict(os.environ, environment, clear=True):
                    VASTClient(address="vms.example.com", token="token").views.get()
                if expected is None:
                    self.direct.assert_called_once_with(cert_reqs="CERT_NONE")
                    self.proxy.assert_not_called()
                else:
                    self.proxy.assert_called_once_with(
                        expected, proxy_headers=None, cert_reqs="CERT_NONE"
                    )
                    self.direct.assert_not_called()

    def test_no_proxy(self) -> None:
        """Bypass matching hosts, domains, ports, wildcard, and lowercase entries."""
        cases = [
            ("vms.example.com", "vms.example.com", True),
            ("vms.example.com", ".example.com", True),
            ("example.com", ".example.com", True),
            ("vms.example.com:8443", "vms.example.com:8443", True),
            ("vms.example.com:8443", "vms.example.com:443", False),
            ("vms.example.com", "other.example.com, .example.com", True),
            ("vms.example.com", "*", True),
            ("notexample.com", ".example.com", False),
            ("[::1]:8443", "[::1]", True),
        ]
        for address, bypass, expected in cases:
            with self.subTest(address=address, bypass=bypass):
                self.direct.reset_mock()
                self.proxy.reset_mock()
                with patch.dict(
                    os.environ,
                    {
                        "HTTPS_PROXY": "http://proxy:8080",
                        "NO_PROXY": bypass,
                    },
                    clear=True,
                ):
                    VASTClient(address=address, token="token").get()
                self.assertEqual(self.direct.called, expected)
                self.assertEqual(self.proxy.called, not expected)

        for lowercase, direct in [("vms.example.com", True), ("", False)]:
            self.direct.reset_mock()
            self.proxy.reset_mock()
            with patch.dict(
                os.environ,
                {
                    "HTTPS_PROXY": "http://proxy",
                    "NO_PROXY": "*",
                    "no_proxy": lowercase,
                },
                clear=True,
            ):
                VASTClient(address="vms.example.com", token="token").get()
            self.assertEqual(self.direct.called, direct)

    def test_preserves_certificate_options(self) -> None:
        """Pass the existing VMS CA and server name to either manager."""
        for environment, manager in [
            ({}, self.direct),
            ({"HTTPS_PROXY": "http://proxy"}, self.proxy),
        ]:
            with self.subTest(environment=environment):
                manager.reset_mock()
                with patch.dict(os.environ, environment, clear=True):
                    VASTClient(
                        address="vms",
                        token="token",
                        cert_file="ca.pem",
                        cert_server_name="vms.example.com",
                    ).views.get()
                options = dict(ca_certs="ca.pem", server_hostname="vms.example.com")
                if environment:
                    manager.assert_called_once_with(
                        "http://proxy", proxy_headers=None, **options
                    )
                else:
                    manager.assert_called_once_with(**options)

    def test_derived_client_preserves_authentication_and_request(self) -> None:
        """Keep origin credentials, tenant, URL, query fields, and JSON bodies."""
        with patch.dict(os.environ, {"HTTPS_PROXY": "http://proxy"}):
            client = VASTClient(address="vms", token="token", tenant="tenant")
            client.views[42].patch(name="new")
            self.proxy.return_value.request.assert_called_once_with(
                "PATCH",
                "https://vms/api/latest/views/42/",
                headers={
                    "authorization": "Api-Token token",
                    "X-Tenant-Name": "tenant",
                    "Content-Type": "application/json",
                },
                fields=None,
                body=b'{"name": "new"}',
            )

            self.proxy.return_value.request.reset_mock()
            VASTClient(address="vms", user="user", password="password").views.get(
                fields=["id", "name"]
            )
            self.proxy.return_value.request.assert_called_once_with(
                "GET",
                "https://vms/api/latest/views/",
                headers=urllib3.make_headers(basic_auth="user:password"),
                fields=[("fields", "id"), ("fields", "name")],
                body=None,
            )

    def test_proxy_credentials_stay_in_proxy_headers(self) -> None:
        """Decode URL credentials separately from VMS authentication."""
        with patch.dict(
            os.environ,
            {
                "HTTPS_PROXY": "http://proxy%40user:p%3Ass%40word@proxy:8080",
            },
        ):
            VASTClient(address="vms", token="token").get()
        self.proxy.assert_called_once_with(
            "http://proxy:8080",
            cert_reqs="CERT_NONE",
            proxy_headers=urllib3.make_headers(proxy_basic_auth="proxy@user:p:ss@word"),
        )
        headers = self.proxy.return_value.request.call_args[1]["headers"]
        self.assertEqual(headers, {"authorization": "Api-Token token"})

    def test_connection_errors_propagate(self) -> None:
        """Do not fall back to a direct connection after a proxy failure."""
        error = urllib3.exceptions.ProxyError("unavailable", OSError("refused"))
        self.proxy.return_value.request.side_effect = error
        with patch.dict(os.environ, {"HTTPS_PROXY": "http://proxy"}):
            with self.assertRaises(urllib3.exceptions.ProxyError) as raised:
                VASTClient(address="vms", token="token").get()
        self.assertIs(raised.exception, error)
        self.direct.assert_not_called()

    def test_api_errors_are_unchanged(self) -> None:
        """Retain the client's RESTFailure for a proxied VMS error."""
        self.response.status = 403
        self.response.data = b"forbidden"
        with patch.dict(os.environ, {"HTTPS_PROXY": "http://proxy"}):
            with self.assertRaises(RESTFailure) as raised:
                VASTClient(address="vms", token="token").views.get()
        self.assertEqual(raised.exception.status, 403)


class _HTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Serve test connections on daemon threads with bounded shutdown."""

    daemon_threads = True
    origin_address: str
    requests: List[Tuple[str, Dict[str, str]]]

    def server_bind(self) -> None:
        """Bind loopback without HTTPServer's external reverse-DNS lookup."""
        socketserver.TCPServer.server_bind(self)
        self.server_name = "localhost"
        self.server_port = self.server_address[1]


class _OriginHandler(http.server.BaseHTTPRequestHandler):
    """Echo the TLS origin request as JSON for behavioral assertions."""

    def do_GET(self) -> None:
        """Return the path and headers received by the origin."""
        body = json.dumps({"path": self.path, "headers": dict(self.headers)}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress routine test-server logging."""


class _ProxyHandler(http.server.BaseHTTPRequestHandler):
    """Relay CONNECT traffic only to the test's loopback origin."""

    server: _HTTPServer

    def do_CONNECT(self) -> None:
        """Record proxy headers, then relay a bounded TCP tunnel."""
        self.server.requests.append((self.path, dict(self.headers)))
        if self.path != self.server.origin_address:
            self.send_error(403)
            return
        host, port = self.path.rsplit(":", 1)
        with socket.create_connection((host, int(port)), timeout=3) as upstream:
            self.send_response(200, "Connection established")
            self.end_headers()
            self.connection.settimeout(3)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                readable, _, _ = select.select([self.connection, upstream], [], [], 0.1)
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    destination = (
                        upstream if source is self.connection else self.connection
                    )
                    destination.sendall(data)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress routine test-server logging."""


@contextlib.contextmanager
def _serving(server: _HTTPServer) -> Iterator[_HTTPServer]:
    """Run a local server and close its listening socket when done.

    Parameters
    ----------
    server : _HTTPServer
        Bound test server to serve on a background thread.

    Yields
    ------
    _HTTPServer
        The running server.
    """
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}
    )
    thread.daemon = True
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@unittest.skipUnless(shutil.which("openssl"), "openssl is required for TLS fixtures")
class ProxyNetworkingTests(unittest.TestCase):
    """Make real HTTPS requests directly and through a local CONNECT proxy."""

    resources: ClassVar[contextlib.ExitStack]
    certificate: ClassVar[str]
    origin_address: ClassVar[str]
    proxy_server: ClassVar[_HTTPServer]
    proxy_address: ClassVar[str]

    @classmethod
    def setUpClass(cls) -> None:
        """Generate an isolated test certificate and start loopback servers."""
        cls.resources = contextlib.ExitStack()
        try:
            cls.start_servers()
        except BaseException:
            cls.resources.close()
            raise

    @classmethod
    def start_servers(cls) -> None:
        """Create certificate and servers under the class cleanup stack."""
        directory = Path(cls.resources.enter_context(tempfile.TemporaryDirectory()))
        cls.certificate = str(directory / "cert.pem")
        key = str(directory / "key.pem")
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-keyout",
                key,
                "-out",
                cls.certificate,
                "-days",
                "1",
                "-subj",
                "/CN=localhost",
                "-addext",
                "subjectAltName=DNS:localhost",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        origin = _HTTPServer(("127.0.0.1", 0), _OriginHandler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cls.certificate, key)
        origin.socket = context.wrap_socket(origin.socket, server_side=True)
        cls.resources.enter_context(_serving(origin))
        cls.origin_address = "localhost:{}".format(origin.server_port)
        cls.proxy_server = _HTTPServer(("127.0.0.1", 0), _ProxyHandler)
        cls.proxy_server.origin_address = cls.origin_address
        cls.proxy_server.requests = []
        cls.resources.enter_context(_serving(cls.proxy_server))
        cls.proxy_address = "127.0.0.1:{}".format(cls.proxy_server.server_port)

    @classmethod
    def tearDownClass(cls) -> None:
        """Stop local servers and remove the temporary certificate."""
        cls.resources.close()

    def setUp(self) -> None:
        """Reset recorded tunnels and isolate proxy variables."""
        self.proxy_server.requests.clear()
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def client(self) -> VASTClient:
        """Create a certificate-verifying VMS client for the test origin."""
        return VASTClient(
            address=self.origin_address,
            token="vms-token",
            tenant="tenant",
            cert_file=self.certificate,
            cert_server_name="localhost",
        )

    def test_connect_tunnel_preserves_origin_and_proxy_auth(self) -> None:
        """Send proxy auth on CONNECT and VMS auth only inside the TLS tunnel."""
        os.environ["HTTPS_PROXY"] = (
            "http://proxy-user:proxy-password@" + self.proxy_address
        )
        result = self.client().views[42].get()
        self.assertEqual(result["path"], "/api/latest/views/42/")
        self.assertEqual(result["headers"]["authorization"], "Api-Token vms-token")
        self.assertEqual(result["headers"]["X-Tenant-Name"], "tenant")
        self.assertNotIn(
            "proxy-authorization", {key.lower() for key in result["headers"]}
        )
        self.assertEqual(len(self.proxy_server.requests), 1)
        target, headers = self.proxy_server.requests[0]
        self.assertEqual(target, self.origin_address)
        expected = base64.b64encode(b"proxy-user:proxy-password").decode()
        self.assertEqual(
            headers.get("proxy-authorization") or headers.get("Proxy-Authorization"),
            "Basic " + expected,
        )
        self.assertNotIn("authorization", {key.lower() for key in headers})

    def test_direct_and_no_proxy_connections(self) -> None:
        """Reach the local TLS origin directly with no proxy or a matching bypass."""
        for environment in [
            {},
            {"HTTPS_PROXY": "http://" + self.proxy_address, "NO_PROXY": "localhost"},
        ]:
            with self.subTest(environment=environment):
                with patch.dict(os.environ, environment, clear=True):
                    result = self.client().views.get()
                self.assertEqual(result["path"], "/api/latest/views/")
                self.assertEqual(self.proxy_server.requests, [])


if __name__ == "__main__":
    unittest.main()
