# Copyright (c) 2026 toolazytoname. SPDX-License-Identifier: GPL-3.0-or-later
"""Authenticate the existing PRL pool before forwarding any miner payload."""
from urllib.parse import urlsplit
from tls_relay import TlsRelay


def verified_pool_transport(pool_url, receipt):
    pool=urlsplit(pool_url)
    if (pool.scheme!='stratum+ssl' or pool.hostname!='prl-hk.kryptex.network'
        or pool.port!=8048 or pool.username or pool.password
        or pool.path not in ('','/') or pool.query or pool.fragment):
        raise ValueError('Expected the original PRL Kryptex TLS endpoint without credentials or extra URL fields')
    return TlsRelay(pool.hostname,pool.port,receipt=receipt)
