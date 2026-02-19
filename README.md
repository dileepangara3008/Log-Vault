# LogVault

LogVault is a centralized log management and analysis platform designed to help teams securely upload, parse, store, search, monitor, and analyze application logs across multiple environments.

It provides role-based access control, multi-format parsing, audit tracking, dashboards, and file lifecycle management in a structured and secure workflow.

---

## Table of Contents

- Overview
- Core Functionalities
- User Roles
- Authentication & Authorization
- File Upload & Parsing
- Log Structure & Validation
- Log Search & Filtering
- Dashboard & Analytics
- File Lifecycle Management
- Audit Logging
- Database Overview
- Application Workflow
- Security Controls
- Error Handling Strategy
- Installation & Setup
- Configuration
- Future Enhancements

---

## Overview

Modern applications generate logs across environments such as DEV, QA, UAT, PROD, and STAG.  
LogVault centralizes log ingestion and provides structured parsing, secure storage, search capability, and analytical insights.

The system is designed to ensure:

- Structured log normalization
- Secure multi-user access
- Accurate parsing statistics
- Controlled visibility by role and team
- Full audit traceability

---

## Core Functionalities

- Secure user registration and login
- Role-based navigation (Admin / User)
- Multi-format log file upload
- Automated parser pipeline
- Accurate parsing statistics (raw vs parsed vs skipped)
- Advanced log search with filters
- Dashboard analytics and summaries
- File archiving and restoration
- Full audit trail for all critical actions

---

## User Roles

### Admin

Admins have full platform access:

- Admin Home
- User Management
- File Management
- Global Log Search (all teams)
- Global Dashboard View
- Audit / Security Logs
- Archive / Restore / Permanent Delete files

Safety Rule:
Admins cannot deactivate or delete their own accounts.

---

### User

Users operate within a restricted scope:

- Upload log files
- View personal logs
- View team logs
- Search logs
- View dashboards (limited to permission scope)
- Manage profile

---

## Authentication & Authorization

### Registration

Users provide:

- Name
- Phone
- Email
- Gender
- Team
- Role (Admin / User)
- Password (strong validation rules)

Data is stored across:

- users
- user_credentials
- user_roles
- user_teams

Passwords are securely hashed before storage.

---

### Login Validation

The system validates:

- Account status (active / deleted)
- Password correctness
- Account lock status (after repeated failures)

On successful login:

- Session is created
- Permissions are loaded into session
- Navigation menu renders dynamically based on role

---

## File Upload & Parsing

### Upload Workflow

1. User selects environment:
   - DEV
   - QA
   - UAT
   - PROD
   - STAG

2. User uploads log file (TXT / CSV / JSON / XML)

3. System actions:
   - Metadata stored in `raw_files`
   - File passed to parser pipeline
   - Upload action recorded in audit log

---

## Supported File Formats

### TXT
- Space-separated logs
- Pipe-separated logs
- Multiline logs supported

### CSV
- With or without headers

### JSON
- Array of log objects

### XML
Structure:
<logs>
  <log>...</log>
</logs>

## ⚙️ Parser Output Contract

Every parser returns:

(parsed_logs, raw_count, skipped_count)

## 🧩 Log Structure & Validation Rules

Each log entry must follow a structured validation model to ensure consistency and accurate parsing.

### Mandatory Fields

Every valid log entry must contain:

- `timestamp`
- `message`

If either of these fields is missing, the entry is considered invalid and will be skipped.

### Optional Field

- `severity` (defaults to `INFO` if not provided)

If severity is missing, the system automatically assigns the value `INFO`.

### Additional Fields

Any extra fields such as:

- `user`
- `ip`
- `service`
- `thread`
- `host`
- `module`
- or any other custom field

are appended to the `message` field to preserve complete log context without data loss.

### Invalid Entries

Invalid entries:

- Are skipped (non-fatal)
- Are counted in `skipped_count`
- Do NOT stop the parsing process
- Do NOT cause system failure

This ensures robustness against malformed or partially structured logs.

---

## 🔄 Parsing Flow

The parsing pipeline follows a structured, step-by-step process.

### Step 1 — File Read

- File is read once into memory
- Empty files are rejected immediately
- Large files are processed efficiently without multiple reads

---

### Step 2 — Format Detection

The parser is selected automatically based on file extension:

- `.txt`
- `.csv`
- `.json`
- `.xml`

This ensures correct parsing logic is applied.

---

### Step 3 — Raw Entry Counting

Before validation, the system calculates the total number of raw log entries.

| Format | Counting Logic |
|--------|---------------|
| TXT    | Number of log headers |
| CSV    | Number of rows |
| JSON   | Number of objects |
| XML    | Number of `<log>` elements |

This value is stored as `raw_count`.

---

### Step 4 — Field Extraction & Normalization

For each detected log entry:

- Normalize key names (`log_time`, `logTime`, `timestamp`)
- Extract required fields
- Assign default severity if missing
- Append additional fields to message
- Validate entry structure

Valid entries are added to `parsed_logs`.  
Invalid entries are safely skipped and recorded in `skipped_count`.

---

## 🔎 Log Search & Viewing

The system provides flexible and efficient log filtering.

### Available Filters

- Keyword search
- Severity level
- Category
- Environment
- Date range
- Pagination support

These filters can be combined for refined queries.

---

### Scope Control

Access is controlled based on user role:

#### Users

- View their own uploaded logs
- View logs belonging to their team

#### Admins

- View logs across all teams
- Filter logs by specific team
- Access complete dataset

This ensures strict role-based visibility control.

---

## 📊 Dashboard & Analytics

The dashboard provides aggregated insights instead of raw logs.

### File Overview Metrics

- Total files uploaded
- Active files
- Archived files

---

### Log Overview Metrics

- Total logs parsed
- Average logs per file
- Last file upload time

---

### Visual Insights

- Logs per day
- Severity distribution
- Top error messages
- Most active systems

Admins can view:

- Combined dashboards across teams
- Team-specific filtered dashboards

Users see dashboards limited to their permission scope.

---

## 🗄️ File Lifecycle Management

The system supports controlled file management.

### Admin Capabilities

Admins can:

- Archive files
- Restore archived files
- Permanently delete files

---

### Archived Files

Archived files:

- Are hidden from regular users
- Are stored in the `archives` table
- Can be restored at any time by administrators

This keeps active datasets optimized while maintaining recoverability.

---

## 🧾 Audit Logging

LogVault maintains a full audit trail to ensure transparency and accountability.

### Tracked Actions

- User login and logout
- File uploads
- Parsing results
- Archive and restore operations
- Administrative actions
- User management changes

Each audit record contains:

- User ID
- Action performed
- Timestamp
- Additional metadata

This ensures full traceability and security compliance.

---


---

## 🔐 Security Controls

LogVault implements multiple security mechanisms:

- Secure password hashing
- Role-based permission enforcement
- Account lock after repeated login failures
- Session-based authentication
- Restricted data visibility
- Full audit tracking
- Protection against unauthorized access

---

## ⚠️ Error Handling Strategy

The system is designed to be fault-tolerant.

- Empty files are rejected immediately
- Invalid entries are skipped safely
- Parsing errors are logged internally
- User-friendly error messages are shown in UI
- No fatal crashes on malformed logs

This ensures stability and reliability even with inconsistent log formats.

---


