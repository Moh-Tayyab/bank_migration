# WorldCheck to Private Individuals Migration Plan

**Project**: UN Wallet Multi-Bank Data Migration Platform
**Migration Type**: AML/KYC Screening Data Migration
**Source**: WorldCheck (50 records, 10 columns)
**Target**: Private Individuals (93 columns)
**Plan Start Date**: June 3, 2026
**Target Go-Live**: July 29, 2026

---

## Executive Summary

This migration plan outlines the step-by-step approach to migrate WorldCheck sanctions/watchlist data to the Private Individuals screening database. This is a **high-risk AML/KYC compliance migration** requiring strict validation, manual review processes, and regulatory sign-off.

### Key Dates

| Milestone | Date | Status |
|-----------|------|--------|
| Plan Approval | June 6, 2026 | Pending |
| Transformation Complete | June 17, 2026 | Pending |
| Testing Complete | July 8, 2026 | Pending |
| Compliance Sign-off | July 22, 2026 | Pending |
| Go-Live | July 29, 2026 | Pending |

### Success Criteria

- ✅ 100% data accuracy (zero data loss)
- ✅ All mandatory fields populated
- ✅ 95%+ records auto-transformed (≤5% manual review)
- ✅ Zero validation errors on export
- ✅ Compliance sign-off obtained
- ✅ Rollback plan tested

---

## Phase 1: Preparation & Planning (Week 1-2)
**Dates**: June 3 - June 14, 2026

### Week 1: June 3-7, 2026

| Day | Date | Task | Owner | Deliverable | Status |
|-----|------|------|-------|-------------|--------|
| Wed | Jun 3 | Project kick-off meeting | Project Lead | Meeting minutes | ✅ Complete |
| Wed | Jun 3 | Schema analysis completion | Data Architect | Analysis docs | ✅ Complete |
| Thu | Jun 4 | Transformation requirements review | Tech Lead | Requirements doc | Pending |
| Thu | Jun 4 | Risk scoring matrix draft | Risk Management | Draft matrix | Pending |
| Fri | Jun 5 | Business rules workshop | Compliance | Draft rules | Pending |
| Fri | Jun 5 | Manual review workflow design | Ops Manager | Workflow design | Pending |

### Week 2: June 10-14, 2026

| Day | Date | Task | Owner | Deliverable | Status |
|-----|------|------|-------|-------------|--------|
| Mon | Jun 9 | Risk scoring matrix approval | Risk Management | Approved matrix | Pending |
| Mon | Jun 9 | ListRecordType mapping approval | Compliance | Approved mapping | Pending |
| Tue | Jun 10 | Migration environment setup | DevOps | Staging env ready | Pending |
| Tue | Jun 10 | Test data preparation | Data Analyst | Test dataset | Pending |
| Wed | Jun 11 | Transformation engine review | Tech Lead | Review complete | Pending |
| Wed | Jun 11 | Validation rules sign-off | Compliance | Signed rules | Pending |
| Thu | Jun 12 | Migration plan final approval | Steering Committee | Approved plan | Pending |
| Thu | Jun 12 | Resource allocation confirmation | PM | Resource plan | Pending |
| Fri | Jun 13 | Pre-migration checklist creation | QA | Checklist | Pending |
| Fri | Jun 13 | Communication plan distribution | PM | Comms plan | Pending |

### Phase 1 Exit Criteria
- [ ] Migration plan approved by steering committee
- [ ] Risk scoring matrix approved
- [ ] Business rules documented and approved
- [ ] Manual review workflow designed
- [ ] Migration environment ready

---

## Phase 2: Transformation Implementation (Week 3-4)
**Dates**: June 15 - June 28, 2026

### Week 3: June 15-21, 2026

| Day | Date | Task | Owner | Deliverable | Status |
|-----|------|------|-------|-------------|--------|
| Sat | Jun 14 | Development begins | Tech Lead | Sprint plan | Pending |
| Mon | Jun 16 | T1: Name Parser implementation | Backend Dev | Working module | Pending |
| Mon | Jun 16 | T2: Risk Scorer implementation | Backend Dev | Working module | Pending |
| Tue | Jun 17 | T3: Gender Transformer implementation | Backend Dev | Working module | Pending |
| Tue | Jun 17 | T4: Record Type Classifier implementation | Backend Dev | Working module | Pending |
| Wed | Jun 18 | T5: Date Validator implementation | Backend Dev | Working module | Pending |
| Wed | Jun 18 | T6: Confidence Calculator implementation | Backend Dev | Working module | Pending |
| Thu | Jun 19 | T7: PEP Classifier implementation | Backend Dev | Working module | Pending |
| Thu | Jun 19 | Orchestrator integration | Backend Dev | Integrated engine | Pending |
| Fri | Jun 20 | Unit test development | QA | Test suite | Pending |
| Fri | Jun 20 | Code review | Tech Lead | Review complete | Pending |

