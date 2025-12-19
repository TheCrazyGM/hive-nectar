Changelog
=========

0.2.2 - 2025-12-16
------------------

Improvements
~~~~~~~~~~~~

-  **HTTP Client**: Completed the migration to ``httpx`` by replacing
   all remaining ``requests`` and ``urllib`` usage in ``market.py``,
   ``haf.py``, and ``nodelist.py``.
-  **Logging**: Reduced log verbosity by setting ``httpx`` and
   ``httpcore`` loggers to ``WARNING`` level.

.. _section-1:

0.2.0 - 2025-12-01
------------------

Breaking Changes
~~~~~~~~~~~~~~~~

-  **Refactor**: Removed ``use_stored_data`` parameter from
   ``_calc_resulting_vote`` call in ``hive.py``.
-  **Refactor**: Converted ``Amount.tuple`` property to ``as_tuple()``
   method.
-  **Refactor**: Converted API method calls from dict parameters to
   positional arguments across multiple modules.
-  **Refactor**: Removed legacy ``HiveSigner`` integration and related
   dependencies.
-  **Refactor**: Standardized API endpoint naming to use ``_api`` suffix
   throughout codebase.
-  **Refactor**: Deprecated ``appbase`` utility functions.

.. _improvements-1:

Improvements
~~~~~~~~~~~~

-  **HTTP Client**: Standardized HTTP/RPC communication by transitioning
   to ``httpx`` and implementing a single, shared client instance for
   improved efficiency and consistency.

Features
~~~~~~~~

-  **Transaction**: Added ``json_str`` parameter to multiple transaction
   operations.
-  **Node Management**: Simplified ``NodeList`` to use PeakD beacon API
   with static fallback nodes.
-  **Performance**: Improved blockchain tests with limited data
   collection and structure validation.
-  **Compatibility**: Removed Python 2 compatibility code and modernized
   syntax.
-  **CLI**: Added string time parsing support to account history
   methods.

Fixes
~~~~~

-  **Security**: Fixed ``PasswordKey`` seed generation and ``PublicKey``
   string methods.
-  **Security**: Fixed cipher decoding in ``extract_memo_data``.
-  **Reliability**: Improved type safety and null handling across almost
   all core modules (``Account``, ``BlockChainInstance``, ``Hive``,
   etc.).
-  **Reliability**: Fixed circular import in instance module.
-  **Reliability**: Improved RPC retry logic and error handling for
   witness and node operations.

.. _section-2:

0.1.5 - 2025-11-04
------------------

-  **Feature**: Added a ``--witness/-w`` flag to the
   ``hive-nectar rewards`` CLI that aggregates producer rewards into a
   PrettyTable, respecting the requested date window.
-  **Fix**: Resolved ``KeyError`` and zero-output issues in the rewards
   CLI by iterating over all relevant operations, normalizing producer
   reward timestamps, and gracefully handling curation entries missing
   ``comment_permlink`` data.
-  **Tests**: Extended CLI coverage to ensure the new witness mode runs
   without errors.

0.1.4b - 2025-10-12
-------------------

-  **Refactor**: Refactored **Account**\ ’s vote‑pct calculation to
   correctly convert the desired token value to an ``Amount``, introduce
   a safe ratio clamp (‑10 to 10) to avoid extreme values, and return 0
   for zero‑vote scenarios; updated all discussion query fallbacks to
   use the *condenser* API and handle dict‑style responses, and tweaked
   tests to instantiate ``Account`` directly.

0.1.4b - 2025-09-19
-------------------

-  **Feature**: Added payout-based vote helpers on ``Comment`` :

   -  ``Comment.to_zero(account, partial=100.0)`` computes the UI
      downvote percent to reduce a post’s pending payout to
      approximately zero (uses reward fund + median price + effective
      vesting shares; scales by the account’s downvoting power). Returns
      negative UI percent and broadcasts automatically (suppress via the
      blockchain instance’s ``no_broadcast``).
   -  ``Comment.to_token_value(account, hbd, partial=100.0)`` computes
      the UI upvote percent to contribute approximately the given HBD
      value. Returns positive UI percent and broadcasts automatically
      (suppress via ``no_broadcast``).

-  **Fix**: Corrected vote value math to align with the beem reference
   formula:

   -  Restored ``get_hbd_per_rshares()`` to derive HBD/share as
      ``(reward_balance / recent_claims) * median_price(HBD/HIVE)`` .
   -  Applied the missing ``/ 100`` scale factor from the sample when
      converting rshares to HBD-equivalent in payout-based helpers.
   -  ``ActiveVotes.get_downvote_pct_to_zero()`` updated to use
      effective vesting shares and the account’s downvoting power;
      analytic path improved and payout-based path added via
      ``Comment.to_zero()`` .
   -  ``vests_to_rshares()`` reverted to chain-accurate power
      computation via ``_calc_resulting_vote`` and dust-threshold
      handling.
   -  ``rshares_to_vote_pct()`` updated to invert the chain power model
      consistently (taking max_vote_denom into account).

-  **Docs/Examples**: Added ``examples/get_vote_pct_script.py`` showing
   how to compute both the downvote-to-zero percent and the upvote
   percent to reach a target HBD.

.. _section-3:

0.1.3 - 2025-09-18
------------------

-  **Test**: Working on getting 100% test coverage
-  **Feature**: Added some HAF features for things like reputation.

.. _section-4:

