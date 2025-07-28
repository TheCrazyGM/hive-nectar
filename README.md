# nectar - Python Library for HIVE

nectar is a python library for HIVE, which is
created from the remains of [beem](https://github.com/holgern/beem) which was derived from [python-bitshares](https://github.com/xeroc/python-bitshares)
The library name is derived from a nectar of a flower.

nectar includes [python-graphenelib](https://github.com/xeroc/python-graphenelib).

[![Latest Version](https://img.shields.io/pypi/v/hive-nectar.svg)](https://pypi.python.org/pypi/hive-nectar/)

[![Python Versions](https://img.shields.io/pypi/pyversions/hive-nectar.svg)](https://pypi.python.org/pypi/hive-nectar/)

## Current build status

# Support & Documentation

You may find help in the [nectar-discord-channel](). The discord channel can also be used to discuss things about nectar.

A complete library documentation is available at
[temporary]()

# About hive-nectar

- Highly opinionated fork of beem
- High unit test coverage
- Complete documentation of hive-nectar and all classes including all functions
- hivesigner integration
- Works on read-only systems
- Own BlockchainObject class with cache
- Contains all broadcast operations
- Estimation of virtual account operation index from date or block number
- the command line tool hive-nectar uses click and has more commands
- NodeRPC can be used to execute even not implemented RPC-Calls
- More complete implemention

# Installation

The minimal working python version is 3.12.x

nectar can be installed parallel to beem.

For Debian and Ubuntu, please ensure that the following packages are installed:

```bash
sudo apt-get install build-essential libssl-dev python3-dev python3-pip python3-setuptools
```

The following package speeds up hive-nectar:

> sudo apt-get install python3-gmpy2

For Fedora and RHEL-derivatives, please ensure that the following
packages are installed:

```bash
sudo yum install gcc openssl-devel python-devel
```

For OSX, please do the following:

    brew install openssl
    export CFLAGS="-I$(brew --prefix openssl)/include $CFLAGS"
    export LDFLAGS="-L$(brew --prefix openssl)/lib $LDFLAGS"

For Termux on Android, please install the following packages:

```bash
pkg install clang openssl python
```

Signing and Verify can be fasten (200 %) by installing cryptography (you
may need to replace pip3 by pip):

```bash
pip3 install -U cryptography
```

or (you may need to replace pip3 by pip):

```bash
pip3 install -U secp256k1prp
```

Install or update nectar by pip(you may need to replace pip3 by pip):

```bash
pip3 install -U hive-nectar
```

You can install nectar from this repository if you want the latest but
possibly non-compiling version:

```bash
git clone https://github.com/thecrazygm/hive-nectar.git
cd hive-nectar
uv sync
uv sync --dev
```

Run tests after install:

```bash
pytest
```

## Ledger support

For Ledger (Nano S) signing, the following package must be installed:

```bash
pip3 install ledgerblue
```

# Changelog

Can be found in CHANGELOG.md.

# License

This library is licensed under the MIT License.

# Acknowledgements

[beem](https://github.com/holgern/beem) was created by Holger Nahrstaedt
[python-bitshares](https://github.com/xeroc/python-bitshares) and [python-graphenelib](https://github.com/xeroc/python-graphenelib) were created by Fabian Schuh (xeroc).
