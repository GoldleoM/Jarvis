"""Parse spoken relative durations for the existing timer and its follow-up."""
import re
from decimal import Decimal


from skills.spoken_numbers import quantity

UNITS = {"hour": 3600, "hr": 3600, "minute": 60, "min": 60, "second": 1, "sec": 1}


def timer_seconds(text):
    text = text.casefold().strip(" .,!?")
    text = re.sub(r"^(?:(?:please|(?:can|could|would) you|i (?:want|need) you to)\s+)+", "", text)
    text = text.removesuffix(" please").rstrip(",")
    text = re.sub(r"(?<=[a-z])-(?=[a-z])|(?<=\d)-(?=[a-z])", " ", text)
    text = re.sub(r"^.*?\b(?:for|in|from)\s+", "", text, count=1)
    text = re.sub(r"^(?:please )?(?:start|set)(?: up)? (?:a |an |the )?", "", text)
    text = re.sub(r"\s+(?:(?:countdown )?timer|from now|please)$", "", text)
    total = Decimal(0)
    end = 0
    for match in re.finditer(r"(hours?|hrs?|minutes?|mins?|seconds?|secs?)\b", text):
        words = text[end:match.start()].strip(" ,").removeprefix("and ").strip()
        amount = quantity(words)
        if amount is None:
            return None
        factor = UNITS[match.group().rstrip("s")]
        total += amount * factor
        end = match.end()
    if not end:
        return None
    tail = text[end:].strip()
    if tail == "and a half":
        total += Decimal("0.5") * factor
    elif tail and not tail.startswith("to "):
        return None
    return int(total) if total >= 1 else None
