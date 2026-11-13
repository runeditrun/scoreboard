#!/usr/bin/env python3
"""Count a: days since anyone outside the owner used a product.

The value needs a read that lists product sign-ins or actions by identities outside the owner and
the fleet. Platform main (86030a5, 14 Nov) has no such door: its admin reads cover access, checkout
invitations, delivery access, suspension and data rights only, and installation reads are scoped to
members. Until a read-only door exists this count is NOT-MEASURED, never an assumed zero.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
import score

score.count('a', 'NOT-MEASURED', 'days since outside use: no read-only door reports use by identities outside the owner and the fleet', 'none')
