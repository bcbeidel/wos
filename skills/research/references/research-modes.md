# Research Modes

Eight investigation modes, each with distinct methodology, intensity, and
output expectations. All modes produce a standard research document but
vary in SIFT rigor, source requirements, and counter-evidence needs.

## Mode Matrix

| Mode | Min Sources | SIFT Rigor | Counter-Evidence | Challenge | Claim Verification | Typical Duration |
|------|-------------|------------|------------------|-----------|-------------------|------------------|
| deep-dive | 8+ | High | Required | Full | Full | Long |
| landscape | 6+ | Medium | Optional | Partial | Full | Medium |
| technical | 6+ | High | Required | Partial | Full | Long |
| feasibility | 4+ | Medium | Required | Full | Full | Medium |
| competitive | 6+ | Medium | Optional | Full | Full | Medium |
| options | 6+ | High | Required | Full | Full | Long |
| historical | 4+ | Low | Optional | Partial | Full | Short |
| open-source | 4+ | Medium | Optional | Partial | Full | Medium |

## Challenge Sub-Steps by Mode

| Mode | Assumptions Check | ACH | Premortem |
|------|-------------------|-----|----------|
| deep-dive | Yes | Yes | Yes |
| landscape | Yes | No | Yes |
| technical | Yes | No | Yes |
| feasibility | Yes | Yes | Yes |
| competitive | Yes | Yes | Yes |
| options | Yes | Yes | Yes |
| historical | Yes | No | Yes |
| open-source | Yes | No | Yes |

- **Full** = Assumptions check + ACH + Premortem
- **Partial** = Assumptions check + Premortem (no ACH)

See `references/challenge-phase.md` for detailed procedures.

## Mode Methodology

Question patterns for mode detection live in SKILL.md. Below is the
methodology guidance unique to each mode.

- **deep-dive** — Comprehensive single-topic investigation. Cast a wide net,
  then narrow to highest-quality sources. Cover background, current state,
  key debates, and practical implications. Counter-evidence actively sought.
- **landscape** — Broad domain survey. Map major players, trends, and
  categories. Prioritize breadth over depth. Goal is orientation, not
  exhaustive coverage.
- **technical** — Deep technical investigation. Focus on architecture,
  implementation details, performance characteristics, and tradeoffs.
  Prefer official documentation and expert practitioners.
- **feasibility** — Evaluate achievability given constraints (time, resources,
  technology, skills). Identify blockers, risks, and prerequisites.
  Actively search for reasons it might fail.
- **competitive** — Systematic comparison across defined criteria. Identify
  differentiators, market positioning, and relative strengths. Watch for
  vendor bias in sources.
- **options** — Structured comparison of alternatives against evaluation
  criteria. Each option gets equal investigation depth. For each option,
  find arguments against it.
- **historical** — Trace development over time. Identify key inflection
  points, decisions, and consequences. Lower SIFT intensity since historical
  sources are often secondary.
- **open-source** — Survey available projects. Evaluate by stars, maintenance
  activity, community health, documentation quality, and license
  compatibility. Use repository metrics as proxy for quality.
