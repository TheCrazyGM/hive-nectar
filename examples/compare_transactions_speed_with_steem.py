from __future__ import absolute_import, division, print_function, unicode_literals

from builtins import range
from timeit import default_timer as timer

from steembase import operations as steemOperations
from steembase.account import PrivateKey as steemPrivateKey
from steembase.transactions import SignedTransaction as steemSignedTransaction

from nectar import Hive as Steem
from nectar.amount import Amount
from nectarbase import operations
from nectarbase.objects import Operation
from nectarbase.signedtransactions import Signed_Transaction
from nectargraphenebase.account import PrivateKey


class nectarTest(object):
    def setup(self):
        self.prefix = "STEEM"
        self.default_prefix = "STM"
        self.wif = "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"
        self.ref_block_num = 34294
        self.ref_block_prefix = 3707022213
        self.expiration = "2016-04-06T08:29:27"
        self.stm = Steem(offline=True)

    def doit(self, printWire=False, ops=None):
        ops = [Operation(ops)]
        tx = Signed_Transaction(
            ref_block_num=self.ref_block_num,
            ref_block_prefix=self.ref_block_prefix,
            expiration=self.expiration,
            operations=ops,
        )
        start = timer()
        tx = tx.sign([self.wif], chain=self.prefix)
        end1 = timer()
        tx.verify([PrivateKey(self.wif, prefix="STM").pubkey], self.prefix)
        end2 = timer()
        return end2 - end1, end1 - start


class SteemTest(object):
    def setup(self):
        self.prefix = "STEEM"
        self.default_prefix = "STM"
        self.wif = "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3"
        self.ref_block_num = 34294
        self.ref_block_prefix = 3707022213
        self.expiration = "2016-04-06T08:29:27"

    def doit(self, printWire=False, ops=None):
        ops = [steemOperations.Operation(ops)]
        tx = steemSignedTransaction(
            ref_block_num=self.ref_block_num,
            ref_block_prefix=self.ref_block_prefix,
            expiration=self.expiration,
            operations=ops,
        )
        start = timer()
        tx = tx.sign([self.wif], chain=self.prefix)
        end1 = timer()
        tx.verify([steemPrivateKey(self.wif, prefix="STM").pubkey], self.prefix)
        end2 = timer()
        return end2 - end1, end1 - start


if __name__ == "__main__":
    steem_test = SteemTest()
    nectar_test = nectarTest()
    steem_test.setup()
    nectar_test.setup()
    steem_times = []
    nectar_times = []
    loops = 50
    for i in range(0, loops):
        print(i)
        opSteem = steemOperations.Transfer(
            **{"from": "foo", "to": "baar", "amount": "111.110 STEEM", "memo": "Fooo"}
        )
        opnectar = operations.Transfer(
            **{
                "from": "foo",
                "to": "baar",
                "amount": Amount("111.110 STEEM", steem_instance=Steem(offline=True)),
                "memo": "Fooo",
            }
        )

        t_s, t_v = steem_test.doit(ops=opSteem)
        steem_times.append([t_s, t_v])

        t_s, t_v = nectar_test.doit(ops=opnectar)
        nectar_times.append([t_s, t_v])

    steem_dt = [0, 0]
    nectar_dt = [0, 0]
    for i in range(0, loops):
        steem_dt[0] += steem_times[i][0]
        steem_dt[1] += steem_times[i][1]
        nectar_dt[0] += nectar_times[i][0]
        nectar_dt[1] += nectar_times[i][1]
    print("steem vs nectar:\n")
    print("steem: sign: %.2f s, verification %.2f s" % (steem_dt[0] / loops, steem_dt[1] / loops))
    print(
        "nectar:  sign: %.2f s, verification %.2f s" % (nectar_dt[0] / loops, nectar_dt[1] / loops)
    )
    print("------------------------------------")
    print(
        "nectar is %.2f %% (sign) and %.2f %% (verify) faster than steem"
        % (steem_dt[0] / nectar_dt[0] * 100, steem_dt[1] / nectar_dt[1] * 100)
    )
