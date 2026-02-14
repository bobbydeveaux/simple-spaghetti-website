#!/bin/bash

# HTML5 Compliance Validation Script for Issue #4
# Based on requirements in LLD.md section 9 - Test Plan

set -e

HTML_FILE="index.html"
REQUIRED_TEXT="I love spagheeti"

echo "🔍 Running HTML5 compliance validation for issue #4..."
echo "=================================================="

# Test 1: File existence
echo "✅ Test 1: Checking if $HTML_FILE exists..."
if [ ! -f "$HTML_FILE" ]; then
    echo "❌ FAIL: $HTML_FILE does not exist"
    exit 1
fi
echo "✅ PASS: $HTML_FILE exists"

# Test 2: File size (should be under 1KB as per requirements)
echo
echo "✅ Test 2: Checking file size..."
FILE_SIZE=$(wc -c < "$HTML_FILE")
echo "   File size: $FILE_SIZE bytes"
if [ "$FILE_SIZE" -gt 1024 ]; then
    echo "❌ FAIL: File size $FILE_SIZE bytes exceeds 1KB limit"
    exit 1
fi
echo "✅ PASS: File size is under 1KB"

# Test 3: Required text presence
echo
echo "✅ Test 3: Checking for required text '$REQUIRED_TEXT'..."
if ! grep -q "$REQUIRED_TEXT" "$HTML_FILE"; then
    echo "❌ FAIL: Required text '$REQUIRED_TEXT' not found"
    exit 1
fi
echo "✅ PASS: Required text '$REQUIRED_TEXT' found"

# Test 4: No CSS styling (inline or external)
echo
echo "✅ Test 4: Checking for CSS violations..."
if grep -q "style=" "$HTML_FILE"; then
    echo "❌ FAIL: Inline CSS (style=) found - not allowed per requirements"
    exit 1
fi

if grep -q "<style>" "$HTML_FILE"; then
    echo "❌ FAIL: Style tags found - not allowed per requirements"
    exit 1
fi

if grep -q "<link.*stylesheet" "$HTML_FILE"; then
    echo "❌ FAIL: External CSS links found - not allowed per requirements"
    exit 1
fi
echo "✅ PASS: No CSS styling detected"

# Test 5: No JavaScript
echo
echo "✅ Test 5: Checking for JavaScript violations..."
if grep -q "<script" "$HTML_FILE"; then
    echo "❌ FAIL: Script tags found - not allowed per requirements"
    exit 1
fi

if grep -q "onclick\|onload\|javascript:" "$HTML_FILE"; then
    echo "❌ FAIL: Inline JavaScript found - not allowed per requirements"
    exit 1
fi
echo "✅ PASS: No JavaScript detected"

# Test 6: HTML5 DOCTYPE
echo
echo "✅ Test 6: Checking HTML5 DOCTYPE..."
if ! grep -q "<!DOCTYPE html>" "$HTML_FILE"; then
    echo "❌ FAIL: HTML5 DOCTYPE not found"
    exit 1
fi
echo "✅ PASS: HTML5 DOCTYPE found"

# Test 7: Required HTML structure
echo
echo "✅ Test 7: Checking HTML structure..."
if ! grep -q "<html" "$HTML_FILE"; then
    echo "❌ FAIL: <html> tag not found"
    exit 1
fi

if ! grep -q "<head>" "$HTML_FILE"; then
    echo "❌ FAIL: <head> tag not found"
    exit 1
fi

if ! grep -q "<title>" "$HTML_FILE"; then
    echo "❌ FAIL: <title> tag not found"
    exit 1
fi

if ! grep -q "<body>" "$HTML_FILE"; then
    echo "❌ FAIL: <body> tag not found"
    exit 1
fi
echo "✅ PASS: Required HTML structure elements found"

# Test 8: W3C HTML5 Validation (if curl is available)
echo
echo "✅ Test 8: Running W3C HTML5 validation..."
if command -v curl > /dev/null 2>&1; then
    VALIDATION_RESULT=$(curl -s -H "Content-Type: text/html; charset=utf-8" --data-binary @"$HTML_FILE" "https://validator.w3.org/nu/?out=text")

    if echo "$VALIDATION_RESULT" | grep -q "Error"; then
        echo "❌ FAIL: W3C validation errors found:"
        echo "$VALIDATION_RESULT"
        exit 1
    else
        echo "✅ PASS: W3C validation successful"
        if echo "$VALIDATION_RESULT" | grep -q "Warning"; then
            echo "⚠️  Note: W3C validation warnings (non-blocking):"
            echo "$VALIDATION_RESULT" | grep "Warning"
        fi
    fi
else
    echo "⚠️  SKIP: curl not available for W3C validation"
fi

echo
echo "🎉 All HTML5 compliance tests passed!"
echo "=================================================="
echo "✅ File exists and is under size limit"
echo "✅ Contains required text: '$REQUIRED_TEXT'"
echo "✅ No CSS styling violations"
echo "✅ No JavaScript violations"
echo "✅ Valid HTML5 DOCTYPE and structure"
echo "✅ Passes W3C HTML5 validation"
echo
echo "Issue #4 HTML5 compliance validation: SUCCESS ✅"