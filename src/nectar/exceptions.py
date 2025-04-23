# -*- coding: utf-8 -*-


class NectarException(Exception):
    """Base exception for all Nectar-related errors"""

    pass


class WalletExists(NectarException):
    """A wallet has already been created and requires a password to be
    unlocked by means of :func:`nectar.wallet.Wallet.unlock`.
    """

    pass


class RPCConnectionRequired(NectarException):
    """An RPC connection is required"""

    pass


class InvalidMemoKeyException(NectarException):
    """Memo key in message is invalid"""

    pass


class WrongMemoKey(NectarException):
    """The memo provided is not equal the one on the blockchain"""

    pass


class OfflineHasNoRPCException(NectarException):
    """When in offline mode, we don't have RPC"""

    pass


class AccountExistsException(NectarException):
    """The requested account already exists"""

    pass


class AccountDoesNotExistsException(NectarException):
    """The account does not exist"""

    pass


class AssetDoesNotExistsException(NectarException):
    """The asset does not exist"""

    pass


class InvalidAssetException(NectarException):
    """An invalid asset has been provided"""

    pass


class InsufficientAuthorityError(NectarException):
    """The transaction requires signature of a higher authority"""

    pass


class VotingInvalidOnArchivedPost(NectarException):
    """The transaction requires signature of a higher authority"""

    pass


class MissingKeyError(NectarException):
    """A required key couldn't be found in the wallet"""

    pass


class InvalidWifError(NectarException):
    """The provided private Key has an invalid format"""

    pass


class BlockDoesNotExistsException(NectarException):
    """The block does not exist"""

    pass


class NoWalletException(NectarException):
    """No Wallet could be found, please use :func:`nectar.wallet.Wallet.create` to
    create a new wallet
    """

    pass


class WitnessDoesNotExistsException(NectarException):
    """The witness does not exist"""

    pass


class ContentDoesNotExistsException(NectarException):
    """The content does not exist"""

    pass


class VoteDoesNotExistsException(NectarException):
    """The vote does not exist"""

    pass


class WrongMasterPasswordException(NectarException):
    """The password provided could not properly unlock the wallet"""

    pass


class VestingBalanceDoesNotExistsException(NectarException):
    """Vesting Balance does not exist"""

    pass


class InvalidMessageSignature(NectarException):
    """The message signature does not fit the message"""

    pass


class NoWriteAccess(NectarException):
    """Cannot store to sqlite3 database due to missing write access"""

    pass


class BatchedCallsNotSupported(NectarException):
    """Batch calls do not work"""

    pass


class BlockWaitTimeExceeded(NectarException):
    """Wait time for new block exceeded"""

    pass
