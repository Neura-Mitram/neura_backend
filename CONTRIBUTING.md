# Neura Backend - Contribution Guide

Welcome contributors! This document explains the development workflow for Neura Backend. Please follow these guidelines carefully.

## 🌿 Branch Structure
- `main` **Protected Production Branch**  
  (Admin-only merges after CI/CD checks)
- `dev` **Primary Development Branch**  
  (All contributor work happens here)

## 🛠️ Contribution Workflow

### 1. Clone the Repository
```bash
git clone https://github.com/Neura-Mitram/neura_backend.git
cd neura_backend

2. Switch to Dev Branch
bash
git checkout dev

3. Create Feature Branch (Directly from dev)
bash
git checkout -b feature/your-feature-name
(Replace your-feature-name with brief description)

4. Make Changes & Commit
bash
git add .
git commit -m "feat: add login endpoint"  # Use conventional commit format
Commit Message Format:
<type>: <description>
Types: feat, fix, docs, style, refactor, test, chore

5. Push Changes
bash
git push origin feature/your-feature-name
6. Create Pull Request (PR)
Go to PR creation page

Set base branch: dev

Set compare branch: your-feature-branch

Add PR title: [Feature] Your Feature Name

Include:

Description of changes

Screenshots if applicable

Verified locally confirmation

7. PR Review Process
CI/CD checks will automatically run

Admin (@byshiladityamallick) will review

Address feedback via new commits to same branch

8. After Merge
Your feature branch will be deleted automatically

Keep local repo updated:

bash
git checkout dev
git pull origin dev
🔒 Critical Rules
⚠️ Never push directly to main
(Branch protection enforced with CI/CD requirements)

⚠️ Always branch from latest dev

Test locally before creating PRs

Update documentation when changing APIs

Keep PRs focused - one feature/fix per PR

✅ Pre-PR Checklist
Ran local tests

Verified functionality

Followed commit message convention

No commented-out code

Updated documentation if needed

🚨 Need Help?
For technical questions: Open an Issue

For workflow questions: Mention @byshiladityamallick in PR comments

For urgent matters: Contact admin via GitHub profile
