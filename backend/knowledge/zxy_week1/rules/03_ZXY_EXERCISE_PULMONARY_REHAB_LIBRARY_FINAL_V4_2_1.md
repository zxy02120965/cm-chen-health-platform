# 03_ZXY_EXERCISE_PULMONARY_REHAB_LIBRARY_FINAL

本文件整合 ZXY 术前运动处方生成规则与动作库 V3.0、肺预康复知识库 V2.0、A/B/C/D/E/F 六型回归结果，以及 01/02 FINAL V4.1 对机器合同与患者可执行性的最新要求。

版本：FINAL V4.2.1｜E型正式有氧资格 + F overlay消费边界｜2026-09-23

---

# FINAL EXERCISE & PULMONARY REHAB OPERATING CONTRACT V4.2.1｜E型正式有氧资格 + F overlay消费边界（2026-09-23）

> **版本定位**：03 V4.2.1 不改变动作库、D/E/F 降阶原则、FULL trace、周次数反算、P01–P06 或 minimum sufficient set。本补丁只补两条语义：E 型“0天正式有氧”必须有患者状态依据，不能由 E 标签自动决定；03 不得仅凭一般教育需求自行追加 F overlay。
>
> 执行优先级：`临床安全/BLOCK规则 > ACTIVE MDT配置 > ACTIVE动作/肺预康复库 > 01 Master V4.2.1 > 本03 V4.2.1 > 03 V4.2 > 03 V4.1 > 历史Exercise/Pulmonary规则`。
>
> **Schema兼容性**：继续使用 `EXERCISE_TRACE_V4_2 / PULMONARY_TRACE_V4_2`。

---

## V4.2.1-EP-1｜E 型不等于“禁止正式有氧”

E 的训练方向仍是：止跌/恢复、保肌、低门槛、短时、可分段、优先完成度。正式有氧是否安排，必须由当前状态派生。

生成 E 型周计划前必须形成：

```yaml
formal_aerobic_eligibility:
  phenotype: E
  intake_stability: STABLE|REDUCED|MARKEDLY_REDUCED|UNKNOWN
  weight_trend: STABLE|CONTINUING_LOSS|UNKNOWN
  fatigue_recovery: ACCEPTABLE|LIMITED|POOR|UNKNOWN
  borg_function_review: ACCEPTABLE|LIMITED|UNKNOWN
  safety_level: GREEN|YELLOW|RED
  status: DEFERRED_FOR_NUTRITION_RECOVERY | ALLOWED_LOW_DOSE | NOT_ASSESSED
  reasons: []
```

### 可以暂为 0 天正式有氧

当当前低摄入/继续下降/疲劳或恢复差/Safety 负担使“训练消耗和任务负担”不合适时：

```yaml
formal_aerobic_days_target: 0
functional_activity_days_target: >0_or_as_tolerated
zero_formal_aerobic_reason:
  allowed: true
  reasons: [...]
  reassess_next_week: true
```

这表示**暂缓正式耐力训练**，不是卧床，也不是禁止日常耐受活动。

### 可以安排低剂量正式有氧

若摄入趋稳、体重趋势不再恶化、症状和恢复允许，则 E 型可以安排低强度、短时、可分段的 `FORMAL_AEROBIC`。具体频次、时长和强度从既有 03 / ACTIVE / candidate 规则读取，本补丁不新建固定数字。

### 禁止两种机械化

- `phenotype=E → formal_aerobic_days_target=0` 的固定映射；
- “每天有轻走 → 7天正式有氧”的错误计数。

---

## V4.2.1-EP-2｜E 型 0 有氧时必须通过机器 validator

```yaml
e_formal_aerobic_validation:
  eligibility_status: DEFERRED_FOR_NUTRITION_RECOVERY|ALLOWED_LOW_DOSE|NOT_ASSESSED
  formal_aerobic_days_target: number|null
  zero_day_reason_present: true|false
  functional_activity_preserved_when_safe: true|false|null
  status: PASS|FAIL
```

若 `formal_aerobic_days_target=0` 但没有 `zero_formal_aerobic_reason`，则 FAIL。

若 `eligibility_status=ALLOWED_LOW_DOSE` 却机械写 0 天，也必须进入 review/FAIL，而不能仅凭 E 标签通过。

---

## V4.2.1-EP-3｜03 不自行扩大 F overlay

03 只消费 01 返回的：

```yaml
primary_nutrition_phenotype: A|B|C|D|E|null
complexity_overlay: F|none
```

“患者不知道怎么运动”“第一次学习动作”本身属于教育/熟悉度问题，可通过动作教学、家属示范、简化说明解决；不能由 03 独立升级为 F。

只有 01 已判定 F，03 才应用：减少动作数、拆短、坐姿/扶持、降低协调需求、增加监督、放慢进阶等复杂度策略。

---

## V4.2.1-EP-4｜周次数反算继续以 V4.2 为准

本补丁不改变 V4.2 的计数方式。仍必须：

1. 先生成 Day1–Day7；
2. 从 `session_role` 反算正式有氧/功能活动/抗阻/恢复天数；
3. 与 declared target 对账；
4. `schedule_consistency_validation=PASS` 才可完成输出。

对 E 型尤其要同时展示 `formal_aerobic_days_actual` 与 `functional_activity_days_actual`，避免临床上把“0天正式有氧”误读为“0活动”。

---

# FINAL EXERCISE & PULMONARY REHAB OPERATING CONTRACT V4.2｜真实 FULL TRACE + 周次数自动对账 + CLOSED-WORLD（2026-09-23）

> V4.2 不改变 Exercise V3 动作库、D/E/F 降阶原则、P01–P06 边界和 minimum sufficient set。它只锁定三件事：full trace 必须真实存在；周训练次数必须由 Day1–Day7 自动反算并对账；默认禁止外部指南/网页混入方案。
>
> 执行优先级：`临床安全/BLOCK规则 > ACTIVE MDT配置 > ACTIVE动作/肺预康复库 > 01 Master V4.2 > 本03 V4.2 > 03 V4.1 > 历史Exercise/Pulmonary规则`。

---

## V4.2-EP-0｜CLOSED-WORLD

除非用户明确要求外部研究，否则 03 不得主动引用任何外部指南、网址、协会、论文或试验，也不得新增“参考原则/外部资料校验”章节。

运动和肺预康复只能依据：当前患者资料 + 01/03 本地规则 + ACTIVE 配置/知识库。

---

## V4.2-EP-1｜每个 session 必须有机器可数的 `session_role`

合法值固定为：

```yaml
session_role:
  FORMAL_AEROBIC
  FUNCTIONAL_ACTIVITY
  RECOVERY
  WARMUP
  RESISTANCE
  FLEXIBILITY
```

### 计数规则

- 同一天一个或多个 `FORMAL_AEROBIC` session → 正式有氧日 +1；
- 同一天一个或多个 `RESISTANCE` session → 抗阻日 +1；
- `FUNCTIONAL_ACTIVITY` 不计正式有氧日；
- `RECOVERY` 不计正式有氧日；
- `WARMUP` 不计正式有氧日；
- 一个 session 不得同时既算 FORMAL_AEROBIC 又算 FUNCTIONAL_ACTIVITY；
- 患者端“轻松散步/室内走动”如果只是保持活动，必须后台标 FUNCTIONAL_ACTIVITY 或 RECOVERY，不得为凑次数标成 FORMAL_AEROBIC。

---

## V4.2-EP-2｜先排 Day1–Day7，再由机器反算周次数

`exercise_plan_trace` 必须包含：

```yaml
exercise_plan_trace:
  schema_version: EXERCISE_TRACE_V4_2
  daily_schedule:
    - day: 1
      sessions:
        - session_role: ...
          ...
    ...
    - day: 7
      sessions: ...
```

Day1–Day7 生成完成后，必须派生：

```yaml
weekly_schedule_derived:
  formal_aerobic_days_actual: ...
  functional_activity_days_actual: ...
  resistance_days_actual: ...
  recovery_days_actual: ...
  flexibility_days_actual: ...
```

然后与计划目标对账：

```yaml
weekly_schedule_declared:
  formal_aerobic_days_target: ...
  functional_activity_days_target: ...
  resistance_days_target: ...

schedule_consistency_validation:
  status: PASS|FAIL
  mismatches: []
```

### 典型必须拦截的错误

```text
文字写：抗阻2天
Day1 / Day3 / Day5 实际都有抗阻
→ resistance_days_actual = 3
→ 不能出最终稿
```

最终出稿前必须修正 daily schedule 或候选目标，并重新计数，直到 PASS。

---

## V4.2-EP-3｜EXERCISE_TRACE_V4_2 的 FULL 条件

只有以下全部成立才可 FULL：

- root `exercise_plan_trace` 实际存在；
- Day1–Day7 均物化；
- 休息日有 `sessions: []` + reason；
- 患者端每个运动任务都有后台 action；
- 每个 session 有 `session_role`；
- 每个 action 有 action_id、patient display name、dose status；
- 所有 action 均在 allowed pool；
- 周次数 derived 已完成；
- `schedule_consistency_validation=PASS`。

任何 `exercise_plan_trace_summary` 都只能 SUMMARY_ONLY。

`trace_validation` 至少包含：

```yaml
trace_validation:
  all_7_days_materialized: true|false
  all_patient_actions_mapped: true|false
  all_sessions_have_role: true|false
  all_actions_in_allowed_pool: true|false
  weekly_counts_derived_from_schedule: true|false
  schedule_consistency_pass: true|false
  no_external_unrequested_sources: true|false
```

---

## V4.2-EP-4｜PULMONARY_TRACE_V4_2 的 FULL 条件

```yaml
pulmonary_rehab_trace:
  schema_version: PULMONARY_TRACE_V4_2
  daily_schedule:
    - day: 1
      actions: [...]
    ...
    - day: 7
      actions: [...]
```

必须：

- Day1–Day7 全部存在；
- 某日无肺康复任务时，写 `actions: []` + reason；
- 患者端每个肺康复动作映射到 P01–P06；
- P05 有明确 reason；
- P06 完整记录适应证/设备/医护指导 gate；
- minimum sufficient set 仍然有效，不因 FULL trace 要求而机械铺满动作。

`trace_validation` 至少包含：

```yaml
trace_validation:
  all_7_days_materialized: true|false
  all_patient_actions_mapped: true|false
  all_actions_from_p01_to_p06: true|false
  p05_condition_respected: true|false
  p06_gate_respected: true|false
  minimum_sufficient_set_respected: true|false
  no_external_unrequested_sources: true|false
```

---

## V4.2-EP-5｜03 向 01 返回的 artifact 状态只能由 root object 派生

```yaml
artifact_return:
  exercise_trace:
    present: true|false
    materialization: FULL|SUMMARY_ONLY|MISSING
    schema_version: EXERCISE_TRACE_V4_2|null
    days_materialized: 0-7
    schedule_consistency_pass: true|false

  pulmonary_trace:
    present: true|false
    materialization: FULL|SUMMARY_ONLY|MISSING
    schema_version: PULMONARY_TRACE_V4_2|null
    days_materialized: 0-7
```

不得因为患者端 Day1–Day7 看起来完整，就把机器 trace 自动写 FULL。

---

# 以下完整继承 03 V4.1

> V4.1 的动作选择、安全过滤、A/B/C 覆盖、D/E/F 简化、minimum sufficient set、P05/P06 gate、患者端名称化等规则全部保留；与上方 V4.2 冲突时以 V4.2 为准。


# FINAL EXERCISE & PULMONARY REHAB OPERATING CONTRACT V4.1｜FULL TRACE + 活动角色语义 + 最小充分肺预康复（2026-09-23）

> 版本定位：V4.1 不重做 Exercise V3 动作库，不新增未审核动作，也不改变 Pulmonary V2 的 P01–P06 临床边界。它是在 V4 已稳定的临床逻辑上，针对六型回归暴露出的“summary 冒充 full trace、功能活动被误记为正式有氧、抗阻覆盖不足但理由不透明、肺预康复任务可能机械铺满、患者执行负担缺少机器检查”等问题进行收口。
>
> 与 01/02 的版本关系：本文件必须与 `01_ZXY_MASTER_AGENT_KNOWLEDGE_BASE_FINAL_V4_1.md` 和 `02_ZXY_NUTRITION_COMPONENT_LIBRARY_FINAL_V4_1.md` 同时使用。若本节与下方 V4 基线合同或原始 V3/V2 源规则在“机器语义、trace 完整性、患者执行性”上冲突，以本 V4.1 为准；临床动作内容与禁忌仍以已 ACTIVE MDT 配置、Safety 规则和原始已审核动作库为上限。
>
> 执行优先级：
>
> `临床安全/BLOCK规则 > ACTIVE MDT配置 > ACTIVE动作/肺预康复知识库 > 01 Master V4.1 > 本03 V4.1合同 > 下方03 V4基线 > Exercise V3 / Pulmonary V2源规则与候选模板 > AI自由编排`。

## V4.1-0｜本轮只修什么，不修什么

本轮只做四类精修：

1. **机器合同加固**：`exercise_plan_trace` 与 `pulmonary_rehab_trace` 必须 FULL materialization；summary 只能做摘要，不能满足 content PASS。
2. **活动角色语义**：严格区分 `formal_aerobic`、`functional_activity`、`recovery_walk`、`warmup`、`resistance`、`flexibility`，避免把 D/E/F 的日常轻活动误记为“7天正式有氧训练”。
3. **运动内容质量**：A/B/C 等保肌/功能优先患者在安全允许时应有合理动作覆盖；如果因 Safety、器材、疼痛、功能、执行障碍而减少动作，必须机器可追踪地写明 reduction reason，而不是默默生成不完整方案。
4. **肺预康复最小充分集**：优先给“这个患者真正需要的最少动作”，不是为了看起来完整而每天堆 P01–P05。

本轮明确**不新增**：

- 新的饮水处方；
- 排尿/排便干预模块；
- IMT；
- 激励性肺量计；
- 源动作库未收录的新抗阻/有氧动作；
- AI自创的设备参数、生命体征停止阈值或医学剂量。

---

# V4.1-1｜01 Master `artifact_manifest` 对 03 的硬要求

03 必须向 01 返回两个可验证 artifact：

```yaml
artifact_manifest:
  exercise_trace:
    present: true | false
    materialization: FULL | SUMMARY_ONLY | MISSING
    schema_version: EXERCISE_TRACE_V4_1 | null

  pulmonary_trace:
    present: true | false
    materialization: FULL | SUMMARY_ONLY | MISSING
    schema_version: PULMONARY_TRACE_V4_1 | null
```

只有同时满足：

```text
exercise_trace.present = true
AND exercise_trace.materialization = FULL
AND pulmonary_trace.present = true
AND pulmonary_trace.materialization = FULL
```

03 才能满足 01 V4.1 对 content PASS 的运动/肺预康复 artifact 前置条件。

以下内容**一律只能算 `SUMMARY_ONLY`**：

```text
exercise_plan_trace_summary
pulmonary_rehab_trace_summary
selected_action_ids: [...]
aerobic_days: [...]
resistance_days: [...]
Day1: A01 + R02 + R04
```

即使患者页面已经写得很完整，只要后台没有逐日、逐 session、逐 action 物化完整字段，就不能把 trace 标成 FULL。

---

# V4.1-2｜活动角色必须确定化：功能活动不等于正式有氧

所有患者端出现的“走路、散步、原地踏步、恢复性活动”等，在后台都必须标记 `activity_role`：

```yaml
activity_role:
  functional_activity
  | formal_aerobic
  | warmup
  | recovery_walk
  | resistance
  | flexibility
```

周汇总必须至少分开保存：

```yaml
weekly_activity_summary:
  formal_aerobic_training_days_target: null
  formal_aerobic_training_days_scheduled: 0
  functional_activity_days_target: null
  functional_activity_days_scheduled: 0
  resistance_training_days_target: null
  resistance_training_days_scheduled: 0
  flexibility_days_scheduled: 0
  recovery_days_target: null
  recovery_days_scheduled: 0
```

### 判定规则

- **formal_aerobic**：处方目的明确为有氧/耐力训练，属于本周正式 FITT 训练量的一部分；
- **functional_activity**：为了维持日常功能、减少久坐、保持活动习惯而安排的短时轻活动，不作为正式有氧训练频次计数；
- **recovery_walk**：恢复日的舒适散步/活动，目的为恢复和维持活动，不计正式有氧；
- **warmup**：为抗阻/正式训练准备的短时热身，不单独计为正式有氧日；
- 同一天可同时存在 `functional_activity + formal_aerobic` 或 `warmup + resistance`，但后台必须分别标记；
- D/E/F 可以出现 `functional_activity_days_target=7`，但不能自动推导 `formal_aerobic_training_days_target=7`。

### E 型特别说明

E 型近期非意愿下降、明显低摄入、疲劳时，如果每天只有 3–10 分钟的舒适轻走或维持性室内活动，应优先标记为 `functional_activity`；只有当动作目的、剂量结构和医护审核都明确作为有氧训练时，才计入 `formal_aerobic`。

---

# V4.1-3｜运动计划先满足“临床方向”，再满足“动作数量”

V4.1 不新增固定“每个人必须几项”的绝对硬阈值，而是要求把**训练目的、覆盖、减少理由**写清楚。

## 3.1 抗阻/功能训练覆盖

对 A/B/C 以及其他以保肌/功能为主要目标、且 Safety/功能允许的患者，后台必须声明本周抗阻/功能训练覆盖情况：

```yaml
resistance_coverage:
  coverage_status: ADEQUATE | REDUCED_WITH_REASON | NOT_APPLICABLE | UNKNOWN
  domains_planned:
    - upper_body
    - lower_body
    - functional_pattern
    - trunk_or_postural
  domains_actually_covered: []
  missing_domains: []
  reduction_reasons: []
```

`domains_planned` 不是要求 AI 自由发明动作，也不是强制所有四类都必须出现；它只是把“本周想保护哪些功能/肌群方向”结构化。具体动作仍必须来自允许池。

## 3.2 当动作少于候选组合时

如果 A/B/C 正常候选规则原本允许较完整抗阻组合，但最后只剩 1–3 个动作，可以接受，但必须满足：

```yaml
resistance_coverage:
  coverage_status: REDUCED_WITH_REASON
  reduction_reasons:
    - insufficient_verified_action_pool
    - joint_pain
    - balance_limit
    - equipment_unavailable
    - yellow_safety
    - first_week_skill_learning
    - complexity_overlay_F
```

并进入 `manual_review_reasons`。

禁止：

- 为凑够 4–6 项调用禁忌动作；
- 为“看起来完整”创建未审核动作；
- 只因为 F overlay 就把所有抗阻永久删掉；
- 动作明显不足却不记录原因。

## 3.3 D/E/F 的任务负担

D/E/F 可以减少每次动作数、缩短单次时长、拆分训练、增加恢复日；但必须同时保存：

```yaml
complexity_reduction:
  applied: true | false
  reasons: []
  what_was_reduced:
    action_count: true | false
    duration: true | false
    frequency: true | false
    coordination_demand: true | false
    equipment_demand: true | false
```

内容检查关注的是“是否有合理理由”，不是机械要求所有表型动作数一致。

