CREATE TABLE IF NOT EXISTS events (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    venue         TEXT NOT NULL DEFAULT '',
    starts_at     TIMESTAMPTZ NOT NULL,
    base_price    NUMERIC(8,2) NOT NULL CHECK (base_price >= 0),
    row_count     INT NOT NULL DEFAULT 10 CHECK (row_count BETWEEN 1 AND 16),
    seats_per_row INT NOT NULL DEFAULT 24 CHECK (seats_per_row BETWEEN 1 AND 24)
);

CREATE TABLE IF NOT EXISTS bookings (
    id         SERIAL PRIMARY KEY,
    event_id   INT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    seat       TEXT NOT NULL,
    holder     TEXT NOT NULL,
    price      NUMERIC(8,2) NOT NULL CHECK (price >= 0),
    ref        TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- The guarantee of last resort. Redis holds can expire; this cannot.
CREATE UNIQUE INDEX IF NOT EXISTS bookings_one_per_seat
    ON bookings (event_id, seat);
CREATE INDEX IF NOT EXISTS bookings_ref ON bookings (ref);
