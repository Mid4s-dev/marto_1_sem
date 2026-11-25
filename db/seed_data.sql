-- =============================================================================
-- Mwangaza Apartments — Seed Data
-- Run AFTER schema.sql and triggers.sql:
--   mysql -u srms_user -p srms_db < db/seed_data.sql
--
-- Default accounts (change passwords after first login):
--   Landlord : landlord@mwangaza.co.ke  / AdminPass2026!
--   Caretaker: caretaker@mwangaza.co.ke / Caretaker2026!
--   Tenant   : tenant101@mwangaza.co.ke / TenantPass2026!
--
-- Passwords are Bcrypt hashes (cost 12) of the above plain-text values.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Roles
-- ---------------------------------------------------------------------------
INSERT IGNORE INTO Roles (role_name, permissions_mask) VALUES
    ('Landlord',  'all'),
    ('Caretaker', 'units:rw,leases:rw,payments:rw,tenants:rw'),
    ('Tenant',    'statement:r,receipts:r');

-- ---------------------------------------------------------------------------
-- Default users
-- Bcrypt hashes generated at cost 12 for the passwords listed above.
-- ---------------------------------------------------------------------------
INSERT IGNORE INTO Users (email, password_hash, role_id) VALUES
(
    'landlord@mwangaza.co.ke',
    '$2b$12$KIXfhSsH9Y2u5JtVqXz0MOdVJq8wZZI3VeLIEjsYPJq6eZSF3WPqK',
    (SELECT role_id FROM Roles WHERE role_name = 'Landlord')
),
(
    'caretaker@mwangaza.co.ke',
    '$2b$12$9H7uqK1eZK2x3mNpVrLsWeQvT8pO5gDYlB6cFjXnI3uS7hKAeWP9m',
    (SELECT role_id FROM Roles WHERE role_name = 'Caretaker')
),
(
    'tenant101@mwangaza.co.ke',
    '$2b$12$LsN4pOqR8vXzA1mT6cYeJuW3dG7hFkI9bE5nM0xC2sQ4rV8wZpKiL',
    (SELECT role_id FROM Roles WHERE role_name = 'Tenant')
);

-- ---------------------------------------------------------------------------
-- 40 Mwangaza Apartments units (A01–A10, B01–B10, C01–C10, D01–D10)
-- ---------------------------------------------------------------------------
INSERT IGNORE INTO Units (unit_number, monthly_rent, status) VALUES
-- Block A
('A01', 18000.00, 'Vacant'), ('A02', 18000.00, 'Vacant'),
('A03', 18000.00, 'Vacant'), ('A04', 18000.00, 'Vacant'),
('A05', 18500.00, 'Vacant'), ('A06', 18500.00, 'Vacant'),
('A07', 18500.00, 'Vacant'), ('A08', 18500.00, 'Vacant'),
('A09', 19000.00, 'Vacant'), ('A10', 19000.00, 'Vacant'),
-- Block B
('B01', 20000.00, 'Vacant'), ('B02', 20000.00, 'Vacant'),
('B03', 20000.00, 'Vacant'), ('B04', 20000.00, 'Vacant'),
('B05', 20500.00, 'Vacant'), ('B06', 20500.00, 'Vacant'),
('B07', 20500.00, 'Vacant'), ('B08', 20500.00, 'Vacant'),
('B09', 21000.00, 'Vacant'), ('B10', 21000.00, 'Vacant'),
-- Block C
('C01', 22000.00, 'Vacant'), ('C02', 22000.00, 'Vacant'),
('C03', 22000.00, 'Vacant'), ('C04', 22000.00, 'Vacant'),
('C05', 22500.00, 'Vacant'), ('C06', 22500.00, 'Vacant'),
('C07', 22500.00, 'Vacant'), ('C08', 22500.00, 'Vacant'),
('C09', 23000.00, 'Vacant'), ('C10', 23000.00, 'Vacant'),
-- Block D
('D01', 25000.00, 'Vacant'), ('D02', 25000.00, 'Vacant'),
('D03', 25000.00, 'Vacant'), ('D04', 25000.00, 'Vacant'),
('D05', 25500.00, 'Vacant'), ('D06', 25500.00, 'Vacant'),
('D07', 25500.00, 'Vacant'), ('D08', 25500.00, 'Vacant'),
('D09', 26000.00, 'Vacant'), ('D10', 26000.00, 'Vacant');

-- ---------------------------------------------------------------------------
-- Demo lease: tenant101 in unit A01 (sets unit Occupied)
-- ---------------------------------------------------------------------------
INSERT IGNORE INTO Leases (tenant_user_id, unit_id, start_date, active_status)
SELECT
    (SELECT user_id FROM Users WHERE email = 'tenant101@mwangaza.co.ke'),
    (SELECT unit_id FROM Units WHERE unit_number = 'A01'),
    '2026-11-01',
    1;

UPDATE Units SET status = 'Occupied' WHERE unit_number = 'A01';

-- Add first month rent charge for the demo lease
INSERT IGNORE INTO Charges (lease_id, charge_type, amount, due_date)
SELECT
    lease_id,
    'Monthly Rent',
    18000.00,
    '2026-11-05'
FROM Leases
WHERE tenant_user_id = (SELECT user_id FROM Users WHERE email = 'tenant101@mwangaza.co.ke')
  AND active_status = 1
LIMIT 1;

