#!/bin/bash

# F1 Analytics Environment Test Script
# Validates the development environment setup

set -e

echo "🧪 F1 Analytics Environment Test Suite"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

test_file_exists() {
    local file=$1
    local description=$2

    print_test "Checking $description"

    if [ -f "$file" ]; then
        print_pass "$description exists"
        ((TESTS_PASSED++))
    else
        print_fail "$description not found at $file"
        ((TESTS_FAILED++))
    fi
}

test_directory_exists() {
    local dir=$1
    local description=$2

    print_test "Checking $description"

    if [ -d "$dir" ]; then
        print_pass "$description exists"
        ((TESTS_PASSED++))
    else
        print_fail "$description not found at $dir"
        ((TESTS_FAILED++))
    fi
}

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"
echo

# Test 1: Project Structure
echo "📁 Testing Project Structure"
echo "----------------------------"

test_directory_exists "backend" "Backend directory"
test_directory_exists "frontend" "Frontend directory"
test_directory_exists "infrastructure" "Infrastructure directory"
test_directory_exists "scripts" "Scripts directory"

echo

# Test 2: Docker Configuration
echo "🐳 Testing Docker Configuration"
echo "-------------------------------"

test_file_exists "backend/Dockerfile" "Backend Dockerfile"
test_file_exists "frontend/Dockerfile" "Frontend Dockerfile"
test_file_exists "infrastructure/docker-compose.yml" "Development Docker Compose"
test_file_exists "infrastructure/docker-compose.prod.yml" "Production Docker Compose"

echo

# Test 3: Backend Configuration
echo "🐍 Testing Backend Configuration"
echo "--------------------------------"

test_file_exists "backend/requirements.txt" "Backend requirements.txt"
test_file_exists "backend/pyproject.toml" "Backend pyproject.toml"
test_file_exists "backend/app/main.py" "Backend main application"
test_file_exists "backend/app/__init__.py" "Backend app package"

echo

# Test 4: Frontend Configuration
echo "⚛️  Testing Frontend Configuration"
echo "---------------------------------"

test_file_exists "frontend/package.json" "Frontend package.json"
test_file_exists "frontend/vite.config.ts" "Frontend Vite config"
test_file_exists "frontend/tailwind.config.js" "Frontend Tailwind config"
test_file_exists "frontend/index.html" "Frontend HTML template"
test_file_exists "frontend/src/main.tsx" "Frontend main component"
test_file_exists "frontend/src/App.tsx" "Frontend App component"
test_file_exists "frontend/nginx.conf" "Frontend Nginx config"

echo

# Test 5: Infrastructure Configuration
echo "🏗️  Testing Infrastructure Configuration"
echo "---------------------------------------"

test_file_exists "infrastructure/init-scripts/01-init-database.sql" "Database initialization script"

echo

# Test 6: Development Scripts
echo "🛠️  Testing Development Scripts"
echo "-------------------------------"

test_file_exists "scripts/init_dev.sh" "Development initialization script"
test_file_exists "scripts/dev_commands.sh" "Development commands script"
test_file_exists "scripts/test_environment.sh" "Environment test script"

# Check if scripts are executable
print_test "Checking script permissions"
if [ -x "scripts/init_dev.sh" ] && [ -x "scripts/dev_commands.sh" ]; then
    print_pass "Development scripts are executable"
    ((TESTS_PASSED++))
else
    print_fail "Development scripts are not executable"
    ((TESTS_FAILED++))
fi

echo

# Test 7: Documentation
echo "📚 Testing Documentation"
echo "------------------------"

test_file_exists "README.md" "Project README"

echo

# Test 8: Configuration File Validation
echo "⚙️  Testing Configuration File Syntax"
echo "-------------------------------------"

# Test Docker Compose YAML syntax
print_test "Validating Docker Compose YAML syntax"
if command -v docker-compose &> /dev/null; then
    if docker-compose -f infrastructure/docker-compose.yml config > /dev/null 2>&1; then
        print_pass "Development Docker Compose YAML is valid"
        ((TESTS_PASSED++))
    else
        print_fail "Development Docker Compose YAML has syntax errors"
        ((TESTS_FAILED++))
    fi

    if docker-compose -f infrastructure/docker-compose.prod.yml config > /dev/null 2>&1; then
        print_pass "Production Docker Compose YAML is valid"
        ((TESTS_PASSED++))
    else
        print_fail "Production Docker Compose YAML has syntax errors"
        ((TESTS_FAILED++))
    fi
else
    print_warn "Docker Compose not available - skipping YAML validation"
fi

# Test JSON syntax (if any JSON files exist)
print_test "Validating JSON file syntax"
JSON_FILES_FOUND=false

if [ -f "frontend/package.json" ]; then
    JSON_FILES_FOUND=true
    if python3 -m json.tool frontend/package.json > /dev/null 2>&1; then
        print_pass "Frontend package.json is valid JSON"
        ((TESTS_PASSED++))
    else
        print_fail "Frontend package.json has JSON syntax errors"
        ((TESTS_FAILED++))
    fi
fi

if [ "$JSON_FILES_FOUND" = false ]; then
    print_warn "No JSON files found to validate"
fi

echo

# Test 9: Required Dependencies Check
echo "📦 Testing Required Dependencies"
echo "-------------------------------"

# Check if Python is available
print_test "Checking Python availability"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_pass "Python $PYTHON_VERSION available"
    ((TESTS_PASSED++))
else
    print_fail "Python 3 not available"
    ((TESTS_FAILED++))
fi

# Check if Node.js would be available for frontend
print_test "Checking Node.js availability"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_pass "Node.js $NODE_VERSION available"
    ((TESTS_PASSED++))
else
    print_warn "Node.js not available in test environment (expected in container)"
fi

echo

# Test 10: File Permissions and Security
echo "🔒 Testing File Permissions"
echo "---------------------------"

# Check that sensitive files don't have world-writable permissions
print_test "Checking file permissions security"
SECURITY_ISSUE=false

# Check Dockerfiles
for dockerfile in "backend/Dockerfile" "frontend/Dockerfile"; do
    if [ -f "$dockerfile" ] && [ -w "$dockerfile" ]; then
        if [ $(stat -c "%a" "$dockerfile" | cut -c3) -gt 4 ]; then
            print_fail "$dockerfile has world-writable permissions"
            SECURITY_ISSUE=true
        fi
    fi
done

if [ "$SECURITY_ISSUE" = false ]; then
    print_pass "No world-writable sensitive files found"
    ((TESTS_PASSED++))
else
    ((TESTS_FAILED++))
fi

echo

# Final Results
echo "📊 Test Results Summary"
echo "======================"
echo -e "Total tests: $((TESTS_PASSED + TESTS_FAILED))"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All tests passed! The F1 Analytics environment is properly configured.${NC}"
    echo
    echo "Next steps:"
    echo "1. Run ./scripts/init_dev.sh to start the development environment"
    echo "2. Access the application at http://localhost:3000"
    echo "3. Check the API documentation at http://localhost:8000/docs"
    exit 0
else
    echo -e "\n${RED}❌ Some tests failed. Please fix the issues above before proceeding.${NC}"
    exit 1
fi