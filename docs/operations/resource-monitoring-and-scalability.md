# Hackathon Radar: Resource Monitoring and Scalability Planning

## 1. Overview & Objectives
As **Hackathon Radar** expands its user base, scraper frequency, and real-time AI prediction workloads, a proactive resource monitoring and scaling strategy is essential to prevent degradation, crashes, and unexpected infrastructure cost spikes.

This plan details:
- Monitored resources, telemetry collectors, and key health indicators.
- Warning and critical threshold matrices.
- Bottleneck profiles for compute-intensive endpoints and asynchronous jobs.
- Horizontal and vertical scaling guidelines for all application tiers.
- Capacity planning models for traffic growth phases (10k, 100k, and 1M monthly active builders).

---

## 2. Monitored Resources & Telemetry Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Hackathon Radar Telemetry Engine                      │
├─────────────────────┬───────────────────────┬───────────────────────────────┤
│ Tier                │ Core Component        │ Primary Resource Concern      │
├─────────────────────┼───────────────────────┼───────────────────────────────┤
│ Frontend            │ React / Nginx / CDN   │ Ingress bandwidth, asset cache│
│ API Backend         │ FastAPI / Python      │ CPU saturation, async threads │
│ ML Engine           │ Prediction Model API  │ Memory (model weights), CPU   │
│ Collector Engine    │ Scrapy / Playwright   │ RAM per browser, network IO   │
│ Persistence         │ PostgreSQL 15+        │ IOPS, connection pool, locks  │
│ Queue & Cache       │ Redis 7+              │ Memory eviction, queue backlog│
└─────────────────────┴───────────────────────┴───────────────────────────────┘
```

### 2.1 Key Metrics & Collection Mechanisms
| Metric Name | Unit | Source | Description |
| :--- | :--- | :--- | :--- |
| `cpu_usage_percent` | % | cAdvisor / Node Exporter | Percentage of CPU cores saturated |
| `memory_usage_percent` | % | cAdvisor / Node Exporter | Resident Set Size (RSS) memory utilization |
| `disk_usage_percent` | % | Node Exporter | Storage fill rate on persistent volumes & logs |
| `database_connection_count`| count | PostgreSQL Exporter | Active sessions vs max connection ceiling |
| `database_query_duration_seconds` | ms / s | `pg_stat_statements` | P95/P99 latency of queries |
| `request_rate` | req/sec | Nginx / Ingress Controller | Ingress requests per second (RPS) |
| `concurrent_requests` | count | FastAPI Middleware | Number of active async handlers executing |
| `worker_job_count` | count | Redis queue depth | Unprocessed jobs waiting in scraper queues |
| `average_job_duration` | seconds| Celery / Worker logger | Mean duration per scraping cycle |
| `prediction_execution_time`| ms | ML Service Prom Client | Inference and scoring calculation latency |
| `scraper_execution_time` | seconds| Collector Runner | Total time to crawl, parse, and store source data|

---

## 3. Threshold Matrix & Alert Levels

Alerts are routed to on-call engineers via Alertmanager (Slack `#alerts-production` and PagerDuty for critical alerts).

| Resource Domain | Metric | Warning Level (🟡) | Critical Level (🔴) | Action Required |
| :--- | :--- | :--- | :--- | :--- |
| **API Backend** | CPU Usage | $> 70\%$ for 5 min | $> 85\%$ for 2 min | Auto-scale pods via HPA; inspect profiling |
| **API Backend** | Memory Usage | $> 75\%$ | $> 90\%$ (OOM risk) | Restart leaking pods; scale pod limits |
| **Backend Latency** | P95 Latency | $> 400\text{ms}$ | $> 1000\text{ms}$ | Query tuning, cache hotkeys, rate limit abusers|
| **HTTP Error Rate** | 5xx Errors | $> 1\%$ of traffic | $> 3\%$ of traffic | Trigger rollback or circuit breaker |
| **Database** | Connection Pool | $> 70\%$ allocated | $> 85\%$ allocated | Engage PgBouncer pooler; inspect unclosed conns |
| **Database** | CPU Utilization | $> 65\%$ | $> 80\%$ | Index missing columns, activate read replicas |
| **Database** | Disk Storage | $> 75\%$ full | $> 88\%$ full | Increase volume size; purge old audit logs |
| **Worker Queue** | Pending Scrapes| $> 100$ jobs delayed | $> 300$ jobs delayed | Scale collector worker replicas |
| **ML Predictions**| Inference Time | $> 500\text{ms}$ | $> 1500\text{ms}$ | Pre-compute popular embeddings; add ML worker |

