# -*- coding: utf-8 -*-
import logging
import warnings

from .comment import Comment
from .instance import shared_blockchain_instance

log = logging.getLogger(__name__)


class Query(dict):
    """Query to be used for all discussion queries

    :param int limit: limits the number of posts
    :param str tag: tag query
    :param int truncate_body:
    :param array filter_tags:
    :param array select_authors:
    :param array select_tags:
    :param str start_author:
    :param str start_permlink:
    :param str start_tag:
    :param str parent_author:
    :param str parent_permlink:
    :param str start_parent_author:
    :param str before_date:
    :param str author: Author (see Discussions_by_author_before_date)

    .. testcode::

        from nectar.discussions import Query
        query = Query(limit=10, tag="hive")

    """

    def __init__(
        self,
        limit=0,
        tag="",
        truncate_body=0,
        filter_tags=None,
        select_authors=None,
        select_tags=None,
        start_author=None,
        start_permlink=None,
        start_tag=None,
        parent_author=None,
        parent_permlink=None,
        start_parent_author=None,
        before_date=None,
        author=None,
    ):
        """
        Initialize a Query mapping for discussion fetches.

        Creates a dict-like Query object containing normalized discussion query parameters used by the Discussions fetchers. List-valued parameters default to empty lists when None. Values are stored as keys on self (e.g. self["limit"], self["tag"], etc.).

        Parameters:
            limit (int): Maximum number of items requested (0 means no explicit client-side limit).
            tag (str): Topic tag or account (used by feed/blog where appropriate).
            truncate_body (int): Number of characters to truncate post bodies to (0 = no truncate).
            filter_tags (list|None): Tags to exclude; defaults to [].
            select_authors (list|None): Authors to include; defaults to [].
            select_tags (list|None): Tags to include; defaults to [].
            start_author (str|None): Author name used as a pagination starting point.
            start_permlink (str|None): Permlink used as a pagination starting point.
            start_tag (str|None): Tag used as a pagination starting point for tag-based queries.
            parent_author (str|None): Parent post author (used for comment/replies queries).
            parent_permlink (str|None): Parent post permlink (used for comment/replies queries).
            start_parent_author (str|None): Parent author used for pagination in replies queries.
            before_date (str|None): ISO 8601 datetime string to fetch items before this timestamp.
            author (str|None): Author name for author-scoped queries.
        """
        self["limit"] = limit
        self["truncate_body"] = truncate_body
        self["tag"] = tag
        self["filter_tags"] = filter_tags or []
        self["select_authors"] = select_authors or []
        self["select_tags"] = select_tags or []
        self["start_author"] = start_author
        self["start_permlink"] = start_permlink
        self["start_tag"] = start_tag
        self["parent_author"] = parent_author
        self["parent_permlink"] = parent_permlink
        self["start_parent_author"] = start_parent_author
        self["before_date"] = before_date
        self["author"] = author


