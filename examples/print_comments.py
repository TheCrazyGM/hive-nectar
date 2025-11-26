import logging

from nectar.blockchain import Blockchain
from nectar.instance import shared_blockchain_instance

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class DemoBot:
    def comment(self, comment_event):
        print(
            "Comment by {} on post {} by {}:".format(
                comment_event["author"],
                comment_event["parent_permlink"],
                comment_event["parent_author"],
            )
        )
        print(comment_event["body"])
        print()


if __name__ == "__main__":
    tb = DemoBot()
    blockchain = Blockchain()
    print("Starting on %s network" % shared_blockchain_instance().get_blockchain_name())
    for vote in blockchain.stream(opNames=["comment"]):
        tb.comment(vote)
