from __future__ import absolute_import, division, print_function, unicode_literals

import re
from builtins import str


def decodeRPCErrorMsg(e):
    """Helper function to decode the raised Exception and give it a
    python Exception class
    """
    found = re.search(
        ("(10 assert_exception: Assert Exception\n|3030000 tx_missing_posting_auth).*: (.*)\n"),
        str(e),
        flags=re.M,
    )
    if found:
        return found.group(2).strip()
    else:
        return str(e)


class NectarApiException(Exception):
    """NectarApiException base Exception."""

    pass


class UnauthorizedError(NectarApiException):
    """UnauthorizedError Exception."""

    pass


class RPCConnection(NectarApiException):
    """RPCConnection Exception."""

    pass


class RPCError(NectarApiException):
    """RPCError Exception."""

    pass


class RPCErrorDoRetry(NectarApiException):
    """RPCErrorDoRetry Exception."""

    pass


class NumRetriesReached(NectarApiException):
    """NumRetriesReached Exception."""

    pass


class CallRetriesReached(NectarApiException):
    """CallRetriesReached Exception. Only for internal use"""

    pass


class MissingRequiredActiveAuthority(RPCError):
    pass


class UnknownKey(RPCError):
    pass


class NoMethodWithName(RPCError):
    pass


class NoApiWithName(RPCError):
    pass


class FollowApiNotEnabled(RPCError):
    pass


class ApiNotSupported(RPCError):
    pass


class UnhandledRPCError(RPCError):
    pass


class NoAccessApi(RPCError):
    pass


class FilteredItemNotFound(RPCError):
    pass


class InvalidEndpointUrl(NectarApiException):
    pass


class InvalidParameters(NectarApiException):
    pass


class SupportedByHivemind(NectarApiException):
    pass


class UnnecessarySignatureDetected(NectarApiException):
    pass


class WorkingNodeMissing(NectarApiException):
    pass


class TimeoutException(NectarApiException):
    pass


class VotedBeforeWaitTimeReached(NectarApiException):
    pass


class UnknownTransaction(NectarApiException):
    pass