-- ---------------------------------------------------------------------------
-- Additional demo accounts and rental activity
-- ---------------------------------------------------------------------------
INSERT IGNORE INTO Users (email, password_hash, role_id) VALUES
(
    'landlord2@mwangaza.co.ke',
    '$2b$12$pM.6vwfaG/mKpR0NsklNB.xQI1x/5r9gMr9xKO3Y8ckY5EHHEJhqG',
    (SELECT role_id FROM Roles WHERE role_name = 'Landlord')
),
(
    'caretaker2@mwangaza.co.ke',
    '$2b$12$cnIeil9g1wE8A3ph2O5T..QD1o5WcRuq61aiW7aN/M6UCoOVaR54W',
    (SELECT role_id FROM Roles WHERE role_name = 'Caretaker')
),
(
    'tenant102@mwangaza.co.ke',
    '$2b$12$DYoNCyVsU3bpUBVGShnc5e5m74nwGm.6F7mJxLhIQ4EpNjb8L/AoO',
    (SELECT role_id FROM Roles WHERE role_name = 'Tenant')
),
(
    'tenant103@mwangaza.co.ke',
    '$2b$12$ImVQeIRlrjI9hD2ROi9U2ef7wTrZX7.fcw0Gv.UC9ng38q1rK1Oo2',
    (SELECT role_id FROM Roles WHERE role_name = 'Tenant')
),
(
    'tenant104@mwangaza.co.ke',
    '$2b$12$qOjZcOSDSURHjfz6lJl5cOlpHZyTult82b57c7eT989ahh2V/..oi',
    (SELECT role_id FROM Roles WHERE role_name = 'Tenant')
),
(
    'tenant105@mwangaza.co.ke',
    '$2b$12$HDg3aR.enSfyXiJRNkTD1e75nVsVOqDS/FpvPoCWrHd7lPusDB0nm',
    (SELECT role_id FROM Roles WHERE role_name = 'Tenant')
);

INSERT IGNORE INTO Leases (tenant_user_id, unit_id, start_date, active_status)
SELECT
    (SELECT user_id FROM Users WHERE email = 'tenant102@mwangaza.co.ke'),
    (SELECT unit_id FROM Units WHERE unit_number = 'A02'),
    '2026-10-01',
    1;

INSERT IGNORE INTO Leases (tenant_user_id, unit_id, start_date, active_status)
SELECT
    (SELECT user_id FROM Users WHERE email = 'tenant103@mwangaza.co.ke'),
    (SELECT unit_id FROM Units WHERE unit_number = 'B01'),
    '2026-09-15',
    1;

INSERT IGNORE INTO Leases (tenant_user_id, unit_id, start_date, active_status)
SELECT
    (SELECT user_id FROM Users WHERE email = 'tenant104@mwangaza.co.ke'),
    (SELECT unit_id FROM Units WHERE unit_number = 'B02'),
    '2026-11-01',
    1;

INSERT IGNORE INTO Leases (tenant_user_id, unit_id, start_date, active_status)
SELECT
    (SELECT user_id FROM Users WHERE email = 'tenant105@mwangaza.co.ke'),
    (SELECT unit_id FROM Units WHERE unit_number = 'C01'),
    '2026-08-01',
    1;

UPDATE Units SET status = 'Occupied'
WHERE unit_number IN ('A02', 'B01', 'B02', 'C01');

INSERT IGNORE INTO Charges (lease_id, charge_type, amount, due_date)
SELECT lease_id, 'Monthly Rent', 18000.00, '2026-11-05'
FROM Leases
WHERE tenant_user_id = (SELECT user_id FROM Users WHERE email = 'tenant102@mwangaza.co.ke')
  AND active_status = 1
LIMIT 1;

INSERT IGNORE INTO Charges (lease_id, charge_type, amount, due_date)
SELECT lease_id, 'Monthly Rent', 20000.00, '2026-11-05'
FROM Leases
WHERE tenant_user_id = (SELECT user_id FROM Users WHERE email = 'tenant103@mwangaza.co.ke')
  AND active_status = 1
LIMIT 1;

INSERT IGNORE INTO Charges (lease_id, charge_type, amount, due_date)
SELECT lease_id, 'Monthly Rent', 20000.00, '2026-11-05'
FROM Leases
WHERE tenant_user_id = (SELECT user_id FROM Users WHERE email = 'tenant104@mwangaza.co.ke')
  AND active_status = 1
LIMIT 1;

INSERT IGNORE INTO Charges (lease_id, charge_type, amount, due_date)
SELECT lease_id, 'Monthly Rent', 22000.00, '2026-11-05'
FROM Leases
WHERE tenant_user_id = (SELECT user_id FROM Users WHERE email = 'tenant105@mwangaza.co.ke')
  AND active_status = 1
LIMIT 1;

INSERT IGNORE INTO Payments (lease_id, amount, mpesa_code, verified_by_user_id)
SELECT
    lease_id,
    18000.00,
    'QK8H3P1L2A',
    (SELECT user_id FROM Users WHERE email = 'caretaker2@mwangaza.co.ke')
FROM Leases
WHERE tenant_user_id = (SELECT user_id FROM Users WHERE email = 'tenant102@mwangaza.co.ke')
  AND active_status = 1
LIMIT 1;

INSERT IGNORE INTO Payments (lease_id, amount, mpesa_code, verified_by_user_id)
SELECT
    lease_id,
    10000.00,
    'RM4T7N9C2B',
    (SELECT user_id FROM Users WHERE email = 'caretaker2@mwangaza.co.ke')
FROM Leases
WHERE tenant_user_id = (SELECT user_id FROM Users WHERE email = 'tenant103@mwangaza.co.ke')
  AND active_status = 1
LIMIT 1;
