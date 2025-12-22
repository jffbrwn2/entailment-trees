#!/usr/bin/env python3
"""
Agent CLI - Command-line interface for hypergraph collaboration.

Run with: python agent_system/cli.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_system.orchestrator import AgentOrchestrator
from agent_system.config import AgentConfig
from agent_system.clients.openrouter import OpenRouterClient
from agent_system import TextEvent, ToolUseEvent, ToolResultEvent, ErrorEvent
from backend.services.auto_mode import AUTO_AGENT_SYSTEM_PROMPT


class AutoModeState:
    """Tracks auto mode state."""
    def __init__(self):
        self.active = False
        self.paused = False
        self.turn_count = 0
        self.max_turns = 20
        self.model = "google/gemini-3-pro-preview"
        self.conversation_history: list[dict] = []
        self.hypothesis = ""


class AgentCLI:
    """Command-line interface for agent system."""

    def __init__(self):
        self.orchestrator = AgentOrchestrator(AgentConfig.from_env())
        self.running = True
        self.auto_state = AutoModeState()
        self.openrouter_client: OpenRouterClient | None = None

    def print_banner(self):
        """Print welcome banner."""
        print("=" * 70)
        print("  Hypergraph Collaboration System")
        print("  Evaluate ideas through simulation and structured reasoning")
        print("=" * 70)
        print()
        print("Commands:")
        print("  /help      - Show available commands")
        print("  /list      - List existing approaches")
        print("  /load      - Load an existing approach")
        print("  /new       - Start a new approach")
        print("  /status    - Show current approach status")
        print("  /auto      - Start auto mode (AI-driven evaluation)")
        print("  /quit      - Exit")
        print()

    def print_help(self):
        """Print help message."""
        print()
        print("Available Commands:")
        print("  /help        - Show this help message")
        print("  /list        - List all existing approaches")
        print("  /load        - Load an existing approach")
        print("  /new         - Start a new approach")
        print("  /status      - Show current approach status and stats")
        print()
        print("Auto Mode (AI-driven evaluation):")
        print("  /auto        - Start auto mode")
        print("  /auto-stop   - Stop auto mode")
        print("  /auto-pause  - Pause auto mode")
        print("  /auto-resume - Resume auto mode")
        print("  /auto-model  - Set auto mode model")
        print()
        print("Hypergraph Tools:")
        print("  /validate    - Run type checker on hypergraph")
        print("  /cleanup     - Remove unreachable nodes from hypergraph")
        print("  /history     - View hypergraph version history")
        print("  /restore     - Restore a previous hypergraph version")
        print()
        print("  /quit        - Exit the CLI")
        print()

    def start_new_approach(self):
        """Guide user through starting a new approach."""
        print("\nLet's start a new approach!")
        print()

        # Get approach name
        name = input("What would you like to call this approach? ").strip()
        if not name:
            print("Approach name cannot be empty.")
            return

        # Get initial claim/hypothesis
        print()
        print("What idea or claim would you like to evaluate?")
        print("Example: 'We can detect neural signals using ultrasound'")
        claim = input("> ").strip()
        if not claim:
            print("Claim cannot be empty.")
            return

        # Optional description
        print()
        description = input("Brief description (optional): ").strip()

        # Create approach
        try:
            result = self.orchestrator.start_approach(name, claim, description)
            print()
            print(f"✓ Created approach: {name}")
            print(f"  Folder: {result['session']['folder']}")
            print(f"  Path: {result['session']['path']}")
            print()
            print("Initial hypergraph created with your hypothesis.")
            print()
        except Exception as e:
            print(f"Error creating approach: {e}")

    def list_approaches(self):
        """List all existing approaches."""
        approaches_dir = self.orchestrator.config.approaches_dir

        if not approaches_dir.exists():
            print("\nNo approaches directory found.")
            return

        approaches = []
        for approach_dir in approaches_dir.iterdir():
            if not approach_dir.is_dir():
                continue

            hypergraph_file = approach_dir / "hypergraph.json"
            if hypergraph_file.exists():
                try:
                    with open(hypergraph_file) as f:
                        data = json.load(f)
                        name = data.get("metadata", {}).get("name", approach_dir.name)
                        description = data.get("metadata", {}).get("description", "")
                        last_updated = data.get("metadata", {}).get("last_updated", "")
                        approaches.append({
                            "folder": approach_dir.name,
                            "name": name,
                            "description": description,
                            "last_updated": last_updated
                        })
                except Exception:
                    continue

        if not approaches:
            print("\nNo approaches found.")
            print("Use /new to start a new approach.")
            return

        print("\nExisting Approaches:")
        print("-" * 70)
        for i, approach in enumerate(sorted(approaches, key=lambda a: a['last_updated'], reverse=True), 1):
            print(f"{i}. {approach['name']}")
            print(f"   Folder: {approach['folder']}")
            if approach['description']:
                print(f"   Description: {approach['description'][:60]}...")
            print(f"   Last updated: {approach['last_updated']}")
            print()

    def load_approach(self):
        """Load an existing approach."""
        approaches_dir = self.orchestrator.config.approaches_dir

        if not approaches_dir.exists():
            print("\nNo approaches directory found.")
            return

        # Get list of approaches
        approaches = []
        for approach_dir in approaches_dir.iterdir():
            if not approach_dir.is_dir():
                continue

            hypergraph_file = approach_dir / "hypergraph.json"
            if hypergraph_file.exists():
                approaches.append(approach_dir)

        if not approaches:
            print("\nNo approaches found.")
            print("Use /new to start a new approach.")
            return

        # Show list
        print("\nAvailable Approaches:")
        for i, approach_dir in enumerate(sorted(approaches, key=lambda d: d.name), 1):
            print(f"{i}. {approach_dir.name}")

        # Get selection
        print()
        try:
            selection = input("Select approach number (or press Enter to cancel): ").strip()
            if not selection:
                print("Cancelled.")
                return

            idx = int(selection) - 1
            if idx < 0 or idx >= len(approaches):
                print("Invalid selection.")
                return

            selected = sorted(approaches, key=lambda d: d.name)[idx]

            # Load the approach
            result = self.orchestrator.load_approach(selected)

            print()
            print(f"✓ Loaded approach: {result['session']['name']}")
            print(f"  Folder: {result['session']['folder']}")
            print()

            # Show current stats
            status = self.orchestrator.get_status()
            if status.get('stats'):
                stats = status['stats']
                print(f"Current state:")
                print(f"  Claims: {stats['num_claims']}")
                print(f"  Implications: {stats['num_implications']}")
                print()

        except ValueError:
            print("Invalid number.")
        except Exception as e:
            print(f"Error loading approach: {e}")

    def show_status(self):
        """Show current status."""
        status = self.orchestrator.get_status()

        if not status['active']:
            print("\nNo active approach.")
            print("Use /new to start a new approach.")
            print()
            return

        print()
        print(f"Approach: {status['approach']}")
        print(f"Folder: {status['folder']}")
        print(f"Turns: {status['turns']}")
        print()
        print("Hypergraph Statistics:")
        stats = status['stats']
        print(f"  Claims: {stats['num_claims']}")
        print(f"  Implications: {stats['num_implications']}")
        print(f"  Claims with evidence: {stats['claims_with_evidence']}")
        print(f"  Average score: {stats['avg_score']:.1f}/10")
        print(f"  Score range: {stats['min_score']:.1f} - {stats['max_score']:.1f}")
        print(f"  Critical blockers: {stats['critical_blockers']}")
        print()

        if self.auto_state.active:
            print("Auto Mode: ACTIVE")
            print(f"  Model: {self.auto_state.model}")
            print(f"  Turn: {self.auto_state.turn_count}/{self.auto_state.max_turns}")
            print(f"  Status: {'PAUSED' if self.auto_state.paused else 'RUNNING'}")
            print()

    def validate_hypergraph(self):
        """Validate current hypergraph."""
        status = self.orchestrator.get_status()
        if not status['active']:
            print("\nNo active approach to validate.")
            return

        print("\nValidating hypergraph...")
        result = self.orchestrator.validate_hypergraph()

        if result['valid']:
            print("✓ Hypergraph is valid!")
        else:
            print("✗ Validation failed:")
            for error in result['errors']:
                print(f"  ERROR: {error}")

        if result['warnings']:
            print("\nWarnings:")
            for warning in result['warnings']:
                print(f"  WARNING: {warning}")

        print()

    def cleanup_hypergraph(self):
        """Remove unreachable nodes from hypergraph."""
        status = self.orchestrator.get_status()
        if not status['active']:
            print("\nNo active approach to clean up.")
            return

        print("\nRunning cleanup (removing unreachable nodes)...")

        try:
            unreachable = self.orchestrator.hypergraph_mgr.remove_unreachable_nodes()

            if unreachable:
                print(f"✓ Removed {len(unreachable)} unreachable node(s):")
                for node_id in unreachable:
                    print(f"  - {node_id}")
            else:
                print("✓ No unreachable nodes found. Hypergraph is clean!")
        except Exception as e:
            print(f"Error during cleanup: {e}")

        print()

    def show_history(self):
        """Show version history of hypergraph."""
        status = self.orchestrator.get_status()
        if not status['active']:
            print("\nNo active approach.")
            return

        print("\nHypergraph Version History:")
        print("-" * 70)

        try:
            versions = self.orchestrator.hypergraph_mgr.get_history()

            if not versions:
                print("No history found.")
                print()
                return

            for i, version in enumerate(reversed(versions), 1):
                print(f"{i}. {version['timestamp']}")
                print(f"   File: {version['filename']}")
                print()

            print(f"Total versions: {len(versions)}")
            print("Use /restore to revert to a previous version")

        except Exception as e:
            print(f"Error reading history: {e}")

        print()

    def restore_version(self):
        """Restore a previous version of the hypergraph."""
        status = self.orchestrator.get_status()
        if not status['active']:
            print("\nNo active approach.")
            return

        try:
            versions = self.orchestrator.hypergraph_mgr.get_history()

            if not versions:
                print("\nNo history available to restore.")
                return

            print("\nAvailable Versions:")
            for i, version in enumerate(reversed(versions), 1):
                print(f"{i}. {version['timestamp']}")

            print()
            selection = input("Select version number to restore (or press Enter to cancel): ").strip()

            if not selection:
                print("Cancelled.")
                return

            idx = int(selection) - 1
            if idx < 0 or idx >= len(versions):
                print("Invalid selection.")
                return

            selected = list(reversed(versions))[idx]

            confirm = input(f"Restore version from {selected['timestamp']}? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Cancelled.")
                return

            self.orchestrator.hypergraph_mgr.restore_version(selected['filename'])
            print(f"\n✓ Restored hypergraph to version from {selected['timestamp']}")

        except ValueError:
            print("Invalid number.")
        except Exception as e:
            print(f"Error restoring version: {e}")

        print()

    # --- Auto Mode ---

    def _ensure_openrouter_client(self) -> bool:
        """Ensure OpenRouter client is initialized."""
        if self.openrouter_client is None:
            try:
                self.openrouter_client = OpenRouterClient()
                return True
            except Exception as e:
                print(f"Error initializing OpenRouter client: {e}")
                print("Make sure OPENROUTER_API_KEY is set.")
                return False
        return True

    def set_auto_model(self, command: str):
        """Set the model for auto mode."""
        parts = command.split(maxsplit=1)
        if len(parts) < 2:
            print()
            print(f"Current auto mode model: {self.auto_state.model}")
            print()
            print("Usage: /auto-model <model-id>")
            print("Example: /auto-model google/gemini-2.5-pro-preview")
            print("Example: /auto-model anthropic/claude-sonnet-4")
            print()
            return

        self.auto_state.model = parts[1].strip()
        print(f"\n✓ Auto mode model set to: {self.auto_state.model}\n")

    async def _get_auto_agent_response(self, hypergraph: dict) -> str:
        """Get next message from the Auto agent."""
        system_prompt = AUTO_AGENT_SYSTEM_PROMPT.format(
            hypothesis=self.auto_state.hypothesis,
            hypergraph=json.dumps(hypergraph, indent=2)
        )

        messages = [{"role": "system", "content": system_prompt}] + self.auto_state.conversation_history
        return await self.openrouter_client.chat(messages, self.auto_state.model)

    async def _run_auto_turn(self) -> bool:
        """Run a single auto mode turn. Returns False if should stop."""
        if not self.auto_state.active or self.auto_state.paused:
            return False

        if self.auto_state.turn_count >= self.auto_state.max_turns:
            print(f"\n[AUTO] Reached max turns ({self.auto_state.max_turns})")
            return False

        status = self.orchestrator.get_status()
        if not status['active']:
            print("\n[AUTO] No active approach")
            return False

        # Load current hypergraph
        hypergraph_path = Path(status['folder']) / "hypergraph.json"
        with open(hypergraph_path) as f:
            hypergraph = json.load(f)

        # Get Auto agent's next message
        self.auto_state.turn_count += 1
        print(f"\n{'='*70}")
        print(f"[AUTO TURN {self.auto_state.turn_count}/{self.auto_state.max_turns}]")
        print(f"{'='*70}")

        try:
            auto_message = await self._get_auto_agent_response(hypergraph)
        except Exception as e:
            print(f"\n[AUTO] Error getting auto agent response: {e}")
            return False

        print(f"\n[AUTO AGENT → CLAUDE]:")
        print("-" * 40)
        print(auto_message)
        print("-" * 40)

        # Add to history
        self.auto_state.conversation_history.append({"role": "assistant", "content": auto_message})

        # Check if still active
        if not self.auto_state.active or self.auto_state.paused:
            return False

        # Send to Claude
        print(f"\n[CLAUDE RESPONSE]:")
        print("-" * 40)

        claude_response = ""
        system_prompt = self.orchestrator.get_system_prompt()

        async for event in self.orchestrator.claude_client.query_stream(
            auto_message,
            system_prompt=system_prompt
        ):
            if isinstance(event, TextEvent):
                claude_response += event.text
                print(event.text, end="", flush=True)
            elif isinstance(event, ToolUseEvent):
                print(f"\n[TOOL: {event.tool_name}]", flush=True)
            elif isinstance(event, ToolResultEvent):
                result_preview = str(event.result)[:200]
                print(f"[RESULT: {result_preview}...]", flush=True)
            elif isinstance(event, ErrorEvent):
                print(f"\n[ERROR: {event.error}]", flush=True)

        print()
        print("-" * 40)

        # Add Claude's response to history
        self.auto_state.conversation_history.append({"role": "user", "content": claude_response})

        return True

    async def run_auto_mode(self):
        """Run auto mode loop."""
        status = self.orchestrator.get_status()
        if not status['active']:
            print("\nNo active approach. Use /load or /new first.")
            return

        if not self._ensure_openrouter_client():
            return

        # Get hypothesis from hypergraph
        hypergraph_path = Path(status['folder']) / "hypergraph.json"
        with open(hypergraph_path) as f:
            hypergraph = json.load(f)

        self.auto_state.hypothesis = hypergraph.get("metadata", {}).get("hypothesis", "")
        if not self.auto_state.hypothesis:
            claims = hypergraph.get("claims", [])
            root_claims = [c for c in claims if c.get("id") == "hypothesis"]
            if root_claims:
                self.auto_state.hypothesis = root_claims[0].get("text", "")

        if not self.auto_state.hypothesis:
            print("\nCouldn't find hypothesis in hypergraph.")
            return

        # Reset state
        self.auto_state.active = True
        self.auto_state.paused = False
        self.auto_state.turn_count = 0
        self.auto_state.conversation_history = []

        print()
        print("=" * 70)
        print("  AUTO MODE STARTED")
        print("=" * 70)
        print(f"Model: {self.auto_state.model}")
        print(f"Max turns: {self.auto_state.max_turns}")
        print(f"Hypothesis: {self.auto_state.hypothesis[:100]}...")
        print()
        print("Press Ctrl+C to pause. Use /auto-stop to stop.")
        print("=" * 70)

        try:
            while await self._run_auto_turn():
                # Brief delay between turns
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.auto_state.paused = True
            print("\n\n[AUTO] Paused. Use /auto-resume to continue or /auto-stop to stop.")

        if not self.auto_state.paused:
            self.auto_state.active = False
            print(f"\n[AUTO] Completed after {self.auto_state.turn_count} turns.")

    def start_auto_mode(self):
        """Start auto mode."""
        asyncio.run(self.run_auto_mode())

    def stop_auto_mode(self):
        """Stop auto mode."""
        if not self.auto_state.active:
            print("\nAuto mode is not running.")
            return

        self.auto_state.active = False
        self.auto_state.paused = False
        print(f"\n✓ Auto mode stopped after {self.auto_state.turn_count} turns.")

    def pause_auto_mode(self):
        """Pause auto mode."""
        if not self.auto_state.active:
            print("\nAuto mode is not running.")
            return

        self.auto_state.paused = True
        print("\n✓ Auto mode paused. Use /auto-resume to continue.")

    def resume_auto_mode(self):
        """Resume auto mode."""
        if not self.auto_state.active:
            print("\nAuto mode is not active. Use /auto to start.")
            return

        if not self.auto_state.paused:
            print("\nAuto mode is already running.")
            return

        self.auto_state.paused = False
        print("\nResuming auto mode...")
        asyncio.run(self._continue_auto_mode())

    async def _continue_auto_mode(self):
        """Continue auto mode after resume."""
        try:
            while await self._run_auto_turn():
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.auto_state.paused = True
            print("\n\n[AUTO] Paused. Use /auto-resume to continue or /auto-stop to stop.")

        if not self.auto_state.paused:
            self.auto_state.active = False
            print(f"\n[AUTO] Completed after {self.auto_state.turn_count} turns.")

    def handle_command(self, command: str) -> bool:
        """Handle slash commands. Returns True to continue, False to quit."""
        cmd = command.lower().strip()

        if cmd == "/quit" or cmd == "/exit":
            return False
        elif cmd == "/help":
            self.print_help()
        elif cmd == "/list":
            self.list_approaches()
        elif cmd == "/load":
            self.load_approach()
        elif cmd == "/new":
            self.start_new_approach()
        elif cmd == "/status":
            self.show_status()
        elif cmd == "/validate":
            self.validate_hypergraph()
        elif cmd == "/cleanup":
            self.cleanup_hypergraph()
        elif cmd == "/history":
            self.show_history()
        elif cmd == "/restore":
            self.restore_version()
        elif cmd == "/auto":
            self.start_auto_mode()
        elif cmd == "/auto-stop":
            self.stop_auto_mode()
        elif cmd == "/auto-pause":
            self.pause_auto_mode()
        elif cmd == "/auto-resume":
            self.resume_auto_mode()
        elif cmd.startswith("/auto-model"):
            self.set_auto_model(command)
        else:
            print(f"Unknown command: {command}")
            print("Type /help for available commands")

        return True

    def run(self):
        """Run the CLI REPL."""
        self.print_banner()

        print("\nType /help for commands, or describe what you'd like to do.")
        print()

        while self.running:
            try:
                user_input = input("> ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith('/'):
                    if not self.handle_command(user_input):
                        break
                    continue

                # Process input with Claude
                status = self.orchestrator.get_status()

                if not status['active']:
                    print("\nNo active approach. Use /new or /load first.")
                    print()
                    continue

                print()
                print("Claude: ", end="", flush=True)

                try:
                    response = self.orchestrator.process_user_input(user_input)

                    if response.cost_usd:
                        print(f"\n(Cost: ${response.cost_usd:.4f})")

                except Exception as e:
                    print(f"\nError: {e}")

                print()

            except KeyboardInterrupt:
                print("\n\nInterrupted. Type /quit to exit.")
            except EOFError:
                break

        print("\nGoodbye!")


def main():
    """Entry point for CLI."""
    cli = AgentCLI()
    cli.run()


if __name__ == "__main__":
    main()
