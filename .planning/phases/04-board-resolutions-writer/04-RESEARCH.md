# Phase 04: Board Resolutions & Resolution Writer - Research

**Researched:** 2026-03-04
**Domain:** Digital signature workflow, resolution management UI, PDF export, AI-assisted resolution drafting
**Confidence:** HIGH

## Summary

Phase 04 builds a dedicated board resolution workflow on top of the existing `Decision` model (which already has `type="resolution"`, `resolution_number`, and `document_id` fields). The work breaks into four areas: (1) a new `ResolutionSignature` model and API for digital signatures, (2) a dedicated Resolutions section in the sidebar and frontend pages that filter decisions by `type=resolution`, (3) PDF/printable export of signed resolutions, and (4) a Resolution Writer agent that drafts resolution documents via the agent infrastructure built in Phase 01.

The existing codebase is well-prepared. The `Decision` model already supports resolutions with `type="resolution"`, `resolution_number`, and `document_id` FK to the documents table. The decisions API already accepts `type` as a filter parameter (`GET /decisions?type=resolution`). The frontend decisions page already has a `typeConfig` entry for `resolution` with its own color scheme. What is missing is: signature recording, signature status display, a dedicated Resolutions page (vs. seeing them mixed with votes/consents), export functionality, and the Resolution Writer agent.