---

# V4.1-4｜患者端运动方案必须可执行，不是动作清单

患者端每个正式训练日至少应自然语言说明：

- 做什么；
- 做多久/多少次/多少组；
- 是否可以分段；
- 需要什么器材；
- 动作关键点；
- 什么时候减少/取消；
- 什么时候停止并联系医护；
- 当天漏做是否可以补做（默认不补课）。

患者端不得用工程 ID 作为主要显示：

```text
A01 10min + R02 8x1 + R04 8x1
```

而应显示：

```text
缓慢步行10分钟，可拆成2次5分钟；
墙壁俯卧撑8次×1组；
坐姿腿屈伸每侧8次×1组。
```

后台仍完整保留动作 ID。

### Patient executability 检查

```yaml
exercise_patient_executability:
  patient_view_uses_human_readable_names: true | false
  daily_plan_self_contained: true | false
  no_cross_day_reference: true | false
  dose_is_executable: true | false
  equipment_requirements_clear: true | false
  split_option_clear_when_needed: true | false | null
  stop_and_downgrade_rules_visible: true | false
  task_load_matches_function_and_complexity: true | false | null
  formal_vs_functional_activity_semantics_correct: true | false
  action_coverage_or_reduction_reason_documented: true | false
```

其中无法判断的质量项可为 `null`，但必须进入 review item，不能当作 true。

---

# V4.1-5｜`EXERCISE_TRACE_V4_1`：必须 FULL MATERIALIZATION

完整 trace 固定为：

```yaml
exercise_plan_trace:
  schema_version: EXERCISE_TRACE_V4_1
  trace_materialization_status: FULL | SUMMARY_ONLY | MISSING
  exercise_trace_full: true | false

  context_snapshot:
    primary_nutrition_phenotype: A | B | C | D | E | null
    complexity_overlay: F | none
    q56_goal: null
    surgery_window: null
    safety_level: GREEN | YELLOW | RED
    exercise_dose_status: ACTIVE | PROVISIONAL | UNAVAILABLE

  week_goal: ""

  weekly_activity_targets:
    formal_aerobic_training_days_target: null
    functional_activity_days_target: null
    resistance_training_days_target: null
    recovery_days_target: null

  allowed_action_ids: []
  blocked_action_ids: []
  block_reasons: {}
  alternative_action_ids: []

  resistance_coverage:
    coverage_status: ADEQUATE | REDUCED_WITH_REASON | NOT_APPLICABLE | UNKNOWN
    domains_planned: []
    domains_actually_covered: []
    missing_domains: []
    reduction_reasons: []

  complexity_reduction:
    applied: false
    reasons: []
    what_was_reduced:
      action_count: false
      duration: false
      frequency: false
      coordination_demand: false
      equipment_demand: false

  daily_schedule:
    - day: 1
      sessions:
        - session_type: aerobic | resistance | functional | recovery | flexibility | warmup
          session_index: ""
          activity_role: formal_aerobic | functional_activity | recovery_walk | warmup | resistance | flexibility
          purpose: ""
          actions:
            - action_id: A01
              action_name: 缓慢步行
              knowledge_status: ACTIVE | DRAFT | RETIRED | UNVERIFIED
              dose_status: ACTIVE | PROVISIONAL | UNAVAILABLE
              duration_min: null
              repetitions: null
              sets: null
              intensity: null
              rest: null
              split_allowed: null
              equipment: []
              requires_supervision: false
              key_steps: []
              stop_conditions: []
              alternative_action_ids: []
              source_version: ""
              mdt_confirmed: false

  weekly_stop_rules: []
  manual_review_reasons: []

  weekly_summary:
    formal_aerobic_training_days_scheduled: 0
    functional_activity_days_scheduled: 0
    resistance_training_days_scheduled: 0
    flexibility_days_scheduled: 0
    recovery_days_scheduled: 0
    aerobic_action_types_used: []
    resistance_action_ids_used: []
    repeated_resistance_combo_days: []

  trace_validation:
    trace_materialization_status: FULL | SUMMARY_ONLY | MISSING
    exercise_trace_full: true | false
    all_days_present: true | false
    all_sessions_have_activity_role: true | false
    all_patient_actions_have_ids_in_trace: true | false
    all_actions_in_allowed_pool: true | false
    all_actions_have_name: true | false
    all_actions_have_dose_or_explicit_unavailable_status: true | false
    all_training_sessions_have_session_index: true | false
    weekly_frequencies_computable: true | false
    formal_vs_functional_activity_semantics_correct: true | false
    resistance_recovery_rule_satisfied: true | false | null
    action_coverage_or_reduction_reason_documented: true | false
    alternatives_filtered_for_patient: true | false
    safety_overrides_applied: true | false | null
```

### FULL 的最低条件

必须逐日、逐 session、逐 action 物化；不能用 `exercise_plan_trace_summary`、动作 ID 总表或 weekly summary 替代。

即使 `exercise_dose_status=UNAVAILABLE`，仍然可以建立 FULL trace：剂量字段允许为 null，但必须写明 `dose_status=UNAVAILABLE` 与原因；不能因为剂量未知就省略完整对象。

---

# V4.1-6｜运动内容质量检查：准确、个体化、可行

03 必须向 01 返回：

```yaml
exercise_validation_result:
  trace_contract:
    trace_materialization_status: FULL | SUMMARY_ONLY | MISSING
    exercise_trace_full: true | false

  structure:
    all_days_present: true | false
    all_sessions_have_activity_role: true | false
    all_actions_have_valid_ids: true | false
    all_actions_in_allowed_pool: true | false
    weekly_frequencies_computable: true | false

  personalization:
    primary_direction_respected: true | false
    safety_level_respected: true | false
    pain_and_function_filters_applied: true | false | null
    nutrition_recovery_constraints_applied: true | false | null
    complexity_overlay_applied: true | false | null
    preference_and_setting_used_when_available: true | false | null

  patient_executability:
    patient_view_uses_human_readable_names: true | false
    no_cross_day_reference: true | false
    dose_is_executable: true | false
    task_load_matches_function_and_complexity: true | false | null
    split_option_clear_when_needed: true | false | null
    stop_and_downgrade_rules_visible: true | false

  activity_semantics:
    formal_vs_functional_activity_semantics_correct: true | false

  resistance_quality:
    coverage_status: ADEQUATE | REDUCED_WITH_REASON | NOT_APPLICABLE | UNKNOWN
    action_coverage_or_reduction_reason_documented: true | false

  publication_blockers: []
```

### 必须导致运动 content FAIL 的情况

- `trace_materialization_status != FULL`；
- 只有 `exercise_plan_trace_summary`；
- 日程没有 `activity_role`，导致无法区分功能活动和正式有氧；
- 把恢复性散步/日常轻走机械统计为正式有氧频次；
- 使用不在允许池的动作；
- 缺动作名称/剂量状态/停止条件/替代逻辑等关键字段；
- A/B/C 保肌方向被无理由简化成只有有氧；
- 因 F overlay 或黄色状态减少动作，却没有记录 reduction reason；
- 患者端主要显示工程 ID；
- Day1–Day7 使用“同前/同Day2”而未展开。

### 可以 PASS + warning 的情况

- 第一周为了学习动作重复同一抗阻组合；
- A/B/C 只有较少抗阻动作，但因 Safety、器材、动作库核实状态等有明确 `REDUCED_WITH_REASON`；
- D/E/F 正式有氧天数少，但功能活动天数较多；
- 剂量仍为 PROVISIONAL，但患者执行形式与后台 trace 完整；
- 动作 ACTIVE 状态未核实，但来源、状态和发布阻断正确。

---

# V4.1-7｜肺预康复：从“按需选择”升级为 `minimum_sufficient_set`

肺预康复的目标不是动作越多越完整，而是**用最少但足够的动作覆盖当前需要**。

## 7.1 选择顺序保持不变

```text
Safety
→ 呼吸症状/节律
→ 胸廓/上肢功能需求
→ 痰液/排痰需要
→ 设备 + 医护处方/指导
→ 手术窗口/Q56/执行复杂度
```

## 7.2 最小充分动作集

后台必须形成：

```yaml
minimum_sufficient_set:
  required_needs: []
  selected_action_ids: []
  omitted_action_ids: []
  omission_reasons: {}
  excessive_task_load_avoided: true | false
```

判断原则：

- 无明显呼吸症状、无痰、主要问题不是呼吸功能时，首周通常可以只选 1–2 个基础动作；
- 有气促/呼吸节律问题时，P01/P02 优先；
- 有胸廓活动/上肢协同需求时，才考虑 P03/P04；
- 有痰/排痰技能需求时，才加入 P05；
- P06 仍必须满足“排痰需求 + 设备 + 医护处方/指导”三重 gate；
- A/B 的减脂目标不能成为增加肺预康复任务的理由；
- C 型低肌量/疲劳但无明显呼吸问题时，不应为了“预康复完整”每天固定 P01+P02+P04 全套；可根据本周学习目标只保留真正需要的基础动作；
- D/E/F 应进一步考虑疲劳、摄入、执行复杂度，优先 1–2 个容易掌握的动作。

## 7.3 P05 技能教学

无痰患者若安排 P05，必须显式：

```yaml
skill_learning: true
clinical_need_for_clearance: false
reason: preoperative_skill_rehearsal
```

且剂量来源必须有依据。否则不应为了“术前都应该学咳嗽”自动加入。

---

# V4.1-8｜`PULMONARY_TRACE_V4_1`：同样必须 FULL MATERIALIZATION

```yaml
pulmonary_rehab_trace:
  schema_version: PULMONARY_TRACE_V4_1
  trace_materialization_status: FULL | SUMMARY_ONLY | MISSING
  pulmonary_trace_full: true | false

  context_snapshot:
    safety_level: GREEN | YELLOW | RED
    pulmonary_dose_status: ACTIVE | PROVISIONAL | UNAVAILABLE
    dyspnea_or_rhythm_issue: false | true | null
    sputum_present: false | true | null
    sputum_clearance_difficulty: false | true | null
    opep_device_available: false | true | null
    opep_clinician_order_or_guidance: false | true
    surgery_window: null
    complexity_overlay: F | none

  minimum_sufficient_set:
    required_needs: []
    selected_action_ids: []
    omitted_action_ids: []
    omission_reasons: {}
    excessive_task_load_avoided: true | false

  selected_action_ids: []
  blocked_action_ids: []

  daily_schedule:
    - day: 1
      actions:
        - action_id: P01
          action_name: 缩唇呼吸
          purpose: ""
          knowledge_status: ACTIVE | DRAFT | RETIRED | UNVERIFIED
          dose_status: ACTIVE | PROVISIONAL | UNAVAILABLE
          duration_min: null
          repetitions: null
          daily_frequency: null
          skill_learning: false
          equipment: []
          requires_supervision: false
          stop_conditions: []
          alternative_action_ids: []
          source_version: ""
          mdt_confirmed: false

  p05_reason: null
  p06_gate:
    sputum_or_clearance_need: false | true | null
    device_available: false | true | null
    clinician_order_or_guidance: false | true
    eligible: false | true

  manual_review_reasons: []

  trace_validation:
    trace_materialization_status: FULL | SUMMARY_ONLY | MISSING
    pulmonary_trace_full: true | false
    all_days_present: true | false
    all_patient_actions_have_ids_in_trace: true | false
    all_actions_from_p01_to_p06_library: true | false
    all_actions_have_name: true | false
    all_actions_have_dose_or_explicit_unavailable_status: true | false
    minimum_sufficient_set_documented: true | false
    pulmonary_task_load_not_excessive: true | false | null
    p05_condition_respected: true | false
    p06_gate_respected: true | false
    safety_overrides_applied: true | false | null
```

只有逐日、逐动作完整物化并满足 `pulmonary_trace_full=true`，才算 FULL。

---

# V4.1-9｜肺预康复内容质量检查

```yaml
pulmonary_validation_result:
  trace_contract:
    trace_materialization_status: FULL | SUMMARY_ONLY | MISSING
    pulmonary_trace_full: true | false

  structure:
    all_days_present: true | false
    all_actions_have_valid_ids: true | false
    all_actions_have_dose_status: true | false

  personalization:
    symptom_driven_selection: true | false
    minimum_sufficient_set_documented: true | false
    task_load_matches_complexity_and_fatigue: true | false | null
    p05_condition_respected: true | false
    p06_gate_respected: true | false

  patient_executability:
    patient_view_uses_human_readable_names: true | false
    no_cross_day_reference: true | false
    technique_is_explained: true | false
    stop_conditions_visible: true | false

  publication_blockers: []
```

### 必须导致肺预康复 content FAIL 的情况

- `trace_materialization_status != FULL`；
- 只有 `pulmonary_rehab_trace_summary`；
- 使用 P01–P06 之外的正式动作；
- P05/P06 条件违反；
- 患者端与后台选择动作不一致；
- 明显机械铺满动作，但没有 minimum sufficient set 解释；
- 缺动作剂量状态、用途、停止/替代等关键字段；
- Day1–Day7 跨日省略。

### 可以 PASS + warning 的情况

- 稳定患者只选 1–2 个基础动作；
- C/D/E/F 因主要问题不在呼吸系统而减少肺预康复任务；
- P01/P02 反复作为技能巩固，只要总任务合理且目的明确；
- 动作 ACTIVE 状态未核实，但 trace 完整、状态透明、发布被阻断。

---

# V4.1-10｜运动与肺预康复的联合患者执行负担检查

不能分别看起来合理，但合起来让患者一天任务过多。

因此 03 必须额外输出：

```yaml
combined_rehab_burden_check:
  total_structured_task_blocks_per_day: {}
  excessive_same_day_task_stack: false | true | null
  complexity_overlay_respected: true | false | null
  nutrition_recovery_state_respected: true | false | null
  burden_review_items: []
```

重点关注：

- D/E 摄入不足日是否还安排完整抗阻 + 长时间有氧 + 多个肺康复动作；
- F 是否仍然一天堆很多不同任务；
- C 是否因为“保肌 + 肺预康复”导致每日任务过密；
- 恢复日是否真的恢复，而不是把多个漏做项目挪过去补课。

如果任务负担明显与患者功能/摄入/复杂度不匹配，`patient_executability` 至少应 `PASS_WITH_REVIEW`；若已经构成不合理执行方案，则 content FAIL。

---

# V4.1-11｜周复评：按 activity role 分别评价，不再只看“运动完成率”

周复评至少分别统计：

```yaml
weekly_rehab_review:
  formal_aerobic_completion_rate: null
  functional_activity_completion_rate: null
  resistance_completion_rate: null
  pulmonary_skill_completion_rate: null
  pain_trend: null
  fatigue_trend: null
  dyspnea_trend: null
  next_day_recovery: null
  nutrition_or_intake_constraints: []
  safety_events: []
```

进阶时：

- 不得因为功能活动完成率高，就自动增加正式有氧训练；
- 不得因为肺康复动作完成率高，就机械增加 P03/P04/P05；
- D/E/F 的进阶仍先看摄入、体重/肌肉/功能、疲劳和恢复；
- A/B/C 的抗阻进阶同时看动作质量、恢复、疼痛和允许动作池；
- 每次下一周仍只生成新草稿，不覆盖已发布方案。

---

# V4.1-12｜A–F 回归验收：内容层重点看什么

### A

- 功能基础较好时，有氧与抗阻并行；
- 若抗阻动作数低于候选范围，必须说明是动作库核实/器材/首周学习等原因；
- 不把热身或恢复散步计成正式有氧；
- 无呼吸症状时肺预康复用最小充分集。

### B

- 代谢疾病修饰应改变监测与强度，不只改变饮食；
- 活动气促/BORG 较高时可分段、降阶；
- 肺预康复可比 A 稍积极，但仍按症状，不机械全套。

### C

- 保肌/功能是运动主方向；
- 抗阻覆盖质量应高于单纯减脂型，除非 Safety/动作池限制；
- 若无明显呼吸症状，不因为“术前预康复”就每天堆多个肺动作。

### D

- 短时、低负荷、摄入优先；
- 当日摄入差/早饱/疲劳恶化时抗阻可以取消；
- 多数轻走可标为 `functional_activity`，不必全算 formal aerobic；
- 肺康复可只保留 1 个基础动作。

### E

- 不把每天轻走自动写成 7 天正式有氧；
- 重点是维持功能、避免去体能，同时服从营养恢复；
- 肺康复优先 P01/P02；咳嗽但痰液未知时不自动 P05/P06。

### F overlay

- underlying A–E 方向保留；
- 显著减少协调、器材、任务块数；
- 疼痛/低功能动作过滤真实生效；
- 简化理由必须 traceable；
- 不因简化完全删除保肌训练，除非 Safety 阻断。

---

# V4.1-13｜最终执行规则

V4.1 的最终原则是：

> **患者端要“做得了”，后台要“追得清”，临床逻辑要“够用但不过量”。**
>
> 功能活动不冒充正式有氧；summary 不冒充 full trace；动作减少必须有理由；肺预康复采用最小充分集；任何个体化都不能突破 Safety、ACTIVE 配置和已审核动作库边界。

---

# BASELINE EXERCISE & PULMONARY CONTRACT V4｜保留原有临床动作库、周结构与安全规则（仅在不与 V4.1 冲突时适用）

# FINAL EXERCISE & PULMONARY REHAB OPERATING CONTRACT V4｜患者可执行计划 + 后台严格追踪（2026-09-23）

> 版本定位：本节在保留原 Exercise V3 动作库、周组合层、P01–P06 肺预康复动作库和 Safety 规则的基础上，解决 A/B/C/D/E/F 六型回归中暴露的实现不一致。
>
> 本节不重新发明运动动作，也不替代下方原始动作剂量。它负责统一：A–E 与 F 的关系、患者展示与后台 ID 分离、Day1–Day7 自包含排程、候选剂量语义、D/E/F 降阶逻辑、肺预康复选择、替代动作、安全覆盖、机器 trace、周复评和三层 Validator。
>
> 执行优先级：
>
> `临床安全/BLOCK规则 > 已ACTIVE MDT配置 > 已ACTIVE动作/肺预康复知识库 > 01 Master V4 > 本03 V4合同 > 下方 Exercise V3 / Pulmonary V2 源规则与候选模板 > AI自由编排`。

## 0. 本轮修订范围与边界

本 V4 重点解决以下问题：

1. A–F 不能被理解为六套固定运动模板；必须同时读取疾病、功能、症状、摄入、手术窗口、Q56、执行障碍、偏好、器械/场地和 Safety。
2. F 在 01 Master V4 中定义为复杂度 overlay；03 必须用 underlying A–E 决定训练方向，用 F 决定任务复杂度、分段、陪同和进阶速度。
3. 患者端不得被 `A01/R02/L05/P01` 等工程 ID 主导；ID 仅用于后台审计、视频映射和医护审核。
4. Day1–Day7 患者计划必须自包含，不允许“同 Day2”“同上”“组合A同前”等跨日引用。
5. 精确运动/肺预康复剂量若仍是 PENDING/PROVISIONAL，只能形成医护审核草稿，不得伪装为已批准患者任务。
6. A/B/C 抗阻组合、D/E/F 简化策略、动作多样性和恢复间隔需要统一解释，避免不同模型随意放大或缩小。
7. P01–P06 的调用必须严格按症状、痰液、设备、医护处方和功能选择；不得为了“减脂消耗”增加肺预康复剂量。
8. `exercise_plan_trace` 与 `pulmonary_rehab_trace` 必须固定 schema；不能只在正文写动作名后仍宣称后台可追踪。
9. 周复评必须读取真实完成率、症状、恢复、营养/摄入状态、功能趋势和手术窗口，而不是仅凭“完成/未完成”自动进阶。

