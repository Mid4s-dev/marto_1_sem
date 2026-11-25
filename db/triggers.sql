-- =============================================================================
-- Mwangaza Apartments — Security Triggers
-- Run AFTER schema.sql:
--   mysql -u srms_user -p srms_db < db/triggers.sql
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Trigger 1: Prevent double-allocation of an already-occupied unit
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_verify_unit_availability;

DELIMITER //
CREATE TRIGGER trg_verify_unit_availability
BEFORE INSERT ON Leases
FOR EACH ROW
BEGIN
    DECLARE unit_curr_status VARCHAR(20);
    SELECT status INTO unit_curr_status
    FROM Units
    WHERE unit_id = NEW.unit_id;

    IF unit_curr_status = 'Occupied' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Integrity Violation: Target Unit is already occupied.';
    END IF;
END; //
DELIMITER ;


-- ---------------------------------------------------------------------------
-- Trigger 2: Prevent any UPDATE on AuditLogs (append-only enforcement)
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_prevent_audit_tampering_update;

DELIMITER //
CREATE TRIGGER trg_prevent_audit_tampering_update
BEFORE UPDATE ON AuditLogs
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Security Policy Violation: Mutation of audit log records is prohibited.';
END; //
DELIMITER ;


-- ---------------------------------------------------------------------------
-- Trigger 3: Prevent any DELETE on AuditLogs
-- ---------------------------------------------------------------------------
DROP TRIGGER IF EXISTS trg_prevent_audit_tampering_delete;

DELIMITER //
CREATE TRIGGER trg_prevent_audit_tampering_delete
BEFORE DELETE ON AuditLogs
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Security Policy Violation: Deletion of audit log records is prohibited.';
END; //
DELIMITER ;
