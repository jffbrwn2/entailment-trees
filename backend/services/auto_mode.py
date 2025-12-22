"""Auto mode session management and background task."""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Optional, List

from agent_system import TextEvent, ToolUseEvent, ToolResultEvent, ErrorEvent, DoneEvent

from .state import get_orchestrator, get_openrouter_client, auto_mode_sessions
from .websocket import notify_auto_event


AUTO_AGENT_SYSTEM_PROMPT = """
You are an Auto Agent rigorously evaluating a hypothesis through an entailment tree.

Your role: Act as a knowledgeable user who systematically:
1. Identifies claims needing evidence or scoring
2. Requests simulations and literature searches
3. Points out logical gaps
4. Brainstorms alternatives when hitting blockers

Current hypothesis: {hypothesis}

Current entailment tree (full hypergraph.json):
{hypergraph}

Guidelines:
- Work through claims systematically, one at a time
- Prioritize high-impact claims
- Give Claude clear, specific instructions
- When blocked, suggest OR pathways (alternatives)
- Don't stop until you've either 1) found an entailment tree that assigns the "hypothesis" claim a cost that is low cost (according to the hypergraph) where low cost means -log2(0.8)*number of leaf nodes,  or 2) for every claim that is uncertain, there is a precise experment you propose to eliminate the uncertainty.
- You are a truth seeking entity first, then a problem solver.

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


async def get_auto_agent_response(
    model: str,
    hypothesis: str,
    hypergraph: dict,
    conversation_history: list[dict]
) -> str:
    """Get next message from the Auto agent via OpenRouter."""
    client = get_openrouter_client()
    system_prompt = AUTO_AGENT_SYSTEM_PROMPT.format(
        hypothesis=hypothesis,
        hypergraph=json.dumps(hypergraph, indent=2)
    )

    messages = [{"role": "system", "content": system_prompt}] + conversation_history
    return await client.chat(messages, model)


async def run_auto_mode_loop(folder: str, session: AutoModeSession) -> None:
    """Background task that runs the auto mode loop."""
    print(f"[AUTO MODE] Starting loop for {folder}", flush=True)
    orchestrator = get_orchestrator()

    while session.active and not session.paused and session.turn_count < session.max_turns:
        try:
            # Load current hypergraph state
            hypergraph_path = orchestrator.config.approaches_dir / folder / "hypergraph.json"
            if not hypergraph_path.exists():
                print(f"[AUTO MODE] Hypergraph not found for {folder}", flush=True)
                break

            with open(hypergraph_path) as f:
                hypergraph = json.load(f)

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

            session.turn_count += 1
            await notify_auto_event(folder, {
                "type": "auto_turn",
                "turn_number": session.turn_count,
                "max_turns": session.max_turns
            })

            # Brief delay before next turn
            await asyncio.sleep(1)

        except Exception as e:
            print(f"[AUTO MODE] Error in loop: {e}", flush=True)
            await notify_auto_event(folder, {"type": "error", "error": str(e)})
            break

    # Clean up
    session.active = False
    await notify_auto_event(folder, {"type": "auto_status", "status": "stopped"})
    print(f"[AUTO MODE] Loop ended for {folder} after {session.turn_count} turns", flush=True)
