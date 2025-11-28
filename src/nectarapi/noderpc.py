import logging
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
            except Exception as e:
                self.next_node_on_empty_reply = False
                raise e
            maxRetryCountReached = self.nodes.num_retries_call_reached
        self.next_node_on_empty_reply = False

    def _retry_on_next_node(self, error_msg):
        self.nodes.increase_error_cnt()
        self.nodes.sleep_and_check_retries(error_msg, sleep=False, call_retry=False)
        self.next()

    def get_account(self, name, **kwargs):
        """Get full account details from account name

        :param str name: Account name
        """
        if isinstance(name, str):
            return self.get_accounts([name], **kwargs)
