INSERT INTO events (id, name, venue, starts_at, base_price, row_count, seats_per_row) VALUES
 (1,'Rahman Live in Concert','Chowdiah Memorial Hall', now() + interval '21 days', 800.00, 10, 24),
 (2,'Campus Stand-Up Night','Student Union Auditorium', now() + interval '5 days', 250.00, 6, 24),
 (3,'Jazz Quartet: Late Set','Blue Door Club', now() + interval '2 days', 450.00, 4, 12),
 (4,'Graduation Ceremony 2026','Main Quadrangle', now() + interval '60 days', 0.00, 16, 24)
ON CONFLICT DO NOTHING;
SELECT setval('events_id_seq', (SELECT max(id) FROM events));

-- Event 3 is nearly sold out: row A is gone except A1, and row B has a
-- scattering of singles left. Asking for three together there is interesting.
INSERT INTO bookings (event_id, seat, holder, price, ref)
SELECT 3, 'A' || n, 'earlybird', 787.50, 'SEEDA00001'
FROM generate_series(2, 12) AS n
ON CONFLICT DO NOTHING;

INSERT INTO bookings (event_id, seat, holder, price, ref) VALUES
 (3,'B2','meena',787.50,'SEEDB00002'),
 (3,'B5','meena',787.50,'SEEDB00002'),
 (3,'B9','arjun',787.50,'SEEDB00003'),
 (3,'C4','arjun',562.50,'SEEDB00003')
ON CONFLICT DO NOTHING;

-- A handful of sales on the big show so the seat map is not a blank grid.
INSERT INTO bookings (event_id, seat, holder, price, ref) VALUES
 (1,'A1','nandini',1400.00,'SEED100001'),
 (1,'A2','nandini',1400.00,'SEED100001'),
 (1,'D12','sunil',1000.00,'SEED100002'),
 (1,'D13','sunil',1000.00,'SEED100002'),
 (1,'J7','kiran',800.00,'SEED100003')
ON CONFLICT DO NOTHING;
SELECT setval('bookings_id_seq', (SELECT max(id) FROM bookings));
