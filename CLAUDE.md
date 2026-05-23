# Agentic E2E Lifecycle - Development Principles

## 1. Plan Mode First
- Use plan mode for any non-trivial change to agents or workflow
- Document assumptions and edge cases upfront
- Reduce ambiguity before writing code
- Lightweight inline plan for smaller tasks, formal PLAN.md for major features

## 2. Verify Relentlessly
- Watch the logs in a good IDE
- Check assumptions, edge cases, tradeoffs carefully
- Run tests individually before integration
- Don't blindly accept — stay in the loop
- Verify each agent's output before downstream consumption

## 3. Keep It Simple
- Avoid overengineering and bloated abstractions
- Prefer 100 lines over 1000
- Clean up dead code and cruft
- Ask: "Is there a simpler way?"

## 4. Surgical Edits Only
- Change only what's necessary
- Don't touch unrelated code or comments
- Don't "improve" things that work
- Minimize side effects and churn

## 5. Goal-Driven Execution
- Give clear success criteria before modifying agents
- Write tests first, then make them pass
- Use tools (e.g., browser, assertions) to verify behavior
- Let the agent iterate until goals are met

## 6. Parallelize with Subagents
- Offload research, exploration, analysis to subagents
- Keep context clean — one task per subagent
- Merge results back into main workflow
- Use for: code investigation, data analysis, complex troubleshooting

---

## Core Principles for This Project

### Simplicity First
- Minimal code that solves the problem
- No laziness — investigate root causes
- Minimal impact on unrelated systems

### Integrated Workflow
- Graph-based orchestration keeps dependencies clear
- Each agent has a single responsibility
- State management via `graph/state.py`
- Integration points are explicit

### Quality Gates
- Requirement analysis must produce actionable specs
- Generated scripts must be testable and executable
- Test cases must cover positive and negative paths
- Execution results must be logged and traceable

---

## Agent Success Criteria

### **Requirement Analyzer** (`agents/requirement_analyser.py`)
✓ Extracts clear, measurable requirements from input  
✓ Identifies acceptance criteria and edge cases  
✓ Flags ambiguous or incomplete requirements  
✓ Output is structured for downstream agents  

### **Testcase Generator** (`agents/testcase_generator.py`)
✓ Generates test cases that match requirement scope  
✓ Covers positive, negative, and boundary cases  
✓ Follows naming conventions (test_<feature>_<scenario>)  
✓ Each case is independent and idempotent  

### **Script Generator** (`agents/script_generator.py`)
✓ Produces executable scripts from test cases  
✓ Scripts are safe to run without manual intervention  
✓ Clear error handling and logging  
✓ Output is version-controlled and auditable  

### **Test Executor** (`agents/test_executor.py`)
✓ Executes scripts reliably and captures results  
✓ Provides detailed pass/fail/error reporting  
✓ Retries transient failures intelligently  
✓ Logs execution traces for debugging  

---

## Development Workflow

### When Adding Features
1. **Plan** - Write down what you're adding, why, and success criteria
2. **Verify** - Check against architecture and existing code
3. **Implement** - Minimal, surgical changes only
4. **Test** - Verify with real examples, not just theory
5. **Review** - Are side effects minimal? Is it simple?

### When Debugging
1. Watch the logs in real time
2. Verify assumptions one by one
3. Don't guess — test the actual behavior
4. Find the root cause, not just the symptom
5. Fix minimally, then verify everything still works

### Code Organization Rules
- Keep agent logic in `agents/`
- Keep integration logic in `integrations/`
- Keep data models in `models/`
- Keep configuration in `config/` with prompts in `config/prompts/`
- UI stays in `ui/` with clear separation from business logic
- Utilities in `utils/` (logging, helpers)

---

## Questions to Keep Asking

- What happens at the 10X scale (100 requirements, 1000 test cases)?
- How will debugging work when something fails in production?
- What's the failure mode if an agent hallucinates?
- How much of the workflow can be parallelized?
- What's our rollback strategy?
- Can we verify correctness before execution?

---

## TLDR

**LLM agents crossed a threshold of coherence** — they can now handle multi-step workflows reliably. Agentic workflows are the new capability shift. But we must:
- Plan first, code second
- Verify relentlessly
- Keep it simple
- Make minimal, surgical changes
- Stay in control of the agents, don't let them control you

**2026 will be the year agentic workflows prove their value. Ship reliably.**
