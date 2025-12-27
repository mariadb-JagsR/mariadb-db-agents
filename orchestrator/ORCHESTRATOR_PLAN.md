# DBA Orchestrator Agent - Implementation Plan

## Overview

The DBA Orchestrator Agent is a meta-agent that acts as the primary entry point for database management tasks. It intelligently routes user queries to specialized agents, coordinates multi-agent analysis, and synthesizes comprehensive reports.

## Goals

1. **Unified Interface**: Single entry point for all database management tasks
2. **Intelligent Routing**: Understand user intent and route to appropriate specialized agents
3. **Multi-Agent Coordination**: Coordinate multiple agents for comprehensive analysis
4. **Context Management**: Maintain conversation context across agent interactions
5. **Result Synthesis**: Combine results from multiple agents into coherent reports
6. **Extensibility**: Easy to add new agents without modifying orchestrator core

---

## Architecture

### High-Level Design

```
User Query
    ↓
Orchestrator Agent (LLM-based routing)
    ↓
Intent Classification → Route to Agent(s)
    ↓
Agent Execution (via Runner.run())
    ↓
Result Collection & Synthesis
    ↓
Final Report
```

### Two-Phase Approach

**Phase 1: Direct Agent Invocation (Simpler)**
- Orchestrator has tools that directly invoke other agents
- Each tool wraps an agent's `run_agent_async()` function
- LLM decides which tool(s) to call based on user query

**Phase 2: Agent Composition (Advanced)**
- Orchestrator can compose multiple agents in sequence
- Maintains context between agent calls
- Synthesizes results from multiple agents

---

## Implementation Strategy

### Option A: Tool-Based Agent Invocation (Recommended for Phase 1)

**Concept**: Orchestrator has tools that invoke other agents programmatically.

**Advantages**:
- Simple to implement
- Leverages existing agent infrastructure
- LLM naturally routes via tool selection
- Easy to add new agents (just add a tool)

**Disadvantages**:
- Each agent invocation is independent (no shared context)
- Results need to be synthesized by orchestrator LLM

**Implementation**:
```python
@function_tool
async def analyze_slow_queries(
    hours: float = 1.0,
    max_patterns: int = 8,
) -> dict[str, Any]:
    """Invoke Slow Query Agent to analyze historical slow queries."""
    from ..agents.slow_query.main import run_agent_async
    result = await run_agent_async(hours, max_patterns)
    return {"report": result, "agent": "slow_query"}

@function_tool
async def analyze_running_queries(
    min_time_seconds: float = 1.0,
    include_sleeping: bool = False,
    max_queries: int = 20,
) -> dict[str, Any]:
    """Invoke Running Query Agent to analyze currently executing queries."""
    from ..agents.running_query.main import run_agent_async
    result = await run_agent_async(min_time_seconds, include_sleeping, max_queries)
    return {"report": result, "agent": "running_query"}

@function_tool
async def perform_incident_triage(
    error_log_path: str | None = None,
    service_id: str | None = None,
    max_error_patterns: int = 20,
    error_log_lines: int = 5000,
) -> dict[str, Any]:
    """Invoke Incident Triage Agent to quickly identify database issues."""
    from ..agents.incident_triage.main import run_agent_async
    result = await run_agent_async(
        error_log_path, service_id, max_error_patterns, error_log_lines
    )
    return {"report": result, "agent": "incident_triage"}
```

### Option B: Direct Database Tools (Alternative)

**Concept**: Orchestrator has direct access to database tools, can perform quick checks, then route to specialized agents.

**Advantages**:
- Can do quick health checks before routing
- More flexible routing logic
- Can synthesize data from multiple sources

**Disadvantages**:
- More complex
- Duplicates some agent functionality
- Harder to maintain

**Recommendation**: Start with Option A, add Option B capabilities later if needed.

---

## Agent Registry

### Current Agents

| Agent | Tool Name | Purpose | Parameters |
|-------|-----------|---------|------------|
| Slow Query | `analyze_slow_queries` | Historical slow query analysis | `hours`, `max_patterns` |
| Running Query | `analyze_running_queries` | Real-time query analysis | `min_time_seconds`, `include_sleeping`, `max_queries` |
| Incident Triage | `perform_incident_triage` | Quick health check & issue identification | `error_log_path`, `service_id`, `max_error_patterns`, `error_log_lines` |

### Future Agents (To Be Added)