**Primary recommendation:** Add a `resolution_signatures` table via Alembic migration, create `/api/resolutions/` endpoints that wrap the existing decisions API with resolution-specific signature logic, add a `/resolutions` page and sidebar entry, use WeasyPrint for PDF export, and register a Resolution Writer agent configuration with tools that call the board's own REST API.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RES-01 | Board resolutions appear as a dedicated section (building on existing decisions with type=resolution) | Decision model already has type=resolution. New sidebar entry + /resolutions page filtering decisions by type. Existing API already supports `?type=resolution` filter. |
| RES-02 | Board members can digitally sign a resolution (name + timestamp + IP) | New ResolutionSignature model + POST /api/resolutions/{id}/sign endpoint. Captures member_id, signed_at, ip_address, signature_hash. |
| RES-03 | Resolution shows signature status (who signed, who hasn't) | GET endpoint returns signature list with signed/pending status. Frontend signature status panel on resolution detail page. |
| RES-04 | Chair/admin can view and export signed resolutions | WeasyPrint HTML-to-PDF conversion. Export endpoint at GET /api/resolutions/{id}/export?format=pdf. Printable HTML fallback. |
| BUILT-03 | Resolution Writer agent can draft resolution documents and link them to decisions | Agent config in DB with system prompt, tools: create_resolution, draft_resolution_document, link_document_to_resolution. Uses agent infrastructure from Phase 01. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | >=2.0.25 | ResolutionSignature model, queries | Already in project stack. Mapped column pattern used throughout codebase. |
| Alembic | >=1.13.1 | Database migration for resolution_signatures table | Already in project stack. Sequential versioned migrations (001-004 exist). |
| WeasyPrint | >=62.0 | HTML-to-PDF conversion for resolution export | Best-in-class HTML/CSS to PDF. No browser engine needed. Renders via Jinja2 HTML templates. Actively maintained. |
| Jinja2 | >=3.1 | HTML templates for resolution export | Already a FastAPI/Starlette dependency. Used to render resolution export templates. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fastapi | >=0.135.0 | API endpoints, StreamingResponse for PDF | Already in stack. Use StreamingResponse for PDF byte streaming. |
| pydantic | >=2.5 | Request/response schemas for signature API | Already in stack. |
| litellm | >=1.80 | Resolution Writer agent LLM calls | Added in Phase 01. Agent infrastructure. |
| httpx | >=0.26.0 | Agent tool internal API calls | Already in stack. Tools call board REST API. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| WeasyPrint | ReportLab | ReportLab gives pixel-level control but requires imperative layout code. WeasyPrint uses HTML/CSS which is faster to develop and matches the app's existing web styling. Board resolutions are structured text documents, not complex graphics -- HTML/CSS is ideal. |
| WeasyPrint | Browser-based PDF (Playwright) | Already have Playwright MCP, but it requires a browser instance. WeasyPrint is a pure Python library with no browser dependency, much lighter for server-side PDF generation. |
| Printable HTML export | PDF only | Both should be supported. Printable HTML is simpler (CSS @media print) and works as a fallback. PDF via WeasyPrint for formal distribution. |

**Installation (new dependency):**
```bash
# In backend/requirements.txt, ADD:
weasyprint>=62.0
```

No new frontend dependencies needed. Signature UI uses existing shadcn/ui components (Button, Card, Badge, Dialog).

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── api/
│   ├── decisions.py          # EXISTING - no changes needed (already supports type filter)
│   └── resolutions.py        # NEW - resolution-specific endpoints (sign, status, export)
├── models/
│   ├── decision.py           # EXISTING - add ResolutionSignature model and relationship
│   └── __init__.py           # UPDATE - add ResolutionSignature to exports
├── templates/
│   └── resolution_export.html # NEW - Jinja2 template for PDF/print export
├── tools/
│   └── decisions.py          # NEW (or update if created in Phase 01) - resolution agent tools
└── services/
    └── resolution_export.py  # NEW - WeasyPrint PDF generation service

backend/migrations/versions/
└── 005_add_resolution_signatures.py  # NEW - Alembic migration

frontend/src/
├── app/
│   ├── resolutions/
│   │   ├── page.tsx           # NEW - dedicated resolutions list (filtered decisions)
│   │   └── [id]/
│   │       └── page.tsx       # NEW - resolution detail with signature panel + agent
│   └── decisions/
│       └── page.tsx           # EXISTING - optionally exclude type=resolution from this view
├── components/
│   ├── signature-panel.tsx    # NEW - who signed / who hasn't + sign button
│   ├── resolution-export.tsx  # NEW - export button (PDF download, print)
│   └── sidebar.tsx            # UPDATE - add "Resolutions" nav item with Stamp/Gavel icon
└── lib/
    └── api.ts                 # UPDATE - add resolutionsApi section
```

### Pattern 1: ResolutionSignature Model
**What:** A new model recording digital signatures on resolutions. Each board member can sign once per resolution.
**When to use:** Recording and querying resolution signatures.
**Example:**
```python
# Source: Following existing Vote model pattern in decision.py

from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base
from datetime import datetime

class ResolutionSignature(Base):
    """Digital signature record for a board resolution."""

    __tablename__ = "resolution_signatures"
    __table_args__ = (
        UniqueConstraint("decision_id", "member_id", name="uq_resolution_member_signature"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    decision_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False
    )
    member_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("board_members.id"), nullable=False
    )
    signed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    signature_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # SHA-256 hash of member_name + decision_id + signed_at for tamper evidence

    # Relationships
    decision: Mapped["Decision"] = relationship("Decision", back_populates="signatures")
    member: Mapped["BoardMember"] = relationship("BoardMember")
```

### Pattern 2: Signature Hash for Tamper Evidence
**What:** Generate a SHA-256 hash at signing time that ties the signer, resolution, and timestamp together. Not cryptographic non-repudiation, but provides a tamper evidence trail.
**When to use:** Every signature creation.
**Example:**
```python
import hashlib
from datetime import datetime

def generate_signature_hash(
    member_name: str,
    member_email: str,
    decision_id: int,
    signed_at: datetime,
) -> str:
    """Generate tamper-evidence hash for a resolution signature."""
    payload = f"{member_name}:{member_email}:{decision_id}:{signed_at.isoformat()}"
    return hashlib.sha256(payload.encode()).hexdigest()
```

### Pattern 3: Resolution Export with WeasyPrint
**What:** Render a Jinja2 HTML template with resolution data and signatures, then convert to PDF.
**When to use:** Chair/admin requests PDF export of a signed resolution.
**Example:**
```python
# Source: WeasyPrint API docs + FastAPI StreamingResponse pattern
from io import BytesIO
from fastapi.responses import StreamingResponse
from jinja2 import Environment, FileSystemLoader
import weasyprint

def generate_resolution_pdf(resolution_data: dict) -> bytes:
    """Render resolution HTML template and convert to PDF."""
    env = Environment(loader=FileSystemLoader("app/templates"))
    template = env.get_template("resolution_export.html")
    html_content = template.render(**resolution_data)
    pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
    return pdf_bytes

# FastAPI endpoint
@router.get("/{resolution_id}/export")
async def export_resolution(
    resolution_id: int,
    format: str = Query("pdf", regex="^(pdf|html)$"),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_chair),
):
    """Export a signed resolution as PDF or printable HTML."""
    # ... fetch resolution + signatures ...
    if format == "pdf":
        pdf_bytes = generate_resolution_pdf(resolution_data)
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="Resolution-{resolution.resolution_number}.pdf"'
            },
        )
    # HTML format: return rendered template
    html = render_resolution_html(resolution_data)
    return HTMLResponse(content=html)
