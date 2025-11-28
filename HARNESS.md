# Long-Running Agent Harness

This project uses a **harness system** to enable systematic, incremental development across multiple sessions with Claude Code. This approach is based on [Anthropic's recommendations for effective long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents).

## Why Use a Harness?

Complex multi-week projects like this web application need:
- **Memory across sessions**: Work from Session 1 informs Session 2
- **Feature tracking**: Know what's done, what's next, what's blocked
- **Incremental progress**: One feature at a time prevents context exhaustion
- **Testing requirements**: Verify before marking complete
- **Clear communication**: Human always knows current status

Without a harness, agents tend to:
- Forget what was done in previous sessions
- Try to do everything at once
- Miss important features
- Claim completion prematurely

## Core Components

### 1. `features.json` - Feature List

**Purpose**: Comprehensive list of all features to implement

**Structure**:
```json
{
  "phases": {
    "phase_1_mvp": {
      "features": [
        {
          "id": "backend-setup",
          "name": "FastAPI Backend Setup",
          "status": "pending",
          "tasks": [...],
          "acceptance_criteria": [...]
        }
      ]
    }
  }
}
```

**Statuses**: `pending`, `in_progress`, `completed`, `blocked`

**Usage**:
- Agent reads this at start of each session
- Agent updates status as work progresses
- Human can see exact progress at any time

### 2. `claude-progress.txt` - Session Log

**Purpose**: Narrative log of work completed across sessions

**Format**:
```
## Session 1: Harness Setup
- Created features.json with all Phase 1 & 2 tasks
- Created init.sh environment setup script
- Initialized progress tracking system

## Session 2: Backend Setup
- Set up FastAPI with uvicorn
- Created basic project structure
- Added health check endpoint
- Tested: Server runs on port 8000 ✓

## Next Steps:
- Complete database setup
- Configure PostgreSQL schema
```

**Key practices**:
- Update after EACH completed feature (not at end of session)
- Include test results and verification
- Note blockers or questions
- Keep descriptions concise but specific

### 3. `init.sh` - Environment Setup

**Purpose**: One-command setup for development environment

**What it does**:
- Creates directory structure
- Checks dependencies (Python, Node.js, Docker)
- Initializes progress tracking
- Creates configuration templates
- Provides next steps guidance

**Usage**:
```bash
./init.sh
```

Run this once to set up the environment, or when onboarding new developers.

### 4. Git Commits - Persistent Memory

**Purpose**: Each feature becomes a commit, creating searchable history

**Best practices**:
- Commit after EACH completed feature
- Use descriptive commit messages
- Include Co-Authored-By: Claude
- Never batch multiple features in one commit

**Example**:
```bash
git add backend/api/routes/approaches.py
git commit -m "Add CRUD endpoints for approaches

Implements create, read, update, delete operations for approach management.
Includes validation via Pydantic models.
Tested: All endpoints return proper status codes.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Why git logs matter**: Agent reads `git log` to understand recent work when resuming.

## Workflow

### Starting a New Session

1. **Read the context**:
   ```bash
   cat claude-progress.txt
   git log --oneline -10
   cat features.json | jq '.phases.phase_1_mvp.features[] | select(.status == "in_progress" or .status == "pending") | .id, .name'
   ```

2. **Identify current task**: Look for `in_progress` features or next `pending` feature

3. **Work incrementally**: Complete ONE feature at a time

4. **Verify thoroughly**: Test according to acceptance criteria

5. **Update and commit**:
   ```bash
   # Update features.json status to "completed"
   # Add entry to claude-progress.txt
   git add .
   git commit -m "Feature: [name]..."
   ```

### During Development

- **Stay focused**: Work on one feature until complete
- **Test continuously**: Don't mark complete without testing
- **Document blockers**: If stuck, note in claude-progress.txt
- **Ask questions**: Use context to clarify requirements

### Ending a Session

1. **Update progress**: Add session summary to claude-progress.txt
2. **Update features**: Set current feature status appropriately
3. **Commit changes**: Even incomplete work gets committed
4. **Note next steps**: Write what should happen next session

## Feature Development Guidelines

### When to Mark a Feature "Completed"

A feature is ONLY complete when:
- ✅ All tasks listed are done
- ✅ All acceptance criteria pass
- ✅ Tests run successfully
- ✅ No errors or warnings
- ✅ Code is committed to git

### When to Mark "Blocked"

Mark as blocked when:
- Missing credentials or API keys
- Dependency issues
- Unclear requirements
- Waiting on user input

Include blocker description in claude-progress.txt.

### Acceptance Criteria

Every feature has specific acceptance criteria. Examples:

**Backend Setup**:
- ✓ Backend server runs on port 8000
- ✓ Health check endpoint returns 200 OK
- ✓ CORS configured for localhost:5173

**Don't guess** if criteria pass - actually test them.

## File Organization

```
ai-simulations/
├── features.json              # Feature tracking
├── claude-progress.txt        # Progress log
├── init.sh                    # Setup script
├── HARNESS.md                 # This file
├── backend/                   # Backend code
│   ├── api/
│   │   ├── routes/
│   │   ├── models/
│   │   ├── services/
│   │   └── security/
│   └── worker/
├── frontend/                  # Frontend code
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   └── services/
│   └── public/
└── docker/                    # Docker configs
```

## Testing Requirements

### Phase 1 Testing

Each feature must include tests:
- Backend: `pytest` tests for all endpoints
- Frontend: Manual testing in browser
- Integration: Full user flow works

### Phase 2 Testing

- Docker sandbox: Verify isolation and limits
- Simulation execution: Test with sample code
- Progress tracking: Verify real-time updates

### Before Marking Complete

Always verify:
1. Run the code (don't just assume it works)
2. Check logs for errors
3. Test acceptance criteria explicitly
4. Document test results in claude-progress.txt

## Common Pitfalls to Avoid

❌ **Claiming completion without testing**
- Always run and verify

❌ **Batching multiple features**
- Work on one feature at a time

❌ **Forgetting to update tracking**
- Update after EACH feature, not at end

❌ **Vague progress descriptions**
- Be specific: "Added health check endpoint" not "Made progress"

❌ **Not reading git logs**
- Always check recent commits when resuming

❌ **Ignoring blockers**
- Document and communicate blockers immediately

## Success Metrics

You'll know the harness is working when:
- ✅ Can resume work seamlessly across sessions
- ✅ Always know exactly what's done and what's next
- ✅ No features are forgotten or skipped
- ✅ Testing happens consistently
- ✅ Progress is transparent to user

## References

- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) - Anthropic Engineering
- [WEB_IMPLEMENTATION_RESEARCH.md](./WEB_IMPLEMENTATION_RESEARCH.md) - Technical architecture details
- [features.json](./features.json) - Complete feature list

## Questions?

If you're Claude resuming work:
1. Read `claude-progress.txt` first
2. Check `git log --oneline -10`
3. Review current feature in `features.json`
4. Follow acceptance criteria strictly
5. Update progress after completing feature

If you're human:
- Check `claude-progress.txt` for current status
- Review `features.json` for overall progress
- Look at recent git commits for what changed
- Features marked "blocked" need your input
