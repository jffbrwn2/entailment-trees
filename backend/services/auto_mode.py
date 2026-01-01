"""Auto mode session management and background task."""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Optional, List

from agent_system import TextEvent, ToolUseEvent, ToolResultEvent, ErrorEvent, DoneEvent
from agent_system.hypergraph.manager import HypergraphManager

from .state import get_orchestrator, get_auto_agent_client, auto_mode_sessions
from .websocket import notify_auto_event


AUTO_AGENT_SYSTEM_PROMPT = """
You are an Auto Agent brainstorming about a hypothesis through an entailment tree.

Your role: Act as a knowledgeable user who systematically:
1. Identifies claims needing evidence or scoring
2. Requests simulations and literature searches
3. Points out logical gaps
4. Ensures all leaf claims are testable
5. Brainstorms alternatives when hitting blockers

Current hypothesis: {hypothesis}

Current entailment tree (summary - use read_claim_evidence tool for evidence details):
{hypergraph}

User notes on claims/implications (pay attention to these!):
{notes}

Guidelines:
- Work through claims systematically, one at a time
- Prioritize high-impact claims (look at cost values)
- Pay attention to user notes - they contain important context and feedback
- Give Claude clear, specific instructions
- When blocked, suggest OR pathways (alternatives)
- For claims with infinite experimental_epistemic_cost, ask Claude to either:
  1. Evaluate testability (use evaluate_testability tool) to confirm if testable
  2. Break the claim into more specific, testable sub-claims
- Don't stop until you've either:
  1. Found an entailment tree where "hypothesis" has low cost (evidence_epistemic_cost + experimental_epistemic_cost < -log2(0.8)*number of leaf nodes), OR
  2. For every uncertain claim, there is a proposed experiment that could resolve it (testability=1)
- You are a relentless, optimistic truth seeking entity and problem solver. Solving hard problems often requires going deeper and further into problems than others are willing to go, getting at the fundamentals of how things work to understand how things can be different.

Generate your next message to Claude:"""


@dataclass
class AutoModeSession:
    """Tracks state for an auto mode session."""
    folder: str
    session_id: str
    model: str
    active: bool = True
    paused: bool = False
    turn_count: int = 0
    max_turns: int = 20
    hypothesis: str = ""
    conversation_history: List[dict] = field(default_factory=list)
    task: Optional[asyncio.Task] = None
    consecutive_errors: int = 0
    max_consecutive_errors: int = 3


async def get_auto_agent_response(
    model: str,
    hypothesis: str,
    hypergraph: dict,
    conversation_history: list[dict]
) -> str:
    """Get next message from the Auto agent.

    Uses OpenRouter if available, otherwise falls back to Anthropic.
    """
    client = get_auto_agent_client()

    # Extract notes from hypergraph summary and format for display
    notes = hypergraph.get("notes", [])
    if notes:
        notes_text = "\n".join(
            f"- {n['id']}: {n['note']}" + (" [content changed]" if n.get('content_changed') else "")
            for n in notes
        )
    else:
        notes_text = "(No notes yet)"

    system_prompt = AUTO_AGENT_SYSTEM_PROMPT.format(
        hypothesis=hypothesis,
        hypergraph=json.dumps(hypergraph, indent=2),
        notes=notes_text
    )

    messages = [{"role": "system", "content": system_prompt}] + conversation_history
    return await client.chat(messages, model)


