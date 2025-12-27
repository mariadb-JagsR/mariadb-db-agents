# Complete Agent Requirements Summary

This document consolidates all requirements identified for the MariaDB Database Management Agent Suite.

## 📊 Current Status

### ✅ Implemented Agents

1. **Slow Query Agent** - Analyzes historical slow queries from slow query logs
2. **Running Query Agent** - Analyzes currently executing SQL queries in real-time
3. **Incident Triage Agent** - Meta-agent that quickly identifies database issues, correlates symptoms, and provides actionable checklists

---

## 🎯 Planned Agents - Priority Ranking

### Phase 1: Foundation (Next 2-3 agents)

#### 1. Replication Health & Drift Agent ⭐⭐⭐⭐⭐
**Priority**: P0 (Highest)  
**Status**: Planned  
**Source**: Tier 1 #1 in HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md + ChatGPT #3

**Requirements:**
- Monitor replication lag across all replicas
- Detect replication failures and broken replication chains
- Analyze replication delay trends over time
- Identify which queries are causing replication lag
- Recommend replication topology optimizations
- Check GTID consistency and binlog position health
- Interpret replication state (SHOW SLAVE STATUS / SHOW REPLICA STATUS)
- Detect failure modes (1032, 1062 errors)
- Propose resolution paths

**Tools Needed:**
- `SHOW SLAVE STATUS` / `SHOW REPLICA STATUS`
- `SHOW MASTER STATUS`
- `SHOW BINLOG EVENTS`
- Performance Schema replication metrics
- `information_schema.replication_*` tables

**Use Cases:**
- "Check replication health for service-id X"
- "Why is replication lagging on replica Y?"
- "Which queries are causing replication delays?"
- "Is my replication topology optimal?"

---

#### 2. Lock & Deadlock Detective Agent ⭐⭐⭐⭐⭐
**Priority**: P0 (Highest)  
**Status**: Planned  
**Source**: ChatGPT #2 (can enhance Running Query Agent OR separate)

**Requirements:**
- Detects lock contention patterns
- Identifies blocker sessions
- Summarizes deadlocks from InnoDB status
- Suggests targeted fixes
- Analyze blocking relationships
- Parse deadlock logs

**Tools Needed:**
- `SHOW ENGINE INNODB STATUS` (already accessible)
- `information_schema.innodb_locks` (already used)
- `information_schema.innodb_lock_waits` (already used)
- `information_schema.innodb_trx` (for transaction details)
- `performance_schema.metadata_locks` (for table-level locks)
- Deadlock log parsing (new)

**Implementation Options:**
1. Enhance Running Query Agent - Add deadlock analysis tools
2. Separate Agent - If deadlock analysis becomes complex enough

**Recommendation**: Start by enhancing Running Query Agent, then extract if it grows too large.

---

### Phase 2: Operational Excellence (Next 2-3 agents)

#### 3. Connection Pool & Resource Management Agent ⭐⭐⭐⭐⭐
**Priority**: P0 (Highest)  
**Status**: Planned  
**Source**: Tier 1 #2 in HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md (ChatGPT missed this)

**Requirements:**
- Analyze connection pool usage patterns
- Identify connection leaks and long-lived idle connections
- Recommend optimal connection pool sizes
- Detect connection exhaustion risks
- Analyze connection source patterns (which apps/users are connecting)
- Monitor connection wait times and queue lengths
- Suggest connection timeout optimizations

**Tools Needed:**
- `SHOW PROCESSLIST` (extended analysis)
- `SHOW STATUS LIKE 'Threads_%'`
- `SHOW STATUS LIKE 'Connections'`
- `SHOW STATUS LIKE 'Max_used_connections'`
- `information_schema.PROCESSLIST` (historical analysis)
- Performance Schema connection metrics

**Use Cases:**
- "Why am I hitting max_connections?"
- "Which application is consuming the most connections?"
- "What's the optimal connection pool size for my app?"
- "Are there connection leaks in my application?"

