from __future__ import division, print_function, unicode_literals

import logging

from nectar import Hive as Steem
from nectar.transactionbuilder import TransactionBuilder
from nectarbase import operations

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# example wif
wif = "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"


if __name__ == "__main__":
    stm_online = Steem()
    trx_builder = TransactionBuilder(blockchain_instance=stm_online)
    ref_block_num, ref_block_prefix = trx_builder.get_block_params()
    print("ref_block_num %d - ref_block_prefix %d" % (ref_block_num, ref_block_prefix))

    stm = Steem(offline=True)

    op = operations.Transfer(
        {"from": "thecrazygm", "to": "thecrazygm", "amount": "0.001 HBD", "memo": ""}
    )
    tb = TransactionBuilder(steem_instance=stm)

    tb.appendOps([op])
    tb.appendWif(wif)
    tb.constructTx(ref_block_num=ref_block_num, ref_block_prefix=ref_block_prefix)
    tx = tb.sign(reconstruct_tx=False)
    print(tx.json())
