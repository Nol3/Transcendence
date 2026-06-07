#!/bin/bash

TARGET="https://localhost"

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

test_attack "XSS basic" \
"curl -k -s -o /dev/null -w '%{http_code}' \"$TARGET/?q=%3Cscript%3Ealert(1)%3C/script%3E\""

test_attack "XSS img" \
"curl -k -s -o /dev/null -w '%{http_code}' \"$TARGET/?q=%3Cimg%20src=x%20onerror=alert(1)%3E\""

test_attack "SQLi basic" \
"curl -k -s -o /dev/null -w '%{http_code}' \"$TARGET/?id=1%20OR%201=1--\""

test_attack "SQLi union" \
"curl -k -s -o /dev/null -w '%{http_code}' \"$TARGET/?id=1%20UNION%20SELECT%20null--\""

test_attack "Path traversal" \
"curl -k -s -o /dev/null -w '%{http_code}' \"$TARGET/?file=../../etc/passwd\""

test_attack "Traversal encoded" \
"curl -k -s -o /dev/null -w '%{http_code}' \"$TARGET/?file=%2e%2e%2f%2e%2e%2fetc%2fpasswd\""

test_attack "Command injection" \
"curl -k -s -o /dev/null -w '%{http_code}' \"$TARGET/?cmd=ls%3Bcat%20/etc/passwd\""

test_attack "RCE attempt" \
"curl -k -s -o /dev/null -w '%{http_code}' \"$TARGET/?exec=%24(whoami)\""

test_attack "Header injection" \
"curl -k -s -o /dev/null -w '%{http_code}' \"$TARGET/%0d%0aSet-Cookie:evil=1\""

# =========================
# 🔹 CUSTOM RULE TESTS
# =========================

# Open redirect (your rule)
test_attack "Open redirect blocked" \
"curl -k -s -o /dev/null -w '%{http_code}' \"$TARGET/?redirect=http://evil.com\""

# Scanner detection (User-Agent)
test_attack "Scanner blocked (sqlmap UA)" \
"curl -k -A 'sqlmap' -s -o /dev/null -w '%{http_code}' \"$TARGET/\""

test_attack "Scanner blocked (nikto UA)" \
"curl -k -A 'nikto' -s -o /dev/null -w '%{http_code}' \"$TARGET/\""

# Method restriction
test_attack "Method DELETE blocked" \
"curl -k -X DELETE -s -o /dev/null -w '%{http_code}' \"$TARGET/\""

test_attack "Method PUT blocked" \
"curl -k -X PUT -s -o /dev/null -w '%{http_code}' \"$TARGET/\""

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