### Week 4: June 22-28, 2026

| Day | Date | Task | Owner | Deliverable | Status |
|-----|------|------|-------|-------------|--------|
| Mon | Jun 23 | Integration testing | QA | Test results | Pending |
| Mon | Jun 23 | Performance testing | QA | Perf report | Pending |
| Tue | Jun 24 | Error handling implementation | Backend Dev | Error handling | Pending |
| Tue | Jun 24 | Audit trail implementation | Backend Dev | Audit logs | Pending |
| Wed | Jun 25 | Manual review queue implementation | Backend Dev | Working queue | Pending |
| Wed | Jun 25 | Data quality report generation | Data Analyst | Quality report | Pending |
| Thu | Jun 26 | Transformation engine sign-off | Tech Lead | Sign-off doc | Pending |
| Thu | Jun 26 | Documentation completion | Tech Writer | User guide | Pending |
| Fri | Jun 27 | Phase 2 testing complete | QA | Test summary | Pending |
| Fri | Jun 27 | Sprint retrospective | Team | Retrospective | Pending |

### Phase 2 Exit Criteria
- [ ] All 7 transformation modules implemented
- [ ] Unit tests passing (100%)
- [ ] Integration tests passing (100%)
- [ ] Manual review queue working
- [ ] Audit trail functional
- [ ] Documentation complete

---

## Phase 3: Testing & Validation (Week 5-6)
**Dates**: June 29 - July 12, 2026

### Week 5: June 29 - July 5, 2026

| Day | Date | Task | Owner | Deliverable | Status |
|-----|------|------|-------|-------------|--------|
| Mon | Jun 29 | Test data migration (10 records) | QA | Test results | Pending |
| Mon | Jun 29 | Data quality validation | Data Analyst | Validation report | Pending |
| Tue | Jul 1 | Manual review process test | Compliance | Test results | Pending |
| Tue | Jul 1 | Transformation accuracy check | Data Analyst | Accuracy report | Pending |
| Wed | Jul 2 | Full batch migration (50 records) | QA | Migration results | Pending |
| Wed | Jul 2 | Mandatory field validation | QA | Validation report | Pending |
| Thu | Jul 3 | Cross-field validation testing | QA | Test results | Pending |
| Thu | Jul 3 | Risk score validation | Risk Management | Validation report | Pending |
| Fri | Jul 4 | Load testing | QA | Performance report | Pending |
| Fri | Jul 4 | Rollback procedure testing | DevOps | Test results | Pending |

### Week 6: July 6-12, 2026

| Day | Date | Task | Owner | Deliverable | Status |
|-----|------|------|-------|-------------|--------|
| Mon | Jul 7 | Sanctions list integration test | Compliance | Test results | Pending |
| Mon | Jul 7 | PEP classification accuracy test | Compliance | Accuracy report | Pending |
| Tue | Jul 8 | End-to-end testing | QA | E2E results | Pending |
| Tue | Jul 8 | User acceptance testing | Business Users | UAT sign-off | Pending |
| Wed | Jul 9 | Security review | Security Lead | Review report | Pending |
| Wed | Jul 9 | Compliance validation | Compliance | Validation report | Pending |
| Thu | Jul 10 | Defect resolution | Dev | Fixed defects | Pending |
| Thu | Jul 10 | Regression testing | QA | Regression results | Pending |
| Fri | Jul 11 | Pre-production migration dry-run | Ops | Dry-run results | Pending |
| Fri | Jul 11 | Test summary report | QA | Summary report | Pending |

### Phase 3 Exit Criteria
- [ ] All tests passing (100%)
- [ ] UAT sign-off obtained
- [ ] Security review complete
- [ ] Compliance validation complete
- [ ] No critical defects outstanding
- [ ] Rollback procedure tested

---

## Phase 4: Compliance & Sign-off (Week 7)
**Dates**: July 13 - July 19, 2026

