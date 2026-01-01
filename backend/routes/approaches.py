"""Approach management endpoints."""

import json
import re
from datetime import datetime
from pathlib import Path

import anthropic
from fastapi import APIRouter, HTTPException

from agent_system import HypergraphManager
from agent_system.hypergraph.typecheck import read_source_lines

from backend.models import CreateApproachRequest, ApproachInfo, GenerateNameRequest, NoteRequest, Note
from backend.services import get_orchestrator, notify_hypergraph_update

router = APIRouter(prefix="/api", tags=["approaches"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    orchestrator = get_orchestrator()
    return {"status": "healthy", "orchestrator_ready": orchestrator is not None}


@router.post("/generate-name")
async def generate_name(request: GenerateNameRequest) -> dict:
    """Generate a short name for an approach using Claude Haiku."""
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": f"Generate a short (2-4 word) name for this research idea. Return ONLY the name, nothing else. Use lowercase with hyphens between words.\n\nIdea: {request.hypothesis}"
            }]
        )
        name = response.content[0].text.strip()
        # Sanitize: lowercase, replace spaces/special chars with hyphens
        name = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:50]
        return {"name": name}
    except Exception as e:
        # Fallback to simple slug
        name = re.sub(r'[^a-z0-9]+', '-', request.hypothesis.lower())[:30].strip('-')
        return {"name": name, "error": str(e)}