```

### Pattern 4: Resolution Writer Agent Tools
**What:** The Resolution Writer agent needs tools to create decisions of type=resolution, draft a document with formal resolution language, and link the document to the decision.
**When to use:** When a user asks the Resolution Writer to draft a resolution.
**Example:**
```python
# Tool definitions for Resolution Writer agent
RESOLUTION_WRITER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_resolution",
            "description": "Create a new board resolution (decision with type=resolution)",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Resolution title"},
                    "description": {"type": "string", "description": "Resolution description/body text"},
                    "resolution_number": {"type": "string", "description": "Resolution number (e.g., '2026-001')"},
                    "meeting_id": {"type": "integer", "description": "Optional meeting ID to link to"},
                },
                "required": ["title", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_resolution_document",
            "description": "Create an HTML document with formal resolution language including WHEREAS/RESOLVED clauses",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Document title"},
                    "content_html": {"type": "string", "description": "HTML content of the resolution document"},
                },
                "required": ["title", "content_html"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "link_document_to_resolution",
            "description": "Link an existing document to a resolution decision",
            "parameters": {
                "type": "object",
                "properties": {
                    "resolution_id": {"type": "integer", "description": "Decision ID of the resolution"},
                    "document_id": {"type": "integer", "description": "Document ID to link"},
                },
                "required": ["resolution_id", "document_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_resolutions",
            "description": "List existing resolutions with their status",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["draft", "open", "closed"], "description": "Filter by status"},
                },
            },
        },
    },
]
```

### Anti-Patterns to Avoid
- **Duplicating Decision data for resolutions:** Resolutions ARE decisions with `type=resolution`. Do not create a separate `resolutions` table that copies Decision fields. Instead, add a `resolution_signatures` table and create resolution-specific API endpoints that delegate to the existing Decision model.
- **Direct database access in agent tools:** Tools must call the board's REST API via httpx, not query the database directly. This preserves auth checks, validation, and audit logging.
- **Storing signatures as JSON blobs:** Each signature should be its own row in `resolution_signatures` with proper FK constraints, not a JSON array on the Decision model.
- **Generating PDFs on every page load:** PDF generation is expensive. Only generate on explicit export request, never as part of a list or detail view.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF generation | Custom binary PDF builder | WeasyPrint with Jinja2 HTML templates | PDF format is complex. WeasyPrint handles pagination, fonts, headers/footers, page margins. HTML/CSS templates are maintainable. |
| IP address capture | Manual header parsing | `request.client.host` from FastAPI Request | FastAPI's Request object handles proxy headers and connection info. |
| Hash generation | Custom hashing | Python `hashlib.sha256` | Standard library, well-tested, no dependency needed. |
| Date formatting in exports | Manual string formatting | Python `datetime.strftime` + Jinja2 filters | Consistent formatting, timezone-aware. |

**Key insight:** The resolution signature system is intentionally lightweight (name + timestamp + IP, not DocuSign). Do not over-engineer with cryptographic signing infrastructure. A SHA-256 hash provides tamper evidence, and the audit log provides the legal trail.

## Common Pitfalls

### Pitfall 1: Signing a Non-Resolution Decision
**What goes wrong:** User tries to sign a decision that is type=vote or type=consent.
**Why it happens:** The signature endpoint accepts a decision_id without checking type.
**How to avoid:** Validate `decision.type == "resolution"` in the sign endpoint before recording the signature.
**Warning signs:** Test with a vote-type decision and confirm it returns 400.

### Pitfall 2: Signing Before Resolution is Closed/Approved
**What goes wrong:** Board members sign a resolution that hasn't been voted on yet.
**Why it happens:** No status check on the decision.
**How to avoid:** Only allow signing when `decision.status == "closed"` (voting is complete). Optionally, also require that the vote passed (yes > no).
**Warning signs:** Draft or open resolutions showing a "Sign" button.

### Pitfall 3: WeasyPrint System Dependencies
**What goes wrong:** WeasyPrint fails on deployment because it requires system-level libraries (Pango, Cairo, GDK-PixBuf).
**Why it happens:** WeasyPrint is a C-binding library, not pure Python.
**How to avoid:** Add system dependencies to Dockerfile/Railway buildpack. On Debian/Ubuntu: `apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0`. Railway supports buildpacks with Aptfile for system packages.
**Warning signs:** `ImportError: cannot import name 'ffi'` or `OSError: cannot load library 'libpango'` on deploy.

### Pitfall 4: Missing IP Address Behind Proxy
**What goes wrong:** `request.client.host` returns the proxy IP, not the user's real IP.
**Why it happens:** Railway (and most deployments) use reverse proxies.
**How to avoid:** Check `X-Forwarded-For` header first, fall back to `request.client.host`. Use a utility function.
**Warning signs:** All signatures show the same IP address (the proxy).

### Pitfall 5: Frontend Routing Collision
**What goes wrong:** `/resolutions` and `/decisions` routes conflict or the sidebar shows both as active.
**Why it happens:** The sidebar uses `pathname.startsWith(item.href)` for active state.
**How to avoid:** Resolutions use `/resolutions` path (not `/decisions/resolutions`). Sidebar active state logic already handles separate paths correctly.
**Warning signs:** Both Decisions and Resolutions highlighted in sidebar simultaneously.

### Pitfall 6: Duplicate Signatures
**What goes wrong:** A board member signs the same resolution twice.
**Why it happens:** Race condition or missing uniqueness check.
**How to avoid:** UniqueConstraint on (decision_id, member_id) in the database. Also check in the API before inserting.
**Warning signs:** Test with rapid double-click on Sign button.

## Code Examples

### Resolution List API (wrapping existing decisions endpoint)
```python
# backend/app/api/resolutions.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.member import BoardMember
from app.models.decision import Decision, ResolutionSignature
from app.api.auth import require_member, require_chair