**本轮不新增**：新的饮水处方、排尿/排便干预模块、IMT、激励性肺量计或源知识库未批准的新运动动作。原知识库已有的脱水、腹泻、便秘、尿量减少等安全信息继续作为 Safety/医护复核信号，但不在本文件扩展为独立处方模块。

---

# 1. 03 文件的最终职责

01 Master V4 决定：

- `primary_nutrition_phenotype: A | B | C | D | E | null`；
- `complexity_overlay: F | none`；
- Safety；
- Q56；
- 手术窗口；
- 疾病/摄入/体成分/功能/执行 modifier；
- 当前方案是否仅为候选/审核草稿。

03 V4 负责把这些上层信息转化为：

```text
本周运动目标
  ↓
允许动作池 allowed_action_ids
  ↓
周有氧/抗阻/柔韧结构
  ↓
每次训练的动作组合
  ↓
Day1–Day7 排程
  ↓
P01–P06 肺预康复选择
  ↓
患者可执行名称/剂量/步骤/停止条件
  ↓
后台 exercise_plan_trace + pulmonary_rehab_trace
  ↓
Content / Safety / Publication Validator
```

### 强制原则

- AI 可以**组合和排程**已允许动作，但不能为正式患者任务自由发明新的运动动作、设备参数、停止阈值或剂量上限。
- 若确实需要库外新动作，只能创建 `DRAFT_ACTION_CANDIDATE` 供 MDT 审核，不得直接进入患者 PUBLISHED 任务。
- 与 02 FOOD 不同，运动领域的“AI自由创造”边界必须更窄：**可以个体化编排，不可以绕过已审核动作库与安全边界。**

---

# 2. 生成前必须读取的输入合同

每次生成第一周或下一周运动/肺预康复前，至少读取：

```yaml
exercise_rehab_context:
  phenotype:
    primary_nutrition_phenotype: A | B | C | D | E | null
    complexity_overlay: F | none
    display_phenotype: A | B | C | D | E | F

  q56_goal: null
  surgery_window: gt8w | 4_8w | 2_4w | 1_2w | le1w | unknown
  safety_level: GREEN | YELLOW | RED
  triggered_rule_ids: []
  blocked_modules: []

  nutrition_recovery_context:
    reduced_intake: false
    early_satiety: false
    nausea: false
    recent_unintentional_weight_loss: false
    meal_completion_low: false

  function_context:
    six_mwt_m: null
    borg: null
    spo2_rest: null
    spo2_post: null
    baseline_activity: null
    fatigue: null
    dyspnea: null
    pain: []
    balance_limit: null
    joint_or_spine_limits: []

  disease_modifiers: []
  medication_relevant_flags: []

  execution_context:
    exercise_preference: null
    available_time: null
    home_or_outdoor: null
    equipment_available: []
    family_support: null
    supervision_needed: null
    digital_or_learning_barriers: []

  pulmonary_context:
    respiratory_symptoms: []
    sputum_present: false
    sputum_clearance_difficulty: false
    hemoptysis_or_blood_sputum: false
    opep_device_available: false
    opep_clinician_order_or_guidance: false

  prescription_state:
    exercise_dose_status: ACTIVE | PROVISIONAL | UNAVAILABLE
    pulmonary_dose_status: ACTIVE | PROVISIONAL | UNAVAILABLE
```

### 数据语义

- `missing` 不得当作 `normal`；
- 未提供关节/平衡/设备情况时，不得默认高复杂度或高负荷动作可用；
- 未提供痰液情况时，不得自动把 P05/P06 当常规任务；
- 红色 Safety 优先于所有周频率、A–E方向和 Q56；
- 黄色 Safety 可降阶、冻结进阶或减少动作数，但不能只在文字里写“注意安全”而计划不变。

---

# 3. A–E 决定训练方向，F 决定复杂度

## 3.1 A–E：训练方向层

A–E 不是固定动作清单，而是改变周结构与优先级：

- **A**：减脂同时保肌；在 Safety 和功能允许时，有氧 + 抗阻并行，不能只给有氧。
- **B**：代谢控制 + 减脂保肌；与 A 相似，但疾病监测和安全优先于强度/频率进阶。
- **C**：肌肉/功能优先；抗阻和功能训练权重更高，不用过量有氧换取体重下降。
- **D**：营养恢复 + 保肌；短时低—中负荷活动，避免高消耗有氧；摄入不足当天不得为了完成次数硬练。
- **E**：止跌/恢复 + 肌肉功能保护；低门槛、短时、可分段，第一周通常不自动进阶；任何继续下降/摄入不足先回营养恢复。

## 3.2 F：复杂度 overlay

F 不作为独立营养方向覆盖 A–E。03 的处理为：

```yaml
primary_training_direction: derived_from_A_to_E_or_function
complexity_overlay: F
```

F overlay 可以：

- 减少每次动作数量；
- 将连续训练拆成 5–10 分钟或更短的小段；
- 优先坐姿、扶持、低协调需求动作；
- 增加家属陪同/监督；
- 减少同一天任务种类；
- 简化记录字段；
- 降低自动进阶速度；
- 根据疼痛/关节/腰背/平衡过滤动作。

F overlay **不能**：

- 把 underlying B/D/E 的营养/恢复逻辑抹掉；
- 为了“简单”删除所有抗阻而只留有氧；
- 为了完成模板调用存在禁忌的动作；
- 自动把所有复杂患者设成同一套动作。

### 兼容旧界面

若 `display_phenotype=F`，后台仍必须保存 underlying `primary_nutrition_phenotype` 或明确 `null`，使运动与营养方向可解释。

---

# 4. 运动处方状态：ACTIVE / PROVISIONAL / UNAVAILABLE

必须和 01 Master V4 的候选参数治理一致。

## 4.1 ACTIVE

```yaml
exercise_dose_status: ACTIVE
```

允许生成正式可发布的精确：

- 周频率；
- 单次时间；
- 次数/组数；
- 强度；
- 休息；
- 进退阶边界；

但仍需通过 Safety 与医护发布流程。

## 4.2 PROVISIONAL

```yaml
exercise_dose_status: PROVISIONAL
```

允许在 TEST/医护审核草稿中生成完整 Day1–Day7 候选剂量，但必须：

- 明确 `candidate / provisional`；
- 保留来源；
- `publication_validation` 阻断直到 ACTIVE/医护审核条件满足；
- 不得把候选 RPE、SpO₂、HR、BP、血糖阈值写成已批准院内阈值。

## 4.3 UNAVAILABLE

```yaml
exercise_dose_status: UNAVAILABLE
```

只能生成：

- 运动类型方向；
- 动作候选；
- 需要医护确认的数据；
- Safety/停止原则；

不得伪造精确周频率、组数、负荷或生命体征阈值。

肺预康复剂量使用同样三态语义：

```yaml
pulmonary_dose_status: ACTIVE | PROVISIONAL | UNAVAILABLE
```

---

# 5. 运动生成必须“先过滤，再组合”，不能先选动作后补禁忌

固定生成顺序：

```text
Safety Gate
  ↓
功能/症状/关节/平衡/设备/场地过滤
  ↓
allowed_action_ids
  ↓
本周频率与组合目标
  ↓
每次训练动作覆盖
  ↓
Day1–Day7 排程
  ↓
替代动作
```

## 5.1 allowed_action_ids 是硬边界

每个被安排的动作必须属于：

```yaml
allowed_action_ids: []
```

若某动作因膝痛、腰痛、平衡差、气促、安全级别、设备不可用等被过滤：

- 不得为了凑满“4–6项”重新调用；
- 只能选择已通过相同过滤的替代动作；
- 若没有安全替代，取消该动作/减少组合并 `manual_review_required=true`。

## 5.2 替代动作不是“自由发挥”

替代动作必须：

- 来自审核动作库；
- 在当前患者 `allowed_action_ids` 内；
- 不违反当前 Safety/关节/平衡/设备条件；
- 在患者端显示真实动作名，不显示工程 ID。

---

# 6. 周结构与 Day1–Day7 排程

## 6.1 先定周总量，再排每天

禁止：每天独立随机选动作。

必须：

```text
先确定本周目标与总频率
→ 再分配到 Day1–Day7
→ 再为每次训练选择动作组合
```

## 6.2 A/B/C 常规保肌组合

沿用 Exercise V3：在功能和 Safety 允许时，A/B/C 的抗阻训练不应整周只给 1 个动作；候选上通常形成多动作组合，并覆盖上肢/下肢/功能等不同模式。

原 V3 的 `4–6项/次` 属于已有候选组合规则；其是否 ACTIVE 由 MDT 配置决定。

如果筛选后不足候选数量：

```yaml
manual_review_required: true
manual_review_reasons:
  - insufficient_allowed_resistance_actions
```

不得调用禁忌动作凑数。

## 6.3 D/E 的训练必须服从摄入与恢复

D/E 或任何存在明显摄入不足/早饱/恶心/疲劳患者：

- 运动目的为功能/保肌，不是热量消耗；
- 有氧优先短时、低负荷、可分段；
- 抗阻可保留，但动作数和总量可减少；
- 当天进食明显不足、恶心/头晕/疲劳加重、恢复变差时，应取消/降阶抗阻；
- 不得为了完成计划次数在 Day7 补练；
- 下一周先看摄入、体重/肌肉/功能和恢复，再决定是否增加运动。

## 6.4 F overlay：完成率优先，但不能无限简化

F overlay 可将每次抗阻从常规多动作组合简化到更少动作，但必须保留“为什么简化”的可追踪理由，例如：

```yaml
complexity_reduction_reasons:
  - knee_pain
  - low_function
  - fatigue
  - time_barrier
```

若 underlying A/B/C 需要保肌，F 不应因为“复杂”就长期只安排有氧；至少应在允许范围内保留可完成的抗阻/功能训练，除非 Safety 或功能限制阻断。

## 6.5 抗阻恢复间隔

沿用原 V3：避免连续高负荷抗阻日。若 ACTIVE 配置未给明确小时数，不由 AI 自行创造固定“必须48/72小时”的院内规则；测试草稿可使用源知识库候选表述并标记候选。

## 6.6 有氧轮换与重复动作

- 若至少有 2 种安全可行有氧形式，优先轮换，避免整周机械重复；
- 若只有 1 种可行形式，可重复使用，但必须记录限制原因；
- 不因为“避免重复”而强行调用患者不适合的第二种动作。

### 抗阻组合多样性

六型回归显示，第一周可能连续三次使用完全相同的抗阻组合。V4 解释为：

- 第一周为了学习动作，重复核心组合**可以接受**；
- 若存在同等安全、同等可执行的替代动作，可在不同抗阻日做 A/B 组合轮换，提高覆盖和可持续性；
- “抗阻组合完全重复”默认属于 `quality_warning`，**不是单独的 content FAIL**；
- 若重复是因为限制导致可用动作不足，应记录原因。

## 6.7 Day1–Day7 患者计划必须自包含

患者端禁止：

```text
同 Day1
同 Day2
同上
组合A同前
按昨日执行
```

即使后台复用同一动作组合，每一天也必须完整显示：

- 动作名称；
- 单次时间/次数/组数；
- 当周第几次；
- 必要的休息/关键动作要点；
- 当日停止/降阶提示。

---

# 7. 患者端、医护端、后台审计端三层分离

## 7.1 Patient-facing

患者端优先显示：

```text
缓慢步行 10分钟，可拆为2×5分钟
墙壁俯卧撑 8–10次×1组
坐姿腿屈伸 每侧8–10次×1组
缩唇呼吸 3分钟/次
```

不应以以下工程形式主导：

```text
A01
R02
R04
P01
allowed_action_ids
session_index
mdt_confirmed
```

患者端替代也必须写动作名称，例如：

```text
“墙壁俯卧撑若肩部不适，可改为坐姿肩推；仍不适则停止上肢推类动作并联系医护。”
```

而不是只写：

```text
R02 → R01
```

## 7.2 Clinician-facing

医护审核端可显示：

- action_id；
- source_version；
- action knowledge status；
- dose status；
- candidate vs ACTIVE；
- allowed/blocked reason；
- 替代 ID；
- video_id；
- manual review reason；
- 计划周频率与患者实际完成。

## 7.3 Audit layer

所有患者端动作都必须在 machine trace 有一一对应记录。患者端隐藏 ID 不等于后台不保存 ID。

---

# 8. 固定 `exercise_plan_trace` schema

每次生成第一周/下一周运动计划，都必须输出完整结构，不允许只在正文出现动作名称。

```yaml
exercise_plan_trace:
  schema_version: EXERCISE_TRACE_V4

  context_snapshot:
    primary_nutrition_phenotype: A | B | C | D | E | null
    complexity_overlay: F | none
    q56_goal: null
    surgery_window: null
    safety_level: GREEN | YELLOW | RED
    exercise_dose_status: ACTIVE | PROVISIONAL | UNAVAILABLE

  week_goal: ""
  aerobic_days_target: null
  resistance_days_target: null
  flexibility_rule: null
  resistance_actions_per_session: null
  aerobic_rotation_min_types: null

  allowed_action_ids: []
  blocked_action_ids: []
  block_reasons: {}
  alternative_action_ids: []

  daily_schedule:
    - day: 1
      training_day: true
      sessions:
        - session_type: aerobic | resistance | flexibility | functional
          session_index: "aerobic#1"
          actions:
            - action_id: A01
              action_name: "缓慢步行"
              patient_display_name: "缓慢步行"
              category: aerobic
              knowledge_status: ACTIVE | DRAFT | RETIRED | UNVERIFIED
              dose_status: ACTIVE | PROVISIONAL | UNAVAILABLE
              duration_min: null
              repetitions: null
              sets: null
              intensity: null
              rest: null
              frequency_note: null
              equipment: []
              requires_supervision: false
              key_steps: []
              stop_conditions: []
              alternative_action_ids: []
              video_id: null
              source_version: ""
              mdt_confirmed: false

  weekly_stop_rules: []
  complexity_reduction_reasons: []
  manual_review_reasons: []

  weekly_summary:
    scheduled_aerobic_days: 0
    scheduled_resistance_days: 0
    scheduled_flexibility_days: 0
    aerobic_action_types_used: []
    resistance_action_ids_used: []
    repeated_resistance_combo_days: []

  trace_validation:
    all_days_present: true | false
    all_patient_actions_have_ids_in_trace: true | false
    all_actions_in_allowed_pool: true | false
    all_actions_have_name: true | false
    all_actions_have_dose_or_explicit_unavailable_status: true | false
    all_training_sessions_have_session_index: true | false
    weekly_frequencies_computable: true | false
    resistance_recovery_rule_satisfied: true | false | null
    aerobic_rotation_rule_satisfied: true | false | null
    safety_overrides_applied: true | false | null
    alternatives_filtered_for_patient: true | false | null
```

### Content Validator 硬规则

以下任一情况存在，运动部分不得 `content_validation=PASS`：

- Day1–Day7 不完整且无明确原因；
- 患者端出现动作，但 trace 中找不到对应 action_id；
- trace 动作不属于 `allowed_action_ids`；
- 有训练动作却没有动作名称；
- 既没有剂量，也没有明确 `dose_status=UNAVAILABLE`；
- 周频率无法从 daily_schedule 重现；
- 使用被 Safety/关节/设备条件明确阻断的动作；
- 替代动作未经当前患者过滤；
- 结构要求的关键字段整体缺失。

以下情况**单独不构成 content FAIL**，但应 warning/发布阻断：

- action ACTIVE 状态尚未核实；
- 精确剂量仍 PROVISIONAL；
- 院内 HR/BP/SpO₂/血糖停止阈值未 ACTIVE；
- 第一周为动作学习而重复相同安全抗阻组合；
- 患者只有一种安全有氧形式，无法满足两种轮换。

---

# 9. 肺预康复 V4：症状驱动，不按表型机械铺满

肺预康复仍以原 P01–P06 知识库为唯一正式动作来源。

## 9.1 选择顺序

```text
先看红/黄 Safety
  ↓
呼吸症状/呼吸节律
  ↓
胸廓/上肢功能需求
  ↓
痰液/排痰困难
  ↓
设备 + 医护处方/指导
  ↓
手术窗口 / Q56 / 执行复杂度
```

## 9.2 P01–P06 最终调用语义

- **P01 缩唇呼吸**：气促/呼吸节律控制，可作为多数稳定患者基础候选之一；
- **P02 腹式呼吸**：基础呼吸控制；
- **P03 胸廓扩张**：胸廓活动/术前技能需要时调用，肩胸疼痛或功能限制需降阶；
- **P04 呼吸-上肢协同**：与功能/运动呼吸节律配合；
- **P05 有效咳嗽**：有痰/排痰需要优先；无痰患者不固定高频使用，若作为术前技巧学习必须明确其“技能学习”属性；
- **P06 OPEP**：仅当“排痰需求 + 已有设备 + 明确医护处方/指导”条件满足时进入；AI不得自行创造设备参数或建议患者自行购买后使用。

## 9.3 多数稳定患者不是“每天P01–P05全部做”

沿用原 Pulmonary V2：多数稳定患者从 P01–P05 按需选 1–3 项；不是机械每天全部推送。

## 9.4 A/B/C/D/E/F 对肺预康复的修饰

- A/B：体重/减脂目标**不能**成为增加肺预康复剂量的理由；
- C：可与抗阻/功能训练协调 P01/P02/P04；
- D/E：摄入不足、乏力时优先简化为低负荷 P01/P02 ± 必要 P05，不将呼吸训练当能量消耗；
- F overlay：第一周可减少同时学习的动作数，优先 1–2 个基础动作，待掌握后再加；
- 任一表型只要出现痰多/排痰困难，都可按条件加入 P05；P06条件始终独立判断。

## 9.5 无痰患者的 P05

六型回归中出现“Day7教学1次 P05”的情况。V4 统一解释：

- 无痰患者**不设固定高频 P05**；
- 若项目/医护希望术前预演有效咳嗽，可在 `skill_learning=true` 且剂量来源明确时安排低频技能教学；
- 若没有 ACTIVE/PROVISIONAL 技能教学规则，不能仅为了“术前都应该学咳嗽”自动加入。

---

# 10. 固定 `pulmonary_rehab_trace` schema

