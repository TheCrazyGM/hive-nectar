import logging
from datetime import timedelta

from nectar import exceptions
from nectar.account import Account
from nectar.blockchain import Blockchain
from nectar.comment import Comment
from nectar.utils import construct_authorperm

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class WatchingTheWatchers:
    def __init__(self):
        self.dvcount = 0
        self.account_type = dict()
        self.account_relations = dict()
        self.by_voter = dict()
        self.by_target = dict()
        self.by_pair = dict()

    def update(self, downvoter, downvoted, dvpower, flagpower):
        pair = downvoter + "/" + downvoted
        if downvoter not in self.by_voter:
            self.by_voter[downvoter] = [0.0, 0.0]
        if downvoted not in self.by_target:
            self.by_target[downvoted] = [0.0, 0.0]
        if pair not in self.by_pair:
            self.by_pair[pair] = [0.0, 0.0]
        self.by_voter[downvoter][0] = self.by_voter[downvoter][0] + dvpower
        self.by_voter[downvoter][1] = self.by_voter[downvoter][1] + flagpower
        self.by_target[downvoted][0] = self.by_target[downvoted][0] + dvpower
        self.by_target[downvoted][1] = self.by_target[downvoted][1] + flagpower
        self.by_pair[pair][0] = self.by_pair[pair][0] + dvpower
        self.by_pair[pair][1] = self.by_pair[pair][1] + flagpower
        self.dvcount = self.dvcount + 1
        if self.dvcount % 100 == 0:
            print(self.dvcount, "downvotes so far.")

    def set_account_info(self, account, fish, related):
        self.account_type[account] = fish
        if len(related) > 0:
            self.account_relations[account] = related

    def report(self):
        print("[REPORT]")
        print(" * account_type :", self.account_type)
        print()
        print(" * account_relations :", self.account_relations)
        print()
        print(" * by voter :", self.by_voter)
        print()
        print(" * by target :", self.by_target)
        print()
        print(" * by pair :", self.by_pair)
        print()
        self.dvcount = 0
        self.account_type = dict()
        self.account_relations = dict()
        self.by_voter = dict()
        self.by_target = dict()
        self.by_pair = dict()


class WatchingTheWatchersBot:
    def __init__(self, wtw):
        self.stopped = None
        self.wtw = wtw
        self.looked_up = set()

    def vote(self, vote_event):
        """
        Process a vote event and record downvote statistics and account metadata.

        When the incoming vote_event represents a negative vote (weight < 0), this method:
        - Extracts the corresponding Comment and inspects its active_votes to find the voter's negative vote(s), splitting any contribution into `downvote_power` and `flag_power`, then records those values with the WatchingTheWatchers instance.
        - Ensures voter and author account information is loaded once: looks up account objects, computes vesting power (VP) from vesting shares, received vesting shares, and delegated vesting shares, then classifies accounts into fish categories ("redfish", "minnow", "dolphin", "orca", "whale") by VP thresholds.
        - Collects related accounts from the account's `recovery_account` (excluded when empty or equal to "hive") and `proxy`, and stores that metadata.

        Parameters:
            vote_event (dict): A vote operation dictionary with at least the keys "weight", "voter", "author", and "permlink". For negative weights this method reads the referenced comment's "active_votes" to compute downvote and flag powers.

        Returns:
            None
        """

        def process_vote_content(event):
            start_rshares = 0.0
            for vote in event["active_votes"]:
                if vote["voter"] == vote_event["voter"] and float(vote["rshares"]) < 0:
                    if start_rshares + float(vote["rshares"]) < 0:
                        flag_power = 0 - start_rshares - float(vote["rshares"])
                    else:
                        flag_power = 0
                    downvote_power = 0 - vote["rshares"] - flag_power
                    self.wtw.update(vote["voter"], vote_event["author"], downvote_power, flag_power)

        def lookup_accounts(acclist):
            """
            Lookup account records for the given account names, compute each account's vesting power (VP) and a fish-category based on VP, collect related accounts (recovery_account except "hive" and non-empty proxy), and store the results by calling self.wtw.set_account_info(account, fish, related). If any related accounts (recovery or proxy) are found and not already processed, they are queued for recursive lookup.

            Parameters:
                acclist (list[str]): List of account names to fetch and process.

            Notes:
                - VP is computed as (vesting_shares + received_vesting_shares - delegated_vesting_shares) / 1_000_000.
                - Fish categories: "redfish" (default), "minnow" (VP >= 1), "dolphin" (VP >= 10), "orca" (VP >= 100), "whale" (VP > 1000).
                - Prints an "OOPS" line if the number of fetched Account objects does not match the input list length.
                - Side effects: calls self.wtw.set_account_info and may call lookup_accounts recursively for related accounts not yet seen.
            """

            def user_info(accounts):
                if len(acclist) != len(accounts):
                    print("OOPS:", len(acclist), len(accounts), acclist)
                for index in range(0, len(accounts)):
                    a = accounts[index]
                    account = acclist[index]
                    vp = (
                        a["vesting_shares"].amount
                        + a["received_vesting_shares"].amount
                        - a["delegated_vesting_shares"].amount
                    ) / 1000000.0
                    fish = "redfish"
                    if vp >= 1.0:
                        fish = "minnow"
                    if vp >= 10.0:
                        fish = "dolphin"
                    if vp >= 100:
                        fish = "orca"
                    if vp > 1000:
                        fish = "whale"
                    racc = None
                    proxy = None
                    related = list()
                    if a["recovery_account"] != "hive" and a["recovery_account"] != "":
                        related.append(a["recovery_account"])
                    if a["proxy"] != "":
                        related.append(a["proxy"])
                    self.wtw.set_account_info(account, fish, related)
                    accl2 = list()
                    if racc is not None and racc not in self.looked_up:
                        accl2.append(racc)
                    if proxy is not None and proxy not in self.looked_up:
                        accl2.append(proxy)
                    if len(accl2) > 0:
                        lookup_accounts(accl2)

            accounts = []
            for a in acclist:
                accounts.append(Account(a))
            user_info(accounts)

        if vote_event["weight"] < 0:
            authorperm = construct_authorperm(vote_event["author"], vote_event["permlink"])
            # print(authorperm)
            try:
                process_vote_content(Comment(authorperm))
            except exceptions.ContentDoesNotExistsException:
                print("Could not find Comment: %s" % (authorperm))
            al = list()
            if vote_event["voter"] not in self.looked_up:
                al.append(vote_event["voter"])
                self.looked_up.add(vote_event["voter"])
            if vote_event["author"] not in self.looked_up:
                al.append(vote_event["author"])
                self.looked_up.add(vote_event["author"])
            if len(al) > 0:
                lookup_accounts(al)


if __name__ == "__main__":
    wtw = WatchingTheWatchers()
    tb = WatchingTheWatchersBot(wtw)
    blockchain = Blockchain()
    threading = True
    thread_num = 16
    cur_block = blockchain.get_current_block()
    stop = cur_block.identifier
    startdate = cur_block.time() - timedelta(days=1)
    start = blockchain.get_estimated_block_num(startdate, accurate=True)
    for vote in blockchain.stream(
        opNames=["vote"], start=start, stop=stop, threading=threading, thread_num=thread_num
    ):
        tb.vote(vote)
    wtw.report()
