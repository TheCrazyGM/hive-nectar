# -*- coding: utf-8 -*-
import nectar


class SharedInstance(object):
    """Singleton for the shared Blockchain Instance (Hive-only)."""

    instance = None
    config = {}


def shared_blockchain_instance():
    """Initialize and return the shared Hive instance.

    Hive-only: this always returns a `nectar.Hive` instance, regardless of any
    legacy configuration that may have referenced other chains.
    """
    if not SharedInstance.instance:
        clear_cache()
        SharedInstance.instance = nectar.Hive(**SharedInstance.config)
    return SharedInstance.instance


def set_shared_blockchain_instance(blockchain_instance):
    """Override the shared Hive instance for all users of ``SharedInstance.instance``."""
    clear_cache()
    SharedInstance.instance = blockchain_instance


def shared_steem_instance():
    """LEGACY alias. Returns the shared Hive instance (Hive-only)."""
    return shared_blockchain_instance()


def set_shared_steem_instance(steem_instance):
    """LEGACY alias. Redirects to set the shared Hive instance (Hive-only)."""
    set_shared_blockchain_instance(steem_instance)


def shared_hive_instance():
    """Initialize (if needed) and return the shared Hive instance."""
    return shared_blockchain_instance()


def set_shared_hive_instance(hive_instance):
    """Override the shared Hive instance for all users of ``SharedInstance.instance``."""
    set_shared_blockchain_instance(hive_instance)


def clear_cache():
    """Clear Caches"""
    from .blockchainobject import BlockchainObject

    BlockchainObject.clear_cache()


def set_shared_config(config):
    """This allows to set a config that will be used when calling
    the shared instance and allows to define the configuration
    without requiring to actually create an instance
    """
    if not isinstance(config, dict):
        raise AssertionError()
    SharedInstance.config.update(config)
    # if one is already set, delete
    if SharedInstance.instance:
        clear_cache()
        SharedInstance.instance = None
