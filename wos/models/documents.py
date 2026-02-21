"""Document models re-export layer.

Preserves backward compatibility for ``from wos.models.documents import X``.
Actual implementations live in focused modules:
  - base_document.py: BaseDocument, Document alias
  - topic_document.py: TopicDocument
  - overview_document.py: OverviewDocument
  - research_document.py: ResearchDocument
  - plan_document.py: PlanDocument
  - note_document.py: NoteDocument
"""

from __future__ import annotations

from wos.models.base_document import BaseDocument, Document  # noqa: F401
from wos.models.topic_document import TopicDocument  # noqa: F401
from wos.models.overview_document import OverviewDocument  # noqa: F401
from wos.models.research_document import ResearchDocument  # noqa: F401
from wos.models.plan_document import PlanDocument  # noqa: F401
from wos.models.note_document import NoteDocument  # noqa: F401
