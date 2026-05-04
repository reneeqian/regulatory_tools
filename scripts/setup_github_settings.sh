#!/usr/bin/env bash
# Applies the standard GitHub repository settings for safety-regulated SaMD projects.
#
# Usage:
#   ./setup_github_settings.sh <owner/repo> [codeowner] [ci_check]
#
# Arguments:
#   owner/repo    Required. e.g. reneeqian/my_new_project
#   codeowner     GitHub username for CODEOWNERS. Defaults to the owner part of owner/repo.
#   ci_check      Name of the CI status check. Default: forge-health
#                 (forge-health runs pytest internally, so no separate test job is needed)
#
# Prerequisites:
#   - gh CLI authenticated (gh auth status)
#   - The repo must already exist on GitHub
#   - Both 'main' and 'dev' branches must already exist in the repo
#
# What this script configures:
#   Repo level:
#     - Squash merge allowed, merge commit allowed, rebase merge DISABLED
#     - Auto-delete head branches on merge enabled
#     - Auto-merge capability enabled (gated by branch protection)
#
#   main branch:
#     - PR required with 1 approving review + code owner review (@codeowner)
#     - Status checks required (ci_check), strict (branch must be up-to-date)
#     - No force pushes, no deletions
#     - Ruleset: only merge commits allowed, stale reviews dismissed on push,
#       deletion and force-push blocked
#
#   dev branch:
#     - PR required, no approval needed
#     - Status checks required (ci_check), non-strict
#     - No force pushes, no deletions
#     - Ruleset: only squash merges allowed, ci_check required before merge
#
#   CODEOWNERS:
#     - Prints instructions to commit .github/CODEOWNERS — not automated because
#       it requires a git commit in the local repo clone.

set -euo pipefail

# ── Arguments ────────────────────────────────────────────────────────────────
REPO="${1:-}"
if [[ -z "$REPO" ]]; then
  echo "Usage: $0 <owner/repo> [codeowner] [ci_check] [health_check]" >&2
  exit 1
fi

OWNER="${REPO%%/*}"
CODEOWNER="${2:-$OWNER}"
CI_CHECK="${3:-forge-health}"

echo "Configuring: $REPO"
echo "  Code owner : @$CODEOWNER"
echo "  CI check   : $CI_CHECK"
echo ""

# ── Helper ───────────────────────────────────────────────────────────────────
gh_api() {
  gh api "$@"
}

# ── 1. Repo-level settings ───────────────────────────────────────────────────
echo "[1/5] Repo-level settings..."
gh_api "repos/$REPO" --method PATCH \
  --field allow_squash_merge=true \
  --field allow_merge_commit=true \
  --field allow_rebase_merge=false \
  --field delete_branch_on_merge=true \
  --field allow_auto_merge=true \
  --silent
echo "      rebase=off, squash+merge=on, delete-on-merge=on, auto-merge=on"

# ── 2. main — classic branch protection ──────────────────────────────────────
echo "[2/5] main branch protection (classic)..."
echo "{
  \"required_status_checks\": {
    \"strict\": true,
    \"checks\": [{\"context\": \"$CI_CHECK\"}]
  },
  \"enforce_admins\": false,
  \"required_pull_request_reviews\": {
    \"required_approving_review_count\": 1,
    \"dismiss_stale_reviews\": false,
    \"require_code_owner_reviews\": true
  },
  \"restrictions\": null,
  \"allow_deletions\": false,
  \"allow_force_pushes\": false
}" | gh_api "repos/$REPO/branches/main/protection" --method PUT --input - --silent
echo "      PR required, 1 review + code owner, strict CI, no force-push/delete"

# ── 3. dev — classic branch protection ───────────────────────────────────────
echo "[3/5] dev branch protection (classic)..."
echo "{
  \"required_status_checks\": {
    \"strict\": false,
    \"checks\": [{\"context\": \"$CI_CHECK\"}]
  },
  \"enforce_admins\": false,
  \"required_pull_request_reviews\": {
    \"required_approving_review_count\": 0,
    \"dismiss_stale_reviews\": false,
    \"require_code_owner_reviews\": false
  },
  \"restrictions\": null,
  \"allow_deletions\": false,
  \"allow_force_pushes\": false
}" | gh_api "repos/$REPO/branches/dev/protection" --method PUT --input - --silent
echo "      PR required (no approval), CI required, no force-push/delete"

