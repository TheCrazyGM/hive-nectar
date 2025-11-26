import logging

from nectar import Hive as Hive
from nectar.transactionbuilder import TransactionBuilder
from nectarbase import operations

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# example wif
wif = "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"


if __name__ == "__main__":
    hv_online = Hive()
    trx_builder = TransactionBuilder(blockchain_instance=hv_online)
    ref_block_num, ref_block_prefix = trx_builder.get_block_params()
    print("ref_block_num %d - ref_block_prefix %d" % (ref_block_num, ref_block_prefix))

    hv = Hive(offline=True)

    op = operations.Transfer(
        {"from": "thecrazygm", "to": "thecrazygm", "amount": "0.001 HBD", "memo": ""}
    )
    tb = TransactionBuilder(blockchain_instance=hv)

    tb.appendOps([op])
    tb.appendWif(wif)
    tb.constructTx(ref_block_num=ref_block_num, ref_block_prefix=ref_block_prefix)
    tx = tb.sign(reconstruct_tx=False)
    print(tx.json())