| Agent | Tool Name | Purpose | Status |
|-------|-----------|---------|--------|
| Replication Health | `check_replication_health` | Replication lag & health | Planned |
| Connection Pool | `analyze_connections` | Connection usage & leaks | Planned |
| Schema Health | `analyze_schema_health` | Index & schema optimization | Planned |
| Configuration Safety | `audit_configuration` | Config best practices | Planned |
| Capacity Planning | `analyze_capacity` | Resource forecasting | Planned |
| Backup & Recovery | `check_backup_health` | Backup verification | Planned |

---

## System Prompt Design

### Core Responsibilities

1. **Intent Understanding**: Parse user queries to understand what they want
2. **Agent Selection**: Choose appropriate agent(s) based on intent
3. **Parameter Extraction**: Extract relevant parameters from user query
4. **Result Synthesis**: Combine results from multiple agents into coherent report
5. **Context Management**: Remember previous interactions in conversation

### Prompt Structure

```
You are the MariaDB Database Management Orchestrator.

Your role:
- Understand user queries about database management
- Route queries to appropriate specialized agents
- Coordinate multi-agent analysis when needed
- Synthesize results into comprehensive reports

Available Agents:
1. Slow Query Agent - Analyzes historical slow queries
2. Running Query Agent - Analyzes currently executing queries
3. Incident Triage Agent - Quick health check & issue identification
[Future agents will be added here]

Routing Guidelines:
- "slow queries", "query performance", "optimization" → Slow Query Agent
- "running queries", "current queries", "blocking" → Running Query Agent
- "health check", "something's wrong", "incident" → Incident Triage Agent
- "is my database healthy?" → Incident Triage + Running Query (comprehensive)
- "why is my database slow?" → Incident Triage → Slow Query (if needed)

Multi-Agent Coordination:
- For comprehensive health checks, use Incident Triage first, then route to specific agents
- For performance issues, use Running Query for immediate issues, Slow Query for patterns
- Always synthesize results from multiple agents into a unified report

Output Format:
- Start with a summary of what you're analyzing
- Show which agent(s) you're using
- Present findings in a structured format
- End with actionable recommendations
```

---

## File Structure

```
orchestrator/
├── __init__.py
├── agent.py              # Orchestrator agent definition
├── tools.py              # Tools for invoking other agents
├── main.py               # CLI entry point
├── conversation.py      # Interactive conversation mode
├── agent_registry.py     # Registry of available agents (for extensibility)
└── ORCHESTRATOR_PLAN.md  # This file
```

---

## Implementation Steps

### Step 1: Create Basic Structure
- [ ] Create `orchestrator/` directory
- [ ] Create `__init__.py`
- [ ] Create `agent_registry.py` with agent metadata
- [ ] Create `tools.py` with agent invocation tools

### Step 2: Implement Agent Invocation Tools
- [ ] Implement `analyze_slow_queries()` tool
- [ ] Implement `analyze_running_queries()` tool
- [ ] Implement `perform_incident_triage()` tool
- [ ] Test each tool independently

### Step 3: Create Orchestrator Agent
- [ ] Write system prompt
- [ ] Create `create_orchestrator_agent()` function
- [ ] Add tools to agent
- [ ] Add guardrails

### Step 4: Create CLI Entry Point
- [ ] Create `main.py` with CLI arguments
- [ ] Support both one-shot and interactive modes
- [ ] Add to unified CLI in `cli/main.py`

### Step 5: Testing
- [ ] Test routing to individual agents
- [ ] Test multi-agent coordination
- [ ] Test result synthesis
- [ ] Test conversation context

### Step 6: Documentation
- [ ] Update README with orchestrator usage
- [ ] Add examples of orchestrator queries
- [ ] Document agent registry for future agents

---

## Agent Registry Design

### Purpose
Central registry of all available agents for easy extensibility.

### Structure

```python
# orchestrator/agent_registry.py

from dataclasses import dataclass
from typing import Callable, Any
import asyncio

@dataclass
class AgentMetadata:
    """Metadata for a specialized agent."""
    name: str
    description: str
    tool_name: str
    invoke_function: Callable[..., Any]
    default_params: dict[str, Any]
    use_cases: list[str]

# Registry of all agents
AGENT_REGISTRY: dict[str, AgentMetadata] = {
    "slow_query": AgentMetadata(
        name="Slow Query Agent",
        description="Analyzes historical slow queries from slow query logs",
        tool_name="analyze_slow_queries",
        invoke_function=lambda **kwargs: asyncio.run(
            __import__("mariadb_db_agents.agents.slow_query.main", fromlist=["run_agent_async"]).run_agent_async(**kwargs)
        ),
        default_params={"hours": 1.0, "max_patterns": 8},
        use_cases=[
            "Analyze slow queries from the last hour",
            "Find query optimization opportunities",
            "Identify performance patterns",
        ],
    ),
    # ... other agents
}
```

