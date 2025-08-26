# -*- coding: utf-8 -*-
import logging

from nectar.blockchaininstance import BlockChainInstance

log = logging.getLogger(__name__)


class Steem(BlockChainInstance):
    """Hive-only build stub for legacy Steem class.

    This project is Hive-only. Steem support has been removed.
    Importing this class remains possible for backward compatibility,
    but attempting to instantiate it will raise NotImplementedError.
    """

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "Hive-only build: Steem support has been removed. Use nectar.Hive instead."
        )
