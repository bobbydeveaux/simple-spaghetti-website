#!/bin/bash

# Test script for HTML structure validation
# Based on LLD Section 9 specifications

echo "=== HTML Structure and Validation Tests ==="
echo "Testing file: index.html"
echo

# Test 1: File exists
if [ -f "index.html" ]; then
    echo "✓ index.html exists"
else
    echo "✗ index.html not found"
    exit 1
fi

# Test 2: File is not empty
if [ -s "index.html" ]; then
    echo "✓ File has content"
else
    echo "✗ File is empty"
    exit 1
fi

# Test 3: File size is reasonable (< 1KB)
SIZE=$(wc -c < index.html)
if [ "$SIZE" -lt 1024 ]; then
    echo "✓ File size is ${SIZE} bytes (under 1KB)"
else
    echo "✗ File size is ${SIZE} bytes (exceeds 1KB)"
    exit 1
fi

# Test 4: File contains required text
if grep -q "I love pizza" index.html; then
    echo "✓ Contains required 'I love pizza' text"
else
    echo "✗ Missing required 'I love pizza' text"
    exit 1
fi

# Test 5: Check for proper HTML5 structure
if grep -q "<!DOCTYPE html>" index.html; then
    echo "✓ Contains HTML5 DOCTYPE"
else
    echo "✗ Missing HTML5 DOCTYPE"
    exit 1
fi

# Test 6: Check for essential HTML tags
if grep -q "<html>" index.html && grep -q "<head>" index.html && grep -qE "<body[[:space:]]|<body>" index.html; then
    echo "✓ Contains essential HTML structure (html, head, body)"
else
    echo "✗ Missing essential HTML structure"
    exit 1
fi

# Test 7: Check for title tag
if grep -q "<title>" index.html; then
    echo "✓ Contains title tag"
else
    echo "✗ Missing title tag"
    exit 1
fi

# Test 8: Check for proper tag closure
if [ "$(grep -c '<html>' index.html)" -eq "$(grep -c '</html>' index.html)" ] &&
   [ "$(grep -c '<head>' index.html)" -eq "$(grep -c '</head>' index.html)" ] &&
   [ "$(grep -c '<body' index.html)" -eq "$(grep -c '</body>' index.html)" ]; then
    echo "✓ HTML tags are properly closed"
else
    echo "✗ HTML tags are not properly closed"
    exit 1
fi

# Test 9: Check for CSS styles (should be present in this implementation)
if grep -qE 'style=' index.html; then
    echo "✓ CSS styles detected (expected for this implementation)"
else
    echo "✗ No CSS styles found"
    exit 1
fi

# Test 10: Check for footer element
if grep -q "<footer" index.html; then
    echo "✓ Footer element present"
else
    echo "✗ Footer element missing"
    exit 1
fi

echo
echo "=== Structure Tests Summary ==="
echo "All HTML structure tests passed successfully!"
echo "File is ready for cross-browser testing."