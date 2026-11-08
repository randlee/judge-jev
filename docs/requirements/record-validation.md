# judge-jev Requirements - Record Validation

**ID Range:** REQ-JEV-0101 through REQ-JEV-0101  
**Status:** Draft  
**Created:** 2026-11-07  
**Last Updated:** 2026-11-07  
**Owner:** Rand Lee  
**Version:** 0.1.0  

---

## Overview

judge-jev verifies that a REQ, NFR or ADR is well written.

---

## REQ-JEV-0101: Record quality mode

**Status:** Proposed  

### Requirement Statement

**MUST statements:**

- judge-jev MUST provide a mode that asks whether one REQ, NFR or ADR is
  well written.
- A failing answer MUST report the decision-tree path that failed.

### Rationale

Records Raptor rejects or that judge badly are explained instead of being
accepted by a looser schema.

### Success Criteria

**Acceptance Criteria:**

- [ ] A record with no acceptance criterion reports `no` with the path that
  names the criteria node.
