from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLINICAL_UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"

def validate_uploads_path(requested_path: Path) -> Path:
    # Ensure uploads root exists
    CLINICAL_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Resolve absolute paths
    resolved_root = CLINICAL_UPLOADS_DIR.resolve()
    
    # If requested_path starts with data/uploads, resolve it relative to PROJECT_ROOT
    # to catch any attempts to go up and out. Otherwise, resolve relative to CLINICAL_UPLOADS_DIR.
    parts = requested_path.parts
    if len(parts) >= 2 and parts[0] == "data" and parts[1] == "uploads":
        resolved_requested = (PROJECT_ROOT / requested_path).resolve()
    elif len(parts) >= 1 and parts[0] == "uploads":
        resolved_requested = (PROJECT_ROOT / "data" / requested_path).resolve()
    else:
        resolved_requested = (CLINICAL_UPLOADS_DIR / requested_path).resolve()
    
    try:
        resolved_requested.relative_to(resolved_root)
    except ValueError:
        raise ValueError(f"Directory traversal detected for: {requested_path}")
        
    return resolved_requested
