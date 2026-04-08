# Phase 04: Board Resolutions & Resolution Writer - Research

**Researched:** 2026-03-05
**Domain:** Digital signature workflow, resolution management UI, printable export, AI-assisted resolution drafting
**Confidence:** HIGH

## Summary

Phase 04 builds a dedicated board resolution workflow on top of the existing `Decision` model (which already has `type="resolution"`, `resolution_number`, and `document_id` fields). The work breaks into five areas: (1) a new `ResolutionSignature` model and API for digital signatures, (2) a dedicated Resolutions section in the sidebar and frontend pages filtering decisions by `type=resolution`, (3) a signature status panel showing who signed and who has not, (4) printable export of signed resolutions using CSS `@media print` (no server-side PDF generation), and (5) a Resolution Writer agent that drafts resolution documents via the agent infrastructure built in Phase 01.

The existing codebase is well-prepared for this work. The `Decision` model already supports resolutions via `type="resolution"`, `resolution_number`, and `document_id` FK to the documents table. The decisions API already accepts `type` as a filter parameter (`GET /decisions?type=resolution`). The frontend decisions page already has a `typeConfig` entry for `resolution` with its own color scheme. The agent infrastructure (runner, tool registry, SSE streaming, `useAgentStream` hook) is fully operational from Phase 01. The seed data in `main.py` already includes a placeholder Resolution Writer agent config.

What is missing: signature recording and status display, a dedicated `/resolutions` page and sidebar entry, export functionality, and the Resolution Writer agent's production system prompt and tool implementations.

**Primary recommendation:** Add a `resolution_signatures` table via Alembic migration (007), create `/api/resolutions/` endpoints with signature-specific logic, add a `/resolutions` page and sidebar entry, use CSS `@media print` for printable export (no WeasyPrint), and register Resolution Writer agent tools following the established pattern in `tools/meetings.py` and `tools/transcripts.py`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RES-01 | Board resolutions appear as a dedicated section (building on existing decisions with type=resolution) | Decision model already has `type=resolution`. New sidebar entry + `/resolutions` page filtering decisions by type. Existing API already supports `?type=resolution` filter. Filter resolutions OUT of `/decisions` page. |
| RES-02 | Board members can digitally sign a resolution (name + timestamp + IP) | New `ResolutionSignature` model + `POST /api/resolutions/{id}/sign` endpoint. Captures `member_id`, `signed_at`, `ip_address`, `signature_hash`. UniqueConstraint prevents double-signing. |
| RES-03 | Resolution shows signature status (who signed, who hasn't) | `GET /api/resolutions/{id}/signatures` returns all board members with signed/pending status. Frontend `SignaturePanel` component displays status with sign button. |
| RES-04 | Chair/admin can view and export signed resolutions | Printable HTML view via CSS `@media print`. Print button triggers `window.print()`. No server-side PDF generation needed. |
| BUILT-03 | Resolution Writer agent can draft resolution documents and link them to decisions | Agent config in DB updated from placeholder. Tools: `create_resolution`, `draft_resolution_document`, `list_resolutions`, `get_resolution`. Uses existing agent infrastructure from Phase 01. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | >=2.0.25 | ResolutionSignature model, queries | Already in project stack. Mapped column pattern used throughout. |
| Alembic | >=1.13.1 | Database migration for resolution_signatures table | Already in project stack. Sequential migrations (001-006 exist). Next is 007. |
| FastAPI | >=0.135.0 | API endpoints for signature CRUD, export | Already in stack. |
| Pydantic | >=2.5 | Request/response schemas for signature API | Already in stack. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | >=0.26.0 | Agent tool internal API calls | Already in stack. Tools call board REST API. |
| litellm | >=1.80 | Resolution Writer agent LLM calls | Added in Phase 01. Agent infrastructure. |
| react-markdown | (existing) | Agent output rendering | Already in frontend. Used by MinutesGenerator. |
| lucide-react | (existing) | Icons for Resolutions sidebar, signature panel | Already in frontend. Stamp/Gavel/PenLine icons. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CSS @media print | WeasyPrint server-side PDF | WeasyPrint requires system-level C libraries (Pango, Cairo) that complicate Railway deployment. CSS @media print is zero-dependency, works everywhere, and is sufficient for formal resolution documents. |
| CSS @media print | Playwright PDF | Already have Playwright MCP, but it requires a browser instance. Too heavy for server-side PDF generation. |
| Separate resolutions table | Resolution = Decision with type filter | Resolutions ARE decisions with `type=resolution`. Separate table would duplicate Decision fields. Use FK relationship from ResolutionSignature to Decision. |

**Installation:** No new dependencies needed. All libraries are already in the stack.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
+-- api/
|   +-- decisions.py          # EXISTING - no changes needed
|   +-- resolutions.py        # NEW - resolution-specific endpoints (sign, status, export)
+-- models/
|   +-- decision.py           # MODIFY - add ResolutionSignature model + signatures relationship
|   +-- __init__.py            # MODIFY - export ResolutionSignature
+-- schemas/
|   +-- resolution.py         # NEW - Pydantic schemas for resolution/signature API
+-- tools/
|   +-- resolutions.py        # NEW - Resolution Writer agent tools
+-- main.py                   # MODIFY - update seed agent prompt + tool names

backend/migrations/versions/
+-- 007_add_resolution_signatures.py  # NEW - Alembic migration

frontend/src/
+-- app/
|   +-- resolutions/
|   |   +-- page.tsx           # NEW - resolutions list page
|   |   +-- [id]/
|   |       +-- page.tsx       # NEW - resolution detail + signature panel + agent
+-- components/
|   +-- signature-panel.tsx    # NEW - who signed / who hasn't + sign button
|   +-- resolution-writer.tsx  # NEW - Resolution Writer agent trigger (like MinutesGenerator)
|   +-- sidebar.tsx            # MODIFY - add "Resolutions" nav item
+-- lib/
    +-- api.ts                 # MODIFY - add resolutionsApi section
```

### Pattern 1: ResolutionSignature Model
**What:** A new model recording digital signatures on resolutions. Each board member can sign once per resolution.
**When to use:** Recording and querying resolution signatures.
**Example:**
```python
# Following existing Vote model pattern in decision.py

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
    )  # SHA-256 hash of member_name + decision_id + signed_at

    # Relationships
    decision: Mapped["Decision"] = relationship("Decision", back_populates="signatures")
    member: Mapped["BoardMember"] = relationship("BoardMember")