async def run_auto_mode_loop(folder: str, session: AutoModeSession) -> None:
    """Background task that runs the auto mode loop."""
    print(f"[AUTO MODE] Starting loop for {folder}", flush=True)
    orchestrator = get_orchestrator()

    while session.active and not session.paused and session.turn_count < session.max_turns:
        try:
            # Load current hypergraph state (summary view to reduce context size)
            approach_path = orchestrator.config.approaches_dir / folder
            hypergraph_path = approach_path / "hypergraph.json"
            if not hypergraph_path.exists():
                print(f"[AUTO MODE] Hypergraph not found for {folder}", flush=True)
                break

            manager = HypergraphManager(approach_path)
            hypergraph = manager.get_summary_view()

            # Get Auto agent's next message
            print(f"[AUTO MODE] Turn {session.turn_count + 1}: Getting Auto agent response", flush=True)
            auto_message = await get_auto_agent_response(
                session.model,
                session.hypothesis,
                hypergraph,
                session.conversation_history
            )

            print(f"[AUTO MODE] Auto agent says: {auto_message[:100]}...", flush=True)

            # Add Auto agent message to history
            session.conversation_history.append({"role": "assistant", "content": auto_message})

            # Notify WebSocket clients of the auto message
            await notify_auto_event(folder, {
                "type": "auto_message",
                "text": auto_message,
                "source": "auto"
            })

            # Check for stop signals before sending to Claude
            if not session.active or session.paused:
                break

            # Send to Claude via the existing chat endpoint logic
            # We need to capture Claude's response to add to history
            claude_response = ""
            approach_dir = orchestrator.config.approaches_dir / folder

            # Load approach if not already loaded
            if (orchestrator.current_session is None or
                str(orchestrator.current_session.approach_dir) != str(approach_dir)):
                orchestrator.load_approach(approach_dir)

            system_prompt = orchestrator.get_system_prompt()

            async for event in orchestrator.claude_client.query_stream(
                auto_message,
                system_prompt=system_prompt
            ):
                if isinstance(event, TextEvent):
                    claude_response += event.text
                    await notify_auto_event(folder, {"type": "text", "text": event.text})
                elif isinstance(event, ToolUseEvent):
                    await notify_auto_event(folder, {
                        "type": "tool_use",
                        "tool_name": event.tool_name,
                        "tool_input": event.tool_input
                    })
                elif isinstance(event, ToolResultEvent):
                    await notify_auto_event(folder, {
                        "type": "tool_result",
                        "tool_name": event.tool_name,
                        "result": event.result,
                        "is_error": event.is_error
                    })
                elif isinstance(event, ErrorEvent):
                    await notify_auto_event(folder, {"type": "error", "error": event.error})
                elif isinstance(event, DoneEvent):
                    await notify_auto_event(folder, {
                        "type": "done",
                        "full_response": event.full_response
                    })

            # Add Claude's response to history (for Auto agent's context)
            session.conversation_history.append({"role": "user", "content": claude_response})

            # Reset error counter on successful turn
            session.consecutive_errors = 0
            session.turn_count += 1
            await notify_auto_event(folder, {
                "type": "auto_turn",
                "turn_number": session.turn_count,
                "max_turns": session.max_turns
            })

            # Brief delay before next turn
            await asyncio.sleep(1)

        except Exception as e:
            error_msg = str(e)
            # Check if this is an OpenRouter-specific error
            if "OpenRouter" in error_msg:
                session.consecutive_errors += 1
                print(f"[AUTO MODE] OpenRouter error ({session.consecutive_errors}/{session.max_consecutive_errors}): {error_msg}", flush=True)

                if session.consecutive_errors >= session.max_consecutive_errors:
                    await notify_auto_event(folder, {
                        "type": "error",
                        "error": f"OpenRouter failed {session.max_consecutive_errors} times in a row: {error_msg}. Stopping auto mode."
                    })
                    break
                else:
                    await notify_auto_event(folder, {
                        "type": "warning",
                        "warning": f"OpenRouter issue ({session.consecutive_errors}/{session.max_consecutive_errors}): {error_msg}. Retrying in 5s..."
                    })
                    await asyncio.sleep(5)
                    continue
            else:
                print(f"[AUTO MODE] Error in loop: {e}", flush=True)
                await notify_auto_event(folder, {"type": "error", "error": error_msg})
                break

    # Clean up
    session.active = False
    await notify_auto_event(folder, {"type": "auto_status", "status": "stopped"})
    print(f"[AUTO MODE] Loop ended for {folder} after {session.turn_count} turns", flush=True)