---

## 4. High-Resource Endpoints & Bottleneck Analysis

### 4.1 High-Compute Workloads
1. **AI Match & Recommendation Engine (`/api/predictions/match`)**:
   - Computes multi-dimensional vector similarities between user skill profile and thousands of active competitions.
   - *Mitigation*: Cache computed match embeddings in Redis with a 2-hour TTL. Pre-calculate top clusters asynchronously.
2. **Global Radar Geospatial Aggregator (`/api/events/map-clusters`)**:
   - Groups worldwide hackathons into regional cluster hubs and collision-free bounds.
   - *Mitigation*: Spatial index in PostgreSQL with PostGIS geometry indexing; compute cluster GeoJSON periodically into static CDN cache.
3. **Dynamic Scraper Crawlers (`DynamicCollector` via Playwright/Chromium)**:
   - Headless browser rendering consumes $\sim 300\text{MB}$ RAM per worker instance.
   - *Mitigation*: Run dynamic collectors in isolated worker pods with hard memory limits (`512Mi`), process pooling, and strict timeouts (30s max).

---

## 5. Scalability Strategy: Horizontal & Vertical Scaling

### 5.1 Stateless Application Tiers (Frontend & FastAPI Backend)
- **Primary Mechanism**: **Horizontal Pod Autoscaling (HPA)**.
- **Backend HPA Configuration**:
  ```yaml
  apiVersion: autoscaling/v2
  kind: HorizontalPodAutoscaler
  metadata:
    name: hackathon-radar-backend-hpa
  spec:
    scaleTargetRef:
      apiVersion: apps/v1
      kind: Deployment
      name: hackathon-radar-backend
    minReplicas: 2
    maxReplicas: 10
    metrics:
      - type: Resource
        resource:
          name: cpu
          target:
            type: Utilization
            averageUtilization: 70
      - type: Resource
        resource:
          name: memory
          target:
            type: Utilization
            averageUtilization: 80
  ```
- **Vertical Base Limits**:
  - Backend: `cpu: 250m` request / `1000m` limit; `memory: 512Mi` request / `2Gi` limit.
  - Frontend: `cpu: 100m` request / `500m` limit; `memory: 128Mi` request / `512Mi` limit.

### 5.2 Scraper & Background Workers
- **Queue-Driven Autoscaling**: Workers scale dynamically with **KEDA (Kubernetes Event-driven Autoscaling)** based on Redis queue length.
- **Rule**: Spawn +1 scraper worker for every 20 pending scraping tasks in the queue (maximum 8 workers).

### 5.3 Database Tier Scalability
- **Connection Management**:
  - Implement **PgBouncer** connection pooler in transaction pooling mode.
  - Limits database connections to a stable pool of 50-100 connections while serving thousands of application requests.
- **Read Replicas**:
  - As read queries exceed 1,500 QPS, configure asynchronous read replicas.
  - Direct all read-only queries (event discovery, search, public organizers) to read replicas.
  - Route write operations (user registration, bookmarks, admin moderation) to the primary node.
- **Table Partitioning**:
  - Partition `events` and `event_audit_logs` tables by year/month to keep indexes compact and fast.

---

## 6. Capacity Planning: Growth Milestones

| Capacity Tier | Monthly Active Users | Database Size | Recommended Backend Pods | Recommended Worker Pods | Database Instance |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Phase 1: Launch** | Up to 10k MAU | $\sim 10\text{ GB}$ | 2 – 4 replicas | 2 replicas | 2 vCPU, 8 GB RAM (PostgreSQL) |
| **Phase 2: Growth** | Up to 100k MAU | $\sim 50\text{ GB}$ | 4 – 8 replicas | 4 replicas | 4 vCPU, 16 GB RAM + 1 Read Replica |
| **Phase 3: Scale** | Up to 1M MAU | $\sim 250\text{ GB}$ | 8 – 20 replicas | 8 replicas | 8 vCPU, 32 GB RAM + 2 Read Replicas + PgBouncer |

---

## 7. Performance & Load Testing Verification

All services must be load-tested prior to major tier promotions using the standardized k6 benchmark (`benchmarks/k6-load-test.js`):
- **Target Load**: 200 concurrent users ramping to 500 VUs over 5 minutes.
- **Target Criteria**:
  - P95 response time $< 300\text{ms}$ on event listings.
  - P99 response time $< 800\text{ms}$ on AI predictions.
  - Error rate $< 0.1\%$.
- **Validation Command**:
  ```bash
  k6 run benchmarks/k6-load-test.js
  ```