# ── 4. Rulesets ───────────────────────────────────────────────────────────────
echo "[4/5] Rulesets..."

# Check for existing rulesets to decide create vs update
EXISTING=$(gh_api "repos/$REPO/rulesets" --jq '[.[] | {id: .id, name: .name}]' 2>/dev/null || echo "[]")

get_ruleset_id() {
  local name="$1"
  echo "$EXISTING" | python3 -c "
import json, sys
data = json.load(sys.stdin)
match = next((r['id'] for r in data if r['name'] == '$name'), None)
print(match if match else '')
"
}

upsert_ruleset() {
  local name="$1"
  local body="$2"
  local existing_id
  existing_id=$(get_ruleset_id "$name")
  if [[ -n "$existing_id" ]]; then
    echo "$body" | gh_api "repos/$REPO/rulesets/$existing_id" --method PUT --input - --silent
    echo "      updated ruleset: $name (id=$existing_id)"
  else
    echo "$body" | gh_api "repos/$REPO/rulesets" --method POST --input - --silent
    echo "      created ruleset: $name"
  fi
}

# main ruleset — merge commit only, dismiss stale, no delete/force-push
upsert_ruleset "protect the main" "{
  \"name\": \"protect the main\",
  \"target\": \"branch\",
  \"enforcement\": \"active\",
  \"conditions\": {\"ref_name\": {\"include\": [\"~DEFAULT_BRANCH\"], \"exclude\": []}},
  \"bypass_actors\": [],
  \"rules\": [
    {\"type\": \"deletion\"},
    {\"type\": \"non_fast_forward\"},
    {\"type\": \"pull_request\", \"parameters\": {
      \"allowed_merge_methods\": [\"merge\"],
      \"required_approving_review_count\": 1,
      \"dismiss_stale_reviews_on_push\": true,
      \"require_code_owner_review\": false,
      \"require_last_push_approval\": false,
      \"required_review_thread_resolution\": false
    }}
  ]
}"

# dev ruleset — squash only, CI required before auto-merge
upsert_ruleset "Dev branch — require CI before auto-merge" "{
  \"name\": \"Dev branch — require CI before auto-merge\",
  \"target\": \"branch\",
  \"enforcement\": \"active\",
  \"conditions\": {\"ref_name\": {\"include\": [\"refs/heads/dev\"], \"exclude\": []}},
  \"bypass_actors\": [],
  \"rules\": [
    {\"type\": \"required_status_checks\", \"parameters\": {
      \"required_status_checks\": [{\"context\": \"$CI_CHECK\"}],
      \"strict_required_status_checks_policy\": false,
      \"do_not_enforce_on_create\": false
    }},
    {\"type\": \"pull_request\", \"parameters\": {
      \"allowed_merge_methods\": [\"squash\"],
      \"required_approving_review_count\": 0,
      \"dismiss_stale_reviews_on_push\": false,
      \"require_code_owner_review\": false,
      \"require_last_push_approval\": false,
      \"required_review_thread_resolution\": false
    }}
  ]
}"

# ── 5. CODEOWNERS reminder ───────────────────────────────────────────────────
echo "[5/5] CODEOWNERS..."
echo "      ACTION REQUIRED — commit this file to your repo on the default branch:"
echo ""
echo "      mkdir -p .github"
echo "      echo '* @$CODEOWNER' > .github/CODEOWNERS"
echo "      git add .github/CODEOWNERS"
echo "      git commit -m 'chore: add CODEOWNERS'"
echo "      git push origin dev"
echo ""
echo "      (This cannot be automated here because it requires a local git clone.)"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "Done. Settings applied to $REPO."
echo ""
echo "Summary:"
echo "  main  — 1 review + code owner + strict CI (merge commit only, no force-push/delete)"
echo "  dev   — PR required + CI (squash only, no force-push/delete)"
echo "  repo  — auto-delete branches on merge, auto-merge enabled, rebase disabled"