@router.get("/approaches")
async def list_approaches() -> list[ApproachInfo]:
    """List all existing approaches."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approaches_dir = orchestrator.config.approaches_dir
    if not approaches_dir.exists():
        return []

    approaches = []
    for approach_dir in approaches_dir.iterdir():
        if not approach_dir.is_dir():
            continue

        hypergraph_file = approach_dir / "hypergraph.json"
        if hypergraph_file.exists():
            try:
                with open(hypergraph_file) as f:
                    data = json.load(f)
                    metadata = data.get("metadata", {})
                    approaches.append(ApproachInfo(
                        name=metadata.get("name", approach_dir.name),
                        folder=approach_dir.name,
                        description=metadata.get("description", ""),
                        last_updated=metadata.get("last_updated", ""),
                        num_claims=len(data.get("claims", [])),
                        num_implications=len(data.get("implications", [])),
                    ))
            except Exception:
                continue

    return sorted(approaches, key=lambda a: a.last_updated, reverse=True)


@router.post("/approaches")
async def create_approach(request: CreateApproachRequest) -> dict:
    """Create a new approach."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        result = orchestrator.start_approach(
            name=request.name,
            initial_claim=request.hypothesis,
            description=request.description or ""
        )
        return {
            "success": True,
            "name": result["session"]["name"],
            "folder": result["session"]["folder"],
            "path": result["session"]["path"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/approaches/{folder}/load")
async def load_approach(folder: str) -> dict:
    """Load an existing approach."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approach_dir = orchestrator.config.approaches_dir / folder
    if not approach_dir.exists():
        raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

    try:
        result = orchestrator.load_approach(approach_dir)
        return {
            "success": True,
            "name": result["session"]["name"],
            "folder": result["session"]["folder"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/approaches/{folder}/hypergraph")
async def get_hypergraph(folder: str) -> dict:
    """Get the hypergraph JSON for an approach with computed propagated scores."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    hypergraph_path = orchestrator.config.approaches_dir / folder / "hypergraph.json"
    if not hypergraph_path.exists():
        raise HTTPException(status_code=404, detail=f"Hypergraph not found for '{folder}'")

    with open(hypergraph_path) as f:
        hypergraph = json.load(f)

    # Always compute costs and warnings before serving
    mgr = HypergraphManager(orchestrator.config.approaches_dir / folder)
    mgr.apply_costs_to_claims(hypergraph)
    hypergraph['warnings'] = mgr.compute_warnings(hypergraph)

    return hypergraph


@router.get("/approaches/{folder}/status")
async def get_approach_status(folder: str) -> dict:
    """Get status and stats for an approach."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approach_dir = orchestrator.config.approaches_dir / folder
    if not approach_dir.exists():
        raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

    mgr = HypergraphManager(approach_dir)
    try:
        stats = mgr.get_stats()
        return {
            "folder": folder,
            "stats": stats,
            "is_active": (
                orchestrator.current_session is not None and
                str(orchestrator.current_session.approach_dir) == str(approach_dir)
            )
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/approaches/{folder}/cleanup")
async def cleanup_hypergraph(folder: str) -> dict:
    """Remove unreachable nodes from the hypergraph."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approach_dir = orchestrator.config.approaches_dir / folder
    if not approach_dir.exists():
        raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

    mgr = HypergraphManager(approach_dir)
    try:
        removed = mgr.remove_unreachable_nodes()
        await notify_hypergraph_update(folder)
        return {
            "success": True,
            "removed_count": len(removed),
            "removed_nodes": removed
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/approaches/{folder}/claims/{claim_id}")
async def delete_claim(folder: str, claim_id: str) -> dict:
    """Delete a claim and its related implications."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approach_dir = orchestrator.config.approaches_dir / folder
    if not approach_dir.exists():
        raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

    mgr = HypergraphManager(approach_dir)
    try:
        result = mgr.delete_claim(claim_id)
        await notify_hypergraph_update(folder)
        return {
            "success": True,
            "deleted_claim_id": claim_id,
            "deleted_implications_count": len(result['deleted_implications']),
            "validation": result.get('validation', {})
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/approaches/{folder}/source-code")
async def get_source_code(folder: str, source: str, lines: str) -> dict:
    """
    Fetch source code from a file within an approach directory.

    Args:
        folder: The approach folder name
        source: Relative path to the source file within the approach
        lines: Line specification (e.g., "3-18" or "56-64, 152-156")

    Returns:
        {"code": "..."} or error
    """
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approach_dir = orchestrator.config.approaches_dir / folder
    if not approach_dir.exists():
        raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

    # Resolve the source file path relative to the approach directory
    source_path = approach_dir / source

    # Security: ensure path is within approach directory
    try:
        source_path = source_path.resolve()
        approach_dir_resolved = approach_dir.resolve()
        if not str(source_path).startswith(str(approach_dir_resolved)):
            raise HTTPException(status_code=400, detail="Invalid source path")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid source path")

    if not source_path.exists():
        raise HTTPException(status_code=404, detail=f"Source file not found: {source}")

    code = read_source_lines(source_path, lines)
    if code is None:
        raise HTTPException(status_code=400, detail=f"Could not read lines {lines} from {source}")

    return {"code": code}


def _load_notes(approach_dir: Path) -> dict:
    """Load notes.json from approach directory."""
    notes_path = approach_dir / "notes.json"
    if notes_path.exists():
        with open(notes_path) as f:
            return json.load(f)
    return {"notes": {}}


def _save_notes(approach_dir: Path, data: dict) -> None:
    """Save notes.json to approach directory."""
    notes_path = approach_dir / "notes.json"
    with open(notes_path, "w") as f:
        json.dump(data, f, indent=2)


def _get_current_content(hypergraph: dict, item_id: str) -> tuple[str | None, str]:
    """Get the current content of a claim or implication.

    Returns (content, item_type) where item_type is 'claim' or 'implication'.
    Returns (None, '') if not found.
    """
    # Check claims first
    for claim in hypergraph.get("claims", []):
        if claim["id"] == item_id:
            return claim.get("text", ""), "claim"

    # Check implications
    for impl in hypergraph.get("implications", []):
        if impl["id"] == item_id:
            formula = f"({', '.join(impl['premises'])}) → {impl['conclusion']}"
            return formula, "implication"

    return None, ""


def _enrich_notes_with_status(notes_data: dict, hypergraph: dict) -> dict[str, Note]:
    """Add item_exists and content_changed flags to each note."""
    enriched = {}
    for item_id, note_data in notes_data.get("notes", {}).items():
        current_content, _ = _get_current_content(hypergraph, item_id)
        item_exists = current_content is not None
        content_changed = item_exists and current_content != note_data.get("original_content", "")

        enriched[item_id] = Note(
            text=note_data["text"],
            original_content=note_data["original_content"],
            created_at=note_data["created_at"],
            item_exists=item_exists,
            content_changed=content_changed,
        )
    return enriched


@router.get("/approaches/{folder}/notes")
async def get_notes(folder: str) -> dict[str, Note]:
    """Get all notes for an approach with enriched status."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approach_dir = orchestrator.config.approaches_dir / folder
    if not approach_dir.exists():
        raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

    hypergraph_path = approach_dir / "hypergraph.json"
    if not hypergraph_path.exists():
        return {}

    with open(hypergraph_path) as f:
        hypergraph = json.load(f)

    notes_data = _load_notes(approach_dir)
    return _enrich_notes_with_status(notes_data, hypergraph)


@router.post("/approaches/{folder}/notes/{item_id}")
async def create_or_update_note(folder: str, item_id: str, request: NoteRequest) -> Note:
    """Create or update a note for a claim or implication."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approach_dir = orchestrator.config.approaches_dir / folder
    if not approach_dir.exists():
        raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

    hypergraph_path = approach_dir / "hypergraph.json"
    if not hypergraph_path.exists():
        raise HTTPException(status_code=404, detail="Hypergraph not found")

    with open(hypergraph_path) as f:
        hypergraph = json.load(f)

    # Verify the item exists
    current_content, item_type = _get_current_content(hypergraph, item_id)
    if current_content is None:
        raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found in hypergraph")

    notes_data = _load_notes(approach_dir)

    # Create or update the note
    notes_data["notes"][item_id] = {
        "text": request.text,
        "original_content": request.original_content,
        "created_at": datetime.now().isoformat(),
    }

    _save_notes(approach_dir, notes_data)

    return Note(
        text=request.text,
        original_content=request.original_content,
        created_at=notes_data["notes"][item_id]["created_at"],
        item_exists=True,
        content_changed=current_content != request.original_content,
    )


@router.delete("/approaches/{folder}/notes/{item_id}")
async def delete_note(folder: str, item_id: str) -> dict:
    """Delete a note."""
    orchestrator = get_orchestrator()
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    approach_dir = orchestrator.config.approaches_dir / folder
    if not approach_dir.exists():
        raise HTTPException(status_code=404, detail=f"Approach '{folder}' not found")

    notes_data = _load_notes(approach_dir)

    if item_id not in notes_data.get("notes", {}):
        raise HTTPException(status_code=404, detail=f"Note for '{item_id}' not found")

    del notes_data["notes"][item_id]
    _save_notes(approach_dir, notes_data)

    return {"success": True, "deleted": item_id}
