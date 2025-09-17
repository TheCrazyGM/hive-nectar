from __future__ import print_function

import logging

from memory_profiler import profile

from nectar import Hive as Hive
from nectar.account import Account
from nectar.blockchain import Blockchain
from nectar.instance import clear_cache, set_shared_blockchain_instance

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@profile
def profiling(node, name_list, shared_instance=True, clear_acc_cache=False, clear_all_cache=True):
    """
    Profile memory usage while instantiating Account objects against a Hive node.

    Creates Account instances for each name in name_list using either a new Hive(node)
    instance (when shared_instance is False) or the shared blockchain instance
    (when True). Optionally clears each account's cache and/or the module-wide cache.
    Prints brief flags and the Hive instance (when created). If a non-shared Hive
    instance is created, its `rpc` attribute is deleted at the end to help cleanup.

    Parameters:
        node (str): URL of the Hive RPC node to connect to when creating a non-shared Hive instance.
        name_list (iterable): Iterable of account names (strings) to instantiate as Account objects.
        shared_instance (bool): If False, a new Hive(node=...) instance is created and passed to Account;
            if True, the shared blockchain instance is used (default True).
        clear_acc_cache (bool): If True, calls `clear_cache()` on each created Account (default False).
        clear_all_cache (bool): If True, calls the module-level `clear_cache()` after creating accounts (default True).

    Returns:
        None
    """
    print(
        "shared_instance %d clear_acc_cache %d clear_all_cache %d"
        % (shared_instance, clear_acc_cache, clear_all_cache)
    )
    if not shared_instance:
        hv = Hive(node=node)
        print(str(hv))
    else:
        hv = None
    acc_dict = {}
    for name in name_list:
        acc = Account(name, blockchain_instance=hv)
        acc_dict[name] = acc
        if clear_acc_cache:
            acc.clear_cache()
        acc_dict = {}
    if clear_all_cache:
        clear_cache()
    if not shared_instance:
        del hv.rpc


if __name__ == "__main__":
    hv = Hive()
    print("Shared instance: " + str(hv))
    set_shared_blockchain_instance(hv)
    b = Blockchain()
    account_list = []
    for a in b.get_all_accounts(limit=500):
        account_list.append(a)
    shared_instance = False
    clear_acc_cache = False
    clear_all_cache = False
    node = "https://api.hive.blog"
    n = 3
    for i in range(1, n + 1):
        print("%d of %d" % (i, n))
        profiling(
            node,
            account_list,
            shared_instance=shared_instance,
            clear_acc_cache=clear_acc_cache,
            clear_all_cache=clear_all_cache,
        )
