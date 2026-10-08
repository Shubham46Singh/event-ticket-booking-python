"""Pure seat-map logic. No database, no HTTP, no clock.

A seat is a label like "A12": a row letter and a seat number starting at 1.
Rows are lettered from the stage backwards, so A is the front row.

The one piece of real-world awkwardness modelled here is the aisle. Seats 6
and 7 are physically next to each other on the map but have a gangway between
them, so a group of friends booking "three together" must not be handed
5, 6, 7.

What is worth testing
---------------------
  * `parse_seat` accepts "a1" and "A1" alike, and rejects "1A", "A0", "AA1"
  * `are_adjacent("A6","A7")` is False - the aisle - while ("A5","A6") is True
  * seats in different rows are never adjacent
  * `contiguous_blocks` splits a row at both gaps and aisles
  * `find_block` returns None when nothing big enough is free, and prefers the
    block nearest the centre of the row when several would do
  * `find_block` for a block of 1 still works, and never returns a longer run
  * `is_block_available` is False if even one seat of the run is taken
  * `row_tier` boundaries: C is front, D is middle, H is middle, I is back
  * `seat_price` multiplies by the tier, `quote` adds a per-order booking fee
  * `quote` on an empty seat list raises rather than charging the fee for air
  * `hold_expires_at` and `seconds_left` are pure arithmetic on a timestamp
    you pass in - which is the only way the ten-minute rule can be tested
    without waiting ten minutes
"""
import re

ROWS = "ABCDEFGHIJKLMNOP"
SEATS_PER_ROW = 24

# A gangway runs after seat 6 and after seat 18 in every row.
AISLE_AFTER = frozenset({6, 18})

TIER_MULTIPLIER = {"front": 1.75, "middle": 1.25, "back": 1.0}
BOOKING_FEE = 20.0
HOLD_SECONDS = 600          # ten minutes

_SEAT_RE = re.compile(r"^([A-Za-z])\s*(\d{1,2})$")


class SeatError(ValueError):
    pass


def parse_seat(label):
    """"A12" -> ("A", 12). Raises SeatError on anything else."""
    m = _SEAT_RE.match(str(label).strip())
    if not m:
        raise SeatError(f"{label!r} is not a seat label")
    row = m.group(1).upper()
    num = int(m.group(2))
    if row not in ROWS:
        raise SeatError(f"there is no row {row}")
    if not 1 <= num <= SEATS_PER_ROW:
        raise SeatError(f"seat {num} is outside the row")
    return row, num


def seat_label(row, num):
    return f"{str(row).upper()}{int(num)}"


def row_index(row):
    """A -> 0. Front row first."""
    r = str(row).upper()
    if r not in ROWS:
        raise SeatError(f"there is no row {r}")
    return ROWS.index(r)


def row_tier(row):
    """Which price band a row sits in."""
    i = row_index(row)
    if i < 3:
        return "front"
    if i < 8:
        return "middle"
    return "back"


def seat_price(label, base_price):
    """Base price scaled by the row's tier, rounded to two places."""
    if base_price < 0:
        raise SeatError("a base price cannot be negative")
    row, _ = parse_seat(label)
    return round(float(base_price) * TIER_MULTIPLIER[row_tier(row)], 2)


def quote(labels, base_price, fee=BOOKING_FEE):
    """Price a whole order. The fee is per order, not per seat."""
    seats = list(labels)
    if not seats:
        raise SeatError("an order must contain at least one seat")
    if len(set(seats)) != len(seats):
        raise SeatError("the same seat appears twice in the order")
    lines = [{"seat": s, "tier": row_tier(parse_seat(s)[0]),
              "price": seat_price(s, base_price)} for s in seats]
    subtotal = round(sum(line["price"] for line in lines), 2)
    return {"lines": lines, "subtotal": subtotal, "fee": round(float(fee), 2),
            "total": round(subtotal + float(fee), 2)}


def are_adjacent(a, b):
    """Next to each other with no gangway between them."""
    row_a, num_a = parse_seat(a)
    row_b, num_b = parse_seat(b)
    if row_a != row_b:
        return False
    lo, hi = sorted((num_a, num_b))
    if hi - lo != 1:
        return False
    return lo not in AISLE_AFTER


def contiguous_blocks(seats):
    """Group a set of free seats into runs you could actually sit along.

    Accepts labels from any number of rows. Returns a list of lists, each in
    seat order, split wherever there is a taken seat or an aisle.
    """
    by_row = {}
    for label in seats:
        row, num = parse_seat(label)
        by_row.setdefault(row, set()).add(num)
    blocks = []
    for row in sorted(by_row):
        run = []
        for num in sorted(by_row[row]):
            if run and num == run[-1] + 1 and run[-1] not in AISLE_AFTER:
                run.append(num)
            else:
                if run:
                    blocks.append([seat_label(row, n) for n in run])
                run = [num]
        if run:
            blocks.append([seat_label(row, n) for n in run])
    return blocks


def is_block_available(seats, available):
    """Are these specific seats all free, and do they form one run?"""
    wanted = list(seats)
    if not wanted:
        raise SeatError("no seats requested")
    free = set(available)
    if any(s not in free for s in wanted):
        return False
    if len(wanted) == 1:
        return True
    ordered = sorted(wanted, key=lambda s: (parse_seat(s)[0], parse_seat(s)[1]))
    return all(are_adjacent(ordered[i], ordered[i + 1])
               for i in range(len(ordered) - 1))


def _centre_distance(block):
    """How far the middle of a block sits from the middle of the row."""
    nums = [parse_seat(s)[1] for s in block]
    middle = (nums[0] + nums[-1]) / 2
    return abs(middle - (SEATS_PER_ROW + 1) / 2)


def find_block(available, count):
    """Find `count` seats together, preferring the front and the centre.

    Returns the list of labels, or None if the house cannot seat the group
    in one run.
    """
    if count < 1:
        raise SeatError("a group must be at least one seat")
    candidates = []
    for block in contiguous_blocks(available):
        if len(block) < count:
            continue
        for start in range(len(block) - count + 1):
            window = block[start:start + count]
            row = parse_seat(window[0])[0]
            candidates.append((row_index(row), _centre_distance(window),
                               parse_seat(window[0])[1], window))
    if not candidates:
        return None
    candidates.sort(key=lambda c: (c[0], c[1], c[2]))
    return candidates[0][3]


def best_effort(available, count):
    """What to offer a group that cannot sit together: the largest run you
    can give them, plus how many are left over."""
    block = find_block(available, count)
    if block:
        return {"together": block, "split": [], "short": 0}
    blocks = sorted(contiguous_blocks(available), key=len, reverse=True)
    picked, taken = [], 0
    for b in blocks:
        if taken >= count:
            break
        want = min(len(b), count - taken)
        picked.append(b[:want])
        taken += want
    return {"together": [], "split": picked, "short": max(0, count - taken)}


def hold_expires_at(held_at, seconds=HOLD_SECONDS):
    """A hold placed at `held_at` (epoch seconds) dies at this instant."""
    if seconds <= 0:
        raise SeatError("a hold must last at least one second")
    return float(held_at) + float(seconds)


def seconds_left(held_at, now, seconds=HOLD_SECONDS):
    """Never negative. Zero means it is gone - not 'about to go'."""
    return max(0.0, round(hold_expires_at(held_at, seconds) - float(now), 3))


def hold_is_live(held_at, now, seconds=HOLD_SECONDS):
    """Exactly at the boundary the hold is already dead. One second late is
    one seat sold twice."""
    return float(now) < hold_expires_at(held_at, seconds)