---

#### 4. Schema Health & Index Advisor Agent ⭐⭐⭐⭐
**Priority**: P1 (High)  
**Status**: Planned  
**Source**: Tier 1 #4 in HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md + ChatGPT #5 (merged)

**Requirements:**
- Uses slow queries + live queries to propose ranked index candidates
- Detects redundant/overlapping indexes
- Flags schema smells
- Identify unused tables and indexes (never queried)
- Detect duplicate or redundant indexes
- Analyze index fragmentation and bloat
- Recommend index consolidation opportunities
- Identify tables with missing primary keys
- Detect schema drift between environments
- Analyze foreign key relationships and orphaned records
- Recommend partitioning strategies for large tables

**Tools Needed:**
- `SHOW INDEX FROM table`
- `information_schema.statistics`
- `information_schema.table_constraints`
- Performance Schema index usage statistics
- Query analysis to determine index usage
- Can leverage Slow Query Agent's findings
- Can leverage Running Query Agent's findings

**Use Cases:**
- "What indexes are never being used?"
- "Do I have duplicate indexes?"
- "Which tables should be partitioned?"
- "Is my schema optimized for my query patterns?"

**Key Insight**: This is a natural "composition" agent that uses existing Slow Query + Running Query agents!

---

#### 5. Configuration Safety Agent ⭐⭐⭐⭐
**Priority**: P1 (High)  
**Status**: Planned  
**Source**: Tier 2 #7 in HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md + ChatGPT #6 (merged)

**Requirements:**
- Audits minimal, safe set of settings
- Produces risk-tagged recommendations (Safe / Needs staging / Dangerous)
- "1-click suggested changes (not executed)" - nice UX touch
- Analyze current configuration vs. best practices
- Recommend configuration changes based on workload patterns
- Identify misconfigured parameters
- Suggest buffer pool sizing based on data size
- Recommend query cache settings (if applicable)
- Analyze version-specific configuration recommendations
- Check for deprecated or removed configuration options
- Suggest configuration changes for specific workload types (OLTP vs OLAP)

**Tools Needed:**
- `SHOW VARIABLES`
- `SHOW STATUS`
- `SHOW ENGINE INNODB STATUS`
- Performance Schema metrics
- Workload analysis from query agents

**Use Cases:**
- "Is my configuration optimal for my workload?"
- "What configuration changes would improve performance?"
- "Are there any misconfigured settings?"
- "Should I adjust buffer pool size?"

**Key Improvements from ChatGPT:**
- Risk tagging: Safe / Needs staging / Dangerous
- Focus on "minimal, safe set" (aligns with read-only philosophy)
- "1-click suggested changes" UX (even if not executed, nice presentation)

---

### Phase 3: Planning & Optimization (Next 2 agents)

#### 6. Capacity Planning & Cost Optimization Agent ⭐⭐⭐⭐
**Priority**: P1 (High)  
**Status**: Planned  
**Source**: Tier 1 #3 + Tier 3 #10 in HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md + ChatGPT #4 (merged)

**Requirements:**
- Builds capacity profile from metrics
- Recommends right-sizing
- For serverless: explains scaling events
- Analyze disk space usage trends and predict when storage will be exhausted
- Monitor table growth rates and identify fast-growing tables
- Predict memory usage trends
- Analyze query volume trends
- Recommend right-sizing based on actual usage patterns
- Identify unused or underutilized resources
- Forecast resource needs for next 30/60/90 days
- Identify unused databases/tables that could be archived
- Analyze query costs (compute time, I/O)
- Identify opportunities for query optimization to reduce costs
- Recommend storage optimization (compression, archiving)
- Analyze peak vs. off-peak usage for scheduling optimizations
- Correlate scaling events to query bursts (SkySQL serverless)
- Identify top 3 cost drivers