```yaml
pulmonary_rehab_trace:
  schema_version: PULMONARY_TRACE_V4

  context_snapshot:
    safety_level: GREEN | YELLOW | RED
    pulmonary_dose_status: ACTIVE | PROVISIONAL | UNAVAILABLE
    dyspnea_or_rhythm_issue: false
    sputum_present: false
    sputum_clearance_difficulty: false
    opep_device_available: false
    opep_clinician_order_or_guidance: false
    surgery_window: null
    complexity_overlay: F | none

  selected_action_ids: []
  blocked_action_ids: []

  daily_schedule:
    - day: 1
      actions:
        - action_id: P01
          action_name: "缩唇呼吸"
          patient_display_name: "缩唇呼吸"
          purpose: ""
          knowledge_status: ACTIVE | DRAFT | RETIRED | UNVERIFIED
          dose_status: ACTIVE | PROVISIONAL | UNAVAILABLE
          duration_min: null
          repetitions: null
          sets: null
          daily_frequency: null
          skill_learning: false
          equipment: []
          requires_supervision: false
          indications: []
          cautions: []
          stop_conditions: []
          alternative_action_ids: []
          video_id: null
          source_version: ""
          mdt_confirmed: false

  p05_reason: none | sputum | airway_clearance | skill_learning
  p06_gate:
    sputum_or_clearance_need: false
    device_available: false
    clinician_order_or_guidance: false
    eligible: false

  manual_review_reasons: []

  trace_validation:
    all_days_present: true | false
    all_patient_actions_have_ids_in_trace: true | false
    all_actions_from_p01_to_p06_library: true | false
    all_actions_have_dose_or_explicit_unavailable_status: true | false
    p05_condition_respected: true | false | null
    p06_gate_respected: true | false
    safety_overrides_applied: true | false | null
```

### 肺预康复 Content Validator 硬规则

以下情况不得 PASS：

- 患者端出现 P 动作，但 trace 无对应记录；
- 使用 P06 且三项 gate 条件未同时满足；
- 自行生成 OPEP 设备参数；
- 使用不在 P01–P06 审核库的肺预康复动作作为正式任务；
- P05 高频固定调用却没有痰液/排痰或明确技能学习依据；
- 剂量字段缺失且未明确 UNAVAILABLE。

---

# 11. Safety 覆盖规则：计划完成率永远不能压过安全

## 11.1 GREEN

在允许范围内执行计划；是否进阶仍需看完成率、恢复、营养和手术窗口。

## 11.2 YELLOW

根据触发项采取一种或多种：

- 冻结自动进阶；
- 缩短有氧；
- 改分段；
- 减少抗阻动作数/组数；
- 改坐姿或低协调动作；
- 增加恢复日；
- 暂停特定动作；
- 转医护复核。

黄色不是“所有运动停止”，也不是“照原计划执行只多写一句注意安全”。

## 11.3 RED

暂停相关运动/肺预康复任务并进入人工/紧急流程。红色未经医护解除，不能因患者主观“感觉好了”自动恢复。

### 禁止补课

无论 GREEN/YELLOW，只要当天任务因症状、摄入不足或 Safety 未完成：

- 不在次日自动补做；
- 不为了凑周频率把多个高负荷任务堆到 Day6/Day7；
- 周复评按真实完成情况判断。

---

# 12. 周复评与下一周调整：统一顶层语义

03 的原始资料存在 `PROGRESSION_CANDIDATE / AIRWAY_CLEARANCE_REVIEW / SURGERY_WINDOW_SHORTENED` 等局部标签。为与 01 Master V4 统一，V4 顶层调整标签采用：

```text
MAINTAIN
BARRIER_FIRST
PRESERVE_MUSCLE
NUTRITION_RECOVERY
INTENSIFY_CANDIDATE
DEINTENSIFY
SAFETY_REVIEW
```

并按下列方式映射：

- 原 `PROGRESSION_CANDIDATE` → `INTENSIFY_CANDIDATE`；
- `AIRWAY_CLEARANCE_REVIEW` → 作为 `manual_review_reason/subreason`，不作为独立顶层周结论；
- `SURGERY_WINDOW_SHORTENED` → 作为手术窗口 modifier/subreason；
- `DATA_INSUFFICIENT` → 作为数据状态；数据不足时不得自动进阶，顶层通常维持/保守化并说明原因。

## 12.1 运动周复评至少读取

- 实际完成的有氧天数/分钟；
- 实际抗阻天数、动作和组数；
- 症状、RPE/BORG、疼痛和恢复时间；
- 是否出现黄色/红色事件；
- D/E 或任何营养风险患者的实际摄入完成；
- 体重/肌肉/功能趋势（达到 Master 的数据充分性要求时）；
- 手术窗口变化；
- 执行障碍/家属支持/器械问题。

## 12.2 进阶原则

只有在：

- 数据可评价；
- Safety允许；
- 执行稳定；
- 症状和次日恢复稳定；
- D/E营养/摄入没有继续恶化；
- 手术窗口允许；

才可进入 `INTENSIFY_CANDIDATE`。

每次只改变少数关键变量，例如：

- 时长；
- 次数；
- 组数；
- 阻力；
- 动作复杂度；

不得同时大幅增加多个变量。

---

# 13. Publication Governance

运动/肺预康复能否发布，不由 content PASS 单独决定。

正式 PUBLISHED 前至少要求：

```text
content_validation = PASS
clinical_safety_validation != FAIL
计划中的动作属于允许/已批准知识范围
精确剂量所需配置达到项目要求
P06（若使用）设备/处方/指导条件完整
院内停止阈值/相关 Safety 配置满足发布要求
医护审核状态满足 01 Master V4
publication_validation = READY
```

### 未核实知识状态

若动作知识 ACTIVE 状态无法确认：

```yaml
knowledge_activation_status: UNVERIFIED
```

则：

- content 可以在结构完整时 PASS + warning；
- publication 必须 blocked；
- 不得把 unknown 写成 `non_active=[]`。

---

# 14. A–F 六型回归验收要点（V4）

后续每次修改 03 后，至少用以下场景回归：

### A｜绿色、超重/高体脂、4–8周

应看到：

- 有氧 + 抗阻并行；
- 不因减脂增加肺预康复剂量；
- 多种安全有氧形式可轮换；
- 患者端隐藏动作 ID；
- 重复抗阻组合如用于学习可 warning，不机械 FAIL。

### B｜肥胖 + 代谢异常 + 黄色

应看到：

- 疾病/Safety 先降阶；
- 不为了 B 型频率硬凑高强度；
- 血压/糖尿病等只使用院内 ACTIVE 阈值，不自创数值；
- 抗阻保留但不过量。

### C｜肌肉/功能优先 + 黄色

应看到：

- 抗阻/功能优先；
- 不用过量有氧换体重下降；
- 动作筛选考虑疲劳/BORG/功能；
- 肌肉保护优先于减脂。

### D｜低BMI/营养风险/早饱

应看到：

- 运动不以消耗能量为目标；
- 短时有氧 + 低负荷抗阻；
- 当天摄入不足/疲劳增加时可以取消抗阻；
- 不补课、不自动进阶。

### E｜近期非意愿下降 + 摄入约下降50%

应看到：

- `NUTRITION_RECOVERY / PRESERVE_MUSCLE` 方向；
- 低门槛、可分段；
- 摄入/症状决定是否训练；
- 第一周不因为“完成不错”直接自动加量；
- P05 仅按痰液/技能学习条件。

### F overlay｜B方向 + 多共病 + 膝腰痛 + 低功能

应看到：

- underlying B方向仍可识别；
- 运动任务明显简化、分段；
- 膝腰痛动作被过滤；
- 坐姿/扶持/家属陪同优先；
- 不因为 F 简化而自动删掉所有保肌任务；
- 患者端没有工程 ID 主导。

---

# 15. V4 输出顺序建议

统一输出顺序：

```text
患者相关运动/呼吸画像
→ 本周目标
→ Safety/限制摘要
→ 第一周运动患者版（Day1–Day7完整展开）
→ 第一周肺预康复患者版（Day1–Day7完整展开）
→ 停止/降阶条件
→ 周复评与下一周条件
→ exercise_plan_trace
→ pulmonary_rehab_trace
→ knowledge/governance
→ 三层 Validator
→ clinician review notes
```

患者版与 trace 必须一致，但患者版不暴露后台工程 ID。

---

# 16. V4 与下方源规则的解释关系

下方完整保留 Exercise V3、Exercise V2 与 Pulmonary Rehab V2 源内容，作为动作定义、原始剂量候选、Safety、视频映射和审计来源。

如出现以下旧表述，按 V4 解释：

- “依据A–F生成” → 解释为 A–E方向 + F复杂度 overlay + 多维 modifier；
- “患者显示动作ID” → V4 改为患者显示名称，ID后台保留；
- “D/E/F动作数候选” → 未ACTIVE时保持 PROVISIONAL，不视为正式固定处方；
- “每天/每周固定频率” → 只有 ACTIVE 配置或明确候选状态才可作为对应层级数值；
- “同一动作不应机械重复整周” → 解释为有安全替代时优先轮换；若患者限制或第一周学习需要，可合理重复并记录原因；
- 原局部周调整标签 → 按第12节映射到 Master V4 顶层标签；
- 下方术后内容继续保留为来源，但本项目当前术前方案生成不得因存在术后段落而自动调用术后动作路径。

---

# 03_ZXY_EXERCISE_PULMONARY_REHAB_LIBRARY_FINAL

本文件整合运动V3动作库与肺预康复知识库。



---

# SOURCE: 肺结节患者术前运动处方生成规则与动作库_V3.0_完整版_MDT审阅稿(1).docx

肺结节患者术前运动处方生成规则与动作库 V3.0

周处方组合规则 · 动作库 · 7日排程 · 安全替代 · 程序调用约束

完整版｜MDT审阅稿｜在V2.0基础上新增“周处方组合与排程层”

文件结构

1. 术前患者医嘱指南（基础医嘱 + 条件医嘱；按距手术时间和A-F表型修正）

2. 术后患者医嘱指南（0-3天、4-7天、第2-4周）

3. 饮食/运动/肺预康复过程中的停止与暂停条件

4. 绿色/黄色/红色安全分级条件

5. 运动动作库标签及推荐剂量

基础依据：用户现有术前评估表、A-F分型/疾病分级/执行能力/手术时间窗口规则，以及提供的“机能优化-运动”动作资料。原资料未提供的内容在本文中作为“建议的产品/MDT规则”表达，需审核后采用。

第一部分  术前患者医嘱指南

总体原则：每天方案只围绕三件事输出——每日饮食方案、运动方案、肺预康复方案。AI先读取患者表型、疾病风险、执行能力、手术时间窗口和当日安全状态，再从动作/菜品池中组合；同一动作或同一菜式不应机械重复整周。

1. 基础医嘱与条件医嘱的定义

2. 术前时间窗口总规则

3. 每日饮食基础医嘱：由食物升级为“菜品组合池”

AI不只给出“鱼100 g、蔬菜300 g”，而应组合成患者能直接执行的菜品。每餐优先采用“主食 + 1道优质蛋白菜 + 1-2道蔬菜菜 + 按需奶/水果/加餐”的结构，并根据过敏、不耐受、疾病限制和患者口味替换。

菜品池只是“生成素材”，不是固定食谱。AI正式输出必须包含：菜名、主要食材克重/份数、烹饪方式、估算能量/蛋白质/碳水/脂肪、同类替换；不得只输出“少吃一点”“多吃蛋白质”等模糊指令。

4. A-F表型对饮食/运动/肺预康复的修正规则

为减少LLM机械重复：A-F用于改变目标权重和动作/菜品选择概率，不等于“每型固定一套食谱/动作”。若同时存在肌少、营养风险、代谢异常等，安全和营养优先级高于体重目标。

5. 术前运动基础动作池

6. 肺预康复基础动作池

按你的要求，本版本不纳入吸气肌训练器（IMT）和激励性肺量计。

7. 术前条件医嘱映射

第二部分  术后患者医嘱指南（次要模块，至术后30天）

术后A-F仅作为代谢/营养背景标签。优先级调整为：术后安全与并发症风险 > 摄入与水化 > 疼痛控制对活动/呼吸的影响 > 肺复张/排痰和早期活动 > 肌肉与功能恢复 > 原A-F体重目标。术后早期A/B型不继续执行激进减重。

术后条件医嘱

第三部分  饮食/运动/肺预康复过程中的停止与暂停条件

这里的“停止”指停止当前训练、当前饮食调整或相关自动进阶，不等于所有患者都需要停止进食/活动。AI必须先判断症状严重程度，再决定“暂停观察”“转医护”或“紧急处理”。

1. 运动：立即停止当前训练

新发或明显加重的胸痛、胸闷，尤其伴出汗、恶心、呼吸困难或放射不适。

明显或快速加重的呼吸困难，静息状态也难以恢复。

晕厥、接近晕厥、明显头晕或站立不稳。

明显心悸并伴胸闷、头晕、乏力或其他不适。

新发明显神经系统症状，如肢体无力、言语异常、意识异常。

咯血/鲜红色血痰或其他明显出血。

出现明显紫绀、意识改变，或SpO2达到项目MDT预设停止阈值/较基线出现持续明显下降。

血压、心率、血糖等达到项目MDT预设运动停止/红色阈值，或异常同时伴症状。

突发明显腿痛/腿肿、严重关节疼痛或疑似急性损伤。

运动中出现持续恶心、呕吐、极度乏力，休息后不能缓解。

2. 运动：暂停、休息并重新评估

轻度气促明显超过平时，但停止后数分钟可恢复。

BORG主观呼吸困难/疲劳明显超过个人目标区间。

轻度头晕、心悸、异常疲劳、疼痛影响动作质量。

训练当天食欲差、摄入明显不足、睡眠极差或疾病状态较平时差。

次日仍有明显疲劳/肌肉酸痛影响日常活动，提示上一剂量可能过量。

3. 肺预康复：停止/暂停条件

练习过程中胸痛、明显胸闷或呼吸困难迅速加重。

出现咯血/鲜血痰。

反复深呼吸后明显头晕、手足麻木、过度换气不适，立即停止并恢复自然呼吸。

有效咳嗽训练导致明显胸痛、伤口/胸部剧痛（术后）或无法恢复平静呼吸。

SpO2达到MDT预设停止阈值或持续明显下降。

出现喘鸣明显加重、意识异常或紫绀。

4. 饮食方案：停止当前食物/暂停自动调整并转医护

进食后出现疑似食物过敏：全身风团、口唇/舌咽肿胀、呼吸困难、声音嘶哑等；严重者按红色急症流程。

反复呕吐、无法保留饮水/食物，或明显脱水表现。

明显吞咽困难、呛咳/疑似误吸。

持续腹泻、严重腹痛、明显腹胀或黑便/血便。

糖尿病患者出现明显低血糖/高血糖相关症状或达到医护预设阈值。

短期快速体重下降伴明显乏力、功能恶化或摄入持续不足。

新出现明显水肿、尿量明显减少或医护要求限制液体/蛋白等，此时AI不得继续自行强化原营养方案。

AI遇到上述情况时，不得用“坚持一下”“再加练一次”“少吃一顿补偿”等方式处理。相关任务先冻结，按黄色/红色规则转医护。

第四部分  绿色/黄色/红色安全条件

疾病严重程度等级（Ⅰ/Ⅱ/Ⅲ）与产品安全颜色分开。颜色回答“当前是否还能继续居家AI管理及自动进阶”，不是疾病诊断分级。

颜色升级/降级原则

同一时间存在多种异常时取最高等级：红 > 黄 > 绿。

黄色恢复稳定或经医护确认后可回绿；AI不得仅凭一次正常值自动解除持续性异常。

红色必须经医护确认后解除；患者主观“感觉好了”不足以自动恢复进阶。

安全规则优先于A-F目标、减重/增重目标和周计划完成率。

第五部分  运动动作库标签及推荐剂量

标签用于让LLM“筛动作”，而不是自由发挥。每个动作同时配置“单次剂量 + 日/周频率 + 强度 + 进阶/降阶 + 停止条件”。现有动作剂量优先继承用户提供的“机能优化-运动”资料；原资料未给出的频率为产品建议草案，需康复/胸外科MDT确认。

动作标签字段定义（供程序员/LLM使用）

AI每周生成时的调用顺序（建议写入System Prompt）

先读取当周有效医护方案、最新安全等级、A-F表型、疾病等级、执行能力和距手术时间。

先确定本周目标，再生成每天任务；安全与营养充分优先于减重。

饮食：从菜品池选择并组合，符合过敏/禁忌/疾病规则；避免整周重复同一菜。

运动：从动作标签库筛选，每天有氧/抗阻/柔韧按表型和功能组合；不要求每天所有类别都做。

肺预康复：从P01-P05中轮换1-3项；无痰患者不强制高频有效咳嗽。

每次进阶只改变1-3个关键变量（时间、次数、组数或阻力），不同时大幅增加。

出现第3/4部分异常时，停止或冻结相关自动进阶并转医护；红色未经医护确认不得解除。

建议后续由MDT逐项确认：①胸廓扩张训练/“开肺门”的标准动作名称和视频；②各动作强度与SpO2/HR/BP/血糖阈值；③A-F体重目标是否继续沿用当前项目默认百分比；④术后带管和不同术式的动作上限；⑤疾病专属饮食限制。

现有视频资源映射（根据用户提供截图补充）

以下仅依据截图中的视频文件名进行动作/阶段映射，未直接审核视频内容。正式上线前需由康复医学科/胸外科逐个播放确认动作、强度、适应证及是否与标题一致。重复/同类视频建议选1个主版本，避免LLM随机调用多个同质视频。

备用/待审核/排除资源

视频调用补充规则

呼吸操按体位形成“卧位→坐位→站立位”的进阶资源，但AI仍需根据患者当日体位能力选择，不要求一天三种全部完成。

术前≥2周以建立呼吸、上肢/下肢基础活动和力量习惯为主；术前≤1周增加术后技能预演：翻身、卧位到坐位、坐站转换、踝泵及疼痛管理科普。

术后0-3天优先卧位/坐位呼吸、踝泵、股四头肌等长收缩、翻身/体位变换和早期转移；4-7天再逐步加入站立呼吸、肩部/上肢活动、膝屈伸和直腿抬高。

腰背肌、卧位抬臀等不进入所有胸外科患者基础路径，只在术后第2周以后、无切口牵拉/腰背痛且医护许可时条件使用。

同类重复视频（踝泵、股四头肌、直腿抬高、膝屈伸、腰背肌）上线前由MDT选定主版本；另一版本仅保留备用，不同时推送。

第六部分  食物与运动剂量/频率规则（升级）

核心规则：AI可以根据患者A-F表型、疾病风险、肌肉/营养状态、实际距手术时间和执行情况自主计算每日份量与运动剂量，但只能在MDT配置的安全范围内调整。任何正式方案都必须给出“吃多少/做多少 + 多久一次”，不得只给菜名或动作名。

来源说明：运动单次剂量优先沿用用户提供的“机能优化-运动”资料（例如快步走15-20 min起、逐步30-45 min、每周4-5次；抗阻训练每动作2-3组×12-15次、组间休息60-90 s；多数牵伸保持20 s×2次）。该资料未给出的周频率，以及下述食物“标准1份”，均作为产品默认参数草案，需营养科/康复科/胸外科MDT审核后后台配置。

1. 食物标准份量与菜品组合规则