| Day | Date | Task | Owner | Deliverable | Status |
|-----|------|------|-------|-------------|--------|
| Mon | Jul 14 | Final data quality report | Data Analyst | Quality report | Pending |
| Mon | Jul 14 | Transformation audit report | Tech Lead | Audit report | Pending |
| Tue | Jul 15 | Compliance review meeting | Compliance | Review minutes | Pending |
| Tue | Jul 15 | Risk management sign-off | Risk Mgmt | Sign-off doc | Pending |
| Wed | Jul 16 | Data governance review | Data Gov | Review complete | Pending |
| Wed | Jul 16 | AML/KYC compliance validation | Compliance | Validation report | Pending |
| Thu | Jul 17 | Legal review | Legal | Review complete | Pending |
| Thu | Jul 17 | Final compliance sign-off | Compliance | Sign-off doc | Pending |
| Fri | Jul 18 | Pre-go-live checklist | QA | Checklist complete | Pending |
| Fri | Jul 18 | Go/no-go decision meeting | Steering Committee | Decision | Pending |

### Phase 4 Exit Criteria
- [ ] All compliance reviews complete
- [ ] Risk management sign-off obtained
- [ ] Legal review complete
- [ ] Final compliance sign-off obtained
- [ ] Go/no-go decision made

---

## Phase 5: Production Migration (Week 8)
**Dates**: July 20 - July 26, 2026

### Pre-Migration (July 20-22, 2026)

| Day | Date | Task | Owner | Deliverable | Status |
|-----|------|------|-------|-------------|--------|
| Sun | Jul 20 | Production backup | Ops | Backup confirmed | Pending |
| Sun | Jul 20 | Pre-migration checklist | QA | Checklist complete | Pending |
| Mon | Jul 21 | Source data validation | Data Analyst | Validation report | Pending |
| Mon | Jul 21 | Target system readiness | Ops | Ready confirmation | Pending |
| Tue | Jul 22 | Stakeholder notification | PM | Notifications sent | Pending |
| Tue | Jul 22 | War room setup | PM | War room ready | Pending |

### Migration Day (July 23, 2026)

| Time | Task | Owner | Status |
|------|------|-------|--------|
| 08:00 | Migration war room active | PM | Pending |
| 09:00 | Pre-migration checks complete | QA | Pending |
| 10:00 | Source data final validation | Data Analyst | Pending |
| 11:00 | Migration execution begins | Tech Lead | Pending |
| 12:00 | Transformation monitoring | Tech Lead | Pending |
| 13:00 | Initial data quality check | QA | Pending |
| 14:00 | Mandatory field validation | QA | Pending |
| 15:00 | Manual review queue processing | Compliance | Pending |
| 16:00 | Post-migration validation | QA | Pending |
| 17:00 | Production sign-off | Business Owner | Pending |
| 18:00 | Migration complete | Project Lead | Pending |

### Post-Migration (July 24-26, 2026)

| Day | Date | Task | Owner | Deliverable | Status |
|-----|------|------|-------|-------------|--------|
| Thu | Jul 24 | 24-hour monitoring | Ops | Monitoring report | Pending |
| Thu | Jul 24 | Data accuracy validation | Data Analyst | Validation report | Pending |
| Fri | Jul 25 | User training delivery | Training | Training complete | Pending |
| Fri | Jul 25 | Issue resolution | Dev | Issues resolved | Pending |
| Sat | Jul 26 | Post-mortem meeting | Team | Meeting minutes | Pending |
| Sat | Jul 26 | Project closure documentation | PM | Closure docs | Pending |

---

## Phase 6: Hypercare & Stabilization (Week 9)
**Dates**: July 27 - August 2, 2026

| Day | Date | Task | Owner | Deliverable | Status |
|-----|------|------|-------|-------------|--------|
| Sun | Jul 27 | Go-live support begins | Support Team | Support active | Pending |
| Mon | Jul 28 | Issue monitoring | Support Team | Issue log | Pending |
| Tue | Jul 29 | Performance monitoring | Ops | Performance report | Pending |
| Wed | Jul 30 | User feedback collection | PM | Feedback summary | Pending |
| Thu | Jul 31 | Stabilization fixes | Dev | Fixes deployed | Pending |
| Fri | Aug 1 | Hypercare review meeting | Team | Review complete | Pending |
| Sat | Aug 2 | Hypercare ends, BAU begins | PM | Handover complete | Pending |

---

## Risk Register