**Tools Needed:**
- `information_schema.tables` (data_length, index_length, table_rows)
- `information_schema.schemata` (disk usage)
- `SHOW TABLE STATUS`
- Historical metrics from Performance Schema
- Slow query log analysis for volume trends
- Resource usage metrics
- Query analysis from existing agents
- Storage analysis
- Cost data (if available from cloud provider)

**Use Cases:**
- "When will I run out of disk space?"
- "Which tables are growing fastest?"
- "Should I scale up or down based on usage?"
- "What's my resource utilization trend?"
- "How can I reduce my database costs?"
- "What resources am I paying for but not using?"
- "Which queries are most expensive?"

**Key Addition from ChatGPT:**
- Serverless-specific: correlate scaling events to query bursts
- Cost drivers identification (top 3 cost drivers)
- This is valuable for SkySQL context!

---

#### 7. Backup/Restore & RPO/RTO Readiness Agent ⭐⭐⭐⭐
**Priority**: P1 (High)  
**Status**: Planned  
**Source**: Tier 2 #6 in HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md + ChatGPT #7 (merged)

**Requirements:**
- Verifies backup success, retention
- Estimates RPO/RTO (Recovery Point Objective / Recovery Time Objective)
- Flags dangerous gaps
- Verify backup integrity and completeness
- Analyze backup frequency and retention policies
- Estimate recovery time objectives (RTO)
- Recommend backup strategies based on data criticality
- Identify tables/databases not covered by backups
- Analyze point-in-time recovery capabilities
- Check binlog retention settings
- Recommend backup optimization strategies

**Tools Needed:**
- Backup metadata (if accessible)
- `SHOW BINARY LOGS`
- `SHOW MASTER STATUS`
- `information_schema.tables` (for data volume analysis)
- Backup system APIs (if integrated)
- SkySQL API integration (for backup verification)

**Use Cases:**
- "Are my backups working correctly?"
- "How long would recovery take?"
- "What's my backup strategy and is it optimal?"
- "Can I recover to a specific point in time?"

**Note:** ChatGPT's RPO/RTO focus is valuable - make sure to include this terminology.

---

### Phase 4: Advanced (Later)

#### 8. Security & Compliance Audit Agent ⭐⭐⭐⭐
**Priority**: P1 (High)  
**Status**: Planned  
**Source**: Tier 2 #5 in HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md (ChatGPT missed this)

**Requirements:**
- Audit user permissions and identify over-privileged accounts
- Detect accounts with weak or default passwords
- Identify accounts that haven't logged in recently (stale accounts)
- Check for compliance with security best practices
- Analyze access patterns for suspicious activity
- Recommend least-privilege access models
- Audit SSL/TLS configuration
- Check for exposed sensitive data patterns

**Tools Needed:**
- `mysql.user` table (with proper permissions)
- `information_schema.user_privileges`
- `SHOW GRANTS FOR user`
- Connection logs (if available)
- Performance Schema connection tracking

**Use Cases:**
- "Who has admin access that shouldn't?"
- "Are there any security vulnerabilities?"
- "Which users haven't logged in for 90+ days?"
- "Does my database meet PCI/GDPR compliance requirements?"

---

#### 9. Anomaly Detection & Alerting Agent ⭐⭐⭐⭐
**Priority**: P2 (Medium)  
**Status**: Planned  
**Source**: Tier 2 #8 in HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md (ChatGPT didn't propose this separately)

**Requirements:**
- Detect unusual query patterns (sudden spikes, new query types)
- Identify performance degradation trends
- Detect resource usage anomalies (CPU, memory, I/O spikes)
- Alert on unusual connection patterns
- Detect data access anomalies (potential security issues)
- Identify slow query pattern changes
- Baseline normal behavior and flag deviations

**Tools Needed:**
- Historical slow query log data
- Performance Schema historical metrics
- Current processlist snapshots
- System metrics (CPU, memory, I/O)
- Time-series analysis capabilities

**Use Cases:**
- "Is there unusual activity on my database?"
- "Why did performance suddenly degrade?"
- "Are there any anomalies I should be aware of?"
- "What changed in my query patterns?"