class Discussions(object):
    """Get Discussions

    :param Hive blockchain_instance: Hive instance

    """

    def __init__(self, lazy=False, use_appbase=False, blockchain_instance=None, **kwargs):
        # Handle legacy parameters
        """
        Initialize the Discussions orchestrator.

        Parameters:
            lazy (bool): If True, wrap fetched items in lazy-loading Comment objects.
            use_appbase (bool): If True, prefer appbase/condenser-style endpoints when available.

        Notes:
            - Accepts a blockchain instance via `blockchain_instance`. For backward compatibility this initializer also accepts the deprecated keyword arguments `steem_instance` and `hive_instance`; if one of those is provided it will be used when `blockchain_instance` is not set. Using the deprecated keys emits a DeprecationWarning.
            - If both deprecated legacy instance keys are provided simultaneously, a ValueError is raised.
            - The resolved blockchain instance is stored on self.blockchain (falls back to shared_blockchain_instance() when none provided). The flags `self.lazy` and `self.use_appbase` are set from the corresponding parameters.
        """
        legacy_keys = {"steem_instance", "hive_instance"}
        legacy_instance = None
        for key in legacy_keys:
            if key in kwargs:
                if legacy_instance is not None:
                    raise ValueError(
                        f"Cannot specify both {key} and another legacy instance parameter"
                    )
                legacy_instance = kwargs.pop(key)
                warnings.warn(
                    f"Parameter '{key}' is deprecated. Use 'blockchain_instance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Prefer explicit blockchain_instance, then legacy
        if blockchain_instance is None and legacy_instance is not None:
            blockchain_instance = legacy_instance

        self.blockchain = blockchain_instance or shared_blockchain_instance()
        self.lazy = lazy
        self.use_appbase = use_appbase

    def get_discussions(self, discussion_type, discussion_query, limit=1000, raw_data=False):
        """
        Yield discussions of a given type according to a Query, handling pagination.

        This generator fetches discussions in pages from the appropriate per-type helper
        and yields individual discussion entries until `limit` items have been yielded
        or no more results are available.

        Parameters:
            discussion_type (str): One of:
                "trending", "author_before_date", "payout", "post_payout", "created",
                "active", "cashout", "votes", "children", "hot", "feed", "blog",
                "comments", "promoted", "replies", "tags".
                Determines which backend/query helper is used.
            discussion_query (Query): Query-like mapping with parameters used by the
                underlying helpers (e.g., limit, tag, start_author, start_permlink,
                before_date). If `discussion_query["limit"]` is 0, it will be set to
                100 when `limit >= 100`, otherwise set to the provided `limit`.
                If `before_date` is falsy, it will be set to "1970-01-01T00:00:00".
            limit (int): Maximum number of discussion items to yield (default 1000).
            raw_data (bool): If True, helpers are requested to return raw dict data;
                if False, helpers may return wrapped Comment objects when supported.

        Yields:
            Individual discussion items as returned by the selected helper:
            - For post/comment helpers: dicts when `raw_data=True`, or Comment objects
              when `raw_data=False` and wrapping is supported.
            - For "tags": tag dictionaries.

        Behavior and notes:
            - This function mutates `discussion_query` for pagination (start_* fields)
              and may update `discussion_query["limit"]` and `before_date` as described.
            - Pagination is driven by start markers (author/permlink/tag/parent_author)
              and the function avoids yielding duplicate entries across pages.
            - Raises ValueError if `discussion_type` is not one of the supported values.
        """
        if limit >= 100 and discussion_query["limit"] == 0:
            discussion_query["limit"] = 100
        elif limit < 100 and discussion_query["limit"] == 0:
            discussion_query["limit"] = limit
        query_count = 0
        found_more_than_start_entry = True
        if "start_author" in discussion_query:
            start_author = discussion_query["start_author"]
        else:
            start_author = None
        if "start_permlink" in discussion_query:
            start_permlink = discussion_query["start_permlink"]
        else:
            start_permlink = None
        if "start_tag" in discussion_query:
            start_tag = discussion_query["start_tag"]
        else:
            start_tag = None
        if "start_parent_author" in discussion_query:
            start_parent_author = discussion_query["start_parent_author"]
        else:
            start_parent_author = None
        if not discussion_query["before_date"]:
            discussion_query["before_date"] = "1970-01-01T00:00:00"
        while query_count < limit and found_more_than_start_entry:
            rpc_query_count = 0
            dd = None
            discussion_query["start_author"] = start_author
            discussion_query["start_permlink"] = start_permlink
            discussion_query["start_tag"] = start_tag
            discussion_query["start_parent_author"] = start_parent_author
            if discussion_type == "trending":
                dd = Discussions_by_trending(
                    discussion_query, blockchain_instance=self.blockchain, lazy=self.lazy
                )
            elif discussion_type == "author_before_date":
                dd = Discussions_by_author_before_date(
                    author=discussion_query["author"],
                    start_permlink=discussion_query["start_permlink"],
                    before_date=discussion_query["before_date"],
                    limit=discussion_query["limit"],
                    blockchain_instance=self.blockchain,
                    lazy=self.lazy,
                )
            elif discussion_type == "payout":
                dd = Comment_discussions_by_payout(
                    discussion_query,
                    blockchain_instance=self.blockchain,
                    lazy=self.lazy,
                    use_appbase=self.use_appbase,
                    raw_data=raw_data,
                )
            elif discussion_type == "post_payout":
                dd = Post_discussions_by_payout(
                    discussion_query,
                    blockchain_instance=self.blockchain,
                    lazy=self.lazy,
                    use_appbase=self.use_appbase,
                    raw_data=raw_data,
                )
            elif discussion_type == "created":
                dd = Discussions_by_created(
                    discussion_query,
                    blockchain_instance=self.blockchain,
                    lazy=self.lazy,
                    use_appbase=self.use_appbase,
                    raw_data=raw_data,
                )
            elif discussion_type == "active":
                dd = Discussions_by_active(
                    discussion_query,
                    blockchain_instance=self.blockchain,
                    lazy=self.lazy,
                    use_appbase=self.use_appbase,
                    raw_data=raw_data,
                )
            elif discussion_type == "cashout":
                dd = Discussions_by_cashout(
                    discussion_query,
                    blockchain_instance=self.blockchain,
                    lazy=self.lazy,
                    use_appbase=self.use_appbase,
                    raw_data=raw_data,
                )
            elif discussion_type == "votes":
                dd = Discussions_by_votes(
                    discussion_query,
                    blockchain_instance=self.blockchain,
                    lazy=self.lazy,
                    use_appbase=self.use_appbase,
                    raw_data=raw_data,
                )
            elif discussion_type == "children":
                dd = Discussions_by_children(
                    discussion_query,
                    blockchain_instance=self.blockchain,
                    lazy=self.lazy,
                    use_appbase=self.use_appbase,
                    raw_data=raw_data,
                )
            elif discussion_type == "hot":
                dd = Discussions_by_hot(
                    discussion_query,
                    blockchain_instance=self.blockchain,
                    lazy=self.lazy,
                    use_appbase=self.use_appbase,
                    raw_data=raw_data,
                )
            elif discussion_type == "feed":
                dd = Discussions_by_feed(
                    discussion_query,
                    blockchain_instance=self.blockchain,
                    lazy=self.lazy,
                    use_appbase=self.use_appbase,
                    raw_data=raw_data,
                )
            elif discussion_type == "blog":
                dd = Discussions_by_blog(
                    discussion_query,
                    blockchain_instance=self.blockchain,
                    lazy=self.lazy,
                    use_appbase=self.use_appbase,
                    raw_data=raw_data,
                )
            elif discussion_type == "comments":
                dd = Discussions_by_comments(
                    discussion_query,
                    blockchain_instance=self.blockchain,
                    lazy=self.lazy,
                    use_appbase=self.use_appbase,
                    raw_data=raw_data,
                )
            elif discussion_type == "promoted":
                dd = Discussions_by_promoted(
                    discussion_query,
                    blockchain_instance=self.blockchain,
                    lazy=self.lazy,
                    use_appbase=self.use_appbase,
                    raw_data=raw_data,
                )
            elif discussion_type == "replies":
                dd = Discussions_by_replies(
                    discussion_query,
                    blockchain_instance=self.blockchain,
                    lazy=self.lazy,
                    use_appbase=self.use_appbase,
                    raw_data=raw_data,
                )
            elif discussion_type == "tags":
                dd = Trending_tags(
                    discussion_query,
                    blockchain_instance=self.blockchain,
                    lazy=self.lazy,
                    use_appbase=self.use_appbase,
                )
            else:
                raise ValueError("Wrong discussion_type")
            if not dd:
                return

            for d in dd:
                double_result = False
                if discussion_type == "tags":
                    if query_count != 0 and rpc_query_count == 0 and (d["name"] == start_tag):
                        double_result = True
                        if len(dd) == 1:
                            found_more_than_start_entry = False
                    start_tag = d["name"]
                elif discussion_type == "replies":
                    if (
                        query_count != 0
                        and rpc_query_count == 0
                        and (d["author"] == start_parent_author and d["permlink"] == start_permlink)
                    ):
                        double_result = True
                        if len(dd) == 1:
                            found_more_than_start_entry = False
                    start_parent_author = d["author"]
                    start_permlink = d["permlink"]
                else:
                    if (
                        query_count != 0
                        and rpc_query_count == 0
                        and (d["author"] == start_author and d["permlink"] == start_permlink)
                    ):
                        double_result = True
                        if len(dd) == 1:
                            found_more_than_start_entry = False
                    start_author = d["author"]
                    start_permlink = d["permlink"]
                rpc_query_count += 1
                if not double_result:
                    query_count += 1
                    if query_count <= limit:
                        yield d


class Discussions_by_trending(list):
    """Get Discussions by trending

    :param Query discussion_query: Defines the parameter for
        searching posts
    :param Hive blockchain_instance: Hive instance
    :param bool raw_data: returns list of comments when False, default is False

    .. testcode::

        from nectar.discussions import Query, Discussions_by_trending
        q = Query(limit=10, tag="hive")
        for h in Discussions_by_trending(q):
            print(h)

    """

    def __init__(
        self,
        discussion_query,
        lazy=False,
        use_appbase=False,
        raw_data=False,
        blockchain_instance=None,
        **kwargs,
    ):
        # Handle legacy parameters
        """
        Initialize a Discussions_by_trending iterator that fetches trending discussions and stores results (raw or wrapped).

        Builds a reduced query from discussion_query, prefers a provided blockchain_instance (or a legacy instance passed via the deprecated kwargs "steem_instance" or "hive_instance"), configures RPC node selection based on appbase usage, and tries a bridge API call first with fallbacks to appbase or legacy RPC endpoints. Results are stored by calling the superclass initializer with either raw post dicts or Comment-wrapped objects.

        Parameters:
            discussion_query (dict): Full query dict; only a subset keys are used here (e.g., "tag", "limit", "start_author", "start_permlink").
            lazy (bool): If False, Comment objects are fully initialized; if True, they are created for lazy loading.
            use_appbase (bool): Prefer appbase/tag endpoints when falling back from the bridge API.
            raw_data (bool): If True, store raw post dicts; otherwise wrap posts in Comment objects.

        Side effects:
            - Sets self.blockchain to the resolved blockchain instance.
            - Calls self.blockchain.rpc.set_next_node_on_empty_reply(...) to influence RPC node selection.
            - Calls RPC methods to fetch posts and initializes the superclass with the fetched items.

        Raises:
            ValueError: If more than one legacy instance key is provided in kwargs.

        Notes:
            - Passing "steem_instance" or "hive_instance" in kwargs is supported for backwards compatibility but emits a DeprecationWarning and is mapped to blockchain_instance.
            - No return value; the instance is populated via the superclass initializer.
        """
        legacy_keys = {"steem_instance", "hive_instance"}
        legacy_instance = None
        for key in legacy_keys:
            if key in kwargs:
                if legacy_instance is not None:
                    raise ValueError(
                        f"Cannot specify both {key} and another legacy instance parameter"
                    )
                legacy_instance = kwargs.pop(key)
                warnings.warn(
                    f"Parameter '{key}' is deprecated. Use 'blockchain_instance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Prefer explicit blockchain_instance, then legacy
        if blockchain_instance is None and legacy_instance is not None:
            blockchain_instance = legacy_instance

        self.blockchain = blockchain_instance or shared_blockchain_instance()
        reduced_query = {}
        for key in [
            "tag",
            "limit",
            "filter_tags",
            "select_authors",
            "select_tags",
            "truncate_body",
            "start_author",
            "start_permlink",
        ]:
            if key in discussion_query:
                reduced_query[key] = discussion_query[key]
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        posts = []
        try:
            # Try to use the bridge API first (preferred method)
            bridge_query = {
                "sort": "trending",
                "tag": reduced_query.get("tag", ""),
                "observer": "",
            }
            if "limit" in reduced_query:
                bridge_query["limit"] = reduced_query["limit"]
            if "start_author" in reduced_query and "start_permlink" in reduced_query:
                bridge_query["start_author"] = reduced_query["start_author"]
                bridge_query["start_permlink"] = reduced_query["start_permlink"]
            posts = self.blockchain.rpc.get_ranked_posts(bridge_query, api="bridge")
        except Exception:
            # Fall back to old API methods
            if self.blockchain.rpc.get_use_appbase() and use_appbase:
                try:
                    posts = self.blockchain.rpc.get_discussions_by_trending(
                        reduced_query, api="tags"
                    )["discussions"]
                except Exception:
                    posts = []
            if len(posts) == 0:
                posts = self.blockchain.rpc.get_discussions_by_trending(reduced_query)
        if posts is None:
            posts = []
        if raw_data:
            super(Discussions_by_trending, self).__init__([x for x in posts])
        else:
            super(Discussions_by_trending, self).__init__(
                [Comment(x, lazy=lazy, blockchain_instance=self.blockchain) for x in posts]
            )


class Discussions_by_author_before_date(list):
    """Get Discussions by author before date

    .. note:: To retrieve discussions before date, the time of creation
              of the discussion @author/start_permlink must be older than
              the specified before_date parameter.

    :param str author: Defines the author *(required)*
    :param str start_permlink: Defines the permlink of a starting discussion
    :param str before_date: Defines the before date for query
    :param int limit: Defines the limit of discussions
    :param bool use_appbase: use condenser call when set to False, default is False
    :param bool raw_data: returns list of comments when False, default is False
    :param Hive blockchain_instance: Hive instance

    .. testcode::

        from nectar.discussions import Query, Discussions_by_author_before_date
        for h in Discussions_by_author_before_date(limit=10, author="gtg"):
            print(h)

    """

    def __init__(
        self,
        author="",
        start_permlink="",
        before_date="1970-01-01T00:00:00",
        limit=100,
        lazy=False,
        use_appbase=False,
        raw_data=False,
        blockchain_instance=None,
        **kwargs,
    ):
        # Handle legacy parameters
        """
        Initialize a Discussions_by_author_before_date container of posts by a specific author before a given date.

        Creates an ordered list of posts (either raw dicts or wrapped Comment objects) for the specified author published before `before_date`. Attempts to fetch via the bridge API and falls back to appbase/legacy RPC methods when necessary.

        Parameters:
            author (str): Account name whose posts to retrieve.
            start_permlink (str): Permlink to start pagination from (exclusive); empty means start from newest.
            before_date (str): ISO-8601 timestamp; only posts with `created` < this value are returned. Default is "1970-01-01T00:00:00" (no date filtering).
            limit (int): Maximum number of posts to fetch from each RPC call (may be used for pagination by the caller).
            lazy (bool): When False, posts are wrapped into Comment objects; when True, wrapping is deferred (passed to Comment).
            use_appbase (bool): Prefer appbase/tag APIs when falling back from the bridge API.
            raw_data (bool): If True, store raw post dicts; if False, store Comment-wrapped objects.
            blockchain_instance: (omitted — treated as the blockchain service/client).

        Notes:
            - Legacy kwargs "steem_instance" and "hive_instance" are accepted but deprecated; specifying more than one legacy instance raises ValueError. A DeprecationWarning is emitted when either is used.
            - The instance records the resolved blockchain client on self.blockchain and adjusts RPC next-node behavior based on `use_appbase`.
        """
        legacy_keys = {"steem_instance", "hive_instance"}
        legacy_instance = None
        for key in legacy_keys:
            if key in kwargs:
                if legacy_instance is not None:
                    raise ValueError(
                        f"Cannot specify both {key} and another legacy instance parameter"
                    )
                legacy_instance = kwargs.pop(key)
                warnings.warn(
                    f"Parameter '{key}' is deprecated. Use 'blockchain_instance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Prefer explicit blockchain_instance, then legacy
        if blockchain_instance is None and legacy_instance is not None:
            blockchain_instance = legacy_instance

        self.blockchain = blockchain_instance or shared_blockchain_instance()
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        posts = []
        try:
            # Try to use the bridge API first (preferred method)
            if author:
                bridge_query = {
                    "sort": "posts",
                    "account": author,
                    "limit": limit,
                }
                if start_permlink:
                    bridge_query["start_permlink"] = start_permlink
                posts = self.blockchain.rpc.get_account_posts(bridge_query, api="bridge")
                # Filter by before_date if provided
                if before_date and before_date != "1970-01-01T00:00:00":
                    filtered_posts = []
                    for post in posts:
                        if "created" in post and post["created"] < before_date:
                            filtered_posts.append(post)
                    posts = filtered_posts
        except Exception:
            # Fall back to old API methods
            if self.blockchain.rpc.get_use_appbase() and use_appbase:
                discussion_query = {
                    "author": author,
                    "start_permlink": start_permlink,
                    "before_date": before_date,
                    "limit": limit,
                }
                posts = self.blockchain.rpc.get_discussions_by_author_before_date(
                    discussion_query, api="tags"
                )["discussions"]
            if len(posts) == 0:
                posts = self.blockchain.rpc.get_discussions_by_author_before_date(
                    author, start_permlink, before_date, limit
                )
        if posts is None:
            posts = []
        if raw_data:
            super(Discussions_by_author_before_date, self).__init__([x for x in posts])
        else:
            super(Discussions_by_author_before_date, self).__init__(
                [Comment(x, lazy=lazy, blockchain_instance=self.blockchain) for x in posts]
            )


class Comment_discussions_by_payout(list):
    """Get comment_discussions_by_payout

    :param Query discussion_query: Defines the parameter for
        searching posts
    :param bool use_appbase: use condenser call when set to False, default is False
    :param bool raw_data: returns list of comments when False, default is False
    :param Hive blockchain_instance: Hive instance

    .. testcode::

        from nectar.discussions import Query, Comment_discussions_by_payout
        q = Query(limit=10)
        for h in Comment_discussions_by_payout(q):
            print(h)

    """

    def __init__(
        self,
        discussion_query,
        lazy=False,
        use_appbase=False,
        raw_data=False,
        blockchain_instance=None,
        **kwargs,
    ):
        # Handle legacy parameters
        """
        Initialize a Comment_discussions_by_payout iterator that fetches comment discussions sorted by payout.

        This constructor:
        - Accepts a discussion_query (dict) and reduces it to the supported keys: "tag", "limit", "filter_tags", "select_authors", "select_tags", "truncate_body", "start_author", "start_permlink".
        - Handles legacy keyword arguments "steem_instance" and "hive_instance": if present, the provided legacy instance is used as the blockchain instance and a DeprecationWarning is emitted; specifying more than one legacy key raises ValueError. An explicit blockchain_instance argument takes precedence over any legacy instance.
        - Configures the blockchain RPC node selection based on the blockchain instance's get_use_appbase() and the use_appbase flag.
        - Attempts to fetch posts via the bridge API (get_ranked_posts with sort "payout_comments"); on failure it falls back to the appbase "tags" path or the legacy get_comment_discussions_by_payout RPC. If the RPC returns None, it is treated as an empty list.
        - If raw_data is True, the underlying list is initialized with the raw post dicts; otherwise each post is wrapped in a Comment object (created with the lazy flag and the resolved blockchain instance) before initializing the superclass.

        Parameters:
            discussion_query (dict): Query parameters; expected keys include "tag", "limit", "start_author", "start_permlink", and related filters.
            lazy (bool): If True, Comment wrappers are created in lazy mode (defer loading of full data).
            use_appbase (bool): Prefer appbase/tag-based endpoints when True (affects RPC node selection and fallback behavior).
            raw_data (bool): If True, return raw post dicts instead of Comment objects.
            blockchain_instance: (optional) Blockchain client instance to use; if omitted a shared instance or a legacy instance (if provided via kwargs) will be used.

        Side effects:
            - May emit DeprecationWarning when "steem_instance" or "hive_instance" kwargs are used.
            - Raises ValueError if multiple legacy instance kwargs are provided.
            - Performs RPC calls (bridge and/or legacy/appbase) to fetch discussions.
        """
        legacy_keys = {"steem_instance", "hive_instance"}
        legacy_instance = None
        for key in legacy_keys:
            if key in kwargs:
                if legacy_instance is not None:
                    raise ValueError(
                        f"Cannot specify both {key} and another legacy instance parameter"
                    )
                legacy_instance = kwargs.pop(key)
                warnings.warn(
                    f"Parameter '{key}' is deprecated. Use 'blockchain_instance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Prefer explicit blockchain_instance, then legacy
        if blockchain_instance is None and legacy_instance is not None:
            blockchain_instance = legacy_instance

        self.blockchain = blockchain_instance or shared_blockchain_instance()
        reduced_query = {}
        for key in [
            "tag",
            "limit",
            "filter_tags",
            "select_authors",
            "select_tags",
            "truncate_body",
            "start_author",
            "start_permlink",
        ]:
            if key in discussion_query:
                reduced_query[key] = discussion_query[key]
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        posts = []
        try:
            # Try to use the bridge API first (preferred method)
            bridge_query = {
                "sort": "payout_comments",
                "tag": reduced_query.get("tag", ""),
                "observer": "",
            }
            if "limit" in reduced_query:
                bridge_query["limit"] = reduced_query["limit"]
            if "start_author" in reduced_query and "start_permlink" in reduced_query:
                bridge_query["start_author"] = reduced_query["start_author"]
                bridge_query["start_permlink"] = reduced_query["start_permlink"]
            posts = self.blockchain.rpc.get_ranked_posts(bridge_query, api="bridge")
        except Exception:
            # Fall back to old API methods
            if self.blockchain.rpc.get_use_appbase() and use_appbase:
                try:
                    posts = self.blockchain.rpc.get_comment_discussions_by_payout(
                        reduced_query, api="tags"
                    )["discussions"]
                except Exception:
                    posts = []
            if len(posts) == 0:
                posts = self.blockchain.rpc.get_comment_discussions_by_payout(reduced_query)
        if posts is None:
            posts = []
        if raw_data:
            super(Comment_discussions_by_payout, self).__init__([x for x in posts])
        else:
            super(Comment_discussions_by_payout, self).__init__(
                [Comment(x, lazy=lazy, blockchain_instance=self.blockchain) for x in posts]
            )


class Post_discussions_by_payout(list):
    """Get post_discussions_by_payout

    :param Query discussion_query: Defines the parameter for
        searching posts
    :param bool use_appbase: use condenser call when set to False, default is False
    :param bool raw_data: returns list of comments when False, default is False
    :param Hive blockchain_instance: Hive instance

    .. testcode::

        from nectar.discussions import Query, Post_discussions_by_payout
        q = Query(limit=10)
        for h in Post_discussions_by_payout(q):
            print(h)

    """

    def __init__(
        self,
        discussion_query,
        lazy=False,
        use_appbase=False,
        raw_data=False,
        blockchain_instance=None,
        **kwargs,
    ):
        # Handle legacy parameters
        """
        Initialize Post_discussions_by_payout: fetches post discussions sorted by payout and populates the list (raw dicts or Comment objects).

        Parameters:
            discussion_query (dict): Query parameters; relevant keys: 'tag', 'limit', 'filter_tags', 'select_authors',
                'select_tags', 'truncate_body', 'start_author', 'start_permlink'. Only these keys are used from the dict.
            lazy (bool): If False, wrap results immediately in Comment objects; if True, create Comment objects with lazy loading.
            use_appbase (bool): When True, prefer appbase/tag-based RPC fallbacks if the bridge API is unavailable.
            raw_data (bool): If True, store raw post dicts instead of wrapping them in Comment objects.

        Notes and side effects:
            - Accepts legacy keyword args 'steem_instance' or 'hive_instance' in kwargs; if provided, emits a DeprecationWarning and uses the given instance as the blockchain instance. Supplying more than one legacy instance parameter raises ValueError.
            - The explicit 'blockchain_instance' argument overrides any legacy instance.
            - Resolves and stores the blockchain instance on self.blockchain (or uses a shared instance).
            - Configures the blockchain RPC's next-node behavior based on appbase usage and use_appbase.
            - Attempts to fetch posts via the bridge API first, then falls back to appbase/tag endpoints, and finally to legacy RPC calls.
            - Populates the instance by calling the superclass constructor with either raw post dicts or Comment-wrapped posts.

        Raises:
            ValueError: If more than one legacy instance parameter is provided in kwargs.
        """
        legacy_keys = {"steem_instance", "hive_instance"}
        legacy_instance = None
        for key in legacy_keys:
            if key in kwargs:
                if legacy_instance is not None:
                    raise ValueError(
                        f"Cannot specify both {key} and another legacy instance parameter"
                    )
                legacy_instance = kwargs.pop(key)
                warnings.warn(
                    f"Parameter '{key}' is deprecated. Use 'blockchain_instance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Prefer explicit blockchain_instance, then legacy
        if blockchain_instance is None and legacy_instance is not None:
            blockchain_instance = legacy_instance

        self.blockchain = blockchain_instance or shared_blockchain_instance()
        reduced_query = {}
        for key in [
            "tag",
            "limit",
            "filter_tags",
            "select_authors",
            "select_tags",
            "truncate_body",
            "start_author",
            "start_permlink",
        ]:
            if key in discussion_query:
                reduced_query[key] = discussion_query[key]
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        posts = []
        try:
            # Try to use the bridge API first (preferred method)
            bridge_query = {
                "sort": "payout",
                "tag": reduced_query.get("tag", ""),
                "observer": "",
            }
            if "limit" in reduced_query:
                bridge_query["limit"] = reduced_query["limit"]
            if "start_author" in reduced_query and "start_permlink" in reduced_query:
                bridge_query["start_author"] = reduced_query["start_author"]
                bridge_query["start_permlink"] = reduced_query["start_permlink"]
            posts = self.blockchain.rpc.get_ranked_posts(bridge_query, api="bridge")
        except Exception:
            # Fall back to old API methods
            if self.blockchain.rpc.get_use_appbase() and use_appbase:
                try:
                    posts = self.blockchain.rpc.get_post_discussions_by_payout(
                        reduced_query, api="tags"
                    )["discussions"]
                except Exception:
                    posts = []
            if len(posts) == 0:
                posts = self.blockchain.rpc.get_post_discussions_by_payout(reduced_query)
        if posts is None:
            posts = []
        if raw_data:
            super(Post_discussions_by_payout, self).__init__([x for x in posts])
        else:
            super(Post_discussions_by_payout, self).__init__(
                [Comment(x, lazy=lazy, blockchain_instance=self.blockchain) for x in posts]
            )


class Discussions_by_created(list):
    """Get discussions_by_created

    :param Query discussion_query: Defines the parameter for
        searching posts
    :param bool use_appbase: use condenser call when set to False, default is False
    :param bool raw_data: returns list of comments when False, default is False
    :param Hive blockchain_instance: Hive instance

    .. testcode::

        from nectar.discussions import Query, Discussions_by_created
        q = Query(limit=10)
        for h in Discussions_by_created(q):
            print(h)

    """

    def __init__(
        self,
        discussion_query,
        lazy=False,
        use_appbase=False,
        raw_data=False,
        blockchain_instance=None,
        **kwargs,
    ):
        # Handle legacy parameters
        """
        Initialize a Discussions_by_created fetcher and populate it with posts matching the query.

        Builds a reduced query from `discussion_query`, resolves the blockchain instance (accepting the deprecated legacy kwargs "steem_instance" or "hive_instance" with a DeprecationWarning), configures RPC node selection, attempts to fetch posts via the bridge API and falls back to appbase/legacy RPC endpoints. The instance is initialized (as a list) with raw post dicts when `raw_data` is True or with wrapped Comment objects otherwise.

        Parameters:
            discussion_query (dict): Incoming query dict; keys used include "tag", "limit", "filter_tags",
                "select_authors", "select_tags", "truncate_body", "start_author", and "start_permlink".
            lazy (bool): If False (default), Comment wrappers are fully initialized; if True, Comment objects
                are created in lazy mode.
            use_appbase (bool): When True, prefer appbase/tag RPC endpoints on fallback.
            raw_data (bool): When True, populate the instance with raw post dictionaries instead of Comment objects.
            blockchain_instance: Omitted from param docs as a shared/blockchain client service; if None, a shared
                instance is used. Legacy kwargs "steem_instance" and "hive_instance" are accepted but deprecated.

        Raises:
            ValueError: If more than one legacy instance parameter is provided via kwargs.
            DeprecationWarning: Emitted when a legacy instance kwarg is used (not an exception).

        Side effects:
            - Calls `self.blockchain.rpc.set_next_node_on_empty_reply(...)`.
            - Performs remote RPC calls which may raise exceptions that trigger fallback behavior.
        """
        legacy_keys = {"steem_instance", "hive_instance"}
        legacy_instance = None
        for key in legacy_keys:
            if key in kwargs:
                if legacy_instance is not None:
                    raise ValueError(
                        f"Cannot specify both {key} and another legacy instance parameter"
                    )
                legacy_instance = kwargs.pop(key)
                warnings.warn(
                    f"Parameter '{key}' is deprecated. Use 'blockchain_instance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Prefer explicit blockchain_instance, then legacy
        if blockchain_instance is None and legacy_instance is not None:
            blockchain_instance = legacy_instance

        self.blockchain = blockchain_instance or shared_blockchain_instance()
        reduced_query = {}
        for key in [
            "tag",
            "limit",
            "filter_tags",
            "select_authors",
            "select_tags",
            "truncate_body",
            "start_author",
            "start_permlink",
        ]:
            if key in discussion_query:
                reduced_query[key] = discussion_query[key]
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        posts = []
        try:
            # Try to use the bridge API first (preferred method)
            bridge_query = {
                "sort": "created",
                "tag": reduced_query.get("tag", ""),
                "observer": "",
            }
            if "limit" in reduced_query:
                bridge_query["limit"] = reduced_query["limit"]
            if "start_author" in reduced_query and "start_permlink" in reduced_query:
                bridge_query["start_author"] = reduced_query["start_author"]
                bridge_query["start_permlink"] = reduced_query["start_permlink"]
            posts = self.blockchain.rpc.get_ranked_posts(bridge_query, api="bridge")
        except Exception:
            # Fall back to old API methods
            if self.blockchain.rpc.get_use_appbase() and use_appbase:
                try:
                    posts = self.blockchain.rpc.get_discussions_by_created(
                        reduced_query, api="tags"
                    )["discussions"]
                except Exception:
                    posts = []
            if len(posts) == 0:
                posts = self.blockchain.rpc.get_discussions_by_created(reduced_query)
        if posts is None:
            posts = []
        if raw_data:
            super(Discussions_by_created, self).__init__([x for x in posts])
        else:
            super(Discussions_by_created, self).__init__(
                [Comment(x, lazy=lazy, blockchain_instance=self.blockchain) for x in posts]
            )


class Discussions_by_active(list):
    """get_discussions_by_active

    :param Query discussion_query: Defines the parameter
        searching posts
    :param bool use_appbase: use condenser call when set to False, default is False
    :param bool raw_data: returns list of comments when False, default is False
    :param Hive blockchain_instance: Hive() instance to use when accesing a RPC

    .. testcode::

        from nectar.discussions import Query, Discussions_by_active
        q = Query(limit=10)
        for h in Discussions_by_active(q):
            print(h)

    """

    def __init__(
        self,
        discussion_query,
        lazy=False,
        use_appbase=False,
        raw_data=False,
        blockchain_instance=None,
        **kwargs,
    ):
        # Handle legacy parameters
        """
        Initialize Discussions_by_active: fetch discussions sorted by "active" and populate the sequence.

        This initializer reduces the provided discussion_query to the subset of keys used by the active discussion endpoint,
        configures the blockchain RPC node selection behavior, attempts to fetch posts from the bridge API (preferred),
        and falls back to appbase/tags or legacy RPC endpoints when needed. Results are stored in the underlying sequence
        as raw dicts if raw_data is True, otherwise each post is wrapped in a Comment object with the supplied lazy flag
        and resolved blockchain instance.

        Parameters:
            discussion_query (dict): Query parameters (may include tag, limit, filter_tags, select_authors,
                select_tags, truncate_body, start_author, start_permlink, and others).
            lazy (bool): If False (default), wrap results in Comment objects that may eagerly access data; if True, wrap
                with lazy Comment instances.
            use_appbase (bool): Prefer appbase/tags endpoints when falling back from the bridge API.
            raw_data (bool): If True, keep fetched posts as raw data dicts instead of wrapping in Comment objects.
            blockchain_instance: Optional blockchain client/instance to use; if omitted a shared instance is used.

        Legacy behavior:
            Accepts deprecated kwargs "steem_instance" and "hive_instance". If either is provided it will be used as the
            blockchain instance and a DeprecationWarning is emitted. Providing more than one legacy instance parameter
            raises ValueError.

        Raises:
            ValueError: If more than one legacy instance parameter is supplied (e.g., both "steem_instance" and "hive_instance").
        """
        legacy_keys = {"steem_instance", "hive_instance"}
        legacy_instance = None
        for key in legacy_keys:
            if key in kwargs:
                if legacy_instance is not None:
                    raise ValueError(
                        f"Cannot specify both {key} and another legacy instance parameter"
                    )
                legacy_instance = kwargs.pop(key)
                warnings.warn(
                    f"Parameter '{key}' is deprecated. Use 'blockchain_instance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Prefer explicit blockchain_instance, then legacy
        if blockchain_instance is None and legacy_instance is not None:
            blockchain_instance = legacy_instance

        self.blockchain = blockchain_instance or shared_blockchain_instance()
        reduced_query = {}
        for key in [
            "tag",
            "limit",
            "filter_tags",
            "select_authors",
            "select_tags",
            "truncate_body",
            "start_author",
            "start_permlink",
        ]:
            if key in discussion_query:
                reduced_query[key] = discussion_query[key]
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        posts = []
        try:
            # Try to use the bridge API first (preferred method)
            bridge_query = {
                "sort": "active",
                "tag": reduced_query.get("tag", ""),
                "observer": "",
            }
            if "limit" in reduced_query:
                bridge_query["limit"] = reduced_query["limit"]
            if "start_author" in reduced_query and "start_permlink" in reduced_query:
                bridge_query["start_author"] = reduced_query["start_author"]
                bridge_query["start_permlink"] = reduced_query["start_permlink"]
            posts = self.blockchain.rpc.get_ranked_posts(bridge_query, api="bridge")
        except Exception:
            # Fall back to old API methods
            if self.blockchain.rpc.get_use_appbase() and use_appbase:
                try:
                    posts = self.blockchain.rpc.get_discussions_by_active(
                        reduced_query, api="tags"
                    )["discussions"]
                except Exception:
                    posts = []
            if len(posts) == 0:
                posts = self.blockchain.rpc.get_discussions_by_active(reduced_query)
        if posts is None:
            posts = []
        if raw_data:
            super(Discussions_by_active, self).__init__([x for x in posts])
        else:
            super(Discussions_by_active, self).__init__(
                [Comment(x, lazy=lazy, blockchain_instance=self.blockchain) for x in posts]
            )


class Discussions_by_cashout(list):
    """Get discussions_by_cashout. This query seems to be broken at the moment.
    The output is always empty.

    :param Query discussion_query: Defines the parameter
        searching posts
    :param bool use_appbase: use condenser call when set to False, default is False
    :param bool raw_data: returns list of comments when False, default is False
    :param Hive blockchain_instance: Hive instance

    .. testcode::

        from nectar.discussions import Query, Discussions_by_cashout
        q = Query(limit=10)
        for h in Discussions_by_cashout(q):
            print(h)

    """

    def __init__(
        self,
        discussion_query,
        lazy=False,
        use_appbase=False,
        raw_data=False,
        blockchain_instance=None,
        **kwargs,
    ):
        # Handle legacy parameters
        """
        Initialize Discussions_by_cashout fetcher.

        Sets up internal blockchain instance (accepting deprecated `steem_instance`/`hive_instance` in kwargs with a DeprecationWarning; specifying more than one legacy key raises ValueError), configures RPC pagination behavior, and loads a page of discussions using the bridge API (sort "payout") with fallbacks to appbase (`get_discussions_by_cashout(..., api="tags")`) or legacy RPC. Results are stored as raw dicts when `raw_data` is True, otherwise wrapped into Comment objects created with the resolved blockchain instance and `lazy` flag.

        Parameters:
            discussion_query: dict-like query containing keys such as "tag", "limit", "start_author", and "start_permlink". Only these keys are used from the provided query.
            lazy: bool — if False, Comment wrappers are created eagerly; if True, they are created in lazy mode.
            use_appbase: bool — when True and the RPC supports appbase, prefer appbase ("tags") fallback endpoints.
            raw_data: bool — when True, do not wrap results into Comment objects.

        Side effects:
            - Emits DeprecationWarning when `steem_instance` or `hive_instance` is provided in kwargs.
            - May raise ValueError if multiple legacy instance kwargs are supplied.
            - Calls RPC methods which may perform network I/O.
        """
        legacy_keys = {"steem_instance", "hive_instance"}
        legacy_instance = None
        for key in legacy_keys:
            if key in kwargs:
                if legacy_instance is not None:
                    raise ValueError(
                        f"Cannot specify both {key} and another legacy instance parameter"
                    )
                legacy_instance = kwargs.pop(key)
                warnings.warn(
                    f"Parameter '{key}' is deprecated. Use 'blockchain_instance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Prefer explicit blockchain_instance, then legacy
        if blockchain_instance is None and legacy_instance is not None:
            blockchain_instance = legacy_instance

        self.blockchain = blockchain_instance or shared_blockchain_instance()
        reduced_query = {}
        for key in [
            "tag",
            "limit",
            "filter_tags",
            "select_authors",
            "select_tags",
            "truncate_body",
            "start_author",
            "start_permlink",
        ]:
            if key in discussion_query:
                reduced_query[key] = discussion_query[key]
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        posts = []
        try:
            # Try to use the bridge API first (preferred method)
            # Note: 'payout' is the closest sort to 'cashout' in bridge API
            bridge_query = {
                "sort": "payout",
                "tag": reduced_query.get("tag", ""),
                "observer": "",
            }
            if "limit" in reduced_query:
                bridge_query["limit"] = reduced_query["limit"]
            if "start_author" in reduced_query and "start_permlink" in reduced_query:
                bridge_query["start_author"] = reduced_query["start_author"]
                bridge_query["start_permlink"] = reduced_query["start_permlink"]
            posts = self.blockchain.rpc.get_ranked_posts(bridge_query, api="bridge")
        except Exception:
            # Fall back to old API methods
            if self.blockchain.rpc.get_use_appbase() and use_appbase:
                try:
                    posts = self.blockchain.rpc.get_discussions_by_cashout(
                        reduced_query, api="tags"
                    )["discussions"]
                except Exception:
                    posts = []
            if len(posts) == 0:
                posts = self.blockchain.rpc.get_discussions_by_cashout(reduced_query)
        if posts is None:
            posts = []
        if raw_data:
            super(Discussions_by_cashout, self).__init__([x for x in posts])
        else:
            super(Discussions_by_cashout, self).__init__(
                [Comment(x, lazy=lazy, blockchain_instance=self.blockchain) for x in posts]
            )


class Discussions_by_votes(list):
    """Get discussions_by_votes

    :param Query discussion_query: Defines the parameter
        searching posts
    :param bool use_appbase: use condenser call when set to False, default is False
    :param bool raw_data: returns list of comments when False, default is False
    :param Hive blockchain_instance: Hive instance

    .. testcode::

        from nectar.discussions import Query, Discussions_by_votes
        q = Query(limit=10)
        for h in Discussions_by_votes(q):
            print(h)

    """

    def __init__(
        self,
        discussion_query,
        lazy=False,
        use_appbase=False,
        raw_data=False,
        blockchain_instance=None,
        **kwargs,
    ):
        # Handle legacy parameters
        """
        Initialize Discussions_by_votes: fetch discussions approximating "votes" and store results.

        This initializer prepares and executes a query for discussions ordered by votes. Because the bridge API does not provide a direct "votes" sort, it attempts a bridge query using the "trending" sort, then falls back to appbase (`get_discussions_by_votes` with api="tags") and finally to the legacy RPC method. Results are normalized to an empty list on failure. If raw_data is False, each result is wrapped in a Comment object with the resolved blockchain instance; if True, raw post dicts are kept.

        Parameters:
            discussion_query (dict): Original query parameters; only a reduced subset is used:
                tag, limit, filter_tags, select_authors, select_tags, truncate_body,
                start_author, start_permlink, when present.
            lazy (bool): If False (default), Comment wrappers may load data immediately; if True, they remain lazy.
            use_appbase (bool): When True, prefer appbase/tagged APIs when falling back from the bridge.
            raw_data (bool): If True, keep raw post dicts instead of wrapping them in Comment objects.
            blockchain_instance: Blockchain client instance to use. If not provided, a shared instance is used.
            **kwargs: Accepts legacy parameters "steem_instance" or "hive_instance" (deprecated). If a legacy instance is supplied and blockchain_instance is not provided, it will be used. Supplying more than one legacy instance raises ValueError and emits a DeprecationWarning for each used legacy key.

        Side effects:
            - Resolves and stores self.blockchain.
            - Calls self.blockchain.rpc.set_next_node_on_empty_reply(...) to influence RPC node selection.

        Raises:
            ValueError: If multiple legacy instance kwargs are provided at once.
        """
        legacy_keys = {"steem_instance", "hive_instance"}
        legacy_instance = None
        for key in legacy_keys:
            if key in kwargs:
                if legacy_instance is not None:
                    raise ValueError(
                        f"Cannot specify both {key} and another legacy instance parameter"
                    )
                legacy_instance = kwargs.pop(key)
                warnings.warn(
                    f"Parameter '{key}' is deprecated. Use 'blockchain_instance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Prefer explicit blockchain_instance, then legacy
        if blockchain_instance is None and legacy_instance is not None:
            blockchain_instance = legacy_instance

        self.blockchain = blockchain_instance or shared_blockchain_instance()
        reduced_query = {}
        for key in [
            "tag",
            "limit",
            "filter_tags",
            "select_authors",
            "select_tags",
            "truncate_body",
            "start_author",
            "start_permlink",
        ]:
            if key in discussion_query:
                reduced_query[key] = discussion_query[key]
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        posts = []
        try:
            # Try to use the bridge API first (preferred method)
            # Note: There is no direct 'votes' sort in bridge API, so we'll approximate using trending
            bridge_query = {
                "sort": "trending",
                "tag": reduced_query.get("tag", ""),
                "observer": "",
            }
            if "limit" in reduced_query:
                bridge_query["limit"] = reduced_query["limit"]
            if "start_author" in reduced_query and "start_permlink" in reduced_query:
                bridge_query["start_author"] = reduced_query["start_author"]
                bridge_query["start_permlink"] = reduced_query["start_permlink"]
            posts = self.blockchain.rpc.get_ranked_posts(bridge_query, api="bridge")
        except Exception:
            # Fall back to old API methods
            if self.blockchain.rpc.get_use_appbase() and use_appbase:
                try:
                    posts = self.blockchain.rpc.get_discussions_by_votes(reduced_query, api="tags")[
                        "discussions"
                    ]
                except Exception:
                    posts = []
            if len(posts) == 0:
                posts = self.blockchain.rpc.get_discussions_by_votes(reduced_query)
        if posts is None:
            posts = []
        if raw_data:
            super(Discussions_by_votes, self).__init__([x for x in posts])
        else:
            super(Discussions_by_votes, self).__init__(
                [Comment(x, lazy=lazy, blockchain_instance=self.blockchain) for x in posts]
            )


class Discussions_by_children(list):
    """Get discussions by children

    :param Query discussion_query: Defines the parameter
        searching posts
    :param bool use_appbase: use condenser call when set to False, default is False
    :param bool raw_data: returns list of comments when False, default is False
    :param Hive blockchain_instance: Hive instance

    .. testcode::

        from nectar.discussions import Query, Discussions_by_children
        q = Query(limit=10)
        for h in Discussions_by_children(q):
            print(h)

    """

    def __init__(
        self,
        discussion_query,
        lazy=False,
        use_appbase=False,
        raw_data=False,
        blockchain_instance=None,
        **kwargs,
    ):
        # Handle legacy parameters
        """
        Initialize a Discussions_by_children fetcher that yields child (reply) discussions for a tag/post.

        Builds a reduced query from the provided discussion_query, prefers an explicit blockchain_instance (or a legacy
        steem_instance/hive_instance passed via kwargs), and attempts to fetch discussions via the bridge API before
        falling back to appbase or legacy RPC methods. Results are stored as raw dicts when raw_data is True or wrapped
        as Comment objects otherwise.

        Parameters documented only when non-obvious:
            discussion_query: dict-like query containing keys such as "tag", "limit", "filter_tags",
                "select_authors", "select_tags", "truncate_body", "start_author", and "start_permlink".
                Only those keys are preserved for the reduced query used to fetch discussions.

        Behavior and side effects:
            - If blockchain_instance is None, a shared blockchain instance is used.
            - Accepts legacy kwargs "steem_instance" or "hive_instance"; if present and blockchain_instance is not
              provided, that legacy instance is used. Using a legacy key emits a DeprecationWarning advising to use
              blockchain_instance instead.
            - Raises ValueError if more than one legacy instance key is provided.
            - Calls self.blockchain.rpc.set_next_node_on_empty_reply(...) to configure RPC node selection based on
              whether the RPC is using appbase and the use_appbase flag.
            - Primary fetch path: bridge API via get_ranked_posts with sort "trending" (bridge has no direct "children"
              sort). Falls back to get_discussions_by_children via appbase ("tags" API) or the legacy RPC call as needed.
            - Normalizes None responses to an empty list.
            - Populates the instance with raw posts when raw_data is True, or with Comment-wrapped posts when False.

        Does not return a value.
        """
        legacy_keys = {"steem_instance", "hive_instance"}
        legacy_instance = None
        for key in legacy_keys:
            if key in kwargs:
                if legacy_instance is not None:
                    raise ValueError(
                        f"Cannot specify both {key} and another legacy instance parameter"
                    )
                legacy_instance = kwargs.pop(key)
                warnings.warn(
                    f"Parameter '{key}' is deprecated. Use 'blockchain_instance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Prefer explicit blockchain_instance, then legacy
        if blockchain_instance is None and legacy_instance is not None:
            blockchain_instance = legacy_instance

        self.blockchain = blockchain_instance or shared_blockchain_instance()
        reduced_query = {}
        for key in [
            "tag",
            "limit",
            "filter_tags",
            "select_authors",
            "select_tags",
            "truncate_body",
            "start_author",
            "start_permlink",
        ]:
            if key in discussion_query:
                reduced_query[key] = discussion_query[key]
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        posts = []
        try:
            # Try to use the bridge API first (preferred method)
            # Note: There is no direct 'children' sort in bridge API, we'll use 'trending' as a fallback
            bridge_query = {
                "sort": "trending",
                "tag": reduced_query.get("tag", ""),
                "observer": "",
            }
            if "limit" in reduced_query:
                bridge_query["limit"] = reduced_query["limit"]
            if "start_author" in reduced_query and "start_permlink" in reduced_query:
                bridge_query["start_author"] = reduced_query["start_author"]
                bridge_query["start_permlink"] = reduced_query["start_permlink"]
            posts = self.blockchain.rpc.get_ranked_posts(bridge_query, api="bridge")
            # We could try to sort posts by their children count here if needed
        except Exception:
            # Fall back to old API methods
            if self.blockchain.rpc.get_use_appbase() and use_appbase:
                try:
                    posts = self.blockchain.rpc.get_discussions_by_children(
                        reduced_query, api="tags"
                    )["discussions"]
                except Exception:
                    posts = []
            if len(posts) == 0:
                posts = self.blockchain.rpc.get_discussions_by_children(reduced_query)
        if posts is None:
            posts = []
        if raw_data:
            super(Discussions_by_children, self).__init__([x for x in posts])
        else:
            super(Discussions_by_children, self).__init__(
                [Comment(x, lazy=lazy, blockchain_instance=self.blockchain) for x in posts]
            )


class Discussions_by_hot(list):
    """Get discussions by hot

    :param Query discussion_query: Defines the parameter
        searching posts
    :param bool use_appbase: use condenser call when set to False, default is False
    :param bool raw_data: returns list of comments when False, default is False
    :param Hive blockchain_instance: Hive instance

    .. testcode::

        from nectar.discussions import Query, Discussions_by_hot
        q = Query(limit=10, tag="hive")
        for h in Discussions_by_hot(q):
            print(h)

    """

    def __init__(
        self,
        discussion_query,
        lazy=False,
        use_appbase=False,
        raw_data=False,
        blockchain_instance=None,
        **kwargs,
    ):
        # Handle legacy parameters
        """
        Initialize a Discussions_by_hot iterator that fetches "hot" discussions.

        Builds a reduced query from the provided discussion_query, prefers the bridge API for fetching ranked posts
        with a fallback to appbase or legacy RPC methods, and stores results either as raw dicts or wrapped Comment objects.

        Parameters:
            discussion_query (dict): Query parameters (e.g., tag, limit, start_author, start_permlink). Only a subset is used.
            lazy (bool): If False, Comment objects will be fully initialized; if True, they are created for lazy loading.
            use_appbase (bool): When True prefer appbase/tagged endpoints as a fallback; also affects RPC next-node selection.
            raw_data (bool): If True store and return raw post dicts; if False wrap posts in Comment objects.
            kwargs: Deprecated-only legacy parameters `steem_instance` or `hive_instance` may be provided; if present they are used
                as the blockchain instance and a DeprecationWarning is emitted.

        Side effects:
            - Resolves and assigns self.blockchain (from blockchain_instance, legacy kwargs, or shared instance).
            - Calls self.blockchain.rpc.set_next_node_on_empty_reply(...) to influence RPC backend selection.
            - Performs RPC calls (bridge get_ranked_posts or fallback get_discussions_by_hot), which may raise RPC-related exceptions.

        Raises:
            ValueError: If multiple legacy instance keys are provided in kwargs (e.g., both `steem_instance` and `hive_instance`).
        """
        legacy_keys = {"steem_instance", "hive_instance"}
        legacy_instance = None
        for key in legacy_keys:
            if key in kwargs:
                if legacy_instance is not None:
                    raise ValueError(
                        f"Cannot specify both {key} and another legacy instance parameter"
                    )
                legacy_instance = kwargs.pop(key)
                warnings.warn(
                    f"Parameter '{key}' is deprecated. Use 'blockchain_instance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Prefer explicit blockchain_instance, then legacy
        if blockchain_instance is None and legacy_instance is not None:
            blockchain_instance = legacy_instance

        self.blockchain = blockchain_instance or shared_blockchain_instance()
        reduced_query = {}
        for key in [
            "tag",
            "limit",
            "filter_tags",
            "select_authors",
            "select_tags",
            "truncate_body",
            "start_author",
            "start_permlink",
        ]:
            if key in discussion_query:
                reduced_query[key] = discussion_query[key]
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        posts = []
        try:
            # Try to use the bridge API first (preferred method)
            bridge_query = {
                "sort": "hot",
                "tag": reduced_query.get("tag", ""),
                "observer": "",
            }
            if "limit" in reduced_query:
                bridge_query["limit"] = reduced_query["limit"]
            if "start_author" in reduced_query and "start_permlink" in reduced_query:
                bridge_query["start_author"] = reduced_query["start_author"]
                bridge_query["start_permlink"] = reduced_query["start_permlink"]
            posts = self.blockchain.rpc.get_ranked_posts(bridge_query, api="bridge")
        except Exception:
            # Fall back to old API methods
            if self.blockchain.rpc.get_use_appbase() and use_appbase:
                try:
                    posts = self.blockchain.rpc.get_discussions_by_hot(reduced_query, api="tags")[
                        "discussions"
                    ]
                except Exception:
                    posts = []
            if len(posts) == 0:
                posts = self.blockchain.rpc.get_discussions_by_hot(reduced_query)
        if posts is None:
            posts = []
        if raw_data:
            super(Discussions_by_hot, self).__init__([x for x in posts])
        else:
            super(Discussions_by_hot, self).__init__(
                [Comment(x, lazy=lazy, blockchain_instance=self.blockchain) for x in posts]
            )


class Discussions_by_feed(list):
    """Get discussions by feed

    :param Query discussion_query: Defines the parameter
        searching posts, tag musst be set to a username
    :param bool use_appbase: use condenser call when set to False, default is False
    :param bool raw_data: returns list of comments when False, default is False
    :param Hive blockchain_instance: Hive instance

    .. testcode::

        from nectar.discussions import Query, Discussions_by_feed
        q = Query(limit=10, tag="hive")
        for h in Discussions_by_feed(q):
            print(h)

    """

    def __init__(
        self,
        discussion_query,
        lazy=False,
        use_appbase=False,
        raw_data=False,
        blockchain_instance=None,
        **kwargs,
    ):
        # Handle legacy parameters
        """
        Initialize a Discussions_by_feed instance that fetches a user's feed discussions.

        Builds an internal, reduced query from discussion_query, prefers the bridge API to fetch account feed posts
        (using discussion_query["tag"] as the account), falls back to appbase or legacy RPCs on error, and stores
        results as raw dicts (if raw_data=True) or wrapped Comment objects.

        Parameters:
            discussion_query (dict): Query parameters. Must include "tag" to specify the account; supported keys
                copied into the internal query are: "tag", "limit", "filter_tags", "select_authors",
                "select_tags", "truncate_body", "start_author", "start_permlink".
            lazy (bool): If False (default), created Comment objects are fully initialized; if True, Comment objects
                are created in lazy mode to defer loading heavy fields.
            use_appbase (bool): When True, prefer appbase/tag-based endpoints as a fallback if the bridge call fails.
            raw_data (bool): If True, the instance is populated with raw post dicts; otherwise each post is wrapped
                in a Comment object with the resolved blockchain instance.
            blockchain_instance: If provided, used for RPC calls; otherwise a shared blockchain instance is used.
                (This parameter is a blockchain client and is intentionally not documented as a conventional param.)

        Behavior:
            - Accepts deprecated legacy kwargs "steem_instance" or "hive_instance"; if provided, they are mapped to
              the blockchain instance and a DeprecationWarning is emitted. Supplying more than one legacy instance
              parameter raises ValueError.
            - Calls blockchain.rpc.set_next_node_on_empty_reply(...) using the conjunction of the RPC's
              appbase usage and the use_appbase flag to influence node selection.
            - Attempts to fetch posts via blockchain.rpc.get_account_posts(..., api="bridge") first.
            - On any bridge error, falls back to get_discussions_by_feed(...) using appbase/tags when available,
              then to legacy RPC if necessary.
            - Ensures posts is always a list (never None) before populating the base list.

        Raises:
            ValueError: If more than one legacy instance parameter (e.g., both "steem_instance" and "hive_instance")
                is provided in kwargs.
        """
        legacy_keys = {"steem_instance", "hive_instance"}
        legacy_instance = None
        for key in legacy_keys:
            if key in kwargs:
                if legacy_instance is not None:
                    raise ValueError(
                        f"Cannot specify both {key} and another legacy instance parameter"
                    )
                legacy_instance = kwargs.pop(key)
                warnings.warn(
                    f"Parameter '{key}' is deprecated. Use 'blockchain_instance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Prefer explicit blockchain_instance, then legacy
        if blockchain_instance is None and legacy_instance is not None:
            blockchain_instance = legacy_instance

        self.blockchain = blockchain_instance or shared_blockchain_instance()
        reduced_query = {}
        for key in [
            "tag",
            "limit",
            "filter_tags",
            "select_authors",
            "select_tags",
            "truncate_body",
            "start_author",
            "start_permlink",
        ]:
            if key in discussion_query:
                reduced_query[key] = discussion_query[key]
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        posts = []
        try:
            # Try to use the bridge API first (preferred method)
            account = reduced_query.get("tag", "")
            if account:
                bridge_query = {
                    "sort": "feed",
                    "account": account,
                    "limit": reduced_query.get("limit", 20),
                }
                if "start_author" in reduced_query and "start_permlink" in reduced_query:
                    bridge_query["start_author"] = reduced_query["start_author"]
                    bridge_query["start_permlink"] = reduced_query["start_permlink"]
                posts = self.blockchain.rpc.get_account_posts(bridge_query, api="bridge")
        except Exception:
            # Fall back to old API methods
            if self.blockchain.rpc.get_use_appbase() and use_appbase:
                try:
                    posts = self.blockchain.rpc.get_discussions_by_feed(reduced_query, api="tags")[
                        "discussions"
                    ]
                except Exception:
                    posts = []
            if len(posts) == 0:
                posts = self.blockchain.rpc.get_discussions_by_feed(reduced_query)
        if posts is None:
            posts = []
        if raw_data:
            super(Discussions_by_feed, self).__init__([x for x in posts])
        else:
            super(Discussions_by_feed, self).__init__(
                [Comment(x, lazy=lazy, blockchain_instance=self.blockchain) for x in posts]
            )


class Discussions_by_blog(list):
    """Get discussions by blog

    :param Query discussion_query: Defines the parameter
        searching posts, tag musst be set to a username
    :param bool use_appbase: use condenser call when set to False, default is False
    :param bool raw_data: returns list of comments when False, default is False
    :param Hive blockchain_instance: Hive instance

    .. testcode::

        from nectar.discussions import Query, Discussions_by_blog
        q = Query(limit=10)
        for h in Discussions_by_blog(q):
            print(h)

    """

    def __init__(
        self,
        discussion_query,
        lazy=False,
        use_appbase=False,
        raw_data=False,
        blockchain_instance=None,
        **kwargs,
    ):
        # Handle legacy parameters
        """
        Initialize a Discussions_by_blog fetcher that retrieves a user's blog posts.

        Builds a reduced query from discussion_query (accepts keys like "tag" (account), "limit",
        "start_author", "start_permlink", "filter_tags", "select_authors", "select_tags",
        "truncate_body"), resolves the blockchain instance to use, and attempts to fetch posts
        via the bridge API (get_account_posts) falling back to appbase/legacy RPCs (get_discussions_by_blog).
        Results are stored as raw dicts when raw_data is True, or wrapped as Comment objects when False.

        Parameters:
            discussion_query (dict): Query parameters that may include "tag" (the account name),
                "limit", "start_author", "start_permlink", and other optional filter/select keys.
            lazy (bool): If False, Comment wrappers will be fully initialized; if True, they are lazy.
            use_appbase (bool): When True prefer appbase/tag APIs where available (affects RPC routing).
            raw_data (bool): If True, keep fetched posts as raw dicts instead of Comment instances.
            blockchain_instance: Optional blockchain client to use; if not provided, a shared instance is used.

        Notes:
            - Legacy keyword arguments "steem_instance" and "hive_instance" are accepted via kwargs,
              will emit a DeprecationWarning and be mapped to blockchain_instance. Supplying more than
              one legacy instance parameter raises ValueError.
            - The RPC client's next-node behavior is adjusted based on appbase usage to influence
              which backend is attempted first.
        """
        legacy_keys = {"steem_instance", "hive_instance"}
        legacy_instance = None
        for key in legacy_keys:
            if key in kwargs:
                if legacy_instance is not None:
                    raise ValueError(
                        f"Cannot specify both {key} and another legacy instance parameter"
                    )
                legacy_instance = kwargs.pop(key)
                warnings.warn(
                    f"Parameter '{key}' is deprecated. Use 'blockchain_instance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Prefer explicit blockchain_instance, then legacy
        if blockchain_instance is None and legacy_instance is not None:
            blockchain_instance = legacy_instance

        self.blockchain = blockchain_instance or shared_blockchain_instance()
        reduced_query = {}
        for key in [
            "tag",
            "limit",
            "filter_tags",
            "select_authors",
            "select_tags",
            "truncate_body",
            "start_author",
            "start_permlink",
        ]:
            if key in discussion_query:
                reduced_query[key] = discussion_query[key]
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        posts = []
        try:
            # Try to use the bridge API first (preferred method)
            account = reduced_query.get("tag", "")
            if account:
                bridge_query = {
                    "sort": "blog",
                    "account": account,
                    "limit": reduced_query.get("limit", 20),
                }
                if "start_author" in reduced_query and "start_permlink" in reduced_query:
                    bridge_query["start_author"] = reduced_query["start_author"]
                    bridge_query["start_permlink"] = reduced_query["start_permlink"]
                posts = self.blockchain.rpc.get_account_posts(bridge_query, api="bridge")
        except Exception:
            # Fall back to old API methods
            if self.blockchain.rpc.get_use_appbase() and use_appbase:
                try:
                    posts = self.blockchain.rpc.get_discussions_by_blog(reduced_query, api="tags")
                    if isinstance(posts, dict) and "discussions" in posts:
                        posts = posts["discussions"]
                except Exception:
                    posts = []
            if len(posts) == 0:
                self.blockchain.rpc.set_next_node_on_empty_reply(False)
                posts = self.blockchain.rpc.get_discussions_by_blog(reduced_query)
        if posts is None:
            posts = []
        if raw_data:
            super(Discussions_by_blog, self).__init__([x for x in posts])
        else:
            super(Discussions_by_blog, self).__init__(
                [Comment(x, lazy=lazy, blockchain_instance=self.blockchain) for x in posts]
            )


class Discussions_by_comments(list):
    """Get discussions by comments

    :param Query discussion_query: Defines the parameter
        searching posts, start_author and start_permlink must be set.
    :param bool use_appbase: use condenser call when set to False, default is False
    :param bool raw_data: returns list of comments when False, default is False
    :param Hive blockchain_instance: Hive instance

    .. testcode::

        from nectar.discussions import Query, Discussions_by_comments
        q = Query(limit=10, start_author="hiveio", start_permlink="firstpost")
        for h in Discussions_by_comments(q):
            print(h)

    """

    def __init__(
        self,
        discussion_query,
        lazy=False,
        use_appbase=False,
        raw_data=False,
        blockchain_instance=None,
        **kwargs,
    ):
        """
        Initialize Discussions_by_comments.

        Uses the provided discussion_query (expects at minimum `start_author` and `start_permlink`, optional `limit`) to fetch a discussion thread and produce a flattened list of the root post plus replies. Attempts to use the bridge API (`get_discussion`) first and, on failure, falls back to older endpoints (`get_discussions_by_comments`). If `raw_data` is False, each post is wrapped as a Comment; otherwise raw post dicts are kept.

        Parameters:
            discussion_query (dict): Query containing `start_author`, `start_permlink`, and optional `limit`.
            lazy (bool): If False, Comment objects are fully available; if True, they are created in lazy mode.
            use_appbase (bool): Prefers appbase/tag API paths when True (used to select RPC backend).
            raw_data (bool): When True, yields raw post dicts instead of Comment objects.

        Side effects:
            Adjusts the blockchain RPC node selection via `set_next_node_on_empty_reply` based on the `use_appbase` flag and the RPC's appbase setting.
        """
        self.blockchain = blockchain_instance or shared_blockchain_instance()
        reduced_query = {}
        for key in ["start_author", "start_permlink", "limit"]:
            if key in discussion_query:
                reduced_query[key] = discussion_query[key]
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        posts = []
        try:
            # Try to use the bridge API first (preferred method)
            if "start_author" in reduced_query and "start_permlink" in reduced_query:
                # The bridge.get_discussion API retrieves an entire discussion tree
                author = reduced_query["start_author"]
                permlink = reduced_query["start_permlink"]
                bridge_query = {
                    "author": author,
                    "permlink": permlink,
                }
                # The bridge API returns a discussion tree, we need to flatten it
                discussion = self.blockchain.rpc.get_discussion(bridge_query, api="bridge")
                # Extract comments from the discussion tree
                if discussion and isinstance(discussion, dict):
                    posts = []
                    # Start with the main post
                    main_post = discussion.get(f"@{author}/{permlink}")
                    if main_post:
                        posts.append(main_post)
                    # Add replies
                    for key, value in discussion.items():
                        if key != f"@{author}/{permlink}" and isinstance(value, dict):
                            posts.append(value)
                    # Limit the number of posts if needed
                    if "limit" in reduced_query and len(posts) > reduced_query["limit"]:
                        posts = posts[: reduced_query["limit"]]
        except Exception:
            # Fall back to old API methods
            if self.blockchain.rpc.get_use_appbase() and use_appbase:
                try:
                    posts = self.blockchain.rpc.get_discussions_by_comments(
                        reduced_query, api="tags"
                    )
                    if "discussions" in posts:
                        posts = posts["discussions"]  # inconsistent format across node types
                except Exception:
                    posts = self.blockchain.rpc.get_discussions_by_comments(
                        reduced_query["start_author"],
                        reduced_query["start_permlink"],
                        reduced_query["limit"],
                    )
            if len(posts) == 0:
                posts = self.blockchain.rpc.get_discussions_by_comments(reduced_query)
        if posts is None:
            posts = []
        if raw_data:
            super(Discussions_by_comments, self).__init__([x for x in posts])
        else:
            super(Discussions_by_comments, self).__init__(
                [Comment(x, lazy=lazy, blockchain_instance=self.blockchain) for x in posts]
            )


class Discussions_by_promoted(list):
    """Get discussions by promoted

    :param Query discussion_query: Defines the parameter
        searching posts
    :param bool use_appbase: use condenser call when set to False, default is False
    :param bool raw_data: returns list of comments when False, default is False
    :param Hive blockchain_instance: Hive instance

    .. testcode::

        from nectar.discussions import Query, Discussions_by_promoted
        q = Query(limit=10, tag="hive")
        for h in Discussions_by_promoted(q):
            print(h)

    """

    def __init__(
        self,
        discussion_query,
        lazy=False,
        use_appbase=False,
        raw_data=False,
        blockchain_instance=None,
        **kwargs,
    ):
        """
        Initialize Discussions_by_promoted: fetch promoted discussions and populate the sequence.

        This constructor extracts a reduced set of keys from `discussion_query` (tag, limit, filter_tags,
        select_authors, select_tags, truncate_body, start_author, start_permlink), configures the RPC
        client to switch nodes on empty replies when appbase is in use, then attempts to fetch promoted
        posts via the bridge API. On bridge failure it falls back to appbase (`get_discussions_by_promoted`
        with `api="tags"`) and then to the legacy RPC method. Results are normalized to an empty list
        if None. If `raw_data` is True the raw post dictionaries are stored; otherwise each post is wrapped
        in a `Comment` object with the provided `lazy` and resolved blockchain instance.

        Parameters:
            discussion_query (dict): Query parameters; only the keys listed above are used.
            lazy (bool): If False, Comment wrappers are fully initialized; if True, wrappers use lazy loading.
            use_appbase (bool): Prefer appbase/tag endpoints when True (used to decide fallback behavior).
            raw_data (bool): If True, store raw post dicts instead of `Comment` instances.
            blockchain_instance: Blockchain client to use; if None the shared instance is used.

        Side effects:
            - Calls RPC methods on the resolved blockchain instance (may contact external APIs).
            - Sets RPC behavior via `set_next_node_on_empty_reply`.
        """
        self.blockchain = blockchain_instance or shared_blockchain_instance()
        reduced_query = {}
        for key in [
            "tag",
            "limit",
            "filter_tags",
            "select_authors",
            "select_tags",
            "truncate_body",
            "start_author",
            "start_permlink",
        ]:
            if key in discussion_query:
                reduced_query[key] = discussion_query[key]
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        posts = []
        try:
            # Try to use the bridge API first (preferred method)
            bridge_query = {
                "sort": "promoted",
                "tag": reduced_query.get("tag", ""),
                "observer": "",
            }
            if "limit" in reduced_query:
                bridge_query["limit"] = reduced_query["limit"]
            if "start_author" in reduced_query and "start_permlink" in reduced_query:
                bridge_query["start_author"] = reduced_query["start_author"]
                bridge_query["start_permlink"] = reduced_query["start_permlink"]
            posts = self.blockchain.rpc.get_ranked_posts(bridge_query, api="bridge")
        except Exception:
            # Fall back to old API methods
            if self.blockchain.rpc.get_use_appbase() and use_appbase:
                try:
                    posts = self.blockchain.rpc.get_discussions_by_promoted(
                        reduced_query, api="tags"
                    )["discussions"]
                except Exception:
                    posts = []
            if len(posts) == 0:
                posts = self.blockchain.rpc.get_discussions_by_promoted(reduced_query)
        if posts is None:
            posts = []
        if raw_data:
            super(Discussions_by_promoted, self).__init__([x for x in posts])
        else:
            super(Discussions_by_promoted, self).__init__(
                [Comment(x, lazy=lazy, blockchain_instance=self.blockchain) for x in posts]
            )


class Discussions_by_replies(list):
    """Get replies for an author's post

    :param Query discussion_query: Defines the parameter
        searching posts, start_parent_author, start_permlink must be set.
    :param bool use_appbase: use condenser call when set to False, default is False
    :param bool raw_data: returns list of comments when False, default is False
    :param Hive blockchain_instance: Hive instance

    .. testcode::

        from nectar.discussions import Query, Discussions_by_replies
        q = Query(limit=10, start_parent_author="hiveio", start_permlink="firstpost")
        for h in Discussions_by_replies(q):
            print(h)

    """

    def __init__(
        self,
        discussion_query,
        lazy=False,
        use_appbase=False,
        raw_data=False,
        blockchain_instance=None,
        **kwargs,
    ):
        # Handle legacy parameters
        """
        Initialize the Discussions_by_replies fetcher and populate it with replies to a specified post.

        This constructor accepts a discussion_query that should include `start_parent_author` and `start_permlink` to identify the post whose replies are requested. It normalizes legacy kwargs `steem_instance` / `hive_instance` (emitting a DeprecationWarning and mapping to `blockchain_instance`) and will raise ValueError if multiple legacy instance keys are provided. The RPC's next-node behavior is configured according to the blockchain's appbase usage and the `use_appbase` flag.

        Behavior:
        - Attempts the bridge API (`get_discussion`) first to obtain a discussion tree and extracts all replies (every item except the main post).
        - On any bridge/error path, falls back to `get_replies_by_last_update` (appbase `api="tags"` when appropriate), using `limit` from the query or a default of 100.
        - If `raw_data` is True, initializes the base list with raw reply dicts; otherwise wraps each reply in a Comment(lazy=..., blockchain_instance=...).

        Parameters:
        - discussion_query (dict): Query values; `start_parent_author` and `start_permlink` are required to target a post. `limit` controls the maximum replies returned; if absent a default of 100 is used when falling back.
        - lazy (bool): Whether wrapped Comment objects should be lazy-loaded.
        - use_appbase (bool): Prefer appbase/tag API paths when True (when supported by the blockchain RPC).
        - raw_data (bool): If True, return raw reply dicts instead of Comment instances.

        Note: `blockchain_instance` may be provided explicitly or implied via deprecated legacy kwargs; it is used to access the RPC and is not documented here as a parameter description for services/clients.
        """
        legacy_keys = {"steem_instance", "hive_instance"}
        legacy_instance = None
        for key in legacy_keys:
            if key in kwargs:
                if legacy_instance is not None:
                    raise ValueError(
                        f"Cannot specify both {key} and another legacy instance parameter"
                    )
                legacy_instance = kwargs.pop(key)
                warnings.warn(
                    f"Parameter '{key}' is deprecated. Use 'blockchain_instance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Prefer explicit blockchain_instance, then legacy
        if blockchain_instance is None and legacy_instance is not None:
            blockchain_instance = legacy_instance

        self.blockchain = blockchain_instance or shared_blockchain_instance()
        reduced_query = {}
        for key in ["start_parent_author", "start_permlink", "limit"]:
            if key in discussion_query:
                reduced_query[key] = discussion_query[key]
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        posts = []
        try:
            # Try to use the bridge API first (preferred method)
            if "start_parent_author" in reduced_query and "start_permlink" in reduced_query:
                # The bridge.get_discussion API retrieves replies to a post as well
                author = reduced_query["start_parent_author"]
                permlink = reduced_query["start_permlink"]
                bridge_query = {
                    "author": author,
                    "permlink": permlink,
                }
                # The bridge API returns a discussion tree
                discussion = self.blockchain.rpc.get_discussion(bridge_query, api="bridge")
                # Extract replies from the discussion tree
                if discussion and isinstance(discussion, dict):
                    posts = []
                    # Gather all replies (all items except the main post)
                    main_post_key = f"@{author}/{permlink}"
                    for key, value in discussion.items():
                        if key != main_post_key and isinstance(value, dict):
                            posts.append(value)
                    # Limit the number of posts if needed
                    if "limit" in reduced_query and len(posts) > reduced_query["limit"]:
                        posts = posts[: reduced_query["limit"]]
        except Exception:
            # Fall back to old API methods
            posts = []
            if self.blockchain.rpc.get_use_appbase() and use_appbase:
                try:
                    posts = self.blockchain.rpc.get_replies_by_last_update(
                        reduced_query, api="tags"
                    )
                    if "discussions" in posts:
                        posts = posts["discussions"]
                except Exception:
                    posts = self.blockchain.rpc.get_replies_by_last_update(
                        reduced_query["start_parent_author"],
                        reduced_query["start_permlink"],
                        reduced_query["limit"],
                    )
            if len(posts) == 0:
                if (
                    "start_parent_author" in reduced_query and reduced_query["start_parent_author"]
                ) and ("start_permlink" in reduced_query and reduced_query["start_permlink"]):
                    if "limit" in reduced_query:
                        posts = self.blockchain.rpc.get_replies_by_last_update(
                            reduced_query["start_parent_author"],
                            reduced_query["start_permlink"],
                            reduced_query["limit"],
                        )
                    else:
                        posts = self.blockchain.rpc.get_replies_by_last_update(
                            reduced_query["start_parent_author"],
                            reduced_query["start_permlink"],
                            100,
                        )
        if posts is None:
            posts = []
        if raw_data:
            super(Discussions_by_replies, self).__init__([x for x in posts])
        else:
            super(Discussions_by_replies, self).__init__(
                [Comment(x, lazy=lazy, blockchain_instance=self.blockchain) for x in posts]
            )


class Replies_by_last_update(list):
    """Returns a list of replies by last update

    :param Query discussion_query: Defines the parameter
        searching posts start_parent_author and start_permlink must be set.
    :param bool use_appbase: use condenser call when set to False, default is False
    :param bool raw_data: returns list of comments when False, default is False
    :param Hive blockchain_instance: Hive instance

    .. testcode::

        from nectar.discussions import Query, Replies_by_last_update
        q = Query(limit=10, start_parent_author="hiveio", start_permlink="firstpost")
        for h in Replies_by_last_update(q):
            print(h)

    """

    def __init__(
        self,
        discussion_query,
        lazy=False,
        use_appbase=False,
        raw_data=False,
        blockchain_instance=None,
        **kwargs,
    ):
        # Handle legacy parameters
        """
        Initialize a Replies_by_last_update iterator that loads replies to a specific post, using appbase/tags APIs when available and falling back to legacy RPC calls.

        This constructor:
        - Accepts a discussion_query dict containing at minimum "start_author", "start_permlink", and "limit".
        - Accepts legacy kwargs "steem_instance" or "hive_instance"; if provided they are treated as deprecated aliases for `blockchain_instance` and emit a DeprecationWarning. Specifying more than one legacy key raises ValueError.
        - Chooses the blockchain instance from `blockchain_instance`, legacy parameters, or a shared instance, and configures RPC node selection based on the appbase usage.
        - Attempts to fetch replies via the appbase/tags endpoint (when available and requested) and falls back to the legacy get_replies_by_last_update RPC form if needed.
        - Normalizes missing or None responses to an empty list.
        - If raw_data is False (default), wraps each result in a Comment with the provided lazy and blockchain_instance settings; otherwise returns raw post dicts.
        - Calls the superclass initializer with the resulting list (so the object becomes an iterable/sequence of replies).

        Parameters:
            discussion_query (dict): Query parameters; must include "start_author", "start_permlink", and "limit".
            lazy (bool): If False, Comment objects are fully initialized; if True, Comments are created with lazy-loading enabled.
            use_appbase (bool): When True, prefer appbase/tags endpoints where supported.
            raw_data (bool): If True, initialize with raw post dicts instead of Comment wrappers.
            blockchain_instance: Optional blockchain client instance; if omitted a shared instance is used. Legacy parameters `steem_instance`/`hive_instance` may be passed via kwargs but are deprecated.
        """
        legacy_keys = {"steem_instance", "hive_instance"}
        legacy_instance = None
        for key in legacy_keys:
            if key in kwargs:
                if legacy_instance is not None:
                    raise ValueError(
                        f"Cannot specify both {key} and another legacy instance parameter"
                    )
                legacy_instance = kwargs.pop(key)
                warnings.warn(
                    f"Parameter '{key}' is deprecated. Use 'blockchain_instance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Prefer explicit blockchain_instance, then legacy
        if blockchain_instance is None and legacy_instance is not None:
            blockchain_instance = legacy_instance

        self.blockchain = blockchain_instance or shared_blockchain_instance()
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        posts = []
        if self.blockchain.rpc.get_use_appbase() and use_appbase:
            try:
                posts = self.blockchain.rpc.get_replies_by_last_update(discussion_query, api="tags")
                if "discussions" in posts:
                    posts = posts["discussions"]
            except Exception:
                posts = self.blockchain.rpc.get_replies_by_last_update(
                    discussion_query["start_author"],
                    discussion_query["start_permlink"],
                    discussion_query["limit"],
                )
        if len(posts) == 0:
            posts = self.blockchain.rpc.get_replies_by_last_update(
                discussion_query["start_author"],
                discussion_query["start_permlink"],
                discussion_query["limit"],
            )
        if posts is None:
            posts = []
        if raw_data:
            super(Replies_by_last_update, self).__init__([x for x in posts])
        else:
            super(Replies_by_last_update, self).__init__(
                [Comment(x, lazy=lazy, blockchain_instance=self.blockchain) for x in posts]
            )


class Trending_tags(list):
    """Get trending tags

    :param Query discussion_query: Defines the parameter
        searching posts, start_tag is used if set
    :param Hive blockchain_instance: Hive instance

    .. testcode::

        from nectar.discussions import Query, Trending_tags
        q = Query(limit=10)
        for h in Trending_tags(q):
            print(h)

    """

    def __init__(
        self, discussion_query, lazy=False, use_appbase=False, blockchain_instance=None, **kwargs
    ):
        # Handle legacy parameters
        """
        Initialize a Trending_tags iterator by fetching trending tags from the blockchain RPC.

        Fetches trending tags according to discussion_query["limit"], preferring a bridge/appbase (condenser) path when available and falling back to the legacy RPC. Resolves and stores the blockchain instance, configures RPC next-node behavior based on the use_appbase flag, and initializes the base sequence with the retrieved tag list.

        Parameters:
            discussion_query (dict): Query parameters; only 'limit' is used (defaults to 0 if absent).
            lazy (bool): Unused by this initializer but preserved for API compatibility.
            use_appbase (bool): When True, prefer appbase/condenser endpoints when the RPC reports appbase support.
            blockchain_instance: Optional blockchain client; if not provided, a shared instance is used.
            **kwargs: May contain deprecated legacy keys 'steem_instance' or 'hive_instance'. If present, the single legacy key is accepted (mapped to blockchain_instance) and a DeprecationWarning is emitted. Supplying more than one legacy key raises ValueError.

        Side effects:
            - Sets self.blockchain to the resolved blockchain instance.
            - Calls self.blockchain.rpc.set_next_node_on_empty_reply(...) to control backend selection.
            - Emits DeprecationWarning when a legacy instance key is used.

        Raises:
            ValueError: If more than one legacy instance key is provided.
        """
        legacy_keys = {"steem_instance", "hive_instance"}
        legacy_instance = None
        for key in legacy_keys:
            if key in kwargs:
                if legacy_instance is not None:
                    raise ValueError(
                        f"Cannot specify both {key} and another legacy instance parameter"
                    )
                legacy_instance = kwargs.pop(key)
                warnings.warn(
                    f"Parameter '{key}' is deprecated. Use 'blockchain_instance' instead.",
                    DeprecationWarning,
                    stacklevel=2,
                )

        # Prefer explicit blockchain_instance, then legacy
        if blockchain_instance is None and legacy_instance is not None:
            blockchain_instance = legacy_instance

        self.blockchain = blockchain_instance or shared_blockchain_instance()
        self.blockchain.rpc.set_next_node_on_empty_reply(
            self.blockchain.rpc.get_use_appbase() and use_appbase
        )
        limit = discussion_query["limit"] if "limit" in discussion_query else 0
        tags = []
        try:
            # Try to use bridge API for getting trending tags
            # Unfortunately there's no direct bridge API for tags, so we fall back to condenser API
            if self.blockchain.rpc.get_use_appbase() and use_appbase:
                tags = self.blockchain.rpc.get_trending_tags(
                    {"start": "", "limit": limit}, api="condenser"
                )["tags"]
            else:
                tags = self.blockchain.rpc.get_trending_tags("", limit)
        except Exception:
            # If API fails, return empty list
            pass
        super(Trending_tags, self).__init__(tags)
