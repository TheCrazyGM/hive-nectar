# -*- coding: utf-8 -*-
import json
import logging
import re

import requests
from requests.exceptions import ConnectionError

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
from .rpcutils import get_api_name, get_query, is_network_appbase_ready

log = logging.getLogger(__name__)


class SessionInstance(object):
    """Singleton for the Session Instance"""

    instance = None


def set_session_instance(instance):
    """Set session instance"""
    SessionInstance.instance = instance


def shared_session_instance():
    """Get session instance"""
    if not SessionInstance.instance:
        SessionInstance.instance = requests.Session()
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
        """Initialize the RPC client."""
        self.rpc_methods = {"offline": -1, "appbase": 3}
        self.current_rpc = self.rpc_methods["appbase"]
        self._request_id = 0
        self.timeout = kwargs.get("timeout", 60)
        num_retries = kwargs.get("num_retries", 100)
        num_retries_call = kwargs.get("num_retries_call", 5)
        self.use_condenser = kwargs.get("use_condenser", False)
        self.use_tor = kwargs.get("use_tor", False)
        self.disable_chain_detection = kwargs.get("disable_chain_detection", False)
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
        """Switches to the next node url"""
        self.rpcconnect()

    def is_appbase_ready(self):
        """Check if node is appbase ready"""
        return self.current_rpc == self.rpc_methods["appbase"]

    def get_use_appbase(self):
        """Returns True if appbase ready and appbase calls are set"""
        return not self.use_condenser and self.is_appbase_ready()

    def rpcconnect(self, next_url=True):
        """Connect to next url in a loop."""
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
                if self.disable_chain_detection:
                    # Set to appbase rpc format
                    self.current_rpc = self.rpc_methods["appbase"]
                    break
                try:
                    props = None
                    if not self.use_condenser:
                        props = self.get_config(api="database")
                    else:
                        props = self.get_config()
                except Exception as e:
                    if re.search("Bad Cast:Invalid cast from type", str(e)):
                        # retry with not appbase
                        self.current_rpc = self.rpc_methods["appbase"]
                        props = self.get_config(api="database")
                if props is None:
                    raise RPCError("Could not receive answer for get_config")
                if is_network_appbase_ready(props):
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
        version_list = network_version.split(".")
        return int(int(version_list[0]) * 1e8 + int(version_list[1]) * 1e4 + int(version_list[2]))

    def get_network(self, props=None):
        """Identify the connected network. This call returns a
        dictionary with keys chain_id, core_symbol and prefix
        """
        if props is None:
            props = self.get_config(api="database")
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
        if blockchain_name is None:
            if "STEEM_CHAIN_ID" in props:
                del props["STEEM_CHAIN_ID"]
                log.warning("Using fallback chain preference: HIVE (STEEM removed from detection)")

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
        Execute a call by sending the payload.

        :param json payload: Payload data
        :raises ValueError: if the server does not respond in proper JSON format
        :raises RPCError: if the server returns an error
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
                response = self.request_send(
                    json.dumps(payload, ensure_ascii=False).encode("utf8")
                )
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
            except ConnectionError as e:
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
            api_name = get_api_name(self.is_appbase_ready(), *args, **kwargs)
            if self.is_appbase_ready() and self.use_condenser and api_name != "bridge":
                api_name = "condenser_api"
            if api_name is None:
                api_name = "database_api"

            # let's be able to define the num_retries per query
            stored_num_retries_call = self.nodes.num_retries_call
            self.nodes.num_retries_call = kwargs.get("num_retries_call", stored_num_retries_call)
            add_to_queue = kwargs.get("add_to_queue", False)
            query = get_query(
                self.is_appbase_ready() and not self.use_condenser or api_name == "bridge",
                self.get_request_id(),
                api_name,
                name,
                args,
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
