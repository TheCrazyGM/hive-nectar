#!/usr/bin/env python3
"""
Script to calculate the vote percent needed for the 'themarkymark' account
to downvote the post https://peakd.com/@stayoutoftherz/polymarket-mehr-als-nur-ein-glucksspiel
to zero payout.
"""

from nectar.comment import Comment

c = Comment("@stayoutoftherz/polymarket-mehr-als-nur-ein-glucksspiel")

# Downvote to zero (UI percent, negative)
pct_down = c.to_zero("themarkymark")  # e.g., -77.5
# c.to_zero("themarkymark", broadcast=True)

# Upvote to contribute ~5 HBD (UI percent, positive)
pct_up = c.to_token_value("themarkymark", 5)  # e.g., 34.2
# c.to_token_value("themarkymark", 5, broadcast=True)

print(pct_down, pct_up)
