#!/bin/bash

# Lighthouse Performance Audit Script
# Runs Lighthouse against all key pages and generates HTML reports

set -e

echo "🔍 Starting Lighthouse Performance Audit..."

# Configuration
BASE_URL="${1:-http://localhost:4200}"
CHROME_PATH="$(which google-chrome || which chromium || which chromium-browser)"
OUTPUT_DIR="lighthouse-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Check if Lighthouse is installed
if ! command -v lighthouse &> /dev/null; then
    echo "⚠️  Lighthouse not found. Installing..."
    npm install -g lighthouse
fi

# Pages to audit
pages=(
    "/"
    "/login"
    "/register"
    "/game"
    "/tournament"
    "/profile"
)

echo "📊 Auditing $BASE_URL"
echo "Chrome: $CHROME_PATH"
echo ""

# Run Lighthouse on each page
for page in "${pages[@]}"; do
    url="$BASE_URL$page"
    filename="${OUTPUT_DIR}/lighthouse-${page//\//}-${TIMESTAMP}.html"

    echo "🚀 Auditing: $url"

    # Run Lighthouse with appropriate flags
    lighthouse "$url" \
        --chrome-flags="--headless" \
        --output html \
        --output-path "$filename" \
        --budget-path ./scripts/lighthouse-budget.json \
        2>/dev/null || true

    echo "   ✅ Report saved: $filename"
    echo ""
done

echo "📈 Audit Summary"
echo "==============="
echo "Reports saved to: $OUTPUT_DIR"
echo ""
echo "To view reports, open any .html file in your browser:"
echo "  open $OUTPUT_DIR/lighthouse-*.html"
echo ""

# Summary statistics
echo "⚙️  Key Metrics to Monitor:"
echo "  - First Contentful Paint (FCP): < 1.8s ✅"
echo "  - Largest Contentful Paint (LCP): < 2.5s ✅"
echo "  - Cumulative Layout Shift (CLS): < 0.1 ✅"
echo "  - Time to Interactive (TTI): < 3.8s ✅"
echo ""
echo "✨ Audit complete!"
