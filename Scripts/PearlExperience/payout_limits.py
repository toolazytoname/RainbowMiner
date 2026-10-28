# Copyright (c) 2026 toolazytoname. SPDX-License-Identifier: GPL-3.0-or-later
"""Pure one-shot payout budget. A restart never renews an existing deadline."""
import datetime

def resume_deadline(previous, now, hours=36):
    if now.tzinfo is None:raise ValueError('Current time must have timezone')
    if previous:
        deadline=datetime.datetime.fromisoformat(previous['MiningDeadline'])
        if deadline.tzinfo is None:raise ValueError('Existing deadline must have timezone')
        return deadline
    return now+datetime.timedelta(hours=hours)


def seconds_left(deadline, now):
    if deadline.tzinfo is None or now.tzinfo is None:raise ValueError('Times must have timezone')
    return max(0,(deadline-now).total_seconds())
