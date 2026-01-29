# ITSG-33 Accreditation System User Guide

This guide shows how to use the system in real client workflows where evidence is submitted repeatedly to reduce missing controls.

## What this system does
The platform analyzes your CONOPS and evidence, maps applicable ITSG-33 controls, and highlights missing or partial evidence. The main value is in the iterative loop: submit evidence, rerun, and watch coverage improve.

## Authentication and roles
- Sign in at http://localhost:8000 using the admin account created from `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` on first startup.
- Roles: admin (full access), assessor (run assessments), client (upload and view shared assessments), viewer (read-only for shared assessments).
- Passwords must be at least 12 characters and not common words.

## Core workflow (repeatable loop)
1. Create an assessment
2. Upload evidence with Significance Notes
3. Run the assessment
4. Review missing or partial controls
5. Upload targeted evidence
6. Rerun

Repeat until your missing controls drop to zero or are explicitly marked not applicable.

## Create an assessment
1. Open the dashboard at http://localhost:8000
2. Click New Assessment
3. Fill in Client ID and Project Name
4. (Optional) Upload a CONOPS file

The CONOPS helps the AI categorize the system and choose the right ITSG-33 profile.

## Share assessments
Admins and assessors can grant access to a client or viewer via the API:

```
POST /api/v1/assessment/{assessment_id}/share
{
  "user_id": "<user-id>",
  "role_scope": "client"
}
```

To remove access:

```
DELETE /api/v1/assessment/{assessment_id}/share/{user_id}
```

## Upload evidence
Supported formats include:
- Documents: PDF, DOCX, TXT, MD
- Logs: LOG (large logs are sampled automatically)
- Images: PNG, JPG
- Videos: MP4, MOV (key frames are extracted)
- Repo archives: ZIP, TAR.GZ (Terraform, Helm, and source code)

### Significance Notes (recommended)
Each file has a Significance Note field. Use it to tell the AI why the file matters. Example:

- "Shows encryption at rest for S3 and RDS"
- "Audit logs confirming admin MFA enforcement"
- "Helm chart with RBAC and PodSecurityContext"

You can also edit comments after upload for a single file (use the Uploaded Files list in the Documents step or the API).

API example for updating a single file comment:

```
PATCH /api/v1/assessment/{assessment_id}/documents/{file_id}/metadata
{
  "significance_note": "Updated comment"
}
```

## Repo archive uploads (IaC and code)
If you upload a ZIP or TAR.GZ of a cloned repo, the system will:
- Unpack it
- Identify IaC (Terraform, Helm, Kubernetes manifests)
- Identify application code (Python, JavaScript, Go, etc.)
- Prioritize files with security keywords

Notes:
- Files larger than 1 MB are skipped
- Helm sub charts are included
- Security keyword matches are prioritized but not required

## Evidence strength tiers (high level)
The system prefers machine verifiable evidence. This matters for gap reduction.

1. System generated (logs, config exports)
2. Infrastructure as code (Terraform, Helm, K8s)
3. Automated test (scan reports, CI results)
4. Code enforcement (auth middleware, crypto usage)
5. Screenshot
6. Video walkthrough
7. Narrative text

Best practice: lead with tiers 1 to 4 for faster progress.

## Running and rerunning
After upload, click Run Assessment. When complete, review:
- Controls with Full Evidence
- Controls with Partial Evidence
- Controls Missing Evidence

Then upload targeted evidence and rerun. The system keeps run history so you can track improvements.

## Closing gaps faster (examples)
- Missing AU-2: upload audit log exports or config log settings
- Missing SC-28: upload Terraform or Helm configs that enable encryption at rest
- Missing AC-3: upload RBAC manifests or IAM policies

## Reports
You can download:
- Word report
- POA&M report

Select report language (EN or FR) at download time.

## Soft delete, restore, and purge
Assessments are soft deleted by default:
- Deleted assessments are hidden everywhere
- You can restore within 30 days
- Auto purge runs after 30 days

If needed, you can purge immediately.

## Troubleshooting
### Upload is too fast to add comments
Disable Auto upload in the Documents step. Files stay in a pending list until you click Upload and Continue.

### Repo archives are not accepted
Make sure the upload accepts ZIP and TAR.GZ. The UI should show it in supported formats.

### Evidence not detected
Add a Significance Note and use clear config or code excerpts. Logs and IaC are the fastest path to full coverage.

## Quick checklist for clients
- Did you attach a Significance Note for each file?
- Are missing controls targeted with IaC or logs?
- Are you rerunning after each batch of evidence?
- Are you using repo archives for Terraform and Helm?