份量缩放规则：菜品库统一存“标准1份”；AI只允许按0.5、0.75、1、1.25、1.5份等离散档位缩放，避免生成任意且难执行的克重。若需要更大调整，优先增减餐次或替换菜品，再提交MDT审核。

2. 主蛋白菜标准配方示例（1人份草案）

3. A-F每日餐次与菜品轮换默认规则

4. 每周运动剂量与频率总框架

5. A-F每周运动组合建议

LLM硬性输出约束：每一天必须明确：①每餐菜名与克重/份数；②当天总餐次与是否加餐；③运动动作、单次时间/次数、组数、当天是否训练及本周第几次；④肺预康复动作和日频率；⑤出现停止/黄色/红色条件时自动覆盖原剂量。

第七部分  V3.0新增：周处方组合与7日排程规则

本部分解决V2.0动作库“能筛动作、但不一定能组成完整一周运动处方”的问题。V3.0将“动作库”与“周处方组合层”分开：动作库回答“能做什么、怎么做、单次剂量多少”，周处方组合层回答“一周做几天、每次组合几个动作、如何分布到Day1-Day7、何时替代/降阶/暂停”。

版本原则：本节优先整合V2.0中已经存在的周频率和组合规则；新增而原资料未明确的组合逻辑均标记为“产品/MDT候选规则”，正式生产使用前由胸外科/康复/护理MDT审核。

1. 周处方生成的三层结构

2. A-F周运动总量与每次组合规则

说明：A/B/C“每次4-6个抗阻动作”、有氧至少轮换2种形式、柔韧每次2-4个相关部位来自V2.0既有组合原则；D/E/F的“每次动作数量”在原资料中未完全明确，以上数量仅作为V3.0产品/MDT候选，需审核后方可进入ACTIVE生产配置。

3. 抗阻动作的组合覆盖规则（V3.0候选）

对于A/B/C等需要常规保肌的患者，生成器不应只选择1个抗阻动作作为整周处方。每次抗阻训练应在“允许动作池”中按不同部位/功能选择4-6项，尽量覆盖以下模式；若患者存在限制则使用替代动作或减少动作数量。

硬性约束：动作适用表型、限制条件、Safety和手术窗口优先于“凑满动作数量”。若筛选后不足4项，系统必须输出“可用抗阻动作不足/需医护调整”，不得为了满足数量而调用禁忌动作。

4. 7日排程规则

先确定“本周总量”，再分配到Day1-Day7；不得每天重新独立随机选动作。

抗阻训练尽量隔日安排，避免连续高负荷日；A/B/C常见候选排程为每周2-3次。

有氧可与抗阻同日，但若患者功能较低、症状增加或执行负担大，可拆开安排。

有氧动作至少轮换2种可行形式；患者仅具备一种可行形式时允许不轮换，并记录原因。

柔韧作为热身/整理，优先与当天抗阻肌群匹配；不要求每天完成整套柔韧库。

肺预康复以每日基础呼吸为主，P05仅在有痰/排痰需要时调用，P06仅有设备且有医护指导/处方时调用。

同一周内每个训练日需标记“本周第几次有氧/抗阻训练”，用于防止频率超量。

如出现黄色/红色Safety条件，暂停/降阶规则覆盖原周排程；不得为了完成周次数而补做高负荷训练。

5. A型患者7日排程示例（非固定处方）

以下仅展示V3.0生成器如何把“有氧4-5天/周 + 抗阻2-3天/周 + 每次4-6个抗阻动作 + 每日基础肺预康复”转成Day1-Day7。具体动作仍必须经过患者Q27/Q35-Q37、Safety、关节/平衡限制、器械条件筛选。

示例并不要求固定在星期几。排程器应根据患者偏好和可执行时间移动训练日，但必须保持周频率和恢复间隔约束。

6. A-F排程模板类型（用于生成器，不直接展示给患者）

7. 周处方生成伪代码/程序约束

1) 读取最新有效assessment/profile：phenotype、Q56、Q27、Q35-Q37、Safety、手术时间窗、执行障碍。

2) 依据A-F确定本周类别频率范围（有氧/抗阻/柔韧/肺预康复）。

3) 从动作库过滤禁忌、不适用表型、设备不可用动作，得到allowed_action_ids。

4) 对每次抗阻训练按组合覆盖规则选择动作；不足最小可用组合时标记manual_review_required。

5) 将周总量排入Day1-Day7，抗阻高负荷日不连续；有氧至少两种形式轮换（若可行）。

6) 为每一天输出：动作ID、剂量、组数、强度、当周第几次、停止条件、替代动作。

7) Safety规则最终覆盖：yellow冻结相关进阶，red暂停相关任务并转人工。

8) 周末依据真实完成率/症状/体成分趋势决定下周MAINTAIN/BARRIER_FIRST/PRESERVE_MUSCLE等。

8. 周处方结构化输出字段（建议Plan Contract新增/固定）

9. 周处方Validator（V3.0新增）

A型：有氧周频率是否在4-5天候选范围；抗阻是否2-3天/周；若功能允许，抗阻每次是否形成4-6项组合。

抗阻高负荷日是否避免连续安排。

有氧是否至少轮换2种可行形式；不能轮换时是否记录限制原因。

每个动作是否属于allowed_action_ids，是否违反关节/平衡/症状/Safety限制。

每一天是否明确“是否训练、单次剂量、组数/次数、当周第几次”。

肺预康复是否遵守P05/P06条件，不机械每天全部推送。

出现yellow/red时是否冻结/暂停相关任务，而不是继续补足周次数。

若知识库不足以形成完整周组合，content_validation应提示“运动处方组合不足”，不能伪装PASS。

10. MDT需重点确认的V3.0新增候选项

D/E/F每次抗阻动作数量的候选下限/上限是否采用本稿建议。

A/B/C每次4-6个抗阻动作是否作为正式ACTIVE规则，还是按功能进一步分层。

“主要肌群/动作模式覆盖”的最小要求是否需要固定（例如上肢+下肢至少各1-2项）。

抗阻日之间最小恢复间隔是否需要写成明确小时数，还是仅保留“避免连续高负荷日”。

短手术窗口（≤2周）是否降低组合复杂度、只保留核心动作。

视频ID与动作ID的正式一一/一对多映射。

不同疾病状态下有氧/抗阻周频率是否需要进一步专科阈值。

11. V3.0上线/调用原则

V3.0不改变既有Safety优先级：Safety > 已ACTIVE MDT配置 > 已审核知识库 > 模板 > 生成器。周处方组合规则只负责在允许范围内组织动作和排程，不能绕过禁忌或创造新剂量。

正式生产调用前，需将本节经MDT批准的组合参数写入结构化配置；未批准的候选规则仅允许TEST_ONLY/clinician-only draft使用。

V3.0变更摘要：新增周处方组合层、A-F周频率与每次动作数量规则、7日排程、组合覆盖、结构化输出字段和周处方Validator；保留V2.0全部动作库与安全规则。


## Table


使用边界：本文件用于AI方案生成与医护审核规则设计。所有临床阈值、能量/蛋白质范围、运动强度上限、红黄灯阈值和术后进阶条件均应由项目MDT最终确认并后台配置。AI只能在已审核动作库与边界内组合方案，不自行改变药物、手术安排或专科治疗。


## Table


级别 | 适用对象 | 生成原则

基础医嘱 | 多数无特殊禁忌、状态稳定的患者 | 每日至少从饮食、运动、肺预康复三个池中各选1组；同类动作轮换；强度由基线功能和手术时间校正。

条件医嘱 | 存在特定症状、功能障碍、代谢疾病、营养风险、肌少风险、执行障碍或恢复需求者 | 在基础医嘱上增减或替换，不是简单叠加；出现安全风险时，条件医嘱优先覆盖基础医嘱。


## Table


距手术时间 | 饮食重点 | 运动重点 | 肺预康复重点

>8周 | 建立饮食/运动/肺预康复习惯；逐步改善体脂、代谢和功能 | 可完整实施渐进有氧+抗阻；每1-2周复评并进阶 | 学习腹式/缩唇/胸廓扩张/有效咳嗽，形成动作熟练度

4-8周 | 主要改善窗口；根据A-F设定减脂、保肌、增重或代谢目标 | 有氧+抗阻均可渐进；每周调整1-3个变量 | 基础动作轮换，逐渐增加胸廓扩张与呼吸-上肢协同

2-4周 | 以可实现的代谢改善、肌肉保护和功能提升为主 | 中等剂量为主，不追求短期高强度 | 巩固呼吸技术，保证患者能独立完成

1-2周 | 减少方案复杂度；避免激进节食；优先营养充分、肌肉与体能维持 | 以熟悉动作和中低强度为主；不临时大幅加量 | 重点熟练腹式、缩唇、胸廓扩张、有效咳嗽

≤1周 | 不设置新的激进减重目标；稳定饮食、睡眠、血糖/血压和体能 | 维持活动，不尝试陌生高强度动作；避免运动后明显疲劳延续至次日 | 以“会做、做对”为主，术前复习咳嗽/呼吸技巧


## Table


餐次 | 基础菜品/组合池（示例，可轮换） | AI使用规则

早餐 | 燕麦牛奶+水煮蛋+水果；全麦馒头+番茄炒蛋+无糖奶/豆浆；杂粮粥+鸡蛋羹+青菜；红薯+酸奶+鸡蛋 | 每周至少准备3-5种早餐组合轮换；按A-F调整主食、奶制品和加餐量。

午/晚餐蛋白菜 | 清蒸鱼；香菇鸡丁；西兰花炒瘦肉；番茄炖牛肉；豆腐菌菇煲；虾仁冬瓜；肉末蒸蛋；芹菜瘦肉 | 优先蒸、煮、炖、少油炒；每餐至少1个蛋白来源；过敏或疾病限制时同类替换。

蔬菜菜 | 蒜蓉西兰花；清炒菠菜；番茄青菜；香菇上海青；彩椒木耳；冬瓜菌菇 | 保证多样化，不用单一“水煮菜”贯穿全周。

主食 | 米饭/杂粮饭；面条；全麦馒头；红薯/玉米；燕麦 | A/B型控制总量与精制碳水；D/E型可提高份量或增加加餐。

加餐 | 牛奶/酸奶；水果；鸡蛋；豆浆；坚果少量；营养加餐（医护确认） | C/D/E型优先用于补蛋白或能量；肾病、糖代谢异常、高尿酸等按规则修正。


## Table


表型 | 项目原目标 | 饮食修正 | 运动修正 | 肺预康复修正

A 超重/高体脂 | 2/4/8周默认体重目标：↓3%-5% / ↓5%-10% / ↓10%-15%（按项目原规则，MDT需审核） | 适度能量负平衡，保证蛋白；多用清蒸鱼、鸡肉、豆腐、蔬菜+适量主食 | 有氧+抗阻并重；避免只做长时间有氧 | 按基础池执行

B 肥胖+代谢异常 | 体重目标同A；同时要求代谢指标改善/稳定 | 在A基础上叠加控糖、控盐、低嘌呤/脂肪肝等疾病规则 | 运动与血压/血糖/心血管状态联动 | 基础池；气促/肺功能异常时降低运动负荷

C 肥胖+肌少风险 | 2/4/8周：↓1%-3% / ↓2%-5% / ↓4%-8%；肌肉≥基线，必要时增加 | 蛋白质和总能量底线优先；每餐均有蛋白菜，必要时蛋白加餐 | 抗阻优先+低冲击有氧；避免过快减重 | 与运动前后呼吸节律结合

D 消瘦/营养风险 | 2周↑1%-2%或停止下降；4周↑2%-5%；8周↑5%-10% | 高营养密度、少量多餐；增加肉末蒸蛋、豆腐鱼、奶/酸奶等易执行组合 | 适量抗阻+功能训练，避免过量有氧 | 低负荷基础池，避免训练导致明显疲劳

E 消瘦+快速下降/肌肉减少 | 2周先停止下降；4周↑1%-3%；8周↑3%-5% | 先保证摄入和蛋白；进食困难者改软食/小份多餐并人工复核 | 低门槛功能+轻抗阻；先恢复再进阶 | 短时、低负荷、以耐受为先

F 复杂/执行困难 | 目标个体化；核心任务完成率约≥70%→≥80%→80%-90% | 减少选择复杂度：固定2-3套可替换菜谱；必要时家属参与 | 把长训练拆成5-10分钟小段，优先患者能完成的动作 | 减少动作数量，优先1-2个熟练基础动作


## Table


类别 | 基础动作池 | 组合原则

有氧 | 缓慢步行、快步走、原地踏步、固定自行车/自行车 | 每周至少轮换2种可行形式；体能差者用间歇方式。

抗阻 | 墙壁俯卧撑、弹力带坐姿划船、坐姿腿屈伸、坐姿/站立提踵、上肢屈肘/伸肘、半蹲（适合者） | 每次选4-6个动作，不要求整库全部完成；C/D/E型优先保肌动作。

柔韧 | 肱二头肌、肱三头肌、斜方肌、三角肌、股四头肌、小腿三头肌、臀中肌、臀大肌牵拉 | 作为热身/整理使用，每次选2-4个与当日训练有关的部位。

核心/躯干 | 坐姿收腹、仰卧屈膝抬腿（功能较好者） | 不是所有患者必做；腰背痛、腹部不适、平衡差时替换。


## Table


动作 | 目的 | 要点 | 建议剂量（MDT确认）

P01 缩唇呼吸 | 气促控制、呼气延长 | 鼻吸约2秒，缩唇缓慢呼气约4-6秒；不需用力 | 约3-5分钟/次，2-4次/日或气促时使用

P02 腹式呼吸 | 膈肌参与、呼吸控制 | 坐位或仰卧位，一手胸前一手腹部；鼻吸腹起、口呼腹落 | 5-10分钟/次，2-4次/日

P03 胸廓扩张训练（暂代“开肺门”） | 胸廓活动和深吸气练习 | 坐/站位，配合双上肢外展或扩胸缓慢深吸气，回位时呼气；动作定义需MDT统一 | 5-10次/组，1-3组/日

P04 呼吸-上肢协同 | 把呼吸节律融入上肢活动 | 例如扩胸/肩部活动时吸气，回位时呼气，避免屏气 | 5-10次/组，1-2组/日

P05 有效咳嗽 | 术前学习排痰与术后准备 | 坐直，深吸气后短暂停顿，连续2次有效咳嗽，随后恢复平静呼吸 | 有痰/需练习时2-5个循环，不作为无痰患者的高频训练

P06 呼气正压震荡排痰阀 | 痰多/排痰困难且已有设备与医护指导 | 按设备和医护确认方法执行 | 条件医嘱，不纳入所有患者基础任务


## Table


情况 | 条件医嘱

活动后气促/呼吸节律乱 | 运动降一级或改间歇；加入P01缩唇呼吸和P02腹式呼吸；必要时缩短每段运动时间

痰多/排痰困难 | 增加P05有效咳嗽；已有医护处方和设备者可用P06；保证允许范围内饮水

肌少/SMI低/肌肉下降 | 优先弹力带/坐姿抗阻、腿屈伸、提踵、墙壁俯卧撑；避免只做长时间有氧

膝/髋痛 | 减少深蹲、半蹲横移；改固定自行车、平地步行、坐姿腿屈伸/提踵等低冲击动作

腰背痛 | 暂停或替换仰卧抬腿、屈腿硬拉等可能增加负荷动作；优先步行、坐姿抗阻

平衡差/头晕史 | 优先坐姿动作、扶椅提踵、墙壁俯卧撑；避免无支撑站立抗阻

A/B型且功能良好、距手术≥4周 | 在安全前提下逐步增加有氧总量和抗阻量

D/E型或进食不足 | 不以运动消耗为目标；短时低中强度，训练后关注进食和疲劳恢复

高血压/糖尿病/心血管病 | 按医护设定的监测阈值决定是否训练及强度；AI不自行修改药物或治疗

执行能力差 | 每日只保留1个饮食重点+1段运动+1个呼吸动作，完成后再进阶


## Table


阶段 | 每日饮食 | 运动 | 肺预康复

0-3天 | 以医嘱允许的流质/半流质或正常饮食为基础，少量多餐；关注恶心、腹胀、摄入不足 | 床上踝泵/轻活动→坐起→站立→短距离步行，按医护允许进阶 | 腹式呼吸、缩唇呼吸、胸廓扩张、有效咳嗽；疼痛影响时先处理疼痛再练

4-7天 | 逐渐恢复规律三餐；每餐安排蛋白质；D/E/C型加强蛋白和能量完成度 | 短距离步行增加频次；轻柔上肢/肩部活动；无并发症时加入低负荷抗阻准备 | 继续基础池；痰多者加强有效咳嗽/排痰；无痰无需高频咳嗽训练

第2周 | 形成稳定饮食结构；监测体重、食欲、摄入和胃肠耐受 | 步行总量渐进；墙壁俯卧撑、坐姿腿屈伸、提踵、轻弹力带动作可在医护许可下加入 | 基础呼吸+胸廓扩张；与步行节律结合

第3周 | 根据A-F逐步恢复代谢目标，但仍以恢复为先 | 有氧+低中强度抗阻组合；根据疼痛和疲劳进阶 | 维持1-2项基础训练，减少不必要重复

第4周 | 根据恢复报告决定转入长期代谢管理或常规康复 | 接近术前可耐受水平者逐步恢复常规运动；异常者继续个体化 | 按症状保留；重点转向自主运动中的呼吸控制


## Table


情况 | 处理

胸腔引流管在位 | 所有下床和上肢活动服从胸外科/护理管路安全要求；不做牵拉管路或大幅度动作；步行需确保管路固定和引流装置位置安全。

疼痛明显 | 先按医嘱镇痛/伤口保护，再做呼吸和活动；若疼痛导致无法深呼吸、咳嗽或行走，标黄转医护。

痰多/咳痰困难 | 增加有效咳嗽及医护批准的排痰措施；若咯鲜血或呼吸困难明显，立即停练并按红色处理。

感染/发热/恢复延迟 | 暂停自动进阶；训练维持在医护重新确认的安全剂量。

A/B型 | 术后早期不追求快速减重；先保证蛋白、血糖/血压稳定和活动恢复。

C型 | 肌肉保护优先，尽早在安全条件下恢复低负荷抗阻。

D/E型 | 优先纠正摄入不足和体重/肌肉继续下降；必要时营养科人工复核。

F型 | 任务简化、分段完成、家属协助；异常和依从性问题更早转人工。


## Table


等级 | 条件 | AI动作

绿色 | 无明显新发/加重症状；生命体征/代谢指标在医护目标内或总体稳定；体重、体脂、肌肉、摄入和功能趋势符合当前目标；饮食、运动、肺预康复基本可执行 | 继续已审核方案；常规记录；按周复评

黄色 | 代谢指标连续偏离医护目标；体重趋势偏离目标但无急症；减重伴肌肉下降；消瘦/营养风险者继续下降；连续多日食欲或摄入不足；轻中度气促、头晕、疲劳、疼痛影响执行；轻度胃肠不耐受；连续漏做任务/用药提醒；运动后恢复明显变差 | 标黄并同步医护；冻结与异常直接相关的自动进阶/调整；其他安全任务可继续；优先补充数据和查找原因

