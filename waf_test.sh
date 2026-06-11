#!/bin/bash

TARGET="${TARGET:-https://localhost:8443}"

echo "===== WAF FULL HARDENED TEST ====="
echo ""

PASS=0
FAIL=0
ERRORS=0

test_attack() {
  NAME=$1
  CMD=$2

  RESPONSE=$(eval "$CMD")
  EXIT_CODE=$?

  if [ $EXIT_CODE -ne 0 ]; then
    STATUS="ERROR ❌"
    ((ERRORS++))
  elif [ "$RESPONSE" == "403" ]; then
    STATUS="BLOCKED ✅"
    ((PASS++))
  elif [ "$RESPONSE" == "405" ]; then
    STATUS="METHOD BLOCKED ✅"
    ((PASS++))
  elif [ "$RESPONSE" == "200" ]; then
    STATUS="ALLOWED ❌"
    ((FAIL++))
  else
    STATUS="UNEXPECTED ($RESPONSE)"
    ((FAIL++))
  fi

  printf "[%-35s] → %-20s\n" "$NAME" "$STATUS"
}

echo "Target: $TARGET"
echo ""

# =========================
# 🔹 CORE WAF TESTS
# =========================
# A benign User-Agent (-A 'Mozilla/5.0') is sent so the scanner rule (1000002)
# does NOT short-circuit these. That way a 403 proves ModSecurity detected the
# *payload*, not just the curl User-Agent.

UA="Mozilla/5.0"

test_attack "XSS basic" \
"curl -k -A '$UA' -s -o /dev/null -w '%{http_code}' \"$TARGET/?q=%3Cscript%3Ealert(1)%3C/script%3E\""

test_attack "XSS img" \
"curl -k -A '$UA' -s -o /dev/null -w '%{http_code}' \"$TARGET/?q=%3Cimg%20src=x%20onerror=alert(1)%3E\""

test_attack "SQLi basic" \
"curl -k -A '$UA' -s -o /dev/null -w '%{http_code}' \"$TARGET/?id=1%20OR%201=1--\""

test_attack "SQLi union" \
"curl -k -A '$UA' -s -o /dev/null -w '%{http_code}' \"$TARGET/?id=1%20UNION%20SELECT%20null--\""

test_attack "Path traversal" \
"curl -k -A '$UA' -s -o /dev/null -w '%{http_code}' \"$TARGET/?file=../../etc/passwd\""

test_attack "Traversal encoded" \
"curl -k -A '$UA' -s -o /dev/null -w '%{http_code}' \"$TARGET/?file=%2e%2e%2f%2e%2e%2fetc%2fpasswd\""

test_attack "Command injection" \
"curl -k -A '$UA' -s -o /dev/null -w '%{http_code}' \"$TARGET/?cmd=ls%3Bcat%20/etc/passwd\""

test_attack "RCE attempt" \
"curl -k -A '$UA' -s -o /dev/null -w '%{http_code}' \"$TARGET/?exec=%24(whoami)\""

test_attack "Header injection" \
"curl -k -A '$UA' -s -o /dev/null -w '%{http_code}' \"$TARGET/%0d%0aSet-Cookie:evil=1\""

# =========================
# 🔹 CUSTOM RULE TESTS
# =========================

# Open redirect (custom rule 1000001) — benign UA so we test the rule, not the UA.
test_attack "Open redirect blocked" \
"curl -k -A '$UA' -s -o /dev/null -w '%{http_code}' \"$TARGET/?redirect=http://evil.com\""

# Scanner detection (User-Agent) — these SHOULD be blocked by their UA (rule 1000002).
test_attack "Scanner blocked (sqlmap UA)" \
"curl -k -A 'sqlmap' -s -o /dev/null -w '%{http_code}' \"$TARGET/\""

test_attack "Scanner blocked (nikto UA)" \
"curl -k -A 'nikto' -s -o /dev/null -w '%{http_code}' \"$TARGET/\""

# Method restriction — valid REST verbs (PUT/PATCH/DELETE/OPTIONS) are now allowed,
# so we verify that genuinely invalid methods are still rejected (rule 1000003).
# Benign UA so the block is attributable to the method, not the User-Agent.
test_attack "Method TRACE blocked" \
"curl -k -A '$UA' -X TRACE -s -o /dev/null -w '%{http_code}' \"$TARGET/\""

test_attack "Method INVALID blocked" \
"curl -k -A '$UA' -X INVALID -s -o /dev/null -w '%{http_code}' \"$TARGET/\""

# =========================
# 🔹 SUMMARY
# =========================

echo ""
echo "===== SUMMARY ====="
echo "Blocked (expected): $PASS"
echo "Allowed (unexpected): $FAIL"
echo "Errors: $ERRORS"

echo ""

if [ $FAIL -eq 0 ]; then
  echo "✅ WAF is STRICT (all attacks blocked)"
else
  echo "⚠️ Some attacks passed → review rules"
fi