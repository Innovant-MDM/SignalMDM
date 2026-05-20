-- Migration to add approval tracking to audit_log

ALTER TABLE audit_log
ADD COLUMN approved_by VARCHAR(150) NULL;

ALTER TABLE audit_log
ADD COLUMN approval_reason VARCHAR(500) NULL;

COMMENT ON COLUMN audit_log.approved_by IS 'Who approved the override, if manual intervention occurred.';
COMMENT ON COLUMN audit_log.approval_reason IS 'Why the override was approved.';