```

### Pattern 2: Signature Hash for Tamper Evidence
**What:** Generate a SHA-256 hash at signing time tying signer, resolution, and timestamp together. Lightweight tamper evidence, not cryptographic non-repudiation.
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

### Pattern 3: Agent Tool Registration (Following Established Pattern)
**What:** Tools are registered at module level using `register_tool()` with a `ToolDefinition`. Each tool handler is an async function calling the board REST API via httpx.
**When to use:** All Resolution Writer agent tools.
**Example:**
```python
# backend/app/tools/resolutions.py
# Follows exact pattern from tools/meetings.py and tools/transcripts.py

import json
import os
import httpx
from app.tools import ToolDefinition, register_tool

def _get_base_url() -> str:
    return os.environ.get("TOOL_API_BASE_URL", "http://localhost:3010")

async def _create_resolution(params: dict, user_context: dict) -> str:
    """Create a new decision of type=resolution via the board API."""
    body = {
        "title": params["title"],
        "description": params["description"],
        "type": "resolution",
    }
    if "resolution_number" in params:
        body["resolution_number"] = params["resolution_number"]
    if "meeting_id" in params:
        body["meeting_id"] = params["meeting_id"]

    try:
        async with httpx.AsyncClient(base_url=_get_base_url()) as client:
            response = await client.post(
                "/api/decisions",
                json=body,
                headers={"X-User-Email": user_context["email"]},
            )
            if response.status_code >= 400:
                return json.dumps({"error": response.text, "status": response.status_code})
            return json.dumps(response.json())
    except Exception as e:
        return json.dumps({"error": str(e)})

