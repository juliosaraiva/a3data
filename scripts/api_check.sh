#!/bin/bash

# API Health Check Script
# Quick validation of all FastAPI endpoints

set -e

# Configuration
HOST="localhost"
PORT="8000"
BASE_URL="http://${HOST}:${PORT}"
TIMEOUT="30"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if debug mode is enabled
is_debug_enabled() {
    if [ -f ".env" ]; then
        grep -q "DEBUG=true" .env && return 0
    fi
    return 1
}

# Test endpoint function
test_endpoint() {
    local method="$1"
    local endpoint="$2"
    local data="$3"

    printf "  %-40s" "$endpoint"

    local start_time=$(date +%s.%N)

    # Build HTTPie command
    local cmd="http --timeout=$TIMEOUT --check-status --body $method $BASE_URL$endpoint"

    # Add data if provided
    if [ -n "$data" ]; then
        cmd="$cmd --raw '$data'"
    fi

    # Execute request
    local response_code=0
    eval "$cmd" >/dev/null 2>&1 && response_code=0 || response_code=$?

    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc -l)
    local duration_ms=$(echo "$duration * 1000" | bc -l | cut -d. -f1)

    # Check result
    if [ $response_code -eq 0 ]; then
        printf "${GREEN}✅ PASS${NC} ${YELLOW}(%sms)${NC}\n" "$duration_ms"
        return 0
    else
        printf "${RED}❌ FAIL${NC} ${YELLOW}(%sms)${NC}\n" "$duration_ms"
        return 1
    fi
}

echo -e "${CYAN}🔍 API Health Check${NC}"
echo "==================="
echo -e "${BLUE}Base URL: $BASE_URL${NC}"
echo ""

total_tests=0
passed_tests=0

# Health Endpoints
echo -e "${PURPLE}🏥 Health Endpoints${NC}"
test_endpoint "GET" "/api/health/" && ((passed_tests++)) || true; ((total_tests++))
test_endpoint "GET" "/api/health/detailed" && ((passed_tests++)) || true; ((total_tests++))
test_endpoint "GET" "/api/health/live" && ((passed_tests++)) || true; ((total_tests++))
test_endpoint "GET" "/api/health/ready" && ((passed_tests++)) || true; ((total_tests++))
echo ""

# Single Extraction (skip batch for speed)
echo -e "${PURPLE}🔍 Extraction Endpoints${NC}"
single_extract_data='{"text":"Teste rápido: problema no servidor ontem às 10h."}'
test_endpoint "POST" "/api/v1/incidents/extract" "$single_extract_data" && ((passed_tests++)) || true; ((total_tests++))
echo ""

# Metrics Endpoints
echo -e "${PURPLE}📊 Metrics Endpoints${NC}"
test_endpoint "GET" "/api/metrics/" && ((passed_tests++)) || true; ((total_tests++))
test_endpoint "GET" "/api/metrics/health-score" && ((passed_tests++)) || true; ((total_tests++))
test_endpoint "GET" "/api/metrics/performance" && ((passed_tests++)) || true; ((total_tests++))
echo ""

# Debug Endpoints
echo -e "${PURPLE}🐛 Debug Endpoints${NC}"
test_endpoint "GET" "/api/debug/system-info" && ((passed_tests++)) || true; ((total_tests++))
test_endpoint "GET" "/api/debug/components" && ((passed_tests++)) || true; ((total_tests++))
test_endpoint "GET" "/api/debug/workflow-info" && ((passed_tests++)) || true; ((total_tests++))

# Test debug extraction endpoint only if debug mode is enabled
if is_debug_enabled; then
    debug_extract_data='{"text":"Teste debug: servidor caiu ontem às 10h."}'
    test_endpoint "POST" "/api/debug/test-extraction" "$debug_extract_data" && ((passed_tests++)) || true; ((total_tests++))
else
    printf "  %-40s" "/api/debug/test-extraction"
    printf "${YELLOW}⚠️  SKIP${NC} (debug mode disabled)\n"
fi
echo ""

# Documentation Endpoints
echo -e "${PURPLE}📚 Documentation Endpoints${NC}"
test_endpoint "GET" "/docs" && ((passed_tests++)) || true; ((total_tests++))
test_endpoint "GET" "/openapi.json" && ((passed_tests++)) || true; ((total_tests++))
echo ""

# Summary
echo -e "${BLUE}📋 Health Check Summary${NC}"
echo "========================"
echo -e "Total Tests:   ${YELLOW}$total_tests${NC}"
echo -e "Passed:        ${GREEN}$passed_tests${NC}"
echo -e "Failed:        ${RED}$((total_tests - passed_tests))${NC}"

if [ $passed_tests -eq $total_tests ]; then
    echo -e "Status:        ${GREEN}✅ ALL TESTS PASSED${NC}"
    echo ""
    echo -e "${GREEN}🎉 API is healthy and fully functional!${NC}"
    exit 0
else
    echo -e "Status:        ${RED}❌ SOME TESTS FAILED${NC}"
    exit 1
fi
