"""
Agent CLI - Command-line interface for hypergraph collaboration.

This is a simple REPL-style interface for working with the agent system.
In the future, this will integrate with Headless Claude Code.
"""

import sys
from pathlib import Path
from typing import Optional

from .agent_orchestrator import AgentOrchestrator
from .config import AgentConfig


class AgentCLI:
    """Command-line interface for agent system."""

    def __init__(self):
        self.orchestrator = AgentOrchestrator(AgentConfig.from_env())
        self.running = True

    def print_banner(self):
        """Print welcome banner."""
        print("=" * 70)
        print("  Hypergraph Collaboration System")
        print("  Evaluate ideas through simulation and structured reasoning")
        print("=" * 70)
        print()
        print("Commands:")
        print("  /help      - Show available commands")
        print("  /status    - Show current approach status")
        print("  /validate  - Validate current hypergraph")
        print("  /viz       - Instructions for viewing hypergraph")
        print("  /quit      - Exit")
        print()

    def print_help(self):
        """Print help message."""
        print()
        print("Available Commands:")
        print("  /help      - Show this help message")
        print("  /status    - Show current approach status and stats")
        print("  /validate  - Run type checker on hypergraph")
        print("  /viz       - Show how to visualize the hypergraph")
        print("  /quit      - Exit the CLI")
        print()
        print("When you have an active approach, you can:")
        print("  - Describe what you want to investigate")
        print("  - Ask questions about the current hypergraph")
        print("  - Request simulations to test claims")
        print()
        print("(Note: Full agent integration with Claude Code coming soon!)")
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
            print("Next steps:")
            print("  1. Read the current hypergraph")
            print("  2. Break down the hypothesis into testable claims")
            print("  3. Write simulations to evaluate key assumptions")
            print("  4. Update the hypergraph with evidence")
            print()
            print("System prompt for agent:")
            print("-" * 70)
            print(result['system_prompt'][:500] + "...")
            print("-" * 70)
            print()
        except Exception as e:
            print(f"Error creating approach: {e}")

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

    def show_viz_instructions(self):
        """Show how to visualize hypergraph."""
        status = self.orchestrator.get_status()
        if not status['active']:
            print("\nNo active approach to visualize.")
            return

        folder = status['folder']
        approach_name = Path(folder).name

        print()
        print("To visualize your hypergraph:")
        print()
        print("1. Start a web server from the project root:")
        print("   python -m http.server 8765")
        print()
        print("2. Open in browser:")
        print(f"   http://localhost:8765/entailment_hypergraph/?graph=approaches/{approach_name}/hypergraph.json")
        print()
        print("You'll see an interactive graph where you can:")
        print("  - Click nodes to see claims and evidence")
        print("  - Expand/collapse to view at different levels")
        print("  - See color-coded scores (green=good, red=bad)")
        print()

    def handle_command(self, command: str) -> bool:
        """
        Handle slash commands.

        Returns:
            True to continue, False to quit
        """
        command = command.lower().strip()

        if command == "/quit" or command == "/exit":
            return False
        elif command == "/help":
            self.print_help()
        elif command == "/new":
            self.start_new_approach()
        elif command == "/status":
            self.show_status()
        elif command == "/validate":
            self.validate_hypergraph()
        elif command == "/viz":
            self.show_viz_instructions()
        else:
            print(f"Unknown command: {command}")
            print("Type /help for available commands")

        return True

    def run(self):
        """Run the CLI REPL."""
        self.print_banner()

        # Check if user wants to start immediately
        start = input("Start a new approach? (y/n): ").strip().lower()
        if start == 'y':
            self.start_new_approach()

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

                # For now, just acknowledge non-command input
                # TODO: This is where we'll integrate Headless Claude Code
                print()
                print("Note: Full agent conversation not yet implemented.")
                print("      This will integrate with Headless Claude Code soon.")
                print()
                print("For now, you can:")
                print("  - Manually edit hypergraph.json in your approach folder")
                print("  - Write simulations in the simulations/ folder")
                print("  - Use /validate to check your hypergraph")
                print("  - Use /viz to view it interactively")
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
