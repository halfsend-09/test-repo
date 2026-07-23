#!/usr/bin/env bash
# post-fix-test.sh — Test the push retry logic from post-fix.sh.
#
# Extracts and tests the push-retry decision logic in isolation using shell
# functions. This avoids needing a full git repo or GitHub API access.
#
# Run from the repo root:
#   bash internal/scaffold/fullsend-repo/scripts/post-fix-test.sh

set -euo pipefail

FAILURES=0

# ---------------------------------------------------------------------------
# Test helper — reimplements the push retry logic from post-fix.sh section 5.
# Given a push exit code and output, returns the action.
# ---------------------------------------------------------------------------
decide_push_retry() {
  local push_rc="$1"
  local push_output="$2"

  if [ "${push_rc}" -eq 0 ]; then
    echo "success"
    return 0
  fi

  if echo "${push_output}" | grep -qi "non-fast-forward\|rejected\|fetch first"; then
    echo "retry:force-with-lease"
    return 0
  fi

  echo "fail:unexpected-error"
  return 0
}

run_push_retry_test() {
  local test_name="$1"
  local push_rc="$2"
  local push_output="$3"
  local expected_prefix="$4"

  local actual
  actual="$(decide_push_retry "${push_rc}" "${push_output}")"

  if [[ "${actual}" != ${expected_prefix}* ]]; then
    echo "FAIL: ${test_name}"
    echo "  push_rc:         '${push_rc}'"
    echo "  push_output:     '${push_output}'"
    echo "  expected prefix: '${expected_prefix}'"
    echo "  actual:          '${actual}'"
    FAILURES=$((FAILURES + 1))
    return
  fi

  echo "PASS: ${test_name}"
}

# --- Push retry test cases ---

# Successful push → no retry needed
run_push_retry_test "push-success" \
  "0" "Everything up-to-date" "success"

# Non-fast-forward error → retry with --force-with-lease
run_push_retry_test "push-non-fast-forward" \
  "1" "error: failed to push some refs: non-fast-forward" "retry:force-with-lease"

# Rejected error → retry with --force-with-lease
run_push_retry_test "push-rejected" \
  "1" "! [rejected] agent/42 -> agent/42 (fetch first)" "retry:force-with-lease"

# Unknown error → fail
run_push_retry_test "push-unexpected-error" \
  "1" "fatal: repository not found" "fail:unexpected-error"

# ---------------------------------------------------------------------------
# Test helper — reimplements the pre-commit auto-fix retry decision logic
# from post-fix.sh section 3. Given a pre-commit exit code and whether
# unstaged changes exist, returns the action the script would take.
# ---------------------------------------------------------------------------
decide_precommit_retry() {
  local precommit_rc="$1"          # 0 = passed, 1 = failed
  local has_unstaged="$2"          # "yes" or "no"
  local retry_precommit_rc="$3"    # 0 = passed on retry, 1 = still fails (ignored if no retry)
  local retry_has_unstaged="${4:-no}"  # "yes" if retry left unstaged changes

  if [ "${precommit_rc}" -eq 0 ]; then
    echo "pass:clean"
    return 0
  fi

  # Pre-commit failed — check for auto-fixed files
  if [ "${has_unstaged}" = "yes" ]; then
    if [ "${retry_precommit_rc}" -eq 0 ]; then
      if [ "${retry_has_unstaged}" = "yes" ]; then
        echo "blocked:retry-left-unstaged"
      else
        echo "pass:auto-fixed"
      fi
    else
      echo "blocked:retry-failed"
    fi
  else
    echo "blocked:no-auto-fix"
  fi
}

run_precommit_retry_test() {
  local test_name="$1"
  local precommit_rc="$2"
  local has_unstaged="$3"
  local retry_precommit_rc="$4"
  local expected="$5"
  local retry_has_unstaged="${6:-no}"

  local actual
  actual="$(decide_precommit_retry "${precommit_rc}" "${has_unstaged}" "${retry_precommit_rc}" "${retry_has_unstaged}")"

  if [ "${actual}" != "${expected}" ]; then
    echo "FAIL: ${test_name}"
    echo "  precommit_rc:         '${precommit_rc}'"
    echo "  has_unstaged:         '${has_unstaged}'"
    echo "  retry_precommit_rc:   '${retry_precommit_rc}'"
    echo "  retry_has_unstaged:   '${retry_has_unstaged}'"
    echo "  expected:             '${expected}'"
    echo "  actual:               '${actual}'"
    FAILURES=$((FAILURES + 1))
    return
  fi

  echo "PASS: ${test_name}"
}