register_tool(ToolDefinition(
    name="create_resolution",
    description="Create a new board resolution (a decision with type=resolution)",
    parameters_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Resolution title"},
            "description": {"type": "string", "description": "Resolution body text"},
            "resolution_number": {"type": "string", "description": "Resolution number (e.g., '2026-001')"},
            "meeting_id": {"type": "integer", "description": "Optional meeting ID to link to"},
        },
        "required": ["title", "description"],
    },
    handler=_create_resolution,
    category="resolutions",
))
```

### Pattern 4: Printable Export (CSS @media print)
**What:** A dedicated resolution detail page with `@media print` styles that hide navigation and format the resolution as a formal document when printed.
**When to use:** Chair/admin clicks "Print/Export" on a resolution detail page.
**Example:**
```tsx
// Print styles applied to the resolution detail page
// No server-side PDF generation needed

function PrintableResolution({ resolution, signatures }: PrintableResolutionProps) {
  return (
    <>
      {/* Print-only header */}
      <div className="hidden print:block">
        <h1>{resolution.title}</h1>
        <p>Resolution No. {resolution.resolution_number}</p>
        {/* ... formal resolution content ... */}
        <div className="mt-8">
          <h3>Signatures</h3>
          <table>
            <thead><tr><th>Name</th><th>Date</th></tr></thead>
            <tbody>
              {signatures.filter(s => s.signed_at).map(sig => (
                <tr key={sig.member_id}>
                  <td>{sig.member_name}</td>
                  <td>{new Date(sig.signed_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Screen-only UI (hidden when printing) */}
      <div className="print:hidden">
        {/* Normal resolution detail UI */}
      </div>
    </>
  );
}

// In the page:
<Button onClick={() => window.print()}>
  <Printer className="h-4 w-4 mr-2" />
  Print Resolution
</Button>
```

### Pattern 5: Resolution Writer Agent Invocation (Following MinutesGenerator Pattern)
**What:** A component similar to `MinutesGenerator` that uses `useAgentStream` to invoke the Resolution Writer agent inline on the resolution detail page.
**When to use:** When a user wants to draft a resolution document from a brief description.
**Example:**
```tsx
// frontend/src/components/resolution-writer.tsx
// Follows exact pattern from components/minutes-generator.tsx

export function ResolutionWriter({
  resolutionId,
  resolutionTitle,
  userEmail,
}: ResolutionWriterProps) {
  const { status, text, toolCalls, error, run, reset } = useAgentStream();

  const handleGenerate = () => {
    run(
      "resolution-writer",
      `Draft a formal resolution document for resolution ${resolutionId} ("${resolutionTitle}")`,
      userEmail,
      { resolution_id: resolutionId }
    );
  };

  // ... same streaming UI pattern as MinutesGenerator ...
}
```

### Anti-Patterns to Avoid
- **Duplicating Decision data for resolutions:** Resolutions ARE decisions with `type=resolution`. Do NOT create a separate `resolutions` table with Decision fields. Add `resolution_signatures` only.
- **Direct database access in agent tools:** Tools MUST call the board's REST API via httpx, not query the database directly. This preserves auth checks, validation, and audit logging.
- **Storing signatures as JSON blobs:** Each signature should be its own row in `resolution_signatures` with proper FK constraints, not a JSON array on the Decision model.
- **Server-side PDF generation:** Use CSS `@media print` for export. No WeasyPrint, no Playwright PDF, no new server dependencies.
- **Allowing signatures on non-resolution decisions:** The sign endpoint must validate `decision.type == "resolution"` before recording.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Printable document formatting | Server-side PDF library | CSS `@media print` + `window.print()` | Zero dependency, works in all browsers, sufficient for formal resolution documents |
| IP address capture | Manual header parsing | `request.headers.get("X-Forwarded-For")` then `request.client.host` | Standard proxy-aware IP resolution |
| Hash generation | Custom hashing | Python `hashlib.sha256` | Standard library, well-tested |
| Agent invocation UI | Custom SSE parsing | `useAgentStream` hook from Phase 01 | Already built, tested, handles all SSE event types |
| Tool registration | Custom tool loader | `register_tool()` + `ToolDefinition` from Phase 01 | Already built, auto-registers on import |

**Key insight:** The resolution signature system is intentionally lightweight (name + timestamp + IP, not DocuSign). Do not over-engineer with cryptographic signing infrastructure. A SHA-256 hash provides tamper evidence, and the audit log provides the governance trail.

## Common Pitfalls

### Pitfall 1: Signing a Non-Resolution Decision
**What goes wrong:** User tries to sign a decision that is type=vote or type=consent.
**Why it happens:** The signature endpoint accepts a decision_id without checking type.
**How to avoid:** Validate `decision.type == "resolution"` in the sign endpoint before recording.
**Warning signs:** Test with a vote-type decision and confirm it returns 400.

### Pitfall 2: Signing Before Resolution is Closed
**What goes wrong:** Board members sign a resolution that hasn't been voted on yet.
**Why it happens:** No status check on the decision.
**How to avoid:** Only allow signing when `decision.status == "closed"` (voting is complete).
**Warning signs:** Draft or open resolutions showing a "Sign" button.

### Pitfall 3: Missing IP Address Behind Proxy
**What goes wrong:** `request.client.host` returns the proxy IP, not the user's real IP.
**Why it happens:** Railway (and most deployments) use reverse proxies.
**How to avoid:** Check `X-Forwarded-For` header first, fall back to `request.client.host`.
**Warning signs:** All signatures show the same IP address.

### Pitfall 4: Frontend Routing Collision
**What goes wrong:** `/resolutions` and `/decisions` routes conflict or both appear active in sidebar.
**Why it happens:** Sidebar uses `pathname.startsWith(item.href)` for active state.
**How to avoid:** Resolutions use `/resolutions` path (not `/decisions/resolutions`). Sidebar active state logic already handles separate paths correctly since both start with different prefixes.
**Warning signs:** Both Decisions and Resolutions highlighted in sidebar simultaneously.

### Pitfall 5: Duplicate Signatures
**What goes wrong:** A board member signs the same resolution twice.
**Why it happens:** Race condition or missing uniqueness check.
**How to avoid:** UniqueConstraint on `(decision_id, member_id)` in the database. Also check in the API before inserting. Disable sign button after signing.
**Warning signs:** Test with rapid double-click on Sign button.

### Pitfall 6: Resolution Writer Tool Names Mismatch with Seed Data
**What goes wrong:** The seed data in `main.py` lists `allowed_tool_names=["create_resolution", "get_decision"]` for the Resolution Writer, but the actual registered tool names differ.
**Why it happens:** Seed data was written as a placeholder in Phase 01 before tools were implemented.
**How to avoid:** Update the seed data upgrade block in `_seed_agents()` to match the actual tool names registered in `tools/resolutions.py`. Follow the same upgrade pattern used for Minutes Generator (detect placeholder prompt, update).
**Warning signs:** Agent invocation fails with "Unknown tool" errors in tool_result events.

### Pitfall 7: Decisions Page Still Shows Resolutions After Dedicated Page Exists
**What goes wrong:** Users see resolutions in both `/decisions` and `/resolutions` pages.
**Why it happens:** The decisions list API returns all types including resolutions, and the frontend doesn't filter.
**How to avoid:** Either (a) pass `?type=vote&type=consent` to the decisions API to exclude resolutions, or (b) filter client-side on the decisions page to exclude `type=resolution`.
**Warning signs:** Same resolution appearing on two different pages.

## Code Examples

### Resolutions API Router
```python
# backend/app/api/resolutions.py
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.member import BoardMember
from app.models.decision import Decision, ResolutionSignature
from app.models.audit import AuditLog
from app.api.auth import require_member, require_chair

router = APIRouter()

@router.get("")
async def list_resolutions(
    status: str | None = Query(None),
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
        total_members = db.query(BoardMember).filter(
            BoardMember.deleted_at.is_(None),
            BoardMember.role.in_(["board", "chair", "admin"]),
        ).count()
        items.append({
            **_decision_to_dict(r),
            "signature_count": sig_count,
            "total_signers": total_members,
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

    # Capture IP (proxy-aware)
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
        "signed_at": signature.signed_at.isoformat(),
    }
```

### Signature Status Endpoint
```python
@router.get("/{resolution_id}/signatures")
async def get_signature_status(
    resolution_id: int,
    db: Session = Depends(get_db),
    current_user: BoardMember = Depends(require_member),
):
    """Get signature status -- who signed and who hasn't."""
    decision = db.query(Decision).filter(
        Decision.id == resolution_id,
        Decision.type == "resolution",
        Decision.deleted_at.is_(None),
    ).first()

    if not decision:
        raise HTTPException(404, "Resolution not found")

    # Get all board-level members
    members = db.query(BoardMember).filter(
        BoardMember.deleted_at.is_(None),
        BoardMember.role.in_(["board", "chair", "admin"]),
    ).all()

    # Get existing signatures
    signatures = db.query(ResolutionSignature).filter(
        ResolutionSignature.decision_id == resolution_id
    ).all()
    sig_map = {s.member_id: s for s in signatures}

    result = []
    for member in members:
        sig = sig_map.get(member.id)
        result.append({
            "member_id": member.id,
            "member_name": member.name,
            "signed_at": sig.signed_at.isoformat() if sig else None,
            "ip_address": sig.ip_address if sig else None,
        })

    return {
        "resolution_id": resolution_id,
        "signatures": result,
        "signed_count": len(signatures),
        "total_members": len(members),
    }
```

### Signature Panel (React Component)
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
  signedCount: number;
  totalMembers: number;
  currentUserId: number;
  isClosed: boolean;
  onSign: () => void;
  signing: boolean;
}

export function SignaturePanel({
  signatures, signedCount, totalMembers, currentUserId,
  isClosed, onSign, signing
}: SignaturePanelProps) {
  const hasSigned = signatures.some(s => s.member_id === currentUserId && s.signed_at);

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
// Add to boardNavGroups items array, after "Decisions"
{ label: "Resolutions", href: "/resolutions", icon: Stamp },
// Import: import { Stamp } from "lucide-react";
```

### Frontend API Client Extension
```typescript
// Add to api.ts
export interface ResolutionSignature {
  member_id: number;
  member_name: string;
  signed_at: string | null;
  ip_address: string | null;
}

export interface SignatureStatus {
  resolution_id: number;
  signatures: ResolutionSignature[];
  signed_count: number;
  total_members: number;
}

export const resolutionsApi = {
  list: async (params?: { status?: string }): Promise<Decision[]> => {
    const query = params?.status ? `?status=${params.status}` : "";
    const response = await api.get<PaginatedResponse<Decision>>(`/resolutions${query}`);
    return response.items || [];
  },
  get: async (id: string): Promise<DecisionDetail> => {
    return api.get(`/resolutions/${id}`);
  },
  getSignatures: async (id: string): Promise<SignatureStatus> => {
    return api.get(`/resolutions/${id}/signatures`);
  },
  sign: async (id: string): Promise<{ status: string; signature_id: number }> => {
    return api.post(`/resolutions/${id}/sign`);
  },
};
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| DocuSign/third-party for all signatures | Lightweight name+timestamp+IP for internal board resolutions | v2.0 design decision | No external dependency, simpler UX, sufficient for internal governance |
| Separate resolution model | Resolution = Decision with type=resolution | v1.0 design | Reuse existing CRUD, voting, audit infrastructure |
| Server-side PDF generation (WeasyPrint/ReportLab) | CSS @media print | v2.0 constraint | Zero new dependencies, works in all browsers, sufficient for formal documents |

**Deprecated/outdated:**
- DocuSign integration fields on the Document model (`docusign_envelope_id`, `signing_status`) exist but are not used and are out of scope for v2.0
- The prior research (in `04-board-resolutions-writer/04-RESEARCH.md`) recommended WeasyPrint for PDF generation -- this is superseded by the CSS @media print constraint

## Open Questions

1. **Should resolutions be excluded from the Decisions page?**
   - What we know: Currently all decisions (including type=resolution) show on /decisions
   - What's unclear: Whether users want resolutions in BOTH places or ONLY in /resolutions
   - Recommendation: Show resolutions ONLY in /resolutions. Filter them out from /decisions page to avoid confusion. The dedicated section is the whole point of RES-01.

2. **Auto-numbering for resolution_number?**
   - What we know: The Decision model has `resolution_number` as a nullable string field
   - What's unclear: Whether to auto-generate numbers (e.g., "2026-001") or let users/agents specify
   - Recommendation: Auto-generate with format `YYYY-NNN` (year + sequential number) when creating via the resolutions API. Allow override. The Resolution Writer agent can set this via tool call.

3. **Who can sign? All board members or only those who voted?**
   - What we know: Requirements say "board members can digitally sign"
   - What's unclear: Whether shareholders can also sign
   - Recommendation: Allow all active board members (role in board/chair/admin) to sign. Shareholders cannot sign. Use the existing `require_member` auth dependency. Show pending status for all board-level members.

4. **Should the Resolution Writer create an HTML document (like Minutes Generator) or just create the Decision record?**
   - What we know: The requirements say "draft resolution documents and link them to decisions". The Minutes Generator creates an HTML document and links it to the meeting via `create_minutes_document`.
   - What's unclear: Whether the resolution "document" is the Decision description field or a separate Document model entry.
   - Recommendation: The Resolution Writer should be able to both (a) create a decision of type=resolution with rich description text, and (b) optionally create a formal HTML document and link it via the `document_id` FK. Use tools: `create_resolution` (creates decision), `draft_resolution_document` (creates HTML document via documents API), `list_resolutions`, `get_resolution`.

## Files to Modify (Specific)

### New Files
| File | Purpose |
|------|---------|
| `backend/app/api/resolutions.py` | Resolution-specific API endpoints (list, detail, sign, signatures) |
| `backend/app/schemas/resolution.py` | Pydantic schemas for resolution/signature requests/responses |
| `backend/app/tools/resolutions.py` | Resolution Writer agent tools |
| `backend/migrations/versions/007_add_resolution_signatures.py` | Alembic migration for resolution_signatures table |
| `frontend/src/app/resolutions/page.tsx` | Resolutions list page |
| `frontend/src/app/resolutions/[id]/page.tsx` | Resolution detail with signature panel + agent |
| `frontend/src/components/signature-panel.tsx` | Signature status + sign button component |
| `frontend/src/components/resolution-writer.tsx` | Resolution Writer agent trigger component |

### Modified Files
| File | Change |
|------|--------|
| `backend/app/models/decision.py` | Add `ResolutionSignature` class, add `signatures` relationship to Decision |
| `backend/app/models/__init__.py` | Export `ResolutionSignature` |
| `backend/app/main.py` | Register resolutions router, update Resolution Writer seed prompt + tools, add upgrade block |
| `backend/app/tools/__init__.py` | Import `resolutions` module at bottom for auto-registration |
| `frontend/src/components/sidebar.tsx` | Add Resolutions nav item with Stamp icon |
| `frontend/src/lib/api.ts` | Add `resolutionsApi` section with list, get, sign, getSignatures |
| `frontend/src/app/decisions/page.tsx` | Filter out `type=resolution` from decisions list |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), manual Playwright verification (frontend) |
| Config file | None detected -- Wave 0 gap |
| Quick run command | `cd /Users/amirhaque/Files/swarmify/agents/ivy/tmg-board/backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd /Users/amirhaque/Files/swarmify/agents/ivy/tmg-board/backend && python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RES-01 | GET /api/resolutions returns only type=resolution decisions | integration | `pytest tests/test_resolutions.py::test_list_resolutions_only -x` | No -- Wave 0 |
| RES-01 | Decisions page excludes type=resolution | manual-only | Playwright visual check | N/A |
| RES-02 | POST /api/resolutions/{id}/sign records signature with name+timestamp+IP | integration | `pytest tests/test_resolutions.py::test_sign_resolution -x` | No -- Wave 0 |
| RES-02 | Cannot sign non-resolution decision | unit | `pytest tests/test_resolutions.py::test_sign_non_resolution_rejected -x` | No -- Wave 0 |
| RES-02 | Cannot sign open/draft resolution | unit | `pytest tests/test_resolutions.py::test_sign_not_closed_rejected -x` | No -- Wave 0 |
| RES-02 | Cannot sign twice (UniqueConstraint) | unit | `pytest tests/test_resolutions.py::test_duplicate_signature_rejected -x` | No -- Wave 0 |
| RES-03 | GET /api/resolutions/{id}/signatures returns all members with status | integration | `pytest tests/test_resolutions.py::test_signature_status -x` | No -- Wave 0 |
| RES-04 | Print button calls window.print() | manual-only | Playwright visual check | N/A |
| BUILT-03 | Resolution Writer agent tools registered in TOOL_REGISTRY | unit | `pytest tests/test_resolutions.py::test_resolution_tools_registered -x` | No -- Wave 0 |
| BUILT-03 | Resolution Writer seed config updated from placeholder | unit | `pytest tests/test_resolutions.py::test_resolution_writer_seeded -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_resolutions.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before verification

### Wave 0 Gaps
- [ ] `backend/tests/` directory -- does not exist, needs creation
- [ ] `backend/tests/conftest.py` -- shared fixtures (test DB session, test client, mock board members)
- [ ] `backend/tests/test_resolutions.py` -- covers RES-01 through RES-04, BUILT-03
- [ ] Framework install: pytest and pytest-asyncio already in requirements.txt

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `backend/app/models/decision.py` -- Decision model with `type=resolution`, `resolution_number`, `document_id` FK, Vote model pattern
- Codebase analysis: `backend/app/api/decisions.py` -- Full CRUD with type filter, voting, audit logging
- Codebase analysis: `backend/app/tools/meetings.py` -- Tool registration pattern with `register_tool()`, httpx internal API calls
- Codebase analysis: `backend/app/tools/transcripts.py` -- Minutes Generator tool pattern (parallel fetch, document creation)
- Codebase analysis: `backend/app/services/agent_runner.py` -- Agent loop, SSE event types
- Codebase analysis: `backend/app/main.py` -- `_seed_agents()` function, Resolution Writer placeholder config, upgrade block pattern
- Codebase analysis: `frontend/src/components/minutes-generator.tsx` -- Agent invocation UI pattern with `useAgentStream`
- Codebase analysis: `frontend/src/hooks/use-agent-stream.ts` -- SSE consumption hook API
- Codebase analysis: `frontend/src/components/sidebar.tsx` -- NavGroup structure, visibility rules
- Codebase analysis: `frontend/src/lib/api.ts` -- API client patterns for all entity types
- Codebase analysis: `frontend/src/lib/permissions.ts` -- Role-based permission system
- Codebase analysis: `backend/app/models/member.py` -- BoardMember model with `role` field and `is_board` property

### Secondary (MEDIUM confidence)
- Prior Phase 04 research (`04-board-resolutions-writer/04-RESEARCH.md`) -- architecture patterns validated, WeasyPrint recommendation superseded by CSS @media print constraint
- Phase 01 research (`01-agent-infrastructure/01-RESEARCH.md`) -- LiteLLM, agent loop, tool calling patterns

### Tertiary (LOW confidence)
- None -- all findings are based on direct codebase analysis

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies needed, uses existing project libraries entirely
- Architecture: HIGH -- extends existing Decision model pattern, follows established tool registration and agent invocation patterns exactly
- Pitfalls: HIGH -- identified from codebase analysis, deploy patterns, and prior phase learnings
- Agent integration: HIGH -- Phase 01 agent infrastructure is complete and tested; tool patterns are established in `tools/meetings.py` and `tools/transcripts.py`

**Research date:** 2026-03-05
**Valid until:** 2026-04-05 (stable domain, no fast-moving dependencies)