| Risk ID | Risk Description | Impact | Probability | Mitigation | Owner |
|---------|-----------------|--------|-------------|------------|-------|
| R001 | Data quality issues (34% NULL first_name) | High | High | Conditional name parser implemented | Tech Lead |
| R002 | Missing PEP classifications (34% NULL) | High | High | Manual review workflow | Compliance |
| R003 | Risk scoring matrix misalignment | High | Medium | Business approval required | Risk Mgmt |
| R004 | Transformation engine bugs | High | Low | Comprehensive testing | QA |
| R005 | Manual review bottleneck | Medium | High | SLA for review completion | Ops Manager |
| R006 | Sanctions list integration failure | High | Low | Fallback to manual review | Compliance |
| R007 | Go-live delay | High | Medium | Buffer in timeline | PM |

---

## Resource Plan

### Team Composition

| Role | FTE | Allocation | Key Responsibilities |
|------|-----|------------|---------------------|
| Project Manager | 1 | 100% | Overall delivery, stakeholder management |
| Tech Lead | 1 | 100% | Technical implementation, architecture |
| Backend Developer | 2 | 100% | Transformation engine development |
| QA Engineer | 1 | 100% | Testing, validation |
| Data Analyst | 1 | 50% | Data quality, validation |
| Compliance Officer | 1 | 25% | Compliance review, sign-off |
| DevOps Engineer | 1 | 25% | Infrastructure, deployment |
| Risk Manager | 1 | 10% | Risk matrix approval |

### Budget Overview

| Category | Allocation | Notes |
|----------|------------|-------|
| Development | 40 hours | Backend developers |
| Testing | 20 hours | QA resources |
| Compliance | 8 hours | Review and sign-off |
| Contingency | 10 hours | Buffer for issues |
| **Total** | **78 hours** | ~2 FTE for 8 weeks |

---

## Communication Plan

### Regular Updates

| Audience | Frequency | Channel | Owner |
|----------|-----------|---------|-------|
| Steering Committee | Weekly | Email + Dashboard | PM |
| Business Users | Bi-weekly | Email | PM |
| Technical Team | Daily | Standup | Tech Lead |
| Compliance | Weekly | Meeting | Compliance Officer |

### Key Milestones

| Milestone | Notification | Audience |
|-----------|--------------|----------|
| Plan Approval | Email | All stakeholders |
| Transformation Complete | Email + Meeting | Technical team |
| Testing Complete | Dashboard | All stakeholders |
| Go-Live | Email + Meeting | All stakeholders |
| Hypercare End | Email | All stakeholders |

---

## Success Metrics

### Migration Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Data Accuracy | 100% | Record count match |
| Auto-Transformation Rate | ≥95% | Records auto-transformed |
| Manual Review Queue | ≤5% | Records requiring review |
| Zero Data Loss | 100% | Source = Target count |
| Mandatory Field Population | 100% | All required fields filled |
| Zero Validation Errors | 100% | Clean export |

### Post-Migration Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| System Performance | <2s query response | Performance monitoring |
| Data Quality Score | ≥75 | Average confidence |
| User Satisfaction | ≥90% | Survey results |
| Issue Resolution | <24 hours | Support ticket SLA |

---

## Contingency Plans

### Scenario 1: Data Quality Issues

**Trigger**: >10% records require manual review

**Actions**:
1. Pause migration
2. Review transformation logic
3. Adjust confidence thresholds
4. Increase manual review capacity
5. Resume with approval

### Scenario 2: Go-Live Delay

**Trigger**: Critical defect found in Week 7

**Actions**:
1. Assess impact
2. Determine fix duration
3. Communicate delay
4. Adjust timeline
5. Reschedule go-live

### Scenario 3: Compliance Sign-off Not Obtained

**Trigger**: Compliance rejects migration

**Actions**:
1. Understand concerns
2. Implement additional controls
3. Re-submit for approval
4. Escalate if needed

---

## Appendix

### A. Pre-Migration Checklist

- [ ] Migration plan approved
- [ ] Risk scoring matrix approved
- [ ] Business rules documented
- [ ] Transformation engine tested
- [ ] All tests passing
- [ ] UAT sign-off obtained
- [ ] Compliance sign-off obtained
- [ ] Production backup completed
- [ ] Rollback plan tested
- [ ] Communication plan executed

### B. Migration Day Contacts

| Role | Name | Contact |
|------|------|---------|
| Project Lead | TBD | TBD |
| Tech Lead | TBD | TBD |
| Business Owner | TBD | TBD |
| Compliance Officer | TBD | TBD |

### C. Approval Signatories

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Project Manager | | | |
| Tech Lead | | | |
| Risk Manager | | | |
| Compliance Officer | | | |
| Business Owner | | | |

---

**Document Status**: DRAFT - Pending Approval
**Last Updated**: June 3, 2026
**Next Review**: June 6, 2026
