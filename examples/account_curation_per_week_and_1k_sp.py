#!/usr/bin/python
import sys

# mpl.use('Agg')
# mpl.use('TkAgg')
import matplotlib.pyplot as plt

from nectar.snapshot import AccountSnapshot

if __name__ == "__main__":
    if len(sys.argv) != 2:
        # print("ERROR: command line parameter mismatch!")
        # print("usage: %s [account]" % (sys.argv[0]))
        account = "thecrazygm"
    else:
        account = sys.argv[1]
    acc_snapshot = AccountSnapshot(account)
    acc_snapshot.get_account_history()
    acc_snapshot.build(enable_rewards=True)
    acc_snapshot.build_curation_arrays()
    timestamps = acc_snapshot.curation_per_1000_HP_timestamp
    curation_per_1000_HP = acc_snapshot.curation_per_1000_HP

    plt.figure(figsize=(12, 6))
    opts = {"linestyle": "-", "marker": "."}
    plt.plot_date(
        timestamps, curation_per_1000_HP, label="Curation reward per week and 1k HP", **opts
    )
    plt.grid()
    plt.legend()
    plt.title("Curation over time - @%s" % (account))
    plt.xlabel("Date")
    plt.ylabel("Curation rewards (HP / (week * 1k HP))")
    plt.show()
    # plt.savefig("curation_per_week-%s.png" % (account))
    print("last curation reward per week and 1k hp %.2f HP" % (curation_per_1000_HP[-1]))