0.1.2 - 2025-09-17
------------------

-  **Fix**: Replaced missing ``**kwargs`` in ``Blocks`` constructor.

.. _section-5:

0.1.1 - 2025-09-17
------------------

-  **Fix**: Added support for ``only_ops`` and ``only_virtual_ops``
   parameters in ``Blocks`` constructor.

0.1.0b - 2025-09-17
-------------------

-  **Breaking Change**: Killed everything that was not specifcally HIVE
   related. If you used this for STEEM and / or Blurt, they are no
   longer supported.
-  **Fix**: Corrected inverted fallback logic in chain detection to
   prefer HIVE over STEEM when ``blockchain_name`` is None.
-  **Fix**: Restored backward compatibility for constructor parameters:

   -  ``Vote.__init__``: Added support for deprecated ``steem_instance``
      and ``hive_instance`` kwargs with deprecation warnings.
   -  ``ActiveVotes.__init__``: Added support for deprecated
      ``steem_instance`` and ``hive_instance`` kwargs with deprecation
      warnings.
   -  ``Witness.__init__``: Added ``**kwargs`` with warnings for
      unexpected parameters.
   -  ``Comment_options.__init__``: Added fallback support for
      deprecated ``percent_steem_dollars`` parameter.

-  **Improvement**: Removed deprecated websocket support from
   GrapheneRPC, now only supports HTTP/requests for better reliability
   and maintainability.
-  **Improvement**: Simplified ecdsasig.py to use only cryptography
   library, removing complex conditional logic for different secp256k1
   implementations. The ``tweak_add`` operation now raises
   NotImplementedError when called.
-  **Major Feature**: Implemented pure Python secp256k1 elliptic curve
   operations for PublicKey.add() method, restoring compatibility with
   existing code that relies on key derivation. The implementation
   includes proper validation, error handling, and maintains the same
   API as before. All unit tests pass successfully.
-  **Fix**: Fixed HiveSigner integration in TransactionBuilder:

   -  Updated appendSigner() to restrict permissions to ‘posting’ when
      using HiveSigner
   -  Fixed sign() method to properly call hivesigner.sign() and attach
      signatures instead of returning early
   -  Fixed broadcast() method to use hivesigner.broadcast() when use_hs
      is True
   -  Added proper error handling and fallbacks for non-HiveSigner flows
   -  **Fix**: Fixed HiveSigner.broadcast() call in TransactionBuilder
      to pass operations list instead of full transaction JSON, and
      include username when available

-  **Fix**: Fixed Claim_reward_balance operation serialization in
   nectarbase/operations.py:

   -  Removed incorrect mutually-exclusive logic between reward_hive and
      reward_hbd
   -  Updated to always serialize all four fields in canonical order:
      account, reward_hive, reward_hbd, reward_vests
   -  Added proper zero-amount defaults (“0.000 HIVE”/“0.000 HBD”) for
      missing reward fields
   -  Updated docstring to reflect correct behavior and field
      requirements

-  **Fix**: Convert beneficiary weights from ``HIVE_100_PERCENT`` units
   (10000) to percentages in ``Comment.get_beneficiaries_pct()`` to
   ensure accurate outputs.
-  **Fix**: Improve ECDSA signing to correctly handle prehashed messages
   and tighten signature canonicalization checks for better
   interoperability.
-  **Refactor**: Reorder wallet lock verification to run after
   HiveSigner validation in ``TransactionBuilder``, preventing premature
   lock errors for HiveSigner flows.
-  **Refactor**: Replace implicit stdin default with an explicit
   blockchain selection in the CLI argument parser to avoid ambiguous
   behavior.
-  **Refactor**: Update default Hive node configuration to use HTTPS
   endpoints instead of WSS.
-  **Feature**: Add a pure-Python fallback for public key derivation
   when the ``ecdsa`` library is unavailable, improving portability.

.. _section-6:

0.0.11 - 2025-07-25
-------------------

-  Fixed handling of missing ``community`` field in comments
   (``Comment``) and improved ``weighted_score`` type check in node list
   ranking (``NodeList``).

.. _section-7:

0.0.10 - 2025-07-12
-------------------

-  Emergency hotfix: lower-case the UTC timestamp suffix during permlink
   generation (in ``derive_permlink``) to resolve validation errors
   caused by the uppercase ``U``.

.. _section-8:

0.0.9 - 2025-07-12
------------------

-  Refactored ``nodelist`` logic:

   -  ``update_nodes`` now reads authoritative node metadata from
      ``nectarflower`` account ``json_metadata`` only.
   -  Uses ``weighted_score`` directly for ranking and zeroes scores for
      nodes missing from the report.
   -  Dynamically adds new nodes from the report and failing list,
      ensuring completeness.
   -  Removed unused fall-back paths and cleaned up internal code.

.. _section-9:

0.0.8
-----

Added new documentation and type hints to community

.. _section-10:

0.0.7
-----

Removed all python2 legacy dependencies, drop python3 version
requirement to >=3.10

.. _section-11:

0.0.6
-----

Updated to more robust error reporting

.. _section-12:

0.0.5
-----

More community fixes, including the Community Title Property

.. _section-13:

0.0.4
-----

Small community fixes

.. _section-14:

0.0.3
-----

Working on bridge api

.. _section-15:

0.0.2
-----

Rebranded to Nectar

.. _section-16:

0.0.1
-----

-  Initial release
-  Beem stops and Nectar starts
