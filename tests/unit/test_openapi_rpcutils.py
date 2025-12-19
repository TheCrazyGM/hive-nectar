from nectarapi.openapi import get_default_api_for_method
from nectarapi.rpcutils import get_query


def test_openapi_default_api_map():
    assert get_default_api_for_method("get_block") == "block_api"
    assert get_default_api_for_method("get_account_history") == "account_history_api"
    assert get_default_api_for_method("get_followers") == "condenser_api"
    assert get_default_api_for_method("get_methods") == "jsonrpc"
    assert get_default_api_for_method("unknown_method") is None


def test_rpcutils_empty_params_use_list_for_condenser():
    q = get_query(1, "condenser_api", "get_account_count", args={})
    assert q["params"] in ({}, [])
    q2 = get_query(1, "block_api", "get_block", args={})
    assert q2["params"] == {}


def test_rpcutils_batch_and_positional():
    # Single dict list
    batch = get_query(1, "block_api", "get_block", args=[{"block_num": 1}, {"block_num": 2}])
    assert isinstance(batch, list)
    assert batch[0]["id"] == 1 and batch[1]["id"] == 2

    # Positional list
    pos = get_query(1, "block_api", "get_block_range", args=[1, 2])
    assert pos["params"] == [1, 2]

    # Tuple converted to list
    pos_tuple = get_query(1, "block_api", "get_block_range", args=(1, 2))
    assert pos_tuple["params"] == [1, 2]