红色 | 明显/持续加重胸痛或胸闷；明显或快速加重呼吸困难；晕厥/近晕厥；意识异常或新发神经症状；明显心悸伴不适；咯血/明显出血；严重过敏；严重低/高血糖症状；误服/重复用药或疑似严重药物不良反应；快速体重下降伴明显乏力/脱水/功能恶化；运动或呼吸训练中出现上述事件 | 立即停止相关运动/肺预康复/自动饮食调整；高优先级转医护；紧急情况按平台预设就医流程；红色仅由医护确认后解除


## Table


ID | 动作 | 标签 | 阶段 | 强度 | 适用/优先 | 推荐剂量 | 停止/慎用 | 默认频率（MDT确认）

P01 | 缩唇呼吸 | 肺预康复/呼吸控制 | 术前全程；术后全程 | 低 | A-F均可；气促优先 | 3-5 min/次，2-4次/日或气促时 | 胸痛、明显加重气促、头晕/过度换气、SpO2异常 | 每日2-4次；气促时可按需追加

P02 | 腹式呼吸 | 肺预康复/呼吸控制 | 术前全程；术后全程 | 低 | A-F均可 | 5-10 min/次，2-4次/日 | 同P01；不能强迫深吸 | 每日2-4次

P03 | 胸廓扩张训练（暂定“开肺门”） | 肺预康复/胸廓活动 | 术前全程；术后医护许可 | 低 | A-F均可；胸廓活动不足 | 5-10次×1-3组/日 | 肩部疼痛、胸痛、气促明显时减量/停 | 每日1-2次

P04 | 呼吸-上肢协同 | 肺预康复/功能 | 术前；术后恢复期 | 低 | A-F均可 | 5-10次×1-2组/日 | 上肢/肩痛、气促、头晕 | 每日1次

P05 | 有效咳嗽 | 排痰/术前技能学习 | 术前有痰/学习；术后按需 | 低-中 | 痰多、排痰困难 | 2次咳嗽/循环×2-5循环，按需 | 咯血、明显胸痛、无法恢复呼吸 | 有痰/排痰需要时按需；不作为无痰患者固定任务

P06 | 呼气正压震荡排痰阀 | 排痰 | 条件使用 | 低-中 | 痰多且已有医护处方/设备 | 按设备和医护处方 | 无处方/不会操作不使用；不适立即停 | 仅按医护/设备处方频率

A01 | 缓慢步行 | 有氧/功能 | 术前全程；术后渐进 | 低 | F、D/E、低体能、术后早期 | 5-10 min起，可分段；逐步增加 | 胸痛、明显气促、晕厥/头晕、SpO2异常 | 建议5-7天/周，可分段完成

A02 | 快步走 | 有氧/减脂/耐力 | 术前>1周，功能允许；术后较晚 | 中 | A/B；功能良好的C | 15-20 min起，逐步30-45 min；4-5次/周 | 同A01；C/D/E避免过量 | 4-5次/周（源资料）

A03 | 原地踏步 | 有氧/低空间需求 | 术前；术后恢复 | 低-中 | F、低场地、低体能 | 1-3 min/段×3-5段，逐步增加 | 平衡差需支撑；头晕/气促停 | 建议3-7天/周，低体能者短时多段

A04 | 固定自行车 | 有氧/低冲击 | 术前；术后医护许可 | 低-中 | 膝髋承重不耐、A/B/C | 5-10 min低阻力起，逐步增加 | 膝痛、胸闷、明显气促 | 建议3-5次/周

A05 | 自行车 | 有氧 | 术前功能良好 | 中 | A/B，平衡良好者 | 10-15 min起，逐步增加 | 平衡差/头晕/术后早期不选 | 建议3-5次/周

A06 | 游泳 | 有氧 | 术前功能良好 | 中 | A/B且无禁忌 | 按个人基础逐步增加 | 术后伤口未愈/感染风险不选；胸闷气促停 | 建议2-3次/周；仅功能良好且无禁忌者

C01 | 坐姿收腹 | 核心/躯干稳定 | 术前 | 低 | A/B/C，腰背可耐受 | 10-15次×1-2组 | 腰痛/腹部不适停 | 建议2-3次/周

C02 | 仰卧屈膝抬腿 | 核心 | 术前功能较好 | 中 | A/B/C选择性 | 10-15次×1-2组 | 腰背痛、腹部不适、低体能慎用 | 建议2-3次/周

S01 | 肱二头肌牵拉 | 柔韧 | 术前；术后恢复 | 低 | A-F | 20秒×2次/侧 | 疼痛超过牵拉感则停 | 训练日或每日1次

S02 | 肱三头肌牵拉 | 柔韧 | 术前；术后恢复 | 低 | A-F | 20秒×2次/侧 | 肩痛/切口牵拉不适减量 | 训练日或每日1次

S03 | 斜方肌牵拉 | 柔韧 | 术前；术后恢复 | 低 | A-F | 20秒×2次 | 颈肩痛加重停 | 训练日或每日1次

S04 | 三角肌牵拉 | 柔韧 | 术前；术后恢复 | 低 | A-F | 20秒×2次/侧 | 肩痛/切口牵拉不适停 | 训练日或每日1次

S05 | 股四头肌牵拉 | 柔韧/下肢 | 术前 | 低 | A-F，平衡良好 | 20秒×2次/侧 | 平衡差改侧卧/扶物；膝痛停 | 训练日或每日1次

S06 | 小腿三头肌牵拉 | 柔韧/下肢 | 术前；术后恢复 | 低 | A-F | 20秒×2次/侧 | 小腿急性疼痛/肿胀不做 | 训练日或每日1次

S07 | 臀中肌牵拉 | 柔韧/髋 | 术前 | 低 | A-F | 20秒×2次/侧 | 髋痛加重停 | 训练日或每日1次

S08 | 臀大肌牵拉 | 柔韧/髋 | 术前 | 低 | A-F | 20秒×2次/侧 | 髋/腰痛加重停 | 训练日或每日1次

U01 | 弹力带站立侧平举 | 抗阻/肩 | 术前 | 中 | A/B/C；功能良好D/E | 2-3组×12-15次 | 肩痛、平衡差改坐姿 | 建议2-3次/周，避免连续高负荷日

U02 | 弹力带扩胸 | 抗阻/背胸/呼吸协同 | 术前；术后恢复 | 中 | A/B/C；胸廓活动需要 | 2-3组×12-15次 | 肩痛、胸痛、术后切口牵拉慎用 | 建议2-3次/周，避免连续高负荷日

U03 | 弹力带站立屈肘 | 抗阻/上肢 | 术前 | 中 | A-E；F可坐姿 | 2-3组×12-15次 | 平衡差改坐姿；避免屏气 | 建议2-3次/周，避免连续高负荷日

U04 | 弹力带站立伸肘 | 抗阻/上肢 | 术前 | 中 | A-E；F可坐姿 | 2-3组×12-15次 | 肩部受限慎用 | 建议2-3次/周，避免连续高负荷日

L01 | 弹力带马步半蹲 | 抗阻/下肢 | 术前 | 中-较高 | A/B/C，膝髋功能良好 | 2-3组×12-15次 | 膝髋痛、平衡差、低体能慎用 | 建议2-3次/周，避免连续高负荷日

L02 | 弹力带半蹲横移 | 抗阻/臀中肌 | 术前 | 中-较高 | A/B/C，平衡良好 | 每方向15-20步×1-2组 | 膝髋痛/平衡差不选 | 建议2-3次/周，避免连续高负荷日

L03 | 弹力带屈腿硬拉 | 抗阻/臀腿后链 | 术前 | 中-较高 | A/B/C，动作技术良好 | 2-3组×12-15次 | 腰背痛/动作控制差不选 | 建议2-3次/周，避免连续高负荷日

L04 | 弹力带站立勾腿 | 抗阻/腘绳肌 | 术前 | 中 | A-E，扶椅 | 2-3组×12-15次/侧 | 平衡差必须扶物；膝痛慎用 | 建议2-3次/周，避免连续高负荷日

L05 | 站立提踵 | 抗阻/小腿/平衡 | 术前；术后恢复 | 低-中 | A-F | 10-15次×2-3组 | 平衡差扶物；小腿急痛/肿胀不做 | 建议2-4次/周

L06 | 靠墙静蹲 | 抗阻/下肢 | 术前 | 中 | A/B/C，膝功能良好 | 20-45秒×2-3组 | 膝痛、头晕、低体能不选 | 建议2-3次/周

R01 | 坐姿肩推（徒手/极轻负重） | 抗阻/上肢 | 术前；术后恢复 | 低-中 | C/D/E/F低体能可用 | 8-15次×1-3组 | 肩痛/胸部牵拉不适停 | 建议2-3次/周

R02 | 墙壁俯卧撑 | 抗阻/上肢/胸肩 | 术前；术后恢复 | 低-中 | A-F，低体能友好 | 8-15次×1-3组 | 肩痛、胸痛、术后切口不适停 | 建议2-3次/周

R03 | 弹力带坐姿划船 | 抗阻/背部 | 术前；术后恢复 | 低-中 | C/D/E/F；平衡差者优先 | 8-15次×1-3组 | 肩/背痛，术后牵拉不适停 | 建议2-3次/周

R04 | 坐姿腿屈伸 | 抗阻/股四头肌 | 术前；术后恢复 | 低-中 | C/D/E/F、低体能 | 8-15次×1-3组/侧 | 膝痛明显停 | 建议2-3次/周

R05 | 坐姿提踵 | 抗阻/小腿 | 术前；术后早期恢复 | 低 | A-F、低体能 | 10-20次×1-3组 | 小腿疼痛/肿胀不做 | 建议2-4次/周


## Table


字段 | 示例值 | 用途

stage | preop_all / preop_gt1w / postop_early / postop_recovery | 可被哪个时间阶段调用

domain | breathing / aerobic / resistance / flexibility / core / functional | 动作类别

intensity | low / low_mod / moderate / mod_high | 默认强度层级

phenotype | A/B/C/D/E/F | 优先或可用表型；不是绝对禁忌

indication | dyspnea / sputum / sarcopenia / obesity / low_function / joint_limit / balance_limit | 条件调用标签

position | supine / sitting / standing / walking / cycling | 体位/形式

equipment | none / chair / wall / resistance_band / bike / OPEP | 器械

requires_supervision | yes/no/conditional | 是否需陪同/医护确认

stop_rule | 关联第3部分规则ID | 出现对应异常时停止

progression | time/reps/sets/resistance | 允许的进阶维度，每次只调整1-2个


## Table


视频ID | 视频文件名 | 分类 | 术前阶段 | 术后阶段 | 级别 | 调用说明

V01 | 三位一体呼吸操之卧位呼吸操-运动 | 肺预康复/体位化呼吸 | 术前全程；≤1周重点预演 | 术后0-3天优先；后续按需 | 基础 | 与P01-P04呼吸动作池关联；具体动作内容需视频审核

V02 | 三位一体呼吸操之坐位呼吸操-运动 | 肺预康复/体位化呼吸 | 术前全程 | 术后可坐起后优先 | 基础 | 与P01-P04呼吸动作池关联；术后早期由卧位过渡到坐位

V03 | 三位一体呼吸操之站立位呼吸操-运动 | 肺预康复/体位化呼吸 | 术前全程，功能允许 | 术后能安全站立后 | 基础 | 用于站立/步行阶段呼吸控制；不替代具体呼吸技术教学

V04 | 术后疼痛管理-科普 | 科普/疼痛与康复配合 | 术前≤1-2周预教育 | 术后0-7天重点 | 基础教育 | 不是运动动作；用于解释镇痛与咳嗽、呼吸、活动的关系

V05 | 踝泵-运动 | 床旁活动/循环/下肢 | 术前≤1周技能预演可选 | 术后0-3天基础 | 基础（术后） | 与“踝泵运动-运动”疑似同类，建议审核后二选一主视频

V06 | 踝泵运动-运动 | 床旁活动/循环/下肢 | 术前≤1周技能预演可选 | 术后0-3天基础 | 备选 | 与V05重复候选

V07 | 股四头肌舒缩-运动 | 下肢等长力量/床旁 | 术前低体能者可选 | 术后0-3天基础 | 基础（术后） | 与“股四头肌等长舒缩运动-运动”同类，建议二选一

V08 | 股四头肌等长舒缩运动-运动 | 下肢等长力量/床旁 | 术前C/D/E或低体能者可选 | 术后0-3天基础 | 备选 | 与V07重复候选

V09 | 直腿抬高-运动 | 下肢抗阻/功能 | 术前C/D/E或低体能者 | 术后4-7天后、耐受允许 | 条件 | 与“直腿抬高运动-运动”同类；术后早期不强制

V10 | 直腿抬高运动-运动 | 下肢抗阻/功能 | 术前C/D/E或低体能者 | 术后4-7天后、耐受允许 | 备选 | 与V09重复候选

V11 | 膝关节屈伸锻炼-运动 | 下肢活动度/功能 | 术前可作为低门槛活动 | 术后4-7天起 | 基础/条件 | 与“膝关节屈伸运动-运动”同类，建议二选一

V12 | 膝关节屈伸运动-运动 | 下肢活动度/功能 | 术前可作为低门槛活动 | 术后4-7天起 | 备选 | 与V11重复候选

V13 | 上肢的功能锻炼-运动 | 上肢功能/肩胸活动 | 术前全程 | 术后4-7天起，切口/疼痛允许 | 基础 | 可与P03/P04胸廓扩张、呼吸-上肢协同组合

V14 | 腕关节和肘关节屈伸运动-运动 | 上肢关节活动 | 术前低体能/活动受限者可选 | 术后0-3天床旁轻活动 | 条件 | 低负荷；不能替代肩胸活动

V15 | 爬墙及耸肩运动-运动 | 肩关节活动/胸廓功能 | 术前肩部活动受限者；≤1周可预演 | 术后4-7天起，医护许可 | 条件 | 适合胸外科术后肩部活动恢复；疼痛/牵拉明显时减量或停

V16 | 翻身-运动 | 床上功能/体位转换 | 术前≤1周技能预演 | 术后0-3天基础 | 基础（术后） | 与轴线翻身/体位变换内容可能重叠，按视频内容选主版本

V17 | 轴线翻身-运动 | 床上功能/体位转换 | 术前≤1周技能预演 | 术后0-3天条件/备选 | 备选 | 若视频强调骨科脊柱保护，不应机械套用于肺结节患者；需内容审核

V18 | 体位变换-运动 | 床上功能/体位转换 | 术前≤1周技能预演 | 术后0-3天基础 | 基础（术后） | 用于从卧位活动向坐起/站立过渡

V19 | 卧位到坐位-运动 | 转移训练 | 术前≤1周重点预演 | 术后0-3天基础 | 基础（术后） | 适合早期下床路径；带管者需叠加管路安全规则

V20 | 坐位到卧位-运动 | 转移训练 | 术前≤1周预演 | 术后0-3天基础/按需 | 基础（术后） | 与V19配套

V21 | 坐位到站位，站位到坐位-运动 | 转移/功能训练 | 术前1-2周可练；≤1周重点预演 | 术后0-7天渐进 | 基础 | 可作为低门槛下肢功能训练；头晕/平衡差需扶持

V22 | 坐位卧位-运动（截图文件名，待确认） | 转移训练 | 术前≤1周可选 | 术后0-3天备选 | 备选 | 文件名含义不够清晰；审核视频后决定是否保留

V23 | 卧位抬臀-运动 | 核心/臀肌/床上功能 | 术前功能允许者可选 | 术后第2周后条件使用 | 条件 | 胸部切口疼痛、腰背痛、低体能者慎用

V24 | 腰背肌锻炼-运动 | 核心/腰背力量 | 术前功能允许者可选 | 术后第2-4周条件使用 | 条件 | 不是肺结节康复核心动作；有腰背痛者需谨慎

V25 | 腰背肌功能锻炼-运动 | 核心/腰背力量 | 术前功能允许者可选 | 术后第2-4周条件使用 | 备选 | 与V24同类，建议审核后二选一


## Table


视频ID | 视频文件名 | 分类 | 术前 | 术后 | 状态 | 原因/处理

V26 | 握拳、伸指及对指运动-运动 | 手部活动/末梢活动 | 非术前核心 | 术后床旁可选 | 备用 | 对肺结节主路径价值较低；仅作为低负荷末梢活动备用

V27 | 屈指90度及虎爪练习-运动 | 手部专项活动 | 不建议主路径 | 不建议主路径 | 暂不纳入 | 更偏手部专项康复，缺乏肺结节主路径必要性

V28 | 髋骨推移训练-运动 | 髋/骨盆功能（名称推断） | 暂不纳入主路径 | 暂不纳入主路径 | 待审核 | 仅从文件名无法确认动作和适应证，需看视频后再决定

V29 | 踝关节置换术后如何转换体位-运动 | 踝关节置换专项 | 不适用 | 不适用 | 排除 | 病种专项，与肺结节围术期主路径不匹配

V30 | 下肢支具的佩戴方法-运动 | 支具专项 | 不适用 | 不适用 | 排除 | 与肺结节围术期主路径不匹配


## Table


类别 | 建议标准1份（产品草案） | 每餐/每日调用方式 | A-F调整原则 | 备注

熟制主食 | 熟米饭/杂粮饭80-120 g；面/杂粮等按等量碳水替换 | 正餐通常1份起，由AI按总能量调整为0.5/0.75/1/1.25/1.5份 | A/B偏低端；C维持；D/E可上调或增加加餐 | 具体等量替换表由营养科配置

薯类/玉米 | 100-150 g/份 | 可替代部分主食 | 同上 | 与米面同餐时需计入总主食量

鱼/禽/瘦肉 | 生重约75-100 g/份 | 午/晚餐每餐优先1份主要蛋白来源 | C/D/E优先保证；A/B不因减脂取消蛋白 | 肾功能/其他疾病限制优先覆盖

鸡蛋 | 1个约50 g/份 | 早餐或菜品中使用；可与其他蛋白搭配 | C/D/E可按总蛋白目标调整 | 特殊疾病/个人医嘱优先

豆腐/豆制品 | 豆腐约100-150 g/份 | 可作为主蛋白菜或替换部分肉类 | A-F均可，按疾病限制调整 | 过敏/不耐受时替换

奶/无糖酸奶/无糖豆浆 | 约200-250 mL(g)/份 | 早餐或加餐1份 | D/E可作为增加能量/蛋白的简便加餐 | 乳糖不耐或过敏者替换

蔬菜 | 生重约150-200 g/道 | 午/晚餐各1-2道蔬菜菜 | A/B强调多样化；D/E不以大量低能量蔬菜挤占主食/蛋白 | 按胃肠耐受调整

水果 | 约150-200 g/份 | 通常作为餐间/加餐，由AI结合血糖与总能量安排 | 糖代谢异常需结合个人目标 | 果汁不默认等同整果

坚果 | 约10 g/小份 | 可作为加餐或菜品点缀 | D/E可用于提高能量密度；A/B控制总量 | 过敏者禁用

烹调油 | 约3-5 g/一道家庭菜 | 计入菜品总能量，不单独“自由添加” | A/B控制总量；D/E仍需兼顾烹饪可接受性 | 疾病专属脂肪限制优先


