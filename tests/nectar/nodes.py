# -*- coding: utf-8 -*-
from nectar import Hive
from nectar.nodelist import NodeList


def get_hive_nodes():
    """
    Return the current Hive node endpoints after refreshing the NodeList.

    This function instantiates a NodeList, retrieves its Hive node endpoints, uses those endpoints to construct a Hive client (with num_retries=10) and calls NodeList.update_nodes(...) to refresh the stored node information. It then returns the updated list of Hive node endpoints.

    Returns:
        list[str]: Updated Hive node endpoint URLs.
    """
    nodelist = NodeList()
    nodes = nodelist.get_hive_nodes()
    nodelist.update_nodes(blockchain_instance=Hive(node=nodes, num_retries=10))
    return nodelist.get_hive_nodes()
    # return "https://beta.openhive.network"