router = APIRouter()

@router.get("")
async def list_resolutions(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """List resolutions (decisions with type=resolution)."""
    query = db.query(Decision).filter(
        Decision.type == "resolution",
        Decision.deleted_at.is_(None),
        Decision.archived_at.is_(None),
    )
    if status:
        query = query.filter(Decision.status == status)

    total = query.count()
    resolutions = query.order_by(Decision.created_at.desc()).offset(offset).limit(limit).all()

    # Enrich with signature counts
    items = []
    for r in resolutions:
        sig_count = db.query(ResolutionSignature).filter(
            ResolutionSignature.decision_id == r.id
        ).count()
        items.append({
            "decision": r,
            "signature_count": sig_count,
        })

    return {"items": items, "total": total, "limit": limit, "offset": offset}
```

### Sign Resolution Endpoint
```python
@router.post("/{resolution_id}/sign")
async def sign_resolution(
    resolution_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """Digitally sign a resolution (name + timestamp + IP)."""
    decision = db.query(Decision).filter(
        Decision.id == resolution_id,
        Decision.type == "resolution",
        Decision.deleted_at.is_(None),
    ).first()

    if not decision:
        raise HTTPException(404, "Resolution not found")

    if decision.status != "closed":
        raise HTTPException(400, "Resolution must be closed (voted on) before signing")

    # Check for existing signature
    existing = db.query(ResolutionSignature).filter(
        ResolutionSignature.decision_id == resolution_id,
        ResolutionSignature.member_id == current_user.id,
    ).first()
    if existing:
        raise HTTPException(400, "You have already signed this resolution")

    # Capture IP
    ip_address = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not ip_address:
        ip_address = request.client.host if request.client else None

    signed_at = datetime.utcnow()
    signature_hash = generate_signature_hash(
        current_user.name, current_user.email, resolution_id, signed_at
    )

    signature = ResolutionSignature(
        decision_id=resolution_id,
        member_id=current_user.id,
        signed_at=signed_at,
        ip_address=ip_address,
        signature_hash=signature_hash,
    )
    db.add(signature)
    db.add(AuditLog(
        entity_type="resolution_signature",
        entity_id=resolution_id,
        entity_name=decision.title,
        action="sign",
        changed_by_id=current_user.id,
        ip_address=ip_address,
    ))
    db.commit()
    db.refresh(signature)

    return {
        "status": "signed",
        "signature_id": signature.id,
        "signed_at": signature.signed_at,
        "ip_address": signature.ip_address,
    }
```

### Signature Status Panel (React Component)
```tsx
// frontend/src/components/signature-panel.tsx
interface Signature {
  member_id: number;
  member_name: string;
  signed_at: string | null;
  ip_address: string | null;
}

interface SignaturePanelProps {
  resolutionId: string;
  signatures: Signature[];
  currentUserId: number;
  isClosed: boolean;
  onSign: () => void;
  signing: boolean;
}

export function SignaturePanel({
  signatures, currentUserId, isClosed, onSign, signing
}: SignaturePanelProps) {
  const hasSigned = signatures.some(s => s.member_id === currentUserId && s.signed_at);
  const signedCount = signatures.filter(s => s.signed_at).length;
  const totalMembers = signatures.length;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <PenLine className="h-4 w-4" />
          Signatures ({signedCount}/{totalMembers})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {signatures.map((sig) => (
          <div key={sig.member_id} className="flex items-center justify-between py-1.5">
            <span className="text-sm">{sig.member_name}</span>
            {sig.signed_at ? (
              <span className="text-xs text-green-500 flex items-center gap-1">
                <CheckCircle className="h-3 w-3" />
                {new Date(sig.signed_at).toLocaleDateString()}
              </span>
            ) : (
              <span className="text-xs text-muted-foreground">Pending</span>
            )}
          </div>
        ))}
        {isClosed && !hasSigned && (
          <Button onClick={onSign} disabled={signing} className="w-full mt-2">
            {signing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            Sign Resolution
          </Button>
        )}
        {hasSigned && (
          <div className="text-center text-sm text-green-500 flex items-center justify-center gap-1 mt-2">
            <CheckCircle className="h-4 w-4" />
            You have signed this resolution
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

### Sidebar Update
```tsx
// Add to boardNavGroups in sidebar.tsx, after "Decisions"
{ label: "Resolutions", href: "/resolutions", icon: Stamp },
// Import Stamp from lucide-react (or use Gavel, Scale, FileSignature)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| DocuSign/third-party for all signatures | Lightweight name+timestamp+IP for internal board resolutions | v2.0 design decision | No external dependency, simpler UX, sufficient for internal governance |
| Separate resolution model | Resolution = Decision with type=resolution | v1.0 design | Reuse existing CRUD, voting, audit infrastructure |
| PDF via ReportLab imperative API | HTML template + WeasyPrint | 2024-2025 ecosystem shift | Faster development, CSS-based styling, maintainable templates |

**Deprecated/outdated:**
- DocuSign integration fields on the Document model exist but are not used and are out of scope for v2.0 (per REQUIREMENTS.md out-of-scope list)
- The existing `docusign_envelope_id` and `signing_status` fields on the Document model should be ignored (they were spec'd for a different signing flow)

## Open Questions

1. **Should resolutions be excluded from the Decisions page?**
   - What we know: Currently all decisions (including type=resolution) show on /decisions
   - What's unclear: Whether users want resolutions to appear in BOTH places or ONLY in /resolutions
   - Recommendation: Show resolutions ONLY in /resolutions. Filter them out from /decisions page to avoid confusion. The dedicated section is the whole point of RES-01.

2. **Auto-numbering for resolution_number?**
   - What we know: The Decision model has `resolution_number` as a nullable string field
   - What's unclear: Whether to auto-generate numbers (e.g., "2026-001") or let users/agents specify them
   - Recommendation: Auto-generate with format `YYYY-NNN` (year + sequential number) but allow override. The Resolution Writer agent can set this via tool call.

3. **Who can sign? All board members or only those who voted?**
   - What we know: Requirements say "board members can digitally sign" -- implies all active board members
   - What's unclear: Whether shareholders can also sign
   - Recommendation: Allow all active board members (role in board/chair/admin) to sign. Use the same `require_member` auth dependency. Show pending status for all board-level members.

4. **WeasyPrint on Railway deployment**
   - What we know: WeasyPrint requires system libraries (Pango, Cairo)
   - What's unclear: Whether Railway's Python buildpack includes these
   - Recommendation: Test during Phase 04 execution. If system libs are missing, add an `Aptfile` to the backend directory listing required packages, or use a custom Dockerfile.

## Files to Modify (Specific)

### New Files
| File | Purpose |
|------|---------|
| `backend/app/api/resolutions.py` | Resolution-specific API endpoints (list, detail, sign, status, export) |
| `backend/app/templates/resolution_export.html` | Jinja2 HTML template for PDF/printable export |
| `backend/app/services/resolution_export.py` | WeasyPrint PDF generation service |
| `backend/migrations/versions/005_add_resolution_signatures.py` | Alembic migration |
| `frontend/src/app/resolutions/page.tsx` | Resolutions list page |
| `frontend/src/app/resolutions/[id]/page.tsx` | Resolution detail with signature panel |
| `frontend/src/components/signature-panel.tsx` | Signature status + sign button component |
| `frontend/src/components/resolution-export.tsx` | Export button (PDF/print) |

### Modified Files
| File | Change |
|------|--------|
| `backend/app/models/decision.py` | Add ResolutionSignature class, add `signatures` relationship to Decision |
| `backend/app/models/__init__.py` | Export ResolutionSignature |
| `backend/app/api/__init__.py` | Register resolutions router |
| `backend/requirements.txt` | Add `weasyprint>=62.0` |
| `frontend/src/components/sidebar.tsx` | Add Resolutions nav item with Stamp icon |
| `frontend/src/lib/api.ts` | Add `resolutionsApi` section |
| `frontend/src/lib/permissions.ts` | Add `resolutions.sign` and `resolutions.export` permissions |
| `frontend/src/app/decisions/page.tsx` | Filter out type=resolution from decisions list |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), no automated frontend tests (manual Playwright) |
| Config file | None detected -- Wave 0 gap |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RES-01 | GET /api/resolutions returns only type=resolution decisions | unit/integration | `pytest tests/test_resolutions.py::test_list_resolutions_only -x` | No -- Wave 0 |
| RES-02 | POST /api/resolutions/{id}/sign records signature with name+timestamp+IP | integration | `pytest tests/test_resolutions.py::test_sign_resolution -x` | No -- Wave 0 |
| RES-02 | Cannot sign non-resolution decision | unit | `pytest tests/test_resolutions.py::test_sign_non_resolution_rejected -x` | No -- Wave 0 |
| RES-02 | Cannot sign open/draft resolution | unit | `pytest tests/test_resolutions.py::test_sign_not_closed_rejected -x` | No -- Wave 0 |
| RES-02 | Cannot sign twice | unit | `pytest tests/test_resolutions.py::test_duplicate_signature_rejected -x` | No -- Wave 0 |
| RES-03 | GET /api/resolutions/{id}/signatures returns signed + pending members | integration | `pytest tests/test_resolutions.py::test_signature_status -x` | No -- Wave 0 |
| RES-04 | GET /api/resolutions/{id}/export returns PDF bytes | integration | `pytest tests/test_resolutions.py::test_export_pdf -x` | No -- Wave 0 |
| RES-04 | Only chair/admin can export | unit | `pytest tests/test_resolutions.py::test_export_requires_chair -x` | No -- Wave 0 |
| BUILT-03 | Resolution Writer agent config exists in DB | unit | `pytest tests/test_agents.py::test_resolution_writer_config -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_resolutions.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/` directory -- does not exist, needs creation
- [ ] `backend/tests/conftest.py` -- shared fixtures (test DB session, test client, mock members)
- [ ] `backend/tests/test_resolutions.py` -- covers RES-01 through RES-04
- [ ] `backend/tests/test_agents.py` -- covers BUILT-03
- [ ] Framework install: `pip install pytest pytest-asyncio httpx` (test dependencies)

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `backend/app/models/decision.py` -- Decision model with type=resolution, resolution_number, document_id FK
- Codebase analysis: `backend/app/api/decisions.py` -- Full CRUD with type filter, voting, audit logging
- Codebase analysis: `frontend/src/lib/api.ts` -- decisionsApi with list, get, create, vote
- Codebase analysis: `frontend/src/components/sidebar.tsx` -- NavGroup structure with visibility rules
- [Phase 01 Research](/.planning/phases/01-agent-infrastructure/01-RESEARCH.md) -- Agent infrastructure patterns, LiteLLM, tool definitions

### Secondary (MEDIUM confidence)
- [WeasyPrint API Reference](https://doc.courtbouillon.org/weasyprint/stable/api_reference.html) -- PDF generation API
- [FastAPI + WeasyPrint tutorial](https://www.promptzone.com/resumeburger/automate-your-resume-pdf-generation-with-ai-a-fastapi-weasyprint-tutorial-k5e) -- Integration pattern
- [Python PDF generation comparison (2025)](https://templated.io/blog/generate-pdfs-in-python-with-libraries/) -- Library comparison
- [Digital Signatures for Board Governance](https://govrn.com/blog/digital-signatures-governance-best-practice) -- UX patterns for board digital signatures

### Tertiary (LOW confidence)
- WeasyPrint system dependency requirements on Railway -- needs validation during deployment

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- uses existing project libraries plus well-established WeasyPrint
- Architecture: HIGH -- extends existing Decision model pattern, follows codebase conventions exactly
- Pitfalls: HIGH -- identified from codebase analysis and deployment knowledge
- Agent integration: MEDIUM -- depends on Phase 01 agent infrastructure being completed first

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (stable domain, no fast-moving dependencies)
