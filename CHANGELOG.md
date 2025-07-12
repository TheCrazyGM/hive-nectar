# Changelog

## 0.1.0 - 2025-07-12

- Emergency hotfix: lower-case the UTC timestamp suffix during permlink generation (in `derive_permlink`) to resolve validation errors caused by the uppercase `U`.

## 0.0.9 - 2025-07-12

- Refactored `nodelist` logic:
  - `update_nodes` now reads authoritative node metadata from `nectarflower` account `json_metadata` only.
  - Uses `weighted_score` directly for ranking and zeroes scores for nodes missing from the report.
  - Dynamically adds new nodes from the report and failing list, ensuring completeness.
  - Removed unused fall-back paths and cleaned up internal code.

## 0.0.8

Added new documentation and type hints to community

## 0.0.7

Removed all python2 legacy dependencies, drop python3 version requirement to >=3.10

## 0.0.6

Updated to more robust error reporting

## 0.0.5

More community fixes, including the Community Title Property

## 0.0.4

Small community fixes

## 0.0.3

Working on bridge api

## 0.0.2

Rebranded to Nectar

## 0.0.1

- Initial release
- Beem stops and Nectar starts