**Recommendation:** Consider merging into Incident Triage Agent as a feature.

---

#### 10. Data Growth & Hotspot Agent ⭐⭐⭐
**Priority**: P2 (Medium)  
**Status**: Consider merging into Capacity Planning Agent  
**Source**: ChatGPT #8 (partial overlap with Capacity Planning)

**Requirements:**
- Tracks top table growth, churn, skew
- Identifies hotspot tables/indexes
- Ties back to query patterns
- Recommends partitioning/archival

**Assessment:**
- Partial overlap with Capacity Planning Agent (table growth rates)
- Partial overlap with Schema Health Agent (partitioning strategies)

**Recommendation:** ⚠️ **CONSIDER MERGING** into Capacity Planning Agent

**Key Value from ChatGPT:**
- "Ties hotspots back to query patterns" - this is valuable!
- Can leverage Slow Query Agent to see which queries hit hot tables
- Can leverage Running Query Agent to see current hotspots

**Suggestion:** Start by enhancing Capacity Planning Agent with hotspot detection. Extract later if needed.

---

#### 11. Migration & Upgrade Planning Agent ⭐⭐⭐
**Priority**: P2 (Medium)  
**Status**: Planned  
**Source**: Tier 3 #9 in HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md

**Requirements:**
- Analyze compatibility issues for version upgrades
- Identify deprecated features in use
- Recommend migration strategies
- Estimate upgrade complexity and risk
- Check for breaking changes between versions
- Analyze feature usage to determine upgrade benefits

**Tools Needed:**
- Version information (`SELECT VERSION()`)
- Feature usage analysis from query logs
- Schema analysis
- Configuration analysis

**Use Cases:**
- "Can I safely upgrade from MariaDB 10.5 to 10.11?"
- "What deprecated features am I using?"
- "What's the migration plan for my upgrade?"

---

#### 12. Cost Optimization Agent ⭐⭐⭐
**Priority**: P2 (Medium)  
**Status**: Merged into Capacity Planning & Cost Optimization Agent  
**Source**: Tier 3 #10 in HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md

