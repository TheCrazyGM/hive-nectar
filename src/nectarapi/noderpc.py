import logging
import re
from typing import Any, Dict, List, Union

from . import exceptions
from .graphenerpc import GrapheneRPC

log = logging.getLogger(__name__)


class NodeRPC(GrapheneRPC):
    """This class allows to call API methods exposed by the witness node via
    websockets / rpc-json.

    :param str urls: Either a single Websocket/Http URL, or a list of URLs
    :param str user: Username for Authentication
    :param str password: Password for Authentication
    :param int num_retries: Try x times to num_retries to a node on disconnect, -1 for indefinitely
    :param int num_retries_call: Repeat num_retries_call times a rpc call on node error (default is 5)
    :param int timeout: Timeout setting for https nodes (default is 60)
    :param bool use_condenser: Use the old condenser_api rpc protocol on nodes with version
        0.19.4 or higher. The settings has no effect on nodes with version of 0.19.3 or lower.
    :param bool use_tor: When set to true, 'socks5h://localhost:9050' is set as proxy

    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Init NodeRPC

        :param str urls: Either a single Websocket/Http URL, or a list of URLs
        :param str user: Username for Authentication
        :param str password: Password for Authentication
        :param int num_retries: Try x times to num_retries to a node on disconnect, -1 for indefinitely
        :param int num_retries_call: Repeat num_retries_call times a rpc call on node error (default is 5)
        :param int timeout: Timeout setting for https nodes (default is 60)
        :param bool use_tor: When set to true, 'socks5h://localhost:9050' is set as proxy

        """
        super().__init__(*args, **kwargs)
        self.next_node_on_empty_reply = False

    def set_next_node_on_empty_reply(self, next_node_on_empty_reply: bool = True) -> None:
        """Switch to next node on empty reply for the next rpc call"""
        self.next_node_on_empty_reply = next_node_on_empty_reply

    def rpcexec(self, payload: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Any:
        """
        Execute an RPC call with node-aware retry and Hive-specific error handling.

        Sends the given JSON-RPC payload via the underlying GrapheneRPC implementation and handles node-level failures, automatic retries, and node switching when appropriate. If the instance flag `next_node_on_empty_reply` is set, an empty reply may trigger switching to the next node (when multiple nodes are available). Retries are governed by the node manager's retry policy.

        Parameters:
            payload (dict or list): JSON-RPC payload to send (method, params, id, etc.).

        Raises:
            RPCConnection: if no RPC URL is configured (connection not established).
            CallRetriesReached: when the node-manager's retry budget is exhausted and no alternative node can be used.
            RPCError: when the remote node returns an RPC error that is not recoverable by retries/switching.
            Exception: any other unexpected exception raised by the underlying RPC call is propagated.
        """
        if self.url is None:
            raise exceptions.RPCConnection("RPC is not connected!")
        doRetry = True
        maxRetryCountReached = False
        while doRetry and not maxRetryCountReached:
            doRetry = False
            try:
                # Forward call to GrapheneWebsocketRPC and catch+evaluate errors
                reply = super().rpcexec(payload)
                if (
                    self.next_node_on_empty_reply
                    and not bool(reply)
                    and self.nodes.working_nodes_count > 1
                ):
                    self._retry_on_next_node("Empty Reply")
                    doRetry = True
                    self.next_node_on_empty_reply = True
                else:
                    self.next_node_on_empty_reply = False
                    return reply
            except exceptions.RPCErrorDoRetry as e:
                msg = exceptions.decodeRPCErrorMsg(e).strip()
                try:
                    self.nodes.sleep_and_check_retries(str(msg), call_retry=True)
                    doRetry = True
                except exceptions.CallRetriesReached:
                    if self.nodes.working_nodes_count > 1:
                        self._retry_on_next_node(msg)
                        doRetry = True
                    else:
                        self.next_node_on_empty_reply = False
                        raise exceptions.CallRetriesReached
            except exceptions.RPCError as e:
                try:
                    doRetry = self._check_error_message(e, self.error_cnt_call)
                except exceptions.CallRetriesReached:
                    msg = exceptions.decodeRPCErrorMsg(e).strip()
                    if self.nodes.working_nodes_count > 1:
                        self._retry_on_next_node(msg)
                        doRetry = True
                    else:
                        self.next_node_on_empty_reply = False
                        raise exceptions.CallRetriesReached
            except Exception as e:
                self.next_node_on_empty_reply = False
                raise e
            maxRetryCountReached = self.nodes.num_retries_call_reached
        self.next_node_on_empty_reply = False

    def _retry_on_next_node(self, error_msg):
        self.nodes.increase_error_cnt()
        self.nodes.sleep_and_check_retries(error_msg, sleep=False, call_retry=False)
        self.next()

    def _check_error_message(self, e, cnt):
        """Check error message and decide what to do"""
        doRetry = False
        msg = exceptions.decodeRPCErrorMsg(e).strip()
        if re.search("missing required active authority", msg):
            raise exceptions.MissingRequiredActiveAuthority
        elif re.match("^no method with name.*", msg):
            raise exceptions.NoMethodWithName(msg)
        elif re.search("Could not find method", msg):
            raise exceptions.NoMethodWithName(msg)
        elif re.search("Unknown Transaction", msg):
            raise exceptions.UnknownTransaction(msg)
        elif re.search("Could not find API", msg):
            if self._check_api_name(msg):
                if self.nodes.working_nodes_count > 1 and self.nodes.num_retries > -1:
                    self.nodes.disable_node()
                    self._switch_to_next_node(msg, "ApiNotSupported")
                    doRetry = True
                else:
                    raise exceptions.ApiNotSupported(msg)
            else:
                raise exceptions.NoApiWithName(msg)
        elif re.search("follow_api_plugin not enabled", msg):
            if self.nodes.working_nodes_count > 1 and self.nodes.num_retries > -1:
                self._switch_to_next_node(str(e))
                doRetry = True
            else:
                raise exceptions.FollowApiNotEnabled(msg)
        elif re.search("irrelevant signature included", msg):
            raise exceptions.UnnecessarySignatureDetected(msg)
        elif re.search("WinError", msg):
            raise exceptions.RPCError(msg)
        elif re.search("Invalid parameters", msg):
            raise exceptions.InvalidParameters()
        elif re.search("Supported by Hivemind", msg):
            raise exceptions.SupportedByHivemind()
        elif re.search("Could not find filtered operation", msg):
            raise exceptions.FilteredItemNotFound(msg)
        elif re.search("Unable to acquire database lock", msg):
            self.nodes.sleep_and_check_retries(str(msg), call_retry=True)
            doRetry = True
        elif re.search("Request Timeout", msg):
            self.nodes.sleep_and_check_retries(str(msg), call_retry=True)
            doRetry = True
        elif re.search("Bad or missing upstream response", msg):
            self.nodes.sleep_and_check_retries(str(msg), call_retry=True)
            doRetry = True
        elif re.search("Internal Error", msg) or re.search("Unknown exception", msg):
            self.nodes.sleep_and_check_retries(str(msg), call_retry=True)
            doRetry = True
        elif re.search("!check_max_block_age", str(e)):
            self._switch_to_next_node(str(e))
            doRetry = True
        elif re.search("Server error", str(e)):
            self._switch_to_next_node(str(e))
            doRetry = True
        elif re.search("Can only vote once every 3 seconds", msg):
            raise exceptions.VotedBeforeWaitTimeReached(msg)
        elif re.search("out_of_rangeEEEE: unknown key", msg) or re.search(
            "unknown key:unknown key", msg
        ):
            raise exceptions.UnknownKey(msg)
        elif re.search("Assert Exception:v.is_object(): Input data have to treated as object", msg):
            raise exceptions.UnhandledRPCError(
                "Use Operation(op, appbase=True) to prevent error: " + msg
            )
        elif re.search("Client returned invalid format. Expected JSON!", msg):
            if self.nodes.working_nodes_count > 1 and self.nodes.num_retries > -1:
                self.nodes.disable_node()
                self._switch_to_next_node(msg)
                doRetry = True
            else:
                raise exceptions.UnhandledRPCError(msg)
        elif msg:
            raise exceptions.UnhandledRPCError(msg)
        else:
            raise e
        return doRetry

    def _switch_to_next_node(self, msg, error_type="UnhandledRPCError"):
        if self.nodes.working_nodes_count == 1:
            if error_type == "UnhandledRPCError":
                raise exceptions.UnhandledRPCError(msg)
            elif error_type == "ApiNotSupported":
                raise exceptions.ApiNotSupported(msg)
        self.nodes.increase_error_cnt()
        self.nodes.sleep_and_check_retries(str(msg), sleep=False)
        self.next()

    def _check_api_name(self, msg):
        error_start = "Could not find API"
        known_apis = [
            "account_history_api",
            "tags_api",
            "database_api",
            "market_history_api",
            "block_api",
            "account_by_key_api",
            "chain_api",
            "follow_api",
            "condenser_api",
            "debug_node_api",
            "witness_api",
            "test_api",
            "bridge",
            "network_broadcast_api",
        ]
        for api in known_apis:
            if re.search(error_start + " " + api, msg):
                return True
        if msg[-18:] == error_start:
            return True
        return False

    def get_account(self, name, **kwargs):
        """Get full account details from account name

        :param str name: Account name
        """
        if isinstance(name, str):
            return self.get_accounts([name], **kwargs)
