import logging

from nectar.blockchain import Blockchain
from nectar.instance import shared_blockchain_instance

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DemoBot:
    def vote(self, vote_event):
        w = vote_event["weight"]
        if w > 0:
            print("Vote by", vote_event["voter"], "for", vote_event["author"])
        else:
            if w < 0:
                print("Downvote by", vote_event["voter"], "for", vote_event["author"])
            else:
                print("(Down)vote by", vote_event["voter"], "for", vote_event["author"], "CANCELED")


if __name__ == "__main__":
    tb = DemoBot()
    blockchain = Blockchain()
    print("Starting on %s network" % shared_blockchain_instance().get_blockchain_name())
    for vote in blockchain.stream(opNames=["vote"]):
        tb.vote(vote)