### Benefits
- Easy to add new agents (just add to registry)
- Can generate help text automatically
- Can validate agent availability
- Can provide suggestions to users

---

## Routing Logic

### Intent Classification

The orchestrator uses LLM-based intent classification. Key patterns:

**Slow Query Intent:**
- "slow queries", "slow query log", "query performance"
- "optimize queries", "query tuning"
- "historical performance", "query patterns"

**Running Query Intent:**
- "running queries", "current queries", "active queries"
- "blocking queries", "long-running queries"
- "what's running now", "current performance"

**Incident Triage Intent:**
- "health check", "database health", "is everything ok"
- "something's wrong", "incident", "troubleshoot"
- "quick check", "status check"

**Multi-Agent Intent:**
- "comprehensive health check" → Incident Triage + Running Query
- "why is it slow?" → Incident Triage → (Slow Query if needed)
- "full analysis" → Incident Triage + Running Query + Slow Query

### Routing Examples

```
User: "Is my database healthy?"
→ perform_incident_triage() → analyze_running_queries()
→ Synthesize: "Database is healthy. No issues found. 5 active queries, all normal."

User: "Why are queries slow?"
→ perform_incident_triage() → analyze_slow_queries(hours=24)
→ Synthesize: "Found 3 slow query patterns. Top issue: missing index on orders table."

User: "What queries are running right now?"
→ analyze_running_queries()
→ Direct response from Running Query Agent

User: "Check everything"
→ perform_incident_triage() → analyze_running_queries() → analyze_slow_queries()
→ Comprehensive health report
```

---

## Result Synthesis

### Approach

The orchestrator LLM receives results from multiple agents and synthesizes them:

1. **Extract Key Findings**: Identify critical issues from each agent
2. **Correlate Symptoms**: Find connections between different agent findings
3. **Prioritize Issues**: Rank issues by severity and impact
4. **Generate Recommendations**: Provide actionable next steps
5. **Format Report**: Present in clear, structured format

### Example Synthesis

```
Agent Results:
- Incident Triage: "Connection usage: 85/100. Lock waits detected."
- Running Query: "3 queries blocking others. Longest: 45 seconds."
- Slow Query: "Top slow query: SELECT * FROM orders WHERE status='pending'"

Synthesized Report:
"Database Health Summary:
- ⚠️ Connection pool near capacity (85/100)
- 🔴 Lock contention: 3 blocking queries
- 📊 Top slow query identified

Immediate Actions:
1. Kill blocking query (ID: 12345) if safe
2. Investigate connection leaks
3. Add index on orders.status

Detailed Analysis:
[Combined findings from all agents]"
```

---

## Conversation Context

### Context Management

The orchestrator maintains conversation context:

1. **Previous Queries**: Remember what was asked before
2. **Agent Results**: Reference previous agent results
3. **User Preferences**: Remember user's preferred time windows, etc.
4. **Follow-up Questions**: Handle "tell me more about X" queries

### Example Conversation Flow

```
User: "Is my database healthy?"
Orchestrator: [Runs Incident Triage] "Database is healthy. 5 active queries."

User: "What about slow queries?"
Orchestrator: [Runs Slow Query Agent] "Found 2 slow patterns. Top issue: missing index."

User: "Tell me more about the first one"
Orchestrator: [References previous Slow Query result] "The first slow query is..."
```

---

## Error Handling

### Agent Invocation Failures

- If an agent fails, gracefully continue with other agents
- Report which agents succeeded/failed
- Suggest alternatives if primary agent unavailable

### Parameter Extraction Failures

- Use sensible defaults if parameters can't be extracted
- Ask user for clarification if critical parameters missing
- Validate parameters before invoking agents

### Result Synthesis Failures

- If synthesis fails, return raw results from agents
- Log errors for debugging
- Provide fallback formatting

---

## Extensibility

### Adding New Agents

To add a new agent to the orchestrator:

1. **Add Agent Invocation Tool** (`tools.py`):
   ```python
   @function_tool
   async def check_replication_health(...) -> dict[str, Any]:
       """Invoke Replication Health Agent."""
       from ..agents.replication_health.main import run_agent_async
       result = await run_agent_async(...)
       return {"report": result, "agent": "replication_health"}
   ```

