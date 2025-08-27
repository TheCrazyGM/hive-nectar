from __future__ import absolute_import, division, print_function, unicode_literals

import logging
from builtins import str

from prettytable import PrettyTable

from nectar import Hive as Hive

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    hv = Hive(node="https://api.hive.blog")
    # hv = Hive(node="https://testnet.steemitdev.com")
    # hv = Hive(node="wss://appbasetest.timcliff.com")
    # hv = Hive(node="https://api.steemitstage.com")
    # hv = Hive(node="https://api.steemitdev.com")
    all_calls = hv.rpc.get_methods(api="jsonrpc")
    t = PrettyTable(["method", "args", "ret"])
    t.align = "l"
    t_condenser = PrettyTable(["method", "args", "ret"])
    t_condenser.align = "l"
    for call in all_calls:
        if "condenser" not in call:
            ret = hv.rpc.get_signature({"method": call}, api="jsonrpc")
            t.add_row([call, ret["args"], ret["ret"]])
        else:
            ret = hv.rpc.get_signature({"method": call}, api="jsonrpc")
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
