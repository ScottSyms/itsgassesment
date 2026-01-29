# ITSG-33 Accreditation System Quickstart

This is the short version. Use it when you just want to run a cycle of evidence submission and close gaps fast.

## The loop
1. Create an assessment
2. Upload evidence
3. Run the assessment
4. Review missing or partial controls
5. Upload targeted evidence
6. Rerun

Repeat until missing controls drop to zero.

## 0) Sign in
- Set `INITIAL_ADMIN_EMAIL` and `INITIAL_ADMIN_PASSWORD` in `.env` before first startup
- Open the dashboard at http://localhost:8000
- Sign in with the admin account

## 1) Create an assessment
- Open the dashboard at http://localhost:8000
- Click New Assessment
- Fill in Client ID and Project Name
- (Optional) Upload a CONOPS file

## 2) Upload evidence
Supported formats include:
- Documents: PDF, DOCX, TXT, MD
- Logs: LOG (large logs are sampled automatically)
- Images: PNG, JPG
- Videos: MP4, MOV (key frames extracted automatically)
- Repo archives: ZIP, TAR.GZ (Terraform, Helm, code)

Tips:
- Add a Significance Note for each file. It tells the AI why the file matters.
- Repo archives are unpacked and scanned for IaC and code.
- Files larger than 1 MB inside a repo archive are skipped.

## 3) Run the assessment
- Click Run Assessment
- Wait for status to show completed

## 4) Review gaps
Look for:
- Controls Missing Evidence
- Controls with Partial Evidence

These are your next targets for evidence.

## 5) Upload targeted evidence and rerun
- Add Docs to an existing assessment or create a new upload batch
- Focus on high quality evidence first (IaC, logs, config exports)
- Rerun the assessment

## 6) Export reports
- Open the assessment
- Choose report language (EN or FR)
- Download Word or POA&M

## 7) Delete, restore, or purge
- Delete in the Assessments tab (soft delete)
- Restore within 30 days
- Purge immediately if needed

## Example gap closing
- Missing AU-2: Upload audit log exports
- Missing SC-28: Upload Terraform or Helm configs showing encryption at rest
- Missing AC-3: Upload Helm RBAC manifests or IAM policy files

## If you want the long version
See docs/USER_GUIDE.md