## Table


菜品 | 1份主要食材 | 建议烹饪 | AI调用说明

番茄炒蛋 | 鸡蛋2个 + 番茄约200 g + 烹调油约3-5 g | 少油炒 | 可作早餐/正餐蛋白菜；与主食和蔬菜组合

清蒸鱼 | 鱼肉约100 g | 清蒸 | A-F均可；按过敏/疾病限制替换

香菇鸡丁 | 鸡肉约100 g + 香菇约100 g | 少油炒/焖 | 适合作为午/晚餐主蛋白菜

西兰花瘦肉 | 瘦肉约75-100 g + 西兰花约200 g | 少油炒 | 兼顾蛋白和蔬菜；另配适量主食

番茄炖牛肉 | 瘦牛肉约80-100 g + 番茄约200 g | 炖 | D/E可配较完整主食；A/B按总能量缩放

豆腐菌菇煲 | 豆腐约150 g + 菌菇约100 g + 绿叶菜约100 g | 炖/煮 | 可作为植物蛋白主菜

虾仁冬瓜 | 虾仁约80-100 g + 冬瓜约250 g | 清炒/煮 | 海鲜过敏者禁用

肉末蒸蛋 | 瘦肉末约50 g + 鸡蛋1个 | 蒸 | 食欲差、咀嚼困难或D/E型可优先考虑


## Table


表型 | 默认餐次结构 | 菜品剂量倾向 | 轮换/频率规则

A 超重/高体脂 | 3餐为主；是否加餐由能量与饥饿情况决定 | 主食/高能量食物偏低端；每餐保留主要蛋白 | 同一主菜原则上不连续两天；早餐至少3种组合轮换

B 肥胖+代谢异常 | 3餐为主；加餐按疾病与用药需要 | 在A基础上叠加控糖/控盐/低嘌呤等规则 | 疾病规则优先；不以跳餐补偿超量

C 肥胖+肌少风险 | 3餐 + 0-1次蛋白型加餐（按目标） | 蛋白份量优先保证；主食/能量不做激进下调 | 每日至少3个餐次出现明确蛋白来源

D 消瘦/营养风险 | 3餐 + 1-2次加餐 | 提高能量密度和蛋白完成度，少量多餐 | 优先患者易接受菜品；避免大量低能量食物挤占正餐

E 快速下降/肌肉丢失风险 | 3餐 + 1-2次加餐；必要时更小份多餐 | 先停止摄入不足和继续下降，再谈体重目标 | 每日重点监测实际摄入完成度；无法达标转营养科

F 复杂/执行困难 | 优先简化为3个核心餐次，必要时1次简便加餐 | 份量和菜品复杂度服从可执行性和疾病安全 | 固定少量“常用安全菜品”允许重复，不为追求多样化增加负担


## Table


类别 | 单次基础剂量 | 默认周/日频率 | 适用重点 | 进阶规则

肺预康复 | 按P01-P05动作库单次剂量 | 基础呼吸每日练；有效咳嗽仅按痰液/排痰需要 | A-F均可 | 先保证动作正确，再增加时间/次数；不同时大幅增加

低强度步行 | 5-10 min起，可分段 | 建议5-7天/周 | 低体能、F、D/E、术后恢复 | 先增加单段耐受或总时间，再提高速度

快步走 | 15-20 min起，逐步30-45 min | 4-5次/周（源资料） | A/B及功能良好C | 症状稳定后逐步延长；C/D/E避免用过量有氧换取体重下降

固定自行车/自行车 | 5-15 min低阻力/基础起 | 建议3-5次/周 | 低冲击有氧；平衡良好者 | 先时间后阻力；术后须医护许可

抗阻训练 | 源资料一般为每动作2-3组×12-15次，组间60-90 s | 建议2-3次/周，避免连续高负荷日 | C优先；A/B保肌；D/E增肌恢复 | 每次只调整1个变量：次数、组数或阻力

柔韧/牵伸 | 多数动作20 s×2次/侧（源资料） | 训练日或每日1次 | 作为热身/整理及局部活动受限条件项 | 只到牵拉感，不追求疼痛

术后床旁/转移 | 小量、多次、逐步体位进阶 | 频率由术后医护方案设定；产品可默认每日多次短任务 | 0-7天为主 | 卧位→坐位→站立→步行，未达到前一级不进阶


## Table


表型 | 有氧 | 抗阻/力量 | 肺预康复与注意

A | 有氧4-5天/周为主，可快走/自行车轮换 | 2-3天/周 | 每日基础呼吸；不以只做有氧替代保肌

B | 按血压/血糖/心血管状态选择3-5天/周 | 2-3天/周，疾病稳定后实施 | 每日基础呼吸；疾病监测规则优先

C | 3-5天/周低-中强度，避免过量 | 2-3天/周优先，是核心模块 | 每日基础呼吸；肌肉/功能下降则不继续强化减重

D | 短时有氧3-5天/周或日常步行，避免高消耗 | 2-3天/周低-中负荷 | 每日基础呼吸；保证摄入完成度后再训练

E | 以短时功能活动为主，耐受后再增加 | 2-3天/周低门槛保肌/恢复 | 每日基础呼吸；持续下降/明显乏力时暂停自动进阶

F | 按可执行性拆成短任务，周总量个体化 | 1-3天/周或分散低负荷，由障碍决定 | 呼吸/运动任务均简化；安全和完成率优先


## Table


层级 | 回答的问题 | 主要输入 | 主要输出

动作层 | 这个动作是否适合患者？单次做多少？ | 动作标签、功能限制、Safety、设备 | 动作ID、单次剂量、强度、停止条件、替代动作

周组合层 | 这一周做几天？每次组合几个动作？ | A-F表型、Q56、Q27/Q35-Q37、手术窗、Safety | 有氧周频率、抗阻周频率、每次动作数量、柔韧/核心规则

7日排程层 | 具体哪一天做什么？ | 周组合结果、恢复间隔、执行偏好、患者日程 | Day1-Day7任务、当日第几次训练、替代/暂停规则


## Table


表型 | 有氧周频率 | 抗阻周频率 | 抗阻每次动作数 | 柔韧/整理 | 肺预康复 | 核心目标

A | 4-5天/周；至少轮换2种可行形式 | 2-3天/周 | 4-6个动作/次 | 训练日选2-4个相关部位 | 每日基础呼吸；按症状选1-3项 | 减脂同时保肌

B | 3-5天/周；随血压/血糖/心血管状态修正 | 2-3天/周，疾病稳定后实施 | 4-6个动作/次，优先低-中风险 | 训练日选2-4个相关部位 | 每日基础呼吸；疾病监测优先 | 减脂+保肌+代谢控制

C | 3-5天/周低-中强度，避免过量 | 2-3天/周，抗阻优先 | 4-6个动作/次，覆盖主要肌群 | 训练日选2-4个相关部位 | 每日基础呼吸；功能下降时冻结减量强化 | 保肌/增肌优先

D | 短时有氧3-5天/周或日常步行 | 2-3天/周低-中负荷 | 3-5个低-中负荷动作/次（候选） | 以舒适、不过度消耗为原则 | 每日基础呼吸；摄入完成度优先 | 营养恢复+功能维持

E | 以短时功能活动为主，耐受后增加 | 2-3天/周低门槛保肌/恢复 | 2-4个低门槛动作/次（候选） | 低负荷整理 | 每日基础呼吸；持续下降/乏力时暂停进阶 | 停止下降+恢复功能

F | 周总量个体化，任务分段 | 1-3天/周或分散低负荷 | 1-3个熟练基础动作/次（候选） | 仅保留必要项目 | 呼吸/运动均简化 | 安全+可执行性


## Table


组合位 | 优先目标 | 动作示例（仅从现有库选择） | 替代原则

上肢推/胸肩 | 胸肩/上肢推力 | R02墙壁俯卧撑、U02弹力带扩胸 | 肩痛/胸痛时降阶或改低负荷

上肢拉/肘屈伸 | 背部/肘关节功能 | U03屈肘、U04伸肘；符合表型时调用其他上肢动作 | 平衡差时改坐姿

下肢膝主导 | 股四头/蹲起能力 | L01半蹲、L06靠墙静蹲；低体能按允许动作降阶 | 膝髋痛时使用低负荷替代

小腿/踝泵功能 | 小腿/平衡/步行支持 | L05站立提踵 | 平衡差扶物；急性腿痛/肿胀禁用

核心/躯干（可选） | 躯干稳定 | C01/C02 | 腰背痛、腹部不适时不选

柔韧整理 | 与当天训练肌群匹配 | S01-S08中选2-4项 | 只到牵拉感，不追求疼痛


## Table


日程 | 有氧 | 抗阻/功能 | 柔韧/整理 | 肺预康复

Day1 | 快步走（第1次） | 抗阻组合A：4-6项 | 相关部位2-4项 | 基础呼吸1-3项

Day2 | 低冲击有氧/自行车（第2次） | 不安排高负荷抗阻 | 按需 | 基础呼吸1-3项

Day3 | 可选轻有氧 | 抗阻组合B：4-6项（第2次） | 相关部位2-4项 | 基础呼吸1-3项

Day4 | 快步走或替代有氧（第3次） | 恢复日 | 按需 | 基础呼吸1-3项

Day5 | 可与抗阻同日的有氧（第4次） | 抗阻组合A/B变体：4-6项（第3次，可选） | 相关部位2-4项 | 基础呼吸1-3项

Day6 | 可选第5次有氧/日常活动 | 无高负荷抗阻 | 轻柔韧 | 基础呼吸1-3项

Day7 | 恢复/日常活动 | 无高负荷抗阻 | 按需 | 基础呼吸；完成周复评


## Table


表型 | 周模板关键词 | 排程重点 | 禁止机械化行为

A | AEROBIC_4_5 + RESIST_2_3 | 减脂+保肌；有氧轮换；抗阻覆盖主要肌群 | 只给有氧或只给1个抗阻动作

B | AEROBIC_3_5 + RESIST_2_3 + DISEASE_MONITOR | 疾病监测优先于强度进阶 | 忽略血压/血糖等状态硬凑周次数

C | RESIST_PRIORITY_2_3 + AEROBIC_3_5 | 抗阻优先；肌肉/功能下降时冻结减重强化 | 用过量有氧换取体重下降

D | LOW_MOD_RESIST_2_3 + SHORT_AEROBIC | 先保证摄入与恢复 | 高消耗有氧或复杂动作过多

E | RECOVERY_FUNCTION + LOW_THRESHOLD_RESIST | 低门槛恢复；持续下降时不进阶 | 固定追求周总量

F | SIMPLIFIED_1_3 + SEGMENTED_TASKS | 减少动作数量、任务分段、完成率优先 | 给过多动作造成执行失败


## Table


字段 | 示例 | 说明

week_goal | fat_loss_preserve_muscle | 本周运动主目标

aerobic_days_target | 4-5 | 允许范围，不强制每天

resistance_days_target | 2-3 | 避免连续高负荷日

resistance_actions_per_session | 4-6 | A/B/C默认组合规则；其他表型按候选规则

aerobic_rotation_min_types | 2 | 若患者只有1种可行形式则记录原因

daily_schedule[] | Day1-Day7 | 每天明确动作、剂量、是否训练

session_index | resistance #2 | 防止重复/超频

allowed_action_ids | [...] | 经过患者限制和Safety筛选

alternative_action_ids | [...] | 不可用动作的替代

weekly_stop_rules | [...] | Safety覆盖规则

manual_review_reasons | [...] | 知识库不足/动作不足/冲突时触发

---

# SOURCE: 肺结节患者术前肺预康复知识库_V2.0_完整版_MDT审阅稿(1).docx

肺结节患者术前肺预康复知识库 V2.0

完整版 · MDT审阅稿 · 产品规则底稿 · AI/Codex调用版

一、文件定位与V2.0版本目标

肺预康复在本平台中是Structured Plan的一级模块，与exercise_plan并列。它承担呼吸控制、胸廓活动、运动中呼吸协同、排痰技能与术后呼吸技能预演，不等同于普通有氧/抗阻训练。患者端正式方案必须看到具体动作、步骤、剂量状态、注意事项、停止条件和替代路径。

V2.0不改变V1.0的P01-P06核心动作池，而是把“怎么选、什么时候不选、如何与Q56/A-F/手术窗口联动、如何记录执行、下一周怎么调”补成可供Codex和后续AI共同调用的结构化规则。

P01 缩唇呼吸：气促控制、延长呼气。

P02 腹式呼吸：膈肌参与、呼吸控制。

P03 胸廓扩张训练：胸廓活动与深吸气练习。

P04 呼吸-上肢协同：把呼吸节律融入上肢活动。

P05 有效咳嗽：排痰与术前技能学习。

P06 OPEP：仅在痰多/排痰困难且已有设备与医护处方/指导时调用。

二、权威来源、版本与冲突解决顺序

若同一患者同时命中多个条件，以“安全 > 营养充分/肌肉保护 > 手术准备与功能 > 代谢/体重目标”的顺序解决冲突。肺预康复不得为了减重或增加能量消耗而额外加量。

三、方案生成前必须读取的数据

四、总生成算法：先安全，再选动作，再定剂量状态

1. 先读当前安全等级；红色事件或明显加重症状时冻结肺预康复自动进阶并转人工。

2. 判断是否有气促/呼吸节律问题：优先P01/P02。

3. 判断是否有胸廓或上肢活动需求：考虑P03/P04，并根据肩痛/平衡选择坐位或低幅度版本。

4. 判断是否有痰/排痰困难：加入P05；P06仅在设备和医护条件同时满足时可进入。

5. 读取Q6手术窗口：>4周可形成规律并在ACTIVE范围内进阶；越接近手术越强调“会做、做对、能独立完成”，不临时增加陌生高负荷任务。

6. 读取A-F、Q56和执行能力：只改变动作优先级、任务复杂度和允许的进阶方向，不突破安全或ACTIVE剂量。

7. 多数稳定患者从P01-P05中选择1-3项；不是每天固定全部P01-P05。

8. 无痰患者不默认高频P05；P06从不属于所有患者基础任务。

9. 若对应剂量尚未MDT确认，动作可进入草稿，但duration/repetitions/sets/frequency保持null或标记candidate，并设置mdt_confirmed=false。

10. 只有PUBLISHED方案才物化为PULMONARY_PREHAB plan_task；患者实际记录进入patient_record，后续新周方案不得反向改写旧任务。

五、Q56目标对肺预康复的影响

六、A-F表型对肺预康复的修正规则

七、P01-P06动作知识库（V2.0）

说明：以下“项目剂量草案”沿用V1.0内部项目数值，当前默认状态仍为PENDING/MDT待确认。V2.0新增的是结构化字段、替代逻辑、记录字段和周调整规则，不把候选剂量升级为已批准处方。

八、症状与条件触发组合

九、距手术时间窗口与本周重点

十、与普通运动模块的边界与去重规则

十一、患者端数据记录：必填、条件必填、选填与系统派生

目标是让周复评能区分“方案没效果”与“没有执行/没有耐受”，同时避免患者每天填写过多内容。字段状态建议统一为R=必填、CR=条件必填、O=选填/自动采集、D=系统派生。

十二、患者端最小提问集（建议前端直接实现）

每完成一个肺预康复任务：①今天完成了吗？【全部/部分/未完成】；②实际做了多少？【分钟或次数×组数】；③做完后有没有不舒服？【无/有】。

若选“有”：展开【气促、胸痛/胸闷、头晕、明显疲劳、肩/上肢疼痛、咳嗽不适、其他】；命中红色症状直接进入安全流程。

若当日任务含P05/P06或患者本来有痰：问“今天痰是否更容易咳出？”【更容易/差不多/更困难】；“是否出现鲜血痰/明显血痰？”【否/是】。

若未完成：问“主要原因是什么？”【忘记/没时间/动作不会/太累/不舒服/环境或设备限制/其他】。

患者不需要每天重新填写动作名称、计划剂量或训练目的；这些来自当前PUBLISHED plan_task。

十三、7天周复评：如何决定下一周肺预康复

周复评不能只看“做了几次”，而应同时看安全、数据完整度、完成率、耐受、症状/排痰变化、手术窗口和Q56目标。命中动态规则只生成下一周待审核草稿，不直接改写当前PUBLISHED方案。

十四、周调整的关键约束

不因为体重目标未达到而加肺预康复剂量；肺预康复不是能量赤字工具。

不因为一次完成良好就在次日大幅加量；真正的剂量进阶只在周计划版本中完成。

每次进阶只改变少量变量，优先“动作质量和规律性”而不是同时增加动作数、时长、次数和组数。

连续摄入不足、肌肉/功能趋势下降或明显疲劳时，冻结运动/肺预康复进阶，先处理营养和恢复。

距手术越近，越强调技能熟练度和耐受稳定，而不是新动作或高负荷。

Q56有“改善肺功能”或“提高运动能力”目标时，只提高该模块的优先级和监测强度，不突破ACTIVE剂量。

十五、停止、暂停与升级规则

练习中出现胸痛、明显胸闷或呼吸困难迅速加重。

出现咯血/鲜血痰。

反复深呼吸后明显头晕、手足麻木或过度换气不适：立即停止并恢复自然呼吸。

有效咳嗽导致明显胸痛或无法恢复平静呼吸。

SpO₂达到项目MDT预设停止阈值或较基线持续明显下降。

喘鸣明显加重、意识异常或紫绀。

AI/Codex遇到上述情况不得用“坚持一下”“再做一组”等方式处理；应冻结相关任务并按黄色/红色规则转医护。具体SpO₂、HR、BP等生理阈值不在本知识库中自行发明，由MDT后台ACTIVE配置提供。

十六、AI/Codex结构化数据模型

十七、后端配置项建议（V2.0）

十八、Codex/AI调用伪代码

if red_safety_event: freeze pulmonary_prehab_auto_progression; escalate_to_clinician

else: read ACTIVE PR configs + ACTIVE P01-P06 knowledge + Q6 + A-F + Q56 + latest_weekly_record

choose 1-3 actions from P01-P05 based on symptoms, sputum, function, time window and tolerance

if dyspnea_or_breathing_rhythm_issue: prioritize P01/P02

if thoracic_or_upper_limb_mobility_need: consider P03/P04 with safe position

if sputum_or_airway_clearance_need: add P05; P06 only if prescribed and device_confirmed

if no_sputum: do not schedule high-frequency P05 by default

if D_or_E_with_low_intake_or_fatigue: simplify and block progression

if surgery_window_shortened: freeze unfamiliar/high-load changes; focus skill rehearsal

if Q56_improve_exercise_capacity_or_pulmonary_function: raise priority, never exceed ACTIVE dose

if dose_not_MDT_confirmed: keep dose null/candidate + mdt_confirmed=false

weekly_adjustment -> create new AI_GENERATED_PENDING_REVIEW plan_version; never overwrite PUBLISHED plan

published_plan -> PULMONARY_PREHAB plan_task; patient_record stores actual completion only

十九、回归测试场景（上线前必须覆盖）

二十、MDT审阅清单

确认P01-P05正式剂量/频率是否沿用现有项目草案，或给出院内允许范围。