# --- Pre-commit auto-fix retry test cases ---

# Pre-commit passes on first run → no retry needed
run_precommit_retry_test "precommit-passes-first-run" \
  "0" "no" "0" "pass:clean"

# Pre-commit fails, hooks auto-fixed files, retry succeeds
run_precommit_retry_test "precommit-auto-fix-retry-succeeds" \
  "1" "yes" "0" "pass:auto-fixed"

# Pre-commit fails, hooks auto-fixed files, retry still fails
run_precommit_retry_test "precommit-auto-fix-retry-fails" \
  "1" "yes" "1" "blocked:retry-failed"

# Pre-commit fails, no unstaged changes (genuine failure)
run_precommit_retry_test "precommit-genuine-failure" \
  "1" "no" "0" "blocked:no-auto-fix"

# Pre-commit passes but unstaged changes exist (e.g. hook wrote a log file)
run_precommit_retry_test "precommit-passes-with-unstaged" \
  "0" "yes" "0" "pass:clean"

# Pre-commit fails, auto-fix retry passes, but retry left unstaged changes
run_precommit_retry_test "precommit-retry-passes-but-left-unstaged" \
  "1" "yes" "0" "blocked:retry-left-unstaged" "yes"

# ---------------------------------------------------------------------------
# Test helper — reimplements the label re-trigger logic from post-fix.sh
# section 5 (#5188), exercising the actual remove-then-add call sequence
# against a stubbed `gh` so failures in either call are tolerated exactly as
# post-fix.sh tolerates them: a failed --remove-label is always silent (the
# label may not have existed), a failed --add-label warns but must never
# make the script exit nonzero — a re-dispatch miss is not worth failing an
# otherwise-successful fix push over.
# ---------------------------------------------------------------------------
perform_relabel_retrigger() {
  local pr_number="$1" repo="$2"
  gh pr edit "${pr_number}" --repo "${repo}" \
    --remove-label "ready-for-review" 2>/dev/null || true
  gh pr edit "${pr_number}" --repo "${repo}" \
    --add-label "ready-for-review" 2>/dev/null || \
    echo "::warning::Failed to re-apply ready-for-review label to PR #${pr_number} — review will not be re-dispatched"
}

run_relabel_test() {
  local test_name="$1" fail_call="$2" expect_warning="$3"

  # Stub gh: fail whichever call fail_call names, succeed otherwise.
  gh() {
    if [[ "$*" == *"--remove-label"* ]]; then
      [[ "${fail_call}" == "remove" || "${fail_call}" == "both" ]] && return 1
      return 0
    elif [[ "$*" == *"--add-label"* ]]; then
      [[ "${fail_call}" == "add" || "${fail_call}" == "both" ]] && return 1
      return 0
    fi
    return 0
  }

  local output rc
  output="$(perform_relabel_retrigger "123" "org/repo")"
  rc=$?
  unset -f gh

  if [ "${rc}" -ne 0 ]; then
    echo "FAIL: ${test_name} (exited ${rc} — re-trigger must never hard-fail)"
    FAILURES=$((FAILURES + 1))
    return
  fi

  local has_warning="no"
  echo "${output}" | grep -q "::warning::Failed to re-apply" && has_warning="yes"

  if [ "${has_warning}" != "${expect_warning}" ]; then
    echo "FAIL: ${test_name}"
    echo "  expected warning: '${expect_warning}', got: '${has_warning}'"
    echo "  output: ${output}"
    FAILURES=$((FAILURES + 1))
    return
  fi

  echo "PASS: ${test_name}"
}

# --- Label re-trigger test cases ---

# Both calls succeed → no warning, no failure.
run_relabel_test "relabel-both-succeed" "none" "no"

# Remove fails (e.g. label wasn't present — first fix run on a PR whose
# label was never applied) — silent, add still runs and succeeds.
run_relabel_test "relabel-remove-fails-add-succeeds" "remove" "no"

# Add fails (e.g. API error, label deleted from repo) — warns, does not fail.
run_relabel_test "relabel-add-fails" "add" "yes"

# Both fail — still just a warning, never a hard failure.
run_relabel_test "relabel-both-fail" "both" "yes"

# --- Summary ---

echo ""
if [ ${FAILURES} -gt 0 ]; then
  echo "${FAILURES} test(s) failed"
  exit 1
fi
echo "All tests passed"
