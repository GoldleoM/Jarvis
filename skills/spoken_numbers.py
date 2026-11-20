"""Quantities shared by spoken arithmetic and timer commands."""
import re
from decimal import Decimal


SMALL = dict(zip("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split(), range(20)))
TENS = dict(zip("twenty thirty forty fifty sixty seventy eighty ninety".split(), range(20, 100, 10)))


def quantity(words):
    if re.fullmatch(r"\d+(?:\.\d+)?", words):
        return Decimal(words)
    if words in ("a", "an"):
        return 1
    if words in ("half a", "half an", "half"):
        return Decimal("0.5")
    if words in ("a quarter of an", "a quarter of a", "a quarter"):
        return Decimal("0.25")
    if words.endswith(" and a half"):
        whole = quantity(words.removesuffix(" and a half"))
        return whole + Decimal("0.5") if whole is not None else None
    if words in SMALL:
        return SMALL[words]
    tens, _, ones = words.partition(" ")
    if tens in TENS and (not ones or ones in SMALL and 0 < SMALL[ones] < 10):
        return TENS[tens] + SMALL.get(ones, 0)
    return None