2. **Add to Agent Registry** (`agent_registry.py`):
   ```python
   "replication_health": AgentMetadata(...)
   ```

3. **Update System Prompt** (`agent.py`):
   - Add agent description
   - Add routing guidelines
   - Add use cases

4. **Update CLI** (`cli/main.py`):
   - Add orchestrator subcommand (if needed)

### No Core Changes Required

The orchestrator is designed so adding new agents doesn't require changes to core routing logic - the LLM naturally learns about new tools.

---

## Testing Strategy

### Unit Tests

- Test each agent invocation tool independently
- Test parameter extraction
- Test error handling

### Integration Tests

- Test routing to correct agents
- Test multi-agent coordination
- Test result synthesis

### Conversation Tests

- Test context management
- Test follow-up questions
- Test complex multi-turn conversations

### Example Test Cases

```python
# Test 1: Simple routing
user_query = "Analyze slow queries from the last hour"
expected_agent = "slow_query"
expected_params = {"hours": 1.0}

# Test 2: Multi-agent coordination
user_query = "Is my database healthy?"
expected_agents = ["incident_triage", "running_query"]

# Test 3: Parameter extraction
user_query = "Check slow queries from the last 3 hours, focus on top 5 patterns"
expected_params = {"hours": 3.0, "max_patterns": 5}

# Test 4: Context management
# Query 1: "Is my database healthy?"
# Query 2: "What about slow queries?"
# Should reference previous health check results
```

---

## Performance Considerations

### Agent Invocation Overhead

- Each agent invocation is independent (can be parallelized in future)
- Current: Sequential execution (simple, reliable)
- Future: Parallel execution for independent agents

### Token Usage

- Orchestrator adds one LLM call per user query
- Agent results are passed back to orchestrator (may be large)
- Consider summarization of agent results before synthesis

### Caching

- Cache agent results for short time window (e.g., 5 minutes)
- Avoid re-running same analysis multiple times
- Future: Implement result caching

---

## Future Enhancements

### Phase 2: Advanced Features

1. **Parallel Agent Execution**
   - Run independent agents in parallel
   - Reduce total analysis time

2. **Result Caching**
   - Cache agent results
   - Avoid redundant analysis

3. **Agent Composition**
   - More sophisticated multi-agent workflows
   - Conditional routing based on intermediate results

4. **Learning from Interactions**
   - Remember user preferences
   - Learn common query patterns
   - Suggest proactive analysis

5. **Integration with Monitoring**
   - Trigger agents based on alerts
   - Scheduled health checks
   - Proactive recommendations

---

## Success Criteria

### Phase 1 (Initial Implementation)

- ✅ Orchestrator can route to all 3 existing agents
- ✅ Can handle simple queries ("analyze slow queries")
- ✅ Can coordinate 2 agents for comprehensive checks
- ✅ Synthesizes results into coherent reports
- ✅ Maintains conversation context

### Phase 2 (Enhanced)

- ✅ Handles complex multi-agent workflows
- ✅ Parallel agent execution
- ✅ Result caching
- ✅ Proactive suggestions

---

## Timeline Estimate

### Phase 1: Basic Orchestrator (1-2 days)

- Day 1: Structure, tools, basic agent
- Day 2: CLI, testing, documentation

### Phase 2: Enhanced Features (Future)

- Parallel execution: 1 day
- Result caching: 1 day
- Advanced composition: 2-3 days

---

## Next Steps

1. **Review this plan** with team
2. **Decide on Phase 1 vs Phase 2** approach
3. **Start implementation** with basic structure
4. **Iterate** based on testing and feedback

---

## Questions to Resolve

1. **Should orchestrator have direct database access?**
   - Pro: Can do quick health checks before routing
   - Con: Duplicates agent functionality
   - **Recommendation**: Start without, add later if needed

2. **How to handle agent failures?**
   - Continue with other agents? Yes
   - Retry failed agents? Maybe (future)
   - **Recommendation**: Graceful degradation

3. **Result size limits?**
   - Agent results can be large
   - Should we summarize before synthesis?
   - **Recommendation**: Start with full results, optimize later

4. **Conversation context storage?**
   - In-memory for session? Yes (Phase 1)
   - Persistent storage? Future
   - **Recommendation**: Start with in-memory

---

## Conclusion

The orchestrator agent provides a unified, intelligent interface to all database management agents. Starting with a simple tool-based approach allows us to:

1. Get it working quickly
2. Validate the concept
3. Iterate based on real usage
4. Add advanced features incrementally

The design is extensible - adding new agents is straightforward and doesn't require core changes.

