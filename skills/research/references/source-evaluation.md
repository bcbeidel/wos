# Source Evaluation Reference

## Source Hierarchy

Sources are ranked by authority. Prefer higher-tier sources. When citing
lower-tier sources, note the tier and explain why a higher-tier source
was not available.

### Tier 1 — Official Documentation
- Official project/product documentation
- Government publications, standards bodies (W3C, IETF, ISO)
- Original author's own writings about their work
- **Example:** Python docs, RFC specifications, AWS documentation

### Tier 2 — Institutional Research
- University research departments
- Think tanks and research organizations
- Industry consortia (Linux Foundation, CNCF)
- **Example:** MIT CSAIL papers, Brookings reports, CNCF surveys

### Tier 3 — Peer-Reviewed
- Academic journals and conference proceedings
- Formally peer-reviewed technical reports
- Published books by domain experts
- **Example:** ACM/IEEE papers, O'Reilly books, Nature publications

### Tier 4 — Expert Practitioners
- Recognized experts writing in their domain of expertise
- Technical blogs from core maintainers or architects
- Conference talks from established practitioners
- **Example:** Martin Fowler's blog, Kelsey Hightower's talks

### Tier 5 — Community Content
- Stack Overflow answers (high-voted)
- Community blog posts and tutorials
- Forum discussions with consensus
- **Example:** Dev.to articles, Reddit threads, HN discussions

### Tier 6 — AI-Generated
- LLM outputs without primary source verification
- AI-summarized content
- Chatbot responses
- **Note:** Never cite AI output as a source. Always trace to primary.

## Authority Annotation Format

When including sources in a research document, annotate each with its tier:

```yaml
sources:
  - url: "https://docs.python.org/3/library/asyncio.html"
    title: "Python asyncio documentation (T1: official docs)"
  - url: "https://martinfowler.com/articles/microservices.html"
    title: "Microservices by Martin Fowler (T4: expert practitioner)"
```

## Red Flags

Watch for these source quality issues:
- **No author or organization identified** — investigate further
- **Circular sourcing** — multiple sources citing the same unverified origin
- **Outdated information** — check publication date vs domain currency
- **Conflict of interest** — vendor-sponsored research about their own product
- **Survivorship bias** — only success stories, no failures mentioned
