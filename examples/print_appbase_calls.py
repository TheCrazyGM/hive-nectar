from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from builtins import str

from prettytable import PrettyTable

from nectar import Hive as Steem

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    stm = Steem(node="https://api.hive.blog")
    # stm = Steem(node="https://testnet.steemitdev.com")
    # stm = Steem(node="wss://appbasetest.timcliff.com")
    # stm = Steem(node="https://api.steemitstage.com")
    # stm = Steem(node="https://api.steemitdev.com")
    all_calls = stm.rpc.get_methods(api="jsonrpc")
    t = PrettyTable(["method", "args", "ret"])
    t.align = "l"
    t_condenser = PrettyTable(["method", "args", "ret"])
    t_condenser.align = "l"
    for call in all_calls:
        if "condenser" not in call:
            ret = stm.rpc.get_signature({"method": call}, api="jsonrpc")
            t.add_row([call, ret["args"], ret["ret"]])
        else:
            ret = stm.rpc.get_signature({"method": call}, api="jsonrpc")
            t_condenser.add_row([call, ret["args"], ret["ret"]])
    print("Finished. Write results...")
    with open("print_appbase.txt", "w") as w:
        w.write(str(t))
    with open("print_appbase.html", "w") as w:
        w.write(str(t.get_html_string()))
    with open("print_appbase_condenser.txt", "w") as w:
        w.write(str(t_condenser))
    with open("print_appbase_condenser.html", "w") as w:
        w.write(str(t_condenser.get_html_string()))
