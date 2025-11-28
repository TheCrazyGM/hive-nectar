import nectar
from nectar.instance import (
    set_shared_blockchain_instance,
    set_shared_config,
    shared_blockchain_instance,
)


def test_shared_instance_reuses_transport():
    # Reset config/instance
    set_shared_config({})
    set_shared_blockchain_instance(None)
    hive1 = shared_blockchain_instance()
    rpc1 = getattr(hive1, "rpc", None)
    assert rpc1 is not None

    # Inject an external instance with the same rpc and ensure reuse
    hive2 = nectar.Hive(node=rpc1.nodes.export_working_nodes(), nobroadcast=True)
    hive2.rpc = rpc1
    set_shared_blockchain_instance(hive2)

    hive3 = shared_blockchain_instance()
    assert hive3.rpc is rpc1


def test_shared_instance_config_resets():
    set_shared_blockchain_instance(None)
    set_shared_config({"nobroadcast": True})
    hive = shared_blockchain_instance()
    assert hive.nobroadcast is True
    # Changing config clears instance
    set_shared_config({"nobroadcast": False})
    hive_new = shared_blockchain_instance()
    assert hive_new is not hive
    assert hive_new.nobroadcast is False
