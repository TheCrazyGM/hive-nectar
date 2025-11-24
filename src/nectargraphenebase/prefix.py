# -*- coding: utf-8 -*-
from typing import Optional


class Prefix:
    """This class is meant to allow changing the prefix.
    The prefix is used to link a public key to a specific blockchain.
    """

    prefix: str = "STM"

    def set_prefix(self, prefix: Optional[str]) -> None:
        if prefix:
            self.prefix = prefix
