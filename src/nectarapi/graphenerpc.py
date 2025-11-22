# -*- coding: utf-8 -*-
import json
import logging
import re

import httpx
from httpx import ConnectError

from nectargraphenebase.chains import known_chains
from nectargraphenebase.version import version as nectar_version

from .exceptions import (
    CallRetriesReached,
    RPCConnection,
    RPCError,
    RPCErrorDoRetry,
    UnauthorizedError,
    WorkingNodeMissing,
)
from .node import Nodes
from .rpcutils import get_query

log = logging.getLogger(__name__)


class SessionInstance(object):
    """Singleton for the Session Instance"""

    instance = None


def set_session_instance(instance):
    """Set session instance"""
    SessionInstance.instance = instance


def shared_session_instance():
    """
    Return a singleton httpx.Client instance, creating it if necessary.

    Ensures a single shared HTTP session is reused across the process to take advantage
    of connection pooling and shared session state (headers, cookies, adapters).

    Returns:
        httpx.Client: The shared session object.
    """
    if not SessionInstance.instance:
        SessionInstance.instance = httpx.Client()
    return SessionInstance.instance


class GrapheneRPC(object):
    """
    This class allows calling API methods synchronously, without callbacks.

    It logs warnings and errors.

    :param str urls: Either a single HTTP URL, or a list of HTTP URLs
    :param str user: Username for Authentication
    :param str password: Password for Authentication
    :param int num_retries: Number of retries for node connection (default is 100)
    :param int num_retries_call: Number of retries for RPC calls on node error (default is 5)
    :param int timeout: Timeout setting for HTTP nodes (default is 60)
    :param bool autoconnect: Automatically connect on initialization (default is True)
    :param bool use_condenser: Use the old condenser_api RPC protocol
    :param bool use_tor: Use Tor proxy for connections
    :param dict custom_chains: Custom chains to add to known chains
    """

    def __init__(self, urls, user=None, password=None, **kwargs):
        """
        Create a synchronous HTTP RPC client for Graphene-based nodes.

        Initializes RPC mode, retry/timeouts, node management, optional credentials, and feature flags. Supported keyword arguments (with defaults) control behavior:
        - timeout (int): request timeout in seconds (default 60).
        - num_retries (int): number of node-retry attempts for node selection (default 100).
        - num_retries_call (int): per-call retry attempts before switching nodes (default 5).
        - use_tor (bool): enable Tor proxies for the shared HTTP session (default False).
        - custom_chains (dict): mapping of additional known chain configurations to merge into the client's known_chains.
        - autoconnect (bool): if True (default), attempts to connect to a working node immediately via rpcconnect().

        Credentials:
        - user, password: optional basic-auth credentials applied to HTTP requests.

        Side effects:
        - Builds a Nodes instance for node tracking and may call rpcconnect() when autoconnect is True.
        """
        self.rpc_methods = {"offline": -1, "appbase": 3}
        self.current_rpc = self.rpc_methods["appbase"]
        self._request_id = 0
        self.timeout = kwargs.get("timeout", 60)
        num_retries = kwargs.get("num_retries", 100)
        num_retries_call = kwargs.get("num_retries_call", 5)
        self.use_tor = kwargs.get("use_tor", False)
        self.known_chains = known_chains
        custom_chain = kwargs.get("custom_chains", {})
        if len(custom_chain) > 0:
            for c in custom_chain:
                if c not in self.known_chains:
                    self.known_chains[c] = custom_chain[c]

        self.nodes = Nodes(urls, num_retries, num_retries_call)
        if self.nodes.working_nodes_count == 0:
            self.current_rpc = self.rpc_methods["offline"]

        self.user = user
        self.password = password
        self.url = None
        self.session = None
        self.rpc_queue = []
        if kwargs.get("autoconnect", True):
            self.rpcconnect()

    @property
    def num_retries(self):
        return self.nodes.num_retries

    @property
    def num_retries_call(self):
        return self.nodes.num_retries_call

    @property
    def error_cnt_call(self):
        return self.nodes.error_cnt_call

    @property
    def error_cnt(self):
        return self.nodes.error_cnt

    def get_request_id(self):
        """Get request id."""
        self._request_id += 1
        return self._request_id

    def next(self):
        """
        Advance to the next available RPC node and attempt to (re)connect.
        """
        self.rpcconnect()

    def rpcconnect(self, next_url=True):
        """
        Selects and establishes connection to an available RPC node.

        Attempts to connect to the next available node (or reuse the current one) and initializes per-instance HTTP session state needed for subsequent RPC calls. On a successful connection this method sets: self.url, self.session (shared session reused), self._proxies (Tor proxies when configured), self.headers, and self.current_rpc (appbase mode by default). It also probes the node using get_config to detect whether the node supports appbase RPC format unless chain detection is disabled.

        Parameters:
            next_url (bool): If True, advance to the next node before attempting connection; if False, retry the current node.

        Raises:
            RPCError: When a get_config probe returns no properties (connection reached but no config received).
            KeyboardInterrupt: Propagated if the operation is interrupted by the user.
        """
        if self.nodes.working_nodes_count == 0:
            return
        while True:
            if next_url:
                self.url = next(self.nodes)
                self.nodes.reset_error_cnt_call()
                log.debug("Trying to connect to node %s" % self.url)
                self.ws = None
                self.session = shared_session_instance()
                self.ws = None
                self.session = shared_session_instance()
                # Do not mutate the shared session; store per-instance proxies.
                self._proxies = None
                if self.use_tor:
                    self._proxies = {
                        "http": "socks5h://localhost:9050",
                        "https": "socks5h://localhost:9050",
                    }
                self.current_rpc = self.rpc_methods["appbase"]
                self.headers = {
                    "User-Agent": "nectar v%s" % (nectar_version),
                    "content-type": "application/json; charset=utf-8",
                }
            try:
                self.current_rpc = self.rpc_methods["appbase"]
                break
            except KeyboardInterrupt:
                raise
            except Exception as e:
                self.nodes.increase_error_cnt()
                do_sleep = not next_url or (next_url and self.nodes.working_nodes_count == 1)
                self.nodes.sleep_and_check_retries(str(e), sleep=do_sleep)
                next_url = True

    def request_send(self, payload):
        """
        Send the prepared RPC payload to the currently connected node via HTTP POST.

        Sends `payload` to the client's active URL using the shared HTTP session. If username and password were provided to the client, HTTP basic auth is applied. Raises UnauthorizedError when the node responds with HTTP 401.

        Parameters:
            payload (str | bytes): The JSON-RPC payload (string or bytes) to send in the POST body.

        Returns:
            requests.Response: The raw HTTP response object from the node.

        Raises:
            UnauthorizedError: If the HTTP response status code is 401 (Unauthorized).
        """
        if self.user is not None and self.password is not None:
            response = self.session.post(
                self.url,
                data=payload,
                headers=self.headers,
                timeout=self.timeout,
                auth=(self.user, self.password),
            )
        else:
            response = self.session.post(
                self.url, data=payload, headers=self.headers, timeout=self.timeout
            )
        if response.status_code == 401:
            raise UnauthorizedError
        return response

    def version_string_to_int(self, network_version):
        """
        Convert a dotted version string "MAJOR.MINOR.PATCH" into a single integer for easy comparison.

        The integer is computed as: major * 10^8 + minor * 10^4 + patch. For example, "2.3.15" -> 200030015.

        Parameters:
            network_version (str): Version string in the form "major.minor.patch".

        Returns:
            int: Integer representation suitable for numeric comparisons.

        Raises:
            ValueError: If any version component is not an integer.
            IndexError: If the version string does not contain three components.
        """
        version_list = network_version.split(".")
        return int(int(version_list[0]) * 1e8 + int(version_list[1]) * 1e4 + int(version_list[2]))

    def get_network(self, props=None):
        """
        Detects and returns the network/chain configuration for the connected node.

        If props is not provided, this call fetches node configuration via get_config(api="database_api") and inspects property keys to determine the chain identifier, address prefix, network/version, and core asset definitions. It builds a chain configuration dict with keys:
        - chain_id: canonical chain identifier string
        - prefix: account/address prefix for the network
        - min_version: reported chain version string
        - chain_assets: list of asset dicts (each with keys "asset" (NAI), "precision", "symbol", and "id")

        If the detected chain matches an entry in self.known_chains (preferring the highest compatible known min_version), that known_chains entry is returned instead of the freshly built config.

        Special behaviors:
        - When props is None, get_config(api="database_api") is called.
        - If detection finds conflicting blockchain prefixes, the most frequent prefix is used.
        - A legacy fallback removes STEEM_CHAIN_ID from props if no blockchain name is inferred, logging a warning to prefer HIVE.
        - Test-network asset NAIs are mapped to "TBD" or "TESTS" symbols when appropriate.
        - Asset entries are assigned stable incremental ids based on sorted NAI order.

        Returns:
            dict: A chain configuration (either a matching entry from self.known_chains or a freshly constructed chain_config) with keys described above.

        Raises:
            RPCError: If chain_id cannot be determined or no compatible known chain is found.
        """
        if props is None:
            props = self.get_config(api="database_api")
        chain_id = None
        network_version = None
        blockchain_name = None
        chain_config = None
        prefix = None
        symbols = []
        chain_assets = []

        prefix_count = {}
        for key in props:
            if key.split("_")[0] in prefix_count:
                prefix_count[key.split("_")[0]] += 1
            else:
                prefix_count[key.split("_")[0]] = 1
        if len(prefix_count) > 0:
            sorted_prefix_count = sorted(prefix_count.items(), key=lambda x: x[1], reverse=True)
            if sorted_prefix_count[0][1] > 1:
                blockchain_name = sorted_prefix_count[0][0]

        # Check for configurable chain preference

        for key in props:
            if key[-8:] == "CHAIN_ID" and blockchain_name is None:
                chain_id = props[key]
                blockchain_name = key.split("_")[0]
            elif key[-8:] == "CHAIN_ID" and key.split("_")[0] == blockchain_name:
                chain_id = props[key]
            elif key[-13:] == "CHAIN_VERSION" and blockchain_name is None:
                network_version = props[key]
            elif key[-13:] == "CHAIN_VERSION" and key.split("_")[0] == blockchain_name:
                network_version = props[key]
            elif key[-14:] == "ADDRESS_PREFIX" and blockchain_name is None:
                prefix = props[key]
            elif key[-14:] == "ADDRESS_PREFIX" and key.split("_")[0] == blockchain_name:
                prefix = props[key]
            elif key[-6:] == "SYMBOL":
                value = {}
                value["asset"] = props[key]["nai"]
                value["precision"] = props[key]["decimals"]
                if (
                    "IS_TEST_NET" in props
                    and props["IS_TEST_NET"]
                    and "nai" in props[key]
                    and props[key]["nai"] == "@@000000013"
                ):
                    value["symbol"] = "TBD"
                elif (
                    "IS_TEST_NET" in props
                    and props["IS_TEST_NET"]
                    and "nai" in props[key]
                    and props[key]["nai"] == "@@000000021"
                ):
                    value["symbol"] = "TESTS"
                else:
                    value["symbol"] = key[:-7]
                value["id"] = -1
                symbols.append(value)
        symbol_id = 0
        if len(symbols) == 2:
            symbol_id = 1
        for s in sorted(symbols, key=lambda self: self["asset"], reverse=False):
            s["id"] = symbol_id
            symbol_id += 1
            chain_assets.append(s)
        if (
            chain_id is not None
            and network_version is not None
            and len(chain_assets) > 0
            and prefix is not None
        ):
            chain_config = {
                "prefix": prefix,
                "chain_id": chain_id,
                "min_version": network_version,
                "chain_assets": chain_assets,
            }

        if chain_id is None:
            raise RPCError("Connecting to unknown network!")
        highest_version_chain = None
        for k, v in list(self.known_chains.items()):
            if (
                blockchain_name is not None
                and blockchain_name not in k
                and blockchain_name != "CHAIN"
            ):
                continue
            if v["chain_id"] == chain_id and self.version_string_to_int(
                v["min_version"]
            ) <= self.version_string_to_int(network_version):
                if highest_version_chain is None:
                    highest_version_chain = v
                elif self.version_string_to_int(v["min_version"]) > self.version_string_to_int(
                    highest_version_chain["min_version"]
                ):
                    highest_version_chain = v
        if highest_version_chain is None and chain_config is not None:
            return chain_config
        elif highest_version_chain is None:
            raise RPCError("Connecting to unknown network!")
        else:
            return highest_version_chain

    def _check_for_server_error(self, reply):
        """Checks for server error message in reply"""
        if re.search("Internal Server Error", reply) or re.search("500", reply):
            raise RPCErrorDoRetry("Internal Server Error")
        elif re.search("Not Implemented", reply) or re.search("501", reply):
            raise RPCError("Not Implemented")
        elif re.search("Bad Gateway", reply) or re.search("502", reply):
            raise RPCErrorDoRetry("Bad Gateway")
        elif re.search("Too Many Requests", reply) or re.search("429", reply):
            raise RPCErrorDoRetry("Too Many Requests")
        elif (
            re.search("Service Temporarily Unavailable", reply)
            or re.search("Service Unavailable", reply)
            or re.search("503", reply)
        ):
            raise RPCErrorDoRetry("Service Temporarily Unavailable")
        elif (
            re.search("Gateway Time-out", reply)
            or re.search("Gateway Timeout", reply)
            or re.search("504", reply)
        ):
            raise RPCErrorDoRetry("Gateway Time-out")
        elif re.search("HTTP Version not supported", reply) or re.search("505", reply):
            raise RPCError("HTTP Version not supported")
        elif re.search("Variant Also Negotiates", reply) or re.search("506", reply):
            raise RPCError("Variant Also Negotiates")
        elif re.search("Insufficient Storage", reply) or re.search("507", reply):
            raise RPCError("Insufficient Storage")
        elif re.search("Loop Detected", reply) or re.search("508", reply):
            raise RPCError("Loop Detected")
        elif re.search("Bandwidth Limit Exceeded", reply) or re.search("509", reply):
            raise RPCError("Bandwidth Limit Exceeded")
        elif re.search("Not Extended", reply) or re.search("510", reply):
            raise RPCError("Not Extended")
        elif re.search("Network Authentication Required", reply) or re.search("511", reply):
            raise RPCError("Network Authentication Required")
        else:
            raise RPCError("Client returned invalid format. Expected JSON!")

    def rpcexec(self, payload):
        """
        Execute the given JSON-RPC payload against the currently selected node and return the RPC result.

        Sends an HTTP POST with `payload` to the connected node, handling empty responses, retries, node rotation, and JSON parsing. On success returns either the `result` field for single-response RPC calls or a list of results when the server returns a JSON-RPC batch/array. Resets per-call error counters on successful responses.

        Parameters:
            payload (dict or list): JSON-serializable RPC request object or a list of request objects (batch).

        Returns:
            The RPC `result` (any) for a single request, or a list of results for a batch response.

        Raises:
            WorkingNodeMissing: if no working nodes are available.
            RPCConnection: if the client is not connected to any node.
            RPCError: for server-reported errors or unexpected / non-JSON responses that indicate an RPC failure.
            KeyboardInterrupt: if execution is interrupted by the user.
        """
        log.debug(f"Payload: {json.dumps(payload)}")
        if self.nodes.working_nodes_count == 0:
            raise WorkingNodeMissing("No working nodes available.")
        if self.url is None:
            raise RPCConnection("RPC is not connected!")

        reply = {}
        response = None
        while True:
            self.nodes.increase_error_cnt_call()
            try:
                response = self.request_send(json.dumps(payload, ensure_ascii=False).encode("utf8"))
                reply = response.text
                if not bool(reply):
                    try:
                        self.nodes.sleep_and_check_retries("Empty Reply", call_retry=True)
                    except CallRetriesReached:
                        self.nodes.increase_error_cnt()
                        self.nodes.sleep_and_check_retries(
                            "Empty Reply", sleep=False, call_retry=False
                        )
                        self.rpcconnect()
                else:
                    break
            except KeyboardInterrupt:
                raise
            except ConnectError as e:
                self.nodes.increase_error_cnt()
                self.nodes.sleep_and_check_retries(str(e), sleep=False, call_retry=False)
                self.rpcconnect()
            except Exception as e:
                self.nodes.increase_error_cnt()
                self.nodes.sleep_and_check_retries(str(e), sleep=False, call_retry=False)
                self.rpcconnect()

        try:
            if response is None:
                try:
                    ret = json.loads(reply, strict=False)
                except ValueError:
                    log.error(f"Non-JSON response: {reply} Node: {self.url}")
                    self._check_for_server_error(reply)
                    raise RPCError("Invalid response format")
            else:
                ret = response.json()
        except ValueError:
            self._check_for_server_error(reply)

        log.debug(f"Reply: {json.dumps(reply)}")

        if isinstance(ret, dict) and "error" in ret:
            if isinstance(ret["error"], dict):
                error_message = ret["error"].get(
                    "detail", ret["error"].get("message", "Unknown error")
                )
                raise RPCError(error_message)
        elif isinstance(ret, list):
            ret_list = []
            for r in ret:
                if isinstance(r, dict) and "error" in r:
                    error_message = r["error"].get(
                        "detail", r["error"].get("message", "Unknown error")
                    )
                    raise RPCError(error_message)
                elif isinstance(r, dict) and "result" in r:
                    ret_list.append(r["result"])
                else:
                    ret_list.append(r)
            self.nodes.reset_error_cnt_call()
            return ret_list
        elif isinstance(ret, dict) and "result" in ret:
            self.nodes.reset_error_cnt_call()
            return ret["result"]
        else:
            log.error(f"Unexpected response format: {ret} Node: {self.url}")
            raise RPCError(f"Unexpected response format: {ret}")

    # End of Deprecated methods
    ####################################################################
    def __getattr__(self, name):
        """Map all methods to RPC calls and pass through the arguments."""

        def method(*args, **kwargs):
            api_name = kwargs.get("api", "database_api")

            # let's be able to define the num_retries per query
            stored_num_retries_call = self.nodes.num_retries_call
            self.nodes.num_retries_call = kwargs.get("num_retries_call", stored_num_retries_call)
            add_to_queue = kwargs.get("add_to_queue", False)
            query = get_query(
                self.get_request_id(),
                api_name,
                name,
                list(args),
            )
            if add_to_queue:
                self.rpc_queue.append(query)
                self.nodes.num_retries_call = stored_num_retries_call
                return None
            elif len(self.rpc_queue) > 0:
                self.rpc_queue.append(query)
                query = self.rpc_queue
                self.rpc_queue = []
            r = self.rpcexec(query)
            self.nodes.num_retries_call = stored_num_retries_call
            return r

        return method
