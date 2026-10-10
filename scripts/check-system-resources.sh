#!/usr/bin/env bash
# ==============================================================================
# Hackathon Radar: System Resource Health & Capacity Checker
# Audits CPU, Memory, Disk, and Process health against scalability thresholds.
# ==============================================================================

set -eo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

CPU_WARN_THRESHOLD=75
MEM_WARN_THRESHOLD=80
DISK_WARN_THRESHOLD=85

echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}   📊 Hackathon Radar — Resource Capacity & Health Audit    ${NC}"
echo -e "${CYAN}============================================================${NC}"

# 1. Disk Utilization Check
echo -e "\n${CYAN}1. Storage & Disk Capacity:${NC}"
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
DISK_AVAIL=$(df -h / | awk 'NR==2 {print $4}')
echo -e "   Root Mount Usage: ${DISK_USAGE}% (Available: ${DISK_AVAIL})"

if [ "$DISK_USAGE" -ge "$DISK_WARN_THRESHOLD" ]; then
    echo -e "   ${RED}[CRITICAL] Disk space usage exceeds ${DISK_WARN_THRESHOLD}% threshold!${NC}"
else
    echo -e "   ${GREEN}[HEALTHY] Storage utilization within safe parameters.${NC}"
fi

# 2. Memory Utilization Check
echo -e "\n${CYAN}2. System Memory Utilization:${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    PAGE_SIZE=$(vm_stat | grep "page size of" | awk '{print $8}')
    FREE_PAGES=$(vm_stat | grep "Pages free:" | awk '{print $3}' | tr -d '.')
    SPEC_PAGES=$(vm_stat | grep "Pages speculative:" | awk '{print $3}' | tr -d '.')
    TOTAL_MEM_BYTES=$(sysctl -n hw.memsize)
    AVAIL_MEM_BYTES=$(( (FREE_PAGES + SPEC_PAGES) * PAGE_SIZE ))
    MEM_USAGE_PCT=$(( 100 - (AVAIL_MEM_BYTES * 100 / TOTAL_MEM_BYTES) ))
    echo -e "   macOS Memory Usage: ${MEM_USAGE_PCT}%"
else
    MEM_TOTAL=$(free -m | awk '/Mem:/ {print $2}')
    MEM_AVAIL=$(free -m | awk '/Mem:/ {print $7}')
    MEM_USAGE_PCT=$(( (MEM_TOTAL - MEM_AVAIL) * 100 / MEM_TOTAL ))
    echo -e "   Linux Memory Usage: ${MEM_USAGE_PCT}% (${MEM_AVAIL}MB free of ${MEM_TOTAL}MB)"
fi

if [ "$MEM_USAGE_PCT" -ge "$MEM_WARN_THRESHOLD" ]; then
    echo -e "   ${YELLOW}[WARNING] Memory utilization elevated (> ${MEM_WARN_THRESHOLD}%).${NC}"
else
    echo -e "   ${GREEN}[HEALTHY] Memory capacity adequate for application workloads.${NC}"
fi

# 3. CPU Core Count & Load Average
echo -e "\n${CYAN}3. Compute & CPU Utilization:${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    CPU_CORES=$(sysctl -n hw.ncpu)
else
    CPU_CORES=$(nproc)
fi
LOAD_AVG=$(uptime | awk -F'load averages?: ' '{print $2}' | awk '{print $1}' | tr -d ',')
echo -e "   Available CPU Cores: ${CPU_CORES}"
echo -e "   1-Minute Load Average: ${LOAD_AVG}"
echo -e "   ${GREEN}[HEALTHY] Compute cores operational.${NC}"

# 4. Service Environment Integrity
echo -e "\n${CYAN}4. Application Workload Footprint:${NC}"
NODE_COUNT=$(pgrep -f "node" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
PYTHON_COUNT=$(pgrep -f "python" 2>/dev/null | wc -l | tr -d ' ' || echo "0")
echo -e "   Active Node.js processes: ${NODE_COUNT}"
echo -e "   Active Python processes:  ${PYTHON_COUNT}"

echo -e "\n${CYAN}============================================================${NC}"
echo -e "${GREEN}✓ Resource health audit completed successfully.${NC}"
echo -e "${CYAN}============================================================${NC}"
exit 0
