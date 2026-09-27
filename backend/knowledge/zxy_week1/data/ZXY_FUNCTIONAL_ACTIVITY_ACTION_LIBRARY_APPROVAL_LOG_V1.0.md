# ZXY FUNCTIONAL_ACTIVITY Action Library Approval Log V1.0

## Asset decision

- Successor asset: `ZXY_FUNCTIONAL_ACTIVITY_ACTION_LIBRARY_FINAL_V1.0.xlsx`
- Previous candidate asset: `ZXY_FUNCTIONAL_ACTIVITY_ACTION_LIBRARY_CANDIDATE_V1.0.xlsx`
- Asset role: clinician-approved project successor asset; connected to the V4 runtime for deferred E plans only
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

This successor asset remains independent from `load_exercises()` and `build_v3_weekly_exercise()`. The V4 runtime loader consumes it only for E plans whose formal-aerobic eligibility is `DEFERRED_FOR_NUTRITION_RECOVERY`; A/B/C/D/F plans continue to use their existing V3 action source. E01 now materializes metadata-matched `FUNCTIONAL_ACTIVITY` sessions from this asset.

```yaml
functional_activity_materialization:
  status: MATERIALIZED
  source_asset: ZXY_FUNCTIONAL_ACTIVITY_ACTION_LIBRARY_FINAL_V1.0.xlsx
```

No frozen clinical rule, V3.0 source document, existing action definition, patient schedule, database schema, or published snapshot was changed.
