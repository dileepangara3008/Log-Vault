# ==========================
# AUTH - REGISTER
# ==========================

GET_TEAMS = """
SELECT team_id, team_name FROM teams
"""

GET_ROLES = """
SELECT role_id, role_name FROM roles
"""

INSERT_USER = """
INSERT INTO users
(first_name, last_name, phone_no, email, username, password_hash, gender)
VALUES (%s,%s,%s,%s,%s,%s,%s)
RETURNING user_id
"""

INSERT_USER_CREDENTIALS = """
INSERT INTO user_credentials (user_id)
VALUES (%s)
"""

INSERT_USER_ROLE = """
INSERT INTO user_roles (user_id, role_id)
VALUES (%s, %s)
"""

INSERT_USER_TEAM = """
INSERT INTO user_teams (user_id, team_id)
VALUES (%s, %s)
"""

# ==========================
# AUTH - LOGIN
# ==========================

GET_USER_FOR_LOGIN = """
SELECT u.user_id, u.password_hash, u.is_active, u.is_deleted,
       COALESCE(c.failed_attempts, 0) AS failed_attempts,
       COALESCE(c.is_locked, FALSE) AS is_locked,
       c.locked_until
FROM users u
LEFT JOIN user_credentials c ON u.user_id = c.user_id
WHERE u.email = %s
"""

UPDATE_FAILED_ATTEMPTS = """
UPDATE user_credentials
SET failed_attempts=%s,
    last_failed_at=NOW(),
    is_locked=%s,
    locked_until=%s
WHERE user_id=%s
"""

RESET_FAILED_ATTEMPTS = """
UPDATE user_credentials
SET failed_attempts=0,
    is_locked=FALSE,
    locked_until=NULL
WHERE user_id=%s
"""

CHECK_ADMIN = """
SELECT 1
FROM user_roles ur
JOIN roles r ON ur.role_id = r.role_id
WHERE ur.user_id = %s AND r.role_name = 'ADMIN'
LIMIT 1
"""

GET_USER_ROLES_AND_PERMISSIONS = """
SELECT r.role_name, p.permission_key
FROM user_roles ur
JOIN roles r ON ur.role_id = r.role_id
LEFT JOIN role_permissions rp ON rp.role_id = r.role_id
LEFT JOIN permissions p ON rp.permission_id = p.permission_id
WHERE ur.user_id = %s
"""

# ==========================
# UPLOAD QUERIES
# ==========================

GET_ENVIRONMENTS = """
SELECT environment_id, environment_code
FROM environments
"""

GET_TEAM_ID = """
SELECT team_id
FROM user_teams
WHERE user_id = %s
LIMIT 1
"""

GET_EXISTING_HASHES = """
SELECT file_hash
FROM raw_files
WHERE is_archived = FALSE
"""

INSERT_RAW_FILE = """
INSERT INTO raw_files
(team_id, uploaded_by, original_name, file_size_bytes,
 format_id, environment_id, file_hash)
VALUES (
    %s, %s, %s, %s,
    (SELECT format_id FROM file_formats WHERE format_name=%s),
    %s, %s
)
RETURNING file_id
"""

INSERT_FILE_PARSE_STATS = """
INSERT INTO file_parse_stats
(file_id, total_logs, parsed_logs, skipped_logs, parsed_percentage)
VALUES (%s, %s, %s, %s, %s)
"""

# ==========================
# FILES MODULE QUERIES
# ==========================

GET_ALL_FILES_ADMIN = """
SELECT rf.file_id, rf.original_name, rf.file_size_bytes,
       to_char(rf.uploaded_at,'YYYY-MM-DD HH24:MI:SS'),
       u.email, t.team_name, rf.is_archived
FROM raw_files rf
JOIN users u ON rf.uploaded_by = u.user_id
JOIN teams t ON rf.team_id = t.team_id
ORDER BY rf.uploaded_at DESC
"""

GET_USER_FILES = """
SELECT rf.file_id, rf.original_name, rf.file_size_bytes,
       to_char(rf.uploaded_at,'YYYY-MM-DD HH24:MI:SS'),
       u.email, t.team_name, rf.is_archived
FROM raw_files rf
JOIN users u ON rf.uploaded_by = u.user_id
JOIN teams t ON rf.team_id = t.team_id
WHERE rf.uploaded_by = %s AND rf.is_archived = FALSE
ORDER BY rf.uploaded_at DESC
"""

GET_FILE_BY_ID = """
SELECT file_id, original_name, uploaded_by, is_archived
FROM raw_files
WHERE file_id = %s
"""

DELETE_FILE = """
DELETE FROM raw_files WHERE file_id = %s
"""

COUNT_FILE_LOGS = """
SELECT COUNT(*)
FROM log_entries
WHERE file_id = %s
"""

INSERT_ARCHIVE = """
INSERT INTO archives (file_id, archived_on, total_records)
VALUES (%s, NOW(), %s)
"""

MARK_FILE_ARCHIVED = """
UPDATE raw_files
SET is_archived = TRUE
WHERE file_id = %s
"""

UNARCHIVE_FILE = """
UPDATE raw_files
SET is_archived = FALSE
WHERE file_id = %s
"""

DELETE_ARCHIVE = """
DELETE FROM archives WHERE file_id = %s
"""

# ==========================
# ADMIN QUERIES
# ==========================

GET_ADMIN_NAME = """
SELECT CONCAT(first_name, ' ', last_name)
FROM users
WHERE user_id = %s
"""

GET_ALL_USERS = """
SELECT user_id, first_name, last_name, email, username,
       is_active, is_deleted,
       to_char(created_at,'YYYY-MM-DD HH24:MI:SS')
FROM users
ORDER BY created_at DESC
"""

INSERT_ADMIN_USER = """
INSERT INTO users
(first_name, last_name, phone_no, email, username, password_hash, gender)
VALUES (%s,%s,%s,%s,%s,%s,%s)
RETURNING user_id
"""

TOGGLE_USER_ACTIVE = """
UPDATE users
SET is_active = NOT is_active,
    updated_at = NOW()
WHERE user_id = %s
RETURNING is_active
"""

GET_USERNAME = """
SELECT username FROM users WHERE user_id = %s
"""

GET_SECURITY_LOGS = """
SELECT a.action_id,
       u.username,
       a.action_type,
       to_char(a.action_time,'YYYY-MM-DD HH24:MI:SS')
FROM audit_trail a
JOIN users u ON u.user_id = a.user_id
ORDER BY a.action_time DESC
"""

SOFT_DELETE_USER = """
UPDATE users
SET is_deleted = TRUE,
    is_active = FALSE,
    updated_at = NOW()
WHERE user_id = %s
"""

RESTORE_USER = """
UPDATE users
SET is_deleted = FALSE,
    is_active = TRUE,
    updated_at = NOW()
WHERE user_id = %s
"""

# ===============
# SEARCH 
# ===============
GET_MIN_MAX_UPLOAD_DATE = """
SELECT MIN(log_timestamp), MAX(log_timestamp)
FROM log_entries
"""

GET_ALL_TEAMS = """
SELECT team_id, team_name
FROM teams
ORDER BY team_name
"""

GET_USER_TEAM_IDS = """
SELECT team_id
FROM user_teams
WHERE user_id = %s
"""

GET_SEVERITIES = """
SELECT severity_code
FROM log_severities
ORDER BY severity_level
"""

GET_CATEGORIES = """
SELECT category_name
FROM log_categories
ORDER BY category_name
"""

GET_ENVIRONMENTS = """
SELECT environment_code
FROM environments
ORDER BY environment_code
"""