**Note:** This has been merged with Capacity Planning Agent (see #6 above).

---

#### 13. Multi-Tenant Database Management Agent ⭐⭐⭐
**Priority**: P3 (Low)  
**Status**: Planned  
**Source**: Tier 3 #11 in HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md

**Requirements:**
- Analyze tenant resource usage and isolation
- Identify noisy neighbor problems
- Recommend tenant-specific optimizations
- Monitor per-tenant query patterns
- Suggest tenant-specific indexing strategies
- Analyze cross-tenant resource contention

**Tools Needed:**
- Tenant identification in schema/queries
- Per-tenant metrics
- Resource usage by tenant
- Query analysis with tenant context

**Use Cases:**
- "Which tenant is consuming the most resources?"
- "Is tenant X affecting other tenants' performance?"
- "How should I optimize for multi-tenant workloads?"

---

#### 14. Query Pattern Analysis & Application Insights Agent ⭐⭐⭐
**Priority**: P3 (Low)  
**Status**: Planned  
**Source**: Tier 3 #12 in HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md

**Requirements:**
- Map queries to application endpoints/features
- Identify N+1 query problems
- Detect inefficient application query patterns
- Recommend application-level optimizations
- Analyze query dependency chains
- Identify opportunities for query result caching

**Tools Needed:**
- Query logs with application context (if available)
- Query pattern analysis
- Performance metrics
- Application metadata (if integrated)

**Use Cases:**
- "Which application features are slowest?"
- "Do I have N+1 query problems?"
- "What queries should I cache?"

---

#### 15. DBA Orchestrator Agent ⭐⭐⭐⭐⭐
**Priority**: P0 (Highest)  
**Status**: Planned  
**Source**: Mentioned in README and HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md

**Requirements:**
- Routes user queries to the appropriate specialized agent
- Coordinates multi-agent analysis when needed
- Provides unified interface for all database management tasks
- Maintains context across agent interactions
- Acts as entry point for "something's wrong" scenarios

**Example Flow:**
```
User: "Is my database healthy?"
Orchestrator:
  1. Routes to Capacity Planning Agent → "Disk space OK, but growing fast"
  2. Routes to Replication Agent → "Replication lag: 5 seconds"
  3. Routes to Slow Query Agent → "3 slow queries identified"
  4. Routes to Connection Pool Agent → "Connection usage: 80%"
  5. Synthesizes comprehensive health report
```

**Implementation Pattern:**
- Can call Slow Query Agent for historical context
- Can call Running Query Agent for current blocking issues
- Can call Incident Triage Agent for quick health checks
- Can route to specialized agents based on symptoms

---

## 🏗️ Shared Infrastructure Requirements

### Common Components (Already Implemented)

1. **Common DB Client** (`common/db_client.py`)
   - Read-only SQL execution with safety checks
   - SSL connection support for SkySQL
   - Error log reading and pattern extraction
   - SkySQL API integration for error logs

2. **Guardrails** (`common/guardrails.py`)
   - Input/output validation
   - SQL injection prevention
   - Read-only enforcement

3. **Observability** (`common/observability.py`)
   - Token usage tracking
   - LLM round trip tracking
   - Metrics logging

4. **Performance Schema Tools** (`common/sys_schema_tools.py`)
   - Direct access to `performance_schema` and `information_schema` tables
   - Lock wait analysis
   - Process list queries
   - I/O bottleneck detection
   - Statement analysis
   - System metrics

5. **Configuration** (`common/config.py`)
   - OpenAI API configuration
   - Database connection configuration
   - SkySQL API configuration (API key, service ID, API URL)

### New Tools Needed (For Future Agents)

1. **Replication Status Tools**
   - `SHOW SLAVE STATUS` / `SHOW REPLICA STATUS` parsing
   - Replication lag analysis
   - GTID consistency checks

2. **Connection Analysis Tools**
   - Connection pool usage analysis
   - Connection leak detection
   - Connection source tracking

3. **Capacity/Disk Usage Tools**
   - Table growth rate analysis
   - Disk space prediction
   - Resource utilization trends

4. **Security Audit Tools**
   - User permission analysis
   - Access pattern analysis
   - Compliance checking

5. **Backup Verification Tools**
   - Backup metadata parsing
   - RPO/RTO estimation
   - Recovery capability analysis

6. **Configuration Analysis Tools**
   - Configuration vs. best practices comparison
   - Risk assessment for configuration changes
   - Workload-specific recommendations

---

## 📦 Dependencies

### Current Dependencies (requirements.txt)

```
openai-agents>=0.6.0
mysql-connector-python>=9.0.0
python-dotenv>=1.0.1
requests>=2.31.0
python-dateutil>=2.8.0
```

### Additional Dependencies (May Be Needed)

- **Time-series analysis** (for Capacity Planning, Anomaly Detection):
  - `pandas>=2.0.0` (for data analysis)
  - `numpy>=1.24.0` (for numerical operations)

- **Statistical analysis** (for Anomaly Detection):
  - `scipy>=1.10.0` (for statistical functions)

- **Visualization** (optional, for reports):
  - `matplotlib>=3.7.0` (for charts)
  - `plotly>=5.14.0` (for interactive charts)

---

## 🔧 Technical Considerations

### Read-Only Safety
- All agents maintain the **read-only** safety principle
- Recommendations should be **actionable** with clear impact estimates
- Agents should **gracefully degrade** when features aren't available (e.g., Performance Schema)

### Agent Composition Pattern
Several agents can **leverage existing agents**:
- **Index Advisor** → calls Slow Query Agent + Running Query Agent
- **Incident Triage** → calls Slow Query Agent + Running Query Agent + others
- **Capacity Planning** → can analyze Slow Query Agent output for trends
- **DBA Orchestrator** → routes to all specialized agents

### SkySQL-Specific Opportunities
Several agents have SkySQL-specific value:
- **Capacity & Cost Agent**: Serverless scaling events correlation
- **Backup Agent**: SkySQL backup API integration
- **Configuration Agent**: SkySQL instance sizing recommendations
- **Error Log Analysis**: SkySQL API integration (already implemented in Incident Triage Agent)

### Integration Points
- **SkySQL API**: For service metadata, connection info, logs, backups
- **Monitoring Stack**: For historical metrics and alerting (future)
- **Backup Systems**: For backup verification (if accessible)
- **Log Aggregation**: For comprehensive log analysis (SkySQL API already integrated)

---

## 📊 Implementation Priority Matrix

| Agent | Business Value | Technical Complexity | User Demand | Priority | Phase |
|-------|---------------|---------------------|-------------|----------|-------|
| **Replication Health Agent** | ⭐⭐⭐⭐⭐ | Medium | High | **P0** | Phase 1 |
| **Lock & Deadlock Detective** | ⭐⭐⭐⭐⭐ | Low-Medium | High | **P0** | Phase 1 |
| **Connection Pool Agent** | ⭐⭐⭐⭐⭐ | Low-Medium | High | **P0** | Phase 2 |
| **Schema Health & Index Advisor** | ⭐⭐⭐⭐ | Medium | Medium | **P1** | Phase 2 |
| **Configuration Safety Agent** | ⭐⭐⭐⭐ | Medium | Medium | **P1** | Phase 2 |
| **Capacity Planning & Cost Optimization** | ⭐⭐⭐⭐⭐ | Medium | High | **P1** | Phase 3 |
| **Backup/Restore & RPO/RTO Agent** | ⭐⭐⭐⭐ | Medium-High | Medium | **P1** | Phase 3 |
| **Security Audit Agent** | ⭐⭐⭐⭐ | Medium | High | **P1** | Phase 4 |
| **Anomaly Detection Agent** | ⭐⭐⭐⭐ | High | Medium | **P2** | Phase 4 |
| **Migration Planning Agent** | ⭐⭐⭐ | Low-Medium | Low | **P2** | Phase 4 |
| **Multi-Tenant Agent** | ⭐⭐⭐ | High | Low (niche) | **P3** | Phase 4 |
| **Query Pattern Analysis** | ⭐⭐⭐ | Medium | Low | **P3** | Phase 4 |
| **DBA Orchestrator** | ⭐⭐⭐⭐⭐ | Medium | High | **P0** | Phase 1-2 |

---

## 🚀 Quick Wins (Can Build First)

1. **Connection Pool Agent** - Relatively simple, high impact
2. **Schema Health Agent** - Builds on existing index analysis
3. **Capacity Planning Agent** - Uses existing table analysis tools
4. **Configuration Tuning Agent** - Leverages existing performance analysis

---

## 💡 Future Enhancements

- **Predictive Analytics**: ML-based predictions for capacity, performance
- **Automated Remediation**: Safe, automated fixes for common issues
- **Integration with CI/CD**: Schema change validation in pipelines
- **Multi-Database Support**: Extend beyond MariaDB to MySQL, PostgreSQL
- **Natural Language Interface**: "Why is my database slow?" → comprehensive analysis

---

## 📝 Notes

- All agents should maintain the **read-only** safety principle
- Recommendations should be **actionable** with clear impact estimates
- Agents should **gracefully degrade** when features aren't available (e.g., Performance Schema)
- Consider **agent composition** - some agents can call others for deeper analysis
- Maintain **observability** for all agent interactions
- All agents use **performance_schema** and **information_schema** directly (NOT sys schema views)

---

## 📚 References

- `docs/HIGH_VALUE_AUTOMATION_OPPORTUNITIES.md` - Original requirements analysis
- `../mariadb_slow_query_agent/AGENT_SUITE_REVIEW.md` - ChatGPT's proposal review
- `README.md` - Project overview and current status
- `NEXT_STEPS.md` - Implementation checklist


