-- =============================================================================
-- Mwangaza Apartments — Secure Rental Management System
-- MySQL 8.0 DDL Schema  (3NF)
-- Run: mysql -u srms_user -p srms_db < db/schema.sql
-- =============================================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------------
-- Roles
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Roles (
    role_id          INT            NOT NULL AUTO_INCREMENT,
    role_name        VARCHAR(50)    NOT NULL,
    permissions_mask VARCHAR(255)   NULL,
    PRIMARY KEY (role_id),
    UNIQUE KEY uq_roles_name (role_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Users (
    user_id         INT            NOT NULL AUTO_INCREMENT,
    email           VARCHAR(120)   NOT NULL,
    password_hash   VARCHAR(255)   NOT NULL,
    role_id         INT            NOT NULL,
    failed_attempts INT            NOT NULL DEFAULT 0,
    is_locked       TINYINT(1)     NOT NULL DEFAULT 0,
    lock_expiry     DATETIME       NULL,
    created_at      DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_users_email (email),
    CONSTRAINT fk_users_role FOREIGN KEY (role_id) REFERENCES Roles (role_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Units
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Units (
    unit_id      INT              NOT NULL AUTO_INCREMENT,
    unit_number  VARCHAR(20)      NOT NULL,
    monthly_rent DECIMAL(10, 2)   NOT NULL,
    status       ENUM('Vacant','Occupied','Maintenance') NOT NULL DEFAULT 'Vacant',
    deposit      DECIMAL(10, 2) NOT NULL DEFAULT 0,
    description  VARCHAR(500) NOT NULL DEFAULT '',
    image_url    VARCHAR(500) NULL,
    bedrooms     INT NOT NULL DEFAULT 1,
    bathrooms    INT NOT NULL DEFAULT 1,
    PRIMARY KEY (unit_id),
    UNIQUE KEY uq_units_number (unit_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Leases
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Leases (
    lease_id       INT        NOT NULL AUTO_INCREMENT,
    tenant_user_id INT        NOT NULL,
    unit_id        INT        NOT NULL,
    start_date     DATE       NOT NULL,
    end_date       DATE       NULL,
    active_status  TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (lease_id),
    CONSTRAINT fk_leases_tenant FOREIGN KEY (tenant_user_id) REFERENCES Users (user_id),
    CONSTRAINT fk_leases_unit   FOREIGN KEY (unit_id)        REFERENCES Units (unit_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Charges
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Charges (
    charge_id   INT            NOT NULL AUTO_INCREMENT,
    lease_id    INT            NOT NULL,
    charge_type VARCHAR(100)   NOT NULL,
    amount      DECIMAL(10, 2) NOT NULL,
    due_date    DATE           NOT NULL,
    created_at  DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (charge_id),
    CONSTRAINT fk_charges_lease FOREIGN KEY (lease_id) REFERENCES Leases (lease_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- Payments  (mpesa_code UNIQUE enforces duplicate-payment prevention)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS Payments (
    payment_id          INT            NOT NULL AUTO_INCREMENT,
    lease_id            INT            NOT NULL,
    amount              DECIMAL(10, 2) NOT NULL,
    mpesa_code          VARCHAR(10)    NOT NULL,
    payment_date        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    verified_by_user_id INT            NULL,
    created_at          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (payment_id),
    UNIQUE KEY uq_payments_mpesa (mpesa_code),
    CONSTRAINT fk_payments_lease    FOREIGN KEY (lease_id)            REFERENCES Leases (lease_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_payments_verifier FOREIGN KEY (verified_by_user_id) REFERENCES Users (user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- AuditLogs  (append-only; protected by trigger in triggers.sql)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS AuditLogs (
    log_id           INT          NOT NULL AUTO_INCREMENT,
    user_id          INT          NULL,
    action_type      VARCHAR(50)  NOT NULL,
    entity_affected  VARCHAR(100) NOT NULL,
    entity_id        INT          NULL,
    pre_change_json  JSON         NULL,
    post_change_json JSON         NULL,
    ip_address       VARCHAR(45)  NULL,
    timestamp        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (log_id),
    CONSTRAINT fk_auditlogs_user FOREIGN KEY (user_id) REFERENCES Users (user_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
