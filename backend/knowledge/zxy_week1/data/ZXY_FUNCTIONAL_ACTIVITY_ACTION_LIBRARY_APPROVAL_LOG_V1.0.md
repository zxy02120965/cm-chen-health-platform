# ZXY FUNCTIONAL_ACTIVITY Action Library Approval Log V1.0

## Asset decision

- Successor asset: `ZXY_FUNCTIONAL_ACTIVITY_ACTION_LIBRARY_FINAL_V1.0.xlsx`
- Previous candidate asset: `ZXY_FUNCTIONAL_ACTIVITY_ACTION_LIBRARY_CANDIDATE_V1.0.xlsx`
- Asset role: clinician-approved project successor asset; not yet connected to runtime
- Approval evidence: `USER_CONFIRMED_CLINICIAN_REVIEW`
- Reviewer name: not provided
- Review date: not provided
- `mdt_confirmed`: `false`

The project confirmed that the five prefilled execution-parameter sets were reviewed and agreed by the relevant clinicians. No reviewer identity, signature, or date was supplied, so none is fabricated in the asset.

## Actions

| action_id | action_name | subtype | source-supported content | clinician-approved project parameters |
|---|---|---|---|---|
| FA-V05 | 踝泵 | BEDSIDE_MOBILITY | bedside/lower-limb activity semantics, source identity | repetitions, sets, frequency, position, execution, stop conditions |
| FA-V18 | 体位变换 | FUNCTIONAL_TRANSFER | bed mobility/position-transfer semantics, progression context | repetitions, frequency, additional frequency, execution, supervision/stop conditions |
| FA-V19 | 卧位到坐位 | FUNCTIONAL_TRANSFER | transfer-training and early out-of-bed pathway semantics, tube-safety context | repetitions, frequency, optional frequency, execution, stop conditions |
| FA-V21 | 坐位到站位/站位到坐位 | FUNCTIONAL_TRANSFER | low-threshold lower-limb functional-training semantics | repetitions, sets, frequency, optional frequency, execution, stop conditions |
| FA-INDOOR | 舒适轻走/维持性室内活动 | DAILY_ACTIVITY_MAINTENANCE | functional-activity role, 3–10 min duration, comfortable-light intensity, E-type context | frequency, optional frequency, segmentation, stop conditions |

All five actions use `session_role = FUNCTIONAL_ACTIVITY`, `knowledge_status = ACTIVE`, `clinical_review_status = APPROVED`, `review_decision = APPROVE`, `clinical_content_status = CLINICIAN_APPROVED`, and `requires_clinical_review = false`.

## Parameter provenance rules

Each populated field has a `parameter_origin` entry in the workbook. The only origins used are:

- `SOURCE_SUPPORTED`: explicitly present in the frozen/existing source material;
- `CLINICIAN_APPROVED_PROJECT_PARAMETER`: supplied in the current project decision and confirmed as reviewed by relevant clinicians.

The project-approved values are not relabeled as `SOURCE_SUPPORTED`, `EXTERNAL_GUIDELINE`, or `MDT_APPROVED`. The asset does not claim `mdt_confirmed=true`.

## Runtime boundary

This successor asset is not referenced by `load_exercises()`, `build_v3_weekly_exercise()`, `v4_exercise_trace`, or E eligibility. Until a later runtime integration phase, E01 remains:

```yaml
functional_activity_materialization:
  status: UNAVAILABLE
  reason_codes:
    - FUNCTIONAL_ACTIVITY_SOURCE_UNAVAILABLE
```

No frozen clinical rule, V3.0 source document, existing action definition, patient schedule, database schema, or published snapshot was changed.