统一P03正式名称、标准动作和主视频；避免“开肺门”等非标准术语在患者端混用。

确认P05技能学习与有痰排痰两种场景的频率差异。

确认P06适应证、设备型号、处方来源和患者教育视频。

确认SpO₂/HR/BP等停止阈值与黄/红升级边界。

确认Q56“改善肺功能/提高运动能力”是否需要额外客观结局指标（如6MWT或其他院内指标）。

确认患者端必填/条件必填字段是否足以支持周复评，同时不会造成过高记录负担。

确认周复评进阶时允许改变的变量数量、进阶幅度和最短复评周期。

确认V2.0继续暂不启用IMT/激励性肺量计；如要启用另行版本升级。

二十一、参考依据与内部来源

1. 项目内部：《肺结节患者术前肺预康复知识库 V1.0 MDT审阅稿》——P01-P06动作池、候选剂量、停止条件、手术窗口和边界的直接来源。

2. 项目内部：《肺结节患者围术期代谢健康管理 AI医嘱指南·停止条件·绿黄红规则·运动动作标签库》——症状触发、动作标签、视频映射和安全框架来源。

3. 项目内部：《AI方案生成治理补齐说明》——安全规则 > MDT配置 > 已审核知识库 > 模板 > AI提示词的治理顺序，以及PENDING/ACTIVE、动态调整和版本发布规则。

4. 项目内部：《肺结节患者术前运动处方生成规则与动作库 V2.0》——与exercise_plan边界、周调整和动作协同规则。

5. Lung Cancer Specialty Committee et al. 肺癌围手术期肺康复训练中国专家共识. 中国肺癌杂志. 2024;27(7):495-503. DOI:10.3779/j.issn.1009-3419.2024.102.25. PMID:39147703.

6. Ligibel JA, et al. Exercise, Diet, and Weight Management During Cancer Treatment: ASCO Guideline. J Clin Oncol. 2022;40(22):2491-2507. PMID:35576506.

7. Rochester CL, et al. Pulmonary Rehabilitation for Adults with Chronic Respiratory Disease: An Official ATS Clinical Practice Guideline. Am J Respir Crit Care Med. 2023;208(4):e7-e26. PMID:37581410.

8. Cavalheri V, et al. Exercise training before lung surgery in people with non-small cell lung cancer. Cochrane Database Syst Rev. 2022 update (CD012020).


## Table


适用范围 | 肺结节/拟行肺切除患者术前多学科代谢健康管理；本版只覆盖术前肺预康复，不替代康复医学科、胸外科或呼吸治疗团队的个体化处方。

V2.0核心变化 | 在V1.0 P01-P06动作池基础上，新增Q56医护目标映射、A-F与手术窗口修正、患者端记录字段、7天周复评与下一周调整、动作替代/降级逻辑、后端配置键和回归测试场景。

治理原则 | 安全规则 > ACTIVE MDT配置 > 已审核肺预康复知识库 > 方案模板 > AI编排。任何PENDING剂量不得以精确处方进入患者任务。

当前边界 | 继续沿用项目决定：V2.0不纳入IMT和激励性肺量计；如未来启用，需新版本知识库、独立安全规则和MDT审批。


## Table


优先级 | 来源 | 作用

1 | 安全规则 | 红/黄/绿分流、停止条件、禁忌、转人工；任何下层规则不得突破。

2 | ACTIVE MDT后台配置 | P01-P06正式剂量、频率、停止阈值、进退阶上限、设备条件。

3 | ACTIVE肺预康复知识库 | 动作目的、标准步骤、适应证、慎用、替代、视频版本。

4 | A-F/Q56/手术窗口模板 | 决定本周优先级、任务复杂度和动作组合，不自行发明剂量。

5 | AI/Codex编排 | 只在上述许可范围内组合成患者可执行的周计划；不能把PENDING变成处方。


## Table


信息组 | 字段/来源 | 系统用途

安全与呼吸 | 胸痛/胸闷、气促及变化、SpO₂（如有）、咯血/鲜血痰、喘鸣、意识/紫绀等 | 缺失关键安全信息时不得自动进阶

气道廓清 | 是否有痰、痰量/排痰困难、是否已有OPEP设备/处方 | 决定P05/P06是否进入

功能与运动 | Q27 6MWT或替代指标、Q35-Q37运动/限制、疲劳、平衡、肩胸活动限制 | 决定体位、复杂度及与exercise_plan的协同

营养/体能 | A-F表型、近期体重/肌肉趋势、摄入不足、D/E风险 | D/E或明显摄入不足时减少任务负担

时间 | Q6距预计手术时间 | 决定“学习/进阶”还是“巩固/预演”

目标 | Q56医护指导的本阶段目标（可空） | 有值时改变优先级；无值按默认肺预康复逻辑

执行能力 | 主要障碍、家庭支持、记录/训练偏好 | F型或执行困难时简化动作数、分段完成

上一周数据 | 完成率、实际剂量、气促/疲劳/不适、是否有痰、异常事件 | 决定下一周维持/降级/进阶候选


## Table


Q56首要目标 | 肺预康复规则

Q56未填写 | 按安全、症状、手术窗口和A-F默认逻辑自动生成；无需医护逐项手填肺预康复数值。

标准减脂 | 维持必要肺预康复，不因减脂目标额外增加呼吸训练量；与常规有氧/抗阻协同。

强化减脂 | 肺预康复仍以呼吸控制、功能和术前技能为目的；不得把P01-P05当作“增加热量消耗”的工具。

体重维持/保肌 | 保持基础呼吸技能与运动中呼吸协同；不为追求体重变化而加量。

营养恢复/增重 | 如乏力/摄入不足，优先简化为低负荷、短时、可完成的P01/P02 ± 必要P05。

停止继续下降 | 同营养恢复；若疲劳或功能下降，冻结自动进阶。

增肌 | 肺预康复服务于抗阻和功能训练中的呼吸节律；不独立增加训练量。

代谢控制 | 基础肺预康复按症状与功能选择；代谢目标本身不改变P01-P06剂量。

提高运动能力 | 优先强化P01/P02与有氧训练的呼吸节律配合；根据胸廓/肩部状态加入P03/P04。

改善肺功能 | 提高肺预康复优先级，重点放在呼吸控制、胸廓活动、运动中呼吸协同与按需排痰；若将肺功能指标改善作为疗效目标，需由MDT另设客观测量指标，AI不得承诺肺功能数值必然提高。

术前综合准备 | 按手术窗口平衡P01-P05；目标是动作熟练、耐受稳定、必要排痰技能准备。


## Table


表型 | 肺预康复修正

A 超重/高体脂 | 按症状与手术窗口选基础池；减脂目标不改变呼吸动作剂量上限。

B 肥胖+代谢异常 | 同A；如气促、心血管/代谢状态影响运动，优先P01/P02并降低exercise_plan负荷，肺预康复不自行修改药物或疾病治疗。

C 高体脂+肌少风险 | 与抗阻/功能训练协同P01/P02/P04；避免通过增加呼吸训练或长时间有氧追求减重。

D 消瘦/营养风险 | 优先保留低负荷呼吸技能；明显乏力/摄入不足时简化总任务量，不以训练消耗为目标。

E 近期非意愿下降/摄入不足 | 低门槛、短时、耐受优先；持续下降或疲劳/功能恶化时冻结进阶并转营养/康复审核。

F 复杂/执行困难 | 任务简化、固定少量动作、允许分段；优先1-2个熟练基础动作，必要时家属协助。


## Table


ID | 动作 | 目的 | 体位 | 标准步骤

P01 | 缩唇呼吸 | 气促控制、延长呼气 | 坐位/半卧/站位均可，优先稳定安全体位 | 鼻吸约2秒；缩唇缓慢呼气约4-6秒；不需用力；出现过度换气不适立即恢复自然呼吸

P02 | 腹式呼吸 | 膈肌参与、呼吸控制 | 坐位或仰卧位 | 一手胸前一手腹部；鼻吸腹起、口呼腹落；不强迫深吸

P03 | 胸廓扩张训练 | 胸廓活动、深吸气练习 | 坐位或站位；平衡差优先坐位 | 配合双上肢外展/扩胸缓慢深吸气，回位呼气；动作标准名称/视频需MDT统一

P04 | 呼吸-上肢协同 | 把呼吸节律融入上肢活动 | 坐位或站位；按肩部和平衡选择 | 扩胸/肩部活动时吸气，回位时呼气；避免屏气

P05 | 有效咳嗽 | 排痰、术前技能学习 | 坐位/直立位，保证安全稳定 | 坐直；深吸气后短暂停顿；连续2次有效咳嗽；随后恢复平静呼吸

P06 | 呼气正压震荡排痰阀（OPEP） | 排痰 | 按设备说明与医护指导 | 仅按设备说明和医护确认方法执行；系统不得自行生成设备参数


## Table


ID | 项目剂量草案 | 适用/优先 | 停止/慎用 | 替代/降级

P01 | 约3-5 min/次，2-4次/日或气促时（项目草案） | A-F均可；活动后气促/呼吸节律乱优先 | 胸痛、明显加重气促、头晕/手足麻木、SpO₂异常 | P02或自然呼吸恢复后再评估

P02 | 5-10 min/次，2-4次/日（项目草案） | A-F均可；基础呼吸控制 | 同P01；明显不适时停止 | P01或缩短时长

P03 | 5-10次/组，1-3组/日（项目草案） | 胸廓活动不足、术前技能准备 | 肩痛、胸痛、气促明显、平衡差 | 改坐位低幅度P03，或P04/P01

P04 | 5-10次/组，1-2组/日（项目草案） | 功能训练需要、提高运动能力/术前综合准备 | 肩/上肢疼痛、气促、头晕 | 低幅度坐位P04，或P01/P02

P05 | 2次咳嗽/循环×2-5循环，按需（项目草案） | 有痰/排痰困难；或术前技能学习 | 咯血/鲜血痰、明显胸痛、无法恢复平静呼吸 | 无痰仅做技巧学习/按需；不能耐受则暂停并转医护

P06 | 按设备+医护处方 | 痰多/排痰困难且已有设备、医护处方/指导 | 无处方/不会操作不使用；不适立即停 | P05或其他医护确认的气道廓清方案


## Table


情形 | 推荐组合/动作 | 安全说明

活动后气促/呼吸节律乱 | P01 + P02；exercise_plan降阶/改间歇，必要时缩短每段运动时间 | 先判断是否较平时明显加重；危险信号优先安全流程

痰多/排痰困难 | P05；已有设备和处方时可P06 | 无痰不高频咳嗽；咯血/鲜血痰禁止继续并转医护

胸廓/肩部活动不足 | P03或P04 | 肩痛/胸痛明显则低幅度、坐位、替代或暂停

平衡差/头晕史 | 优先坐位P01/P02；P03/P04采用坐姿或低幅度 | 避免站位增加跌倒风险

D/E或明显摄入不足/乏力 | 简化P01/P02 ± 必要P05，减少总量 | 目标是保持呼吸技能与功能，不把肺预康复作为能量消耗

高龄/合并慢性呼吸病或高危因素 | 可进入更系统的专业肺康复评估 | 具体强度/疗程由专业评估决定，不由AI仅凭年龄或诊断自动加量

手术时间突然提前 | 保留熟练基础动作和必要咳嗽技能；冻结陌生高负荷项目 | 转“会做、做对、可独立完成”的术前预演模式


## Table


距手术时间 | 重点 | 系统行为

>8周 | 学习P01/P02/P03/P05，形成动作熟练度；按需加入P04 | 可轮换；每1-2周复评；只在ACTIVE范围内渐进

4-8周 | 基础动作轮换；逐渐增加胸廓扩张与呼吸-上肢协同 | 形成规律执行和动作质量；每周调整少量变量

2-4周 | 巩固呼吸技术，保证能独立完成 | 不追求复杂化，与营养/运动共同优化

1-2周 | 重点熟练腹式、缩唇、胸廓扩张、有效咳嗽 | 术后技能预演与正确动作为先，不临时大幅加量

≤1周 | 复习咳嗽/呼吸技巧 | 以“会做、做对”为主；不新增陌生高负荷项目


## Table


内容 | 归属 | 规则

有氧步行/自行车 | exercise_plan | 用于耐力、代谢与功能；肺预康复可引用呼吸节律，但不得重复生成第二个相同有氧任务。

抗阻训练 | exercise_plan | 用于保肌与功能；P04可与上肢抗阻协同，但动作ID和任务归属要明确。

P01-P06 | pulmonary_prehab_plan | 用于呼吸控制、胸廓活动、排痰与术前呼吸技能。

IMT/激励性肺量计 | 当前V2不进入动作池 | 如未来启用，需新增版本、设备/处方条件、安全规则与MDT审批。


## Table


字段 | 状态 | 患者端问题/数据 | 用途

每次任务完成情况 | R | 全部完成 / 部分完成 / 未完成 | 计算任务完成率

实际完成量 | R | 实际分钟，或实际次数×组数；P05可记录实际循环数 | 与计划剂量比较

完成后是否不适 | R | 无 / 有 | 有则展开条件问题

不适类型 | CR | 气促、胸痛/胸闷、头晕、疲劳、肩痛、咳嗽不适、其他 | 决定冻结/降级/转人工

气促或疲劳评分 | CR | 有气促/疲劳或本周重点监测时记录0-10 | 观察耐受趋势；具体阈值由MDT配置

痰/排痰情况 | CR | 仅P05/P06或患者有痰时：痰量变化、是否更易排出、是否出现血痰 | 判断气道廓清需求和安全

SpO₂前后值 | O/CR | 有设备且医护要求时记录 | 辅助安全判断；不是所有患者强制

未完成原因 | CR | 没时间/忘记/动作不会/不适/太累/环境限制/其他 | 下一周优先处理执行障碍

动作视频/照片 | O | 按产品需要上传 | 可用于动作质量复核，不作为必需数据

weekly_completion_rate | D | 由系统从已发布任务与实际记录计算 | 周复评输入

tolerance_trend | D | 根据不适、评分、异常事件汇总 | 决定维持/降级/进阶候选


## Table


周结论 | 典型触发 | 下一周规则

SAFETY_REVIEW | 出现红色事件或新发/加重症状 | 暂停相关任务/冻结进阶；转人工；医护解除前不得恢复自动进阶

DATA_INSUFFICIENT | 关键任务记录不足，无法判断耐受/执行 | 补数提醒；不把数据不足解释成“方案无效”；保持或保守化

BARRIER_FIRST | 完成率低但无安全恶化，主要原因是忘记/不会/时间/环境 | 先简化动作数、改提醒/时段、增加视频或家属协助；不加剂量

MAINTAIN | 完成稳定、无不适、动作熟练、症状稳定 | 下一周维持原动作与剂量，必要时仅轮换组合避免机械重复

PROGRESSION_CANDIDATE | 完成稳定、耐受良好、距手术仍有优化窗口，且有明确功能/肺预康复目标 | 只在ACTIVE允许范围内增加1-2个变量，如时长/次数/组数中的少数项；不同时大幅增加

DEINTENSIFY | 疲劳/气促/疼痛增加或恢复变差，但未达红色 | 降低任务复杂度或剂量；优先坐位/低负荷P01/P02；暂停相关进阶

AIRWAY_CLEARANCE_REVIEW | 痰多/排痰困难持续或新出现 | 评估P05执行质量；P06仅在已有设备/处方时考虑；异常痰/血痰转医护

SURGERY_WINDOW_SHORTENED | 预计手术时间缩短 | 冻结陌生高负荷动作；转技能巩固与术前预演模式


## Table


字段 | 要求

action_id | P01-P06；必须来自ACTIVE审核库

action_name / purpose | 患者可读名称与训练目的

position / steps | 动作体位、标准步骤

duration / repetitions / sets / daily_frequency | 剂量字段；未确认时null或candidate，不得伪装为批准值

indications / cautions / stop_conditions | 适用、慎用、停止条件

alternative_action | 不耐受或条件不满足时替代

equipment / requires_supervision | P06等设备/陪同要求

goal_tags | Q56目标标签，如exercise_capacity / pulmonary_preparation等

phenotype_tags | A/B/C/D/E/F优先标签，非绝对禁忌

surgery_window_tags | gt8w / 4_8w / 2_4w / 1_2w / le1w

mdt_confirmed | 布尔/状态；不能仅用自然语言“待确认”代替

video_id / source_version | 审核视频和知识库版本

record_requirements | R/CR/O记录字段定义

progression_fields | 允许的进阶变量；由ACTIVE配置限定


## Table


配置ID | 内容 | 责任MDT

PR-CFG-001 | P01-P05哪些属于多数稳定患者基础池，哪些仅条件调用 | 康复医学科+胸外科

PR-CFG-002 | P01-P05正式剂量/频率及允许范围 | 康复医学科

PR-CFG-003 | P03标准动作名称、标准动作定义和主视频 | 康复医学科+护理

PR-CFG-004 | SpO₂/HR/BP等停止阈值及黄色/红色升级规则 | 康复+胸外科+相关专科

PR-CFG-005 | P05“术前技能学习”与“有痰排痰”的频率区别 | 康复+胸外科

PR-CFG-006 | P06 OPEP适应证、设备、处方条件与视频 | 呼吸治疗/康复+胸外科

PR-CFG-007 | P01-P05主视频和备用视频版本 | 康复+护理+产品

PR-CFG-008 | 未来是否启用IMT/激励性肺量计及独立规则 | MDT版本升级事项

PR-CFG-009 | Q56各目标对肺预康复优先级/组合的映射 | 康复医学科+胸外科

PR-CFG-010 | 手术窗口对动作选择和进阶冻结的映射 | 胸外科+康复医学科

PR-CFG-011 | 周复评进阶/降级/维持判定所需完成率与耐受边界 | 康复医学科+护理

PR-CFG-012 | 患者端R/CR/O记录字段及最小提问集 | 康复+护理+产品


## Table


场景 | 期望行为

稳定A型、无痰、4-8周、Q56空 | 应从P01-P04按需选1-3项；不高频P05；不得因减脂加呼吸训练量

B型、Q56强化减脂、无气促 | 肺预康复维持基础需求；强化减脂不直接改变P01-P05剂量

C型、肌少风险、提高运动能力 | P01/P02与exercise_plan呼吸节律协同；P04可按肩胸功能调用

D/E型、摄入不足+乏力 | 简化任务；冻结自动进阶；不以训练消耗为目标

气促但无红旗 | P01/P02优先；运动改间歇/降阶；记录耐受

痰多/排痰困难、无OPEP处方 | P05可用；P06必须不可执行并提示设备/医护条件未满足

痰多且已有OPEP设备+处方 | 可调用P06，但剂量只来自医护/设备处方

无痰患者 | P05仅技巧学习/按需，不生成每天高频固定任务

咯鲜血或明显胸痛 | 立即冻结相关肺预康复任务并转安全流程，不生成进阶

手术从4-8周提前到≤1周 | 冻结新动作/高负荷，改技能巩固和术前预演

Q56改善肺功能 | 提高模块优先级和监测，不承诺肺功能检查指标必然提高

一周记录不足 | DATA_INSUFFICIENT；不判定方案无效、不自动加量