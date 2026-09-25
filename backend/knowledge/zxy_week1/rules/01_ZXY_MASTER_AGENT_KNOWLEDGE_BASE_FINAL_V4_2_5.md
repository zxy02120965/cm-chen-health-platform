# 01_ZXY_MASTER_AGENT_KNOWLEDGE_BASE_FINAL

本文件整合 ZXY AI 总控规则、A–F 分型/复杂度叠加、能量计算、多维评估修饰、安全规则、执行方案、周动态调整与发布治理。

版本：FINAL V4.2.5｜F能量状态锁定 + FOOD执行网格 + 真实Root Trace硬门控｜2026-09-24

---

# FINAL OPERATING CONTRACT V4.2.5｜F能量状态锁定 + FOOD执行网格 + 真实Root Trace硬门控（2026-09-24）

> **版本定位**：V4.2.5 是对 V4.2.4 的小范围机器合同收口。它不改变 A–E 主营养方向、F complexity overlay、P1→P4 能量来源、Ingredient Master V1.2、49个 STANDARD_COMPONENT、Exercise 或 Pulmonary Rehab 的临床方向。
>
> 本补丁只修复本轮 A–F 回归暴露的 3 个问题：
>
> 1. `underlying A–E + F overlay` 已具备候选能量链时，生成器仍可能仅因配置未 ACTIVE 而误降为 `STRUCTURE_ONLY`；
> 2. 患者端虽然已有克重，但仍可能展示未通过 Ingredient Master `min/max/step/discrete/package rule` 的数学中间量；
> 3. 最终文件可能只有 `food_trace/exercise_trace/pulmonary_trace` 摘要，却在 `artifact_manifest` 中自报 `FULL`，缺少真实 `diet_plan_trace / exercise_plan_trace / pulmonary_rehab_trace` root。
>
> 执行优先级：`临床安全/BLOCK规则 > ACTIVE MDT配置 > ACTIVE Ingredient Master/FOOD组件状态 > 本V4.2.5 > V4.2.4 > V4.2.3 > 历史规则 > AI自由编排`。

---

## V4.2.5-0｜F overlay 不得删除 underlying A–E 的候选能量链

F 继续仅表示：

```yaml
primary_nutrition_phenotype: A|B|C|D|E
complexity_overlay: F
display_phenotype: F
```

F 只调整：

- 任务数量；
- 餐型复杂度；
- 运动分段；
- 支持/坐位/家庭协助；
- 进阶速度；
- 记录方式。

F **不能**把已经可追踪的 underlying A–E 能量方向删除。

### 候选链形成条件

若同时满足：

```yaml
p1_or_p2_active: false
valid_bia_bmr_for_p3: true
candidate_pal_available_from_local_mapping_or_input: true
underlying_A_to_E_candidate_energy_direction_available: true
true_energy_blocker_present: false
```

则必须：

```yaml
energy_basis:
  primary_source: P3_BIA_BMR_TEMP
  source_status: PROVISIONAL
  pal_status: PENDING

energy_target:
  status: PROVISIONAL
  prescribed_energy_target_kcal: null
  provisional_energy_target_kcal: <single_point_candidate>

diet_generation_mode: EXACT_PROVISIONAL_REVIEW
publication_blocked: true
```

### 不允许的回归

```text
valid P3 + candidate PAL + underlying A–E candidate direction
且无真实安全/营养 blocker
→ 仅因为 PAL/比例不是 ACTIVE
→ UNAVAILABLE / STRUCTURE_ONLY
```

此情况 `energy_state_validation.status = FAIL`。

### F01 回归测试锁（仅用于测试，不是所有F患者的固定处方）

对于当前 SYN-F01 测试病例，如果仍使用：

```text
BIA/BMR = 1390 kcal/d
PAL candidate = 1.30
underlying B ratio candidate = 0.80
```

则回归预期为：

```text
TEE candidate ≈ 1807 kcal/d
provisional energy target ≈ 1446 kcal/d
energy_target.status = PROVISIONAL
diet_generation_mode = EXACT_PROVISIONAL_REVIEW
```

F overlay 只能简化执行，不能把该测试链降为 STRUCTURE_ONLY。

---

## V4.2.5-1｜患者端克重必须是“最终执行量”，不是数学中间量

01 必须从 02 接收并验证每一个患者可见原料的最终执行量。

新增：

```yaml
food_execution_grid_validation:
  all_patient_ingredient_amounts_are_final_executable_amounts: true|false
  all_standard_component_amounts_match_materialized_mapping: true|false
  all_ai_generated_dish_amounts_within_min_max: true|false
  all_ai_generated_dish_amounts_match_step_or_discrete_rule: true|false
  no_fractional_amount_leak_from_algorithmic_scale: true|false
  invalid_items: []
  status: PASS|FAIL
```

### STANDARD_COMPONENT

患者可见量必须来自：

```text
02 FOOD 的“该 component + 该合法 scale”的最终 execution mapping
```

禁止患者端直接显示：

```text
base_amount × portion_scale
```

的数学中间量。

如果映射要求：

```text
V004@0.5
圆白菜 100 g
植物油 3 g
```

则患者端必须显示 `3 g`，不能显示数学中间量 `2.5 g`。

### AI_GENERATED_DISH

患者端 `executable_amount` 必须：

```text
>= candidate_min
<= candidate_max
并满足 candidate_step / discrete / package rule
```

例如：

```text
植物油：step = 1 g
2.5 g -> INVALID

冬瓜：step = 10 g
125 g -> INVALID
```

必须先执行化为合法候选值，再重新计算营养，然后才能进入患者视图。

### STRUCTURE_ONLY 也必须执行化

`STRUCTURE_ONLY` 只表示“不做精确全天 kcal/P/C/F 闭合”。

它**不允许**：

- 越过 min/max；
- 忽略 step；
- 输出半个鸡蛋；
- 输出未定义的包装分数；
- 把算法中间量当患者克重。

因此：

```text
nutrition closure unavailable
!=
execution quantity may be invalid
```

---

## V4.2.5-2｜执行量改变后营养重算状态必须同步

若：

```yaml
algorithmic_amount != executable_amount
```

则：

```yaml
nutrition_recalculation_validation:
  portion_changed: true
  recalculation_required: true
```

如果当前为：

```text
EXACT_ACTIVE
EXACT_PROVISIONAL_REVIEW
```

则重算未完成时不能宣称营养闭合 PASS。

如果当前为：

```text
STRUCTURE_ONLY
```

允许 `planned_nutrition = null`，但仍必须把：

```yaml
nutrition_recalculation_required: true
```

记录在 trace 中，供后续营养服务处理。

---

## V4.2.5-3｜真实 Root Trace 是 FULL 的唯一依据

最终 artifact 中只有以下 3 个**真实根对象**可以作为 FULL 的物理依据：

```yaml
diet_plan_trace:
exercise_plan_trace:
pulmonary_rehab_trace:
```

以下内容**不能**替代 root：

```yaml
food_trace:
exercise_trace:
pulmonary_trace:
artifact_manifest:
validation:
```

这些只能是 summary / derived snapshot。

### FOOD FULL 的最低物理要求

最终文档必须真实存在：

```yaml
diet_plan_trace:
  trace_schema_version: FOOD_TRACE_V4_2
  days:
    Day1: ...
    Day2: ...
    Day3: ...
    Day4: ...
    Day5: ...
    Day6: ...
    Day7: ...
```

并且：

- 每个患者实际计划餐次都有映射；
- 每个患者可见 food item 有唯一 trace 实体；
- 每个 food item 至少包含 `dish_name + ingredients + simple_method + audit identity`；
- STANDARD_COMPONENT 要有 component_id + scale + materialized ingredients；
- AI_GENERATED_DISH 要有 generated_dish_id + structured ingredients；
- Patient View 与 root trace 数量、名称、执行量、做法必须一致。

### Exercise / Pulmonary FULL

同理必须分别真实存在：

```yaml
exercise_plan_trace:
  daily_schedule:
    Day1: ...
    ...
    Day7: ...

pulmonary_rehab_trace:
  daily_schedule:
    Day1: ...
    ...
    Day7: ...
```

只有 summary 数字或周次数不能算 FULL。

---

## V4.2.5-4｜禁止“自报 FULL”

新增硬校验：

```yaml
physical_root_trace_validation:
  diet_plan_trace_root_present: true|false
  exercise_plan_trace_root_present: true|false
  pulmonary_rehab_trace_root_present: true|false

  food_days_physically_materialized: 0..7
  exercise_days_physically_materialized: 0..7
  pulmonary_days_physically_materialized: 0..7

  food_root_is_summary_only: true|false
  exercise_root_is_summary_only: true|false
  pulmonary_root_is_summary_only: true|false

  status: PASS|FAIL
```

只有：

```text
root present
AND 7 days physically materialized
AND not summary_only
```

才能：

```yaml
artifact_manifest:
  food_trace:
    materialization: FULL
```

其余两类同理。

### 典型 FAIL

```yaml
food_trace:
  materialization: FULL
  patient_visible_days: 7
```

但最终文件里没有真实 `diet_plan_trace:` root：

```text
=> physical_root_trace_validation = FAIL
=> artifact_manifest.food_trace.materialization != FULL
=> content_validation = FAIL
```

---

## V4.2.5-5｜Patient View / Root Trace / Execution Grid 三重一致性

最终 FOOD Validator 不再只检查“有没有克重”。

必须同时满足：

```yaml
food_three_way_consistency_validation:
  patient_view_recipe_complete: true|false
  root_trace_physically_complete: true|false
  patient_view_matches_root_trace: true|false
  root_trace_matches_ingredient_master_execution_grid: true|false
  patient_view_matches_ingredient_master_execution_grid: true|false
  status: PASS|FAIL
```

三层必须一致：

```text
Patient View
↕
diet_plan_trace
↕
Ingredient Master / component execution mapping
```

只要任一层不一致，不能给 `content_validation.status = PASS/PASS_WITH_REVIEW`。

---

## V4.2.5-6｜Content Validator 新增硬失败条件

以下任一成立：

```text
F eligible candidate energy chain 被错误降为 STRUCTURE_ONLY
患者端出现不符合 min/max/step/discrete/package 的执行量
STANDARD_COMPONENT 患者量不是 final materialized amount
只有 food_trace 摘要但没有 diet_plan_trace root
只有 exercise_trace 摘要但没有 exercise_plan_trace root
只有 pulmonary_trace 摘要但没有 pulmonary_rehab_trace root
artifact_manifest 自报 FULL 与物理 root 不一致
Patient View 与 root trace 克重/菜名/做法不一致
```

则：

```yaml
content_validation:
  status: FAIL
```

不能降为普通 warning。

---

## V4.2.5-7｜最终生成顺序

```text
1. Safety Gate
2. A–E primary phenotype
3. F overlay
4. P1→P4 energy source
5. energy_state_validation
6. 调用 02 FOOD 生成 algorithmic candidate
7. 02 完成 min/max/step/discrete/package execution materialization
8. 需要时重新计算 nutrition
9. 生成 patient-visible dish_name + final executable amount + simple_method
10. 写真实 diet_plan_trace root
11. 写真实 exercise_plan_trace root
12. 写真实 pulmonary_rehab_trace root
13. 扫描 physical root
14. 运行 execution grid validation
15. 运行 Patient View ↔ Root Trace ↔ Ingredient Master 三重一致性
16. 从真实 root 派生 artifact_manifest
17. Content Validator
18. Safety Validator
19. Publication Validator
20. 输出唯一 final validator snapshot
```

---

## V4.2.5-8｜本轮 A–F 回归最低验收

```yaml
A_to_F_regression_gate:
  patient_recipe_contract: PASS
  no_bare_component_share_language: PASS
  execution_grid_validation: PASS
  physical_root_trace_validation: PASS
  patient_view_root_trace_consistency: PASS
  energy_state_validation: PASS
```

其中：

- A/B/C/D：保持正确的 PROVISIONAL 能量链；
- E：若真实低摄入/再喂养信息未澄清，可继续 `UNAVAILABLE + STRUCTURE_ONLY`，但克重仍必须合法执行化；
- F：underlying B + F，若候选链条件完整且无 blocker，必须 `PROVISIONAL + EXACT_PROVISIONAL_REVIEW`；
- 所有病例：没有真实 root trace，绝不能标 FULL。

---

## V4.2.5-9｜最终一句话

> **菜谱“有克重”还不够：克重必须是 Ingredient Master/组件执行映射允许的最终执行量；F 不能删除 underlying A–E 的候选能量链；FULL 只能由最终文件中真实存在的 Day1–Day7 root trace 派生，绝不能靠 summary 自报。**

---

# 以下完整继承 V4.2.4；与上方 V4.2.5 冲突时，以 V4.2.5 为准

# FINAL OPERATING CONTRACT V4.2.4｜患者菜谱物化 + Patient View/Trace 强一致性 Validator（2026-09-24）

> **版本定位**：V4.2.4 在 V4.2.3 的 Ingredient Master、合法 scale、份量物化和营养来源校验基础上，修复回归测试暴露的最后一类问题：后台 FOOD trace 可能已经是 FULL，但患者端仍显示“杂粮饭1份/鸡胸彩椒/香菇油麦菜”，导致 trace 与实际患者视图不一致。
>
> V4.2.4 要求最终 Validator 同时检查 **patient-visible menu** 和 **backend FOOD trace**；任何一层没有真正物化，都不能 PASS。
>
> 本补丁不改变 A–E 主营养方向、F overlay、能量 P1→P4、Exercise、Pulmonary Rehab 或 Ingredient Master V1.2 的医学规则。

---

## V4.2.4-0｜01 必须读取 02 FOOD V4.2.3 的患者菜谱合同

01 最终检查时，每个患者可见 food item 必须存在：

```yaml
patient_food_item:
  dish_name: string
  ingredients:
    - ingredient_name: string
      executable_amount: number
      execution_unit: g|ml|个
  simple_method: string
```

后台 component/ingredient/scale 对象不能替代患者端这三个字段。

---

## V4.2.4-1｜新增 `patient_food_recipe_display_validation`

最终 artifact 必须直接扫描 Day1–Day7 患者可见饮食文本/结构，而不是只相信 trace 中的布尔声明。

```yaml
patient_food_recipe_display_validation:
  all_7_days_have_patient_visible_meals: true|false
  all_patient_food_items_have_dish_name: true|false
  all_patient_food_items_have_ingredients: true|false
  all_patient_ingredients_have_executable_amounts: true|false
  all_patient_food_items_have_simple_method: true|false
  no_bare_component_share_language: true|false
  no_component_id_or_scale_as_patient_portion: true|false
  simple_methods_within_allowed_cooking_rules: true|false
  patient_view_matches_food_trace: true|false
  unresolved_patient_food_items: []
  status: PASS|FAIL
```

### FAIL 例子

```text
杂粮饭1份
糙米饭1份
鸡胸彩椒
香菇油麦菜
西兰花胡萝卜双蔬
```

即使后台已经存在：

```text
C003@1.0
C002@1.0
P011@1.0
V003@1.0
V012@1.0
```

也必须 FAIL，因为 patient view 没有展开为真实可执行菜谱。

---

## V4.2.4-2｜“有克重”不等于“菜谱已物化”

以下也不能作为最终患者饮食视图直接 PASS：

```text
大米50g + 鸡胸100g + 西兰花200g + 油5g
```

它有克重，但没有明确患者应该把这些食材组成什么菜、如何完成。

最终至少要达到：

```text
米饭：大米50g（干重）；煮熟成饭。
鸡胸西兰花：鸡胸肉100g + 西兰花200g + 植物油5g；鸡胸切片，与西兰花少油炒熟。
```

因此：

```text
quantity_materialized = true
```

不能自动推出：

```text
patient_recipe_materialized = true
```

两者必须独立校验。

---

## V4.2.4-3｜增强现有 `nutrition_portion_materialization_validation`

在 V4.2.3 原字段基础上追加：

```yaml
nutrition_portion_materialization_validation:
  all_patient_food_items_materialized: true|false
  all_patient_food_items_have_dish_name: true|false
  all_patient_food_items_have_simple_method: true|false
  patient_recipe_materialization_complete: true|false
  patient_view_matches_trace: true|false
  # 其余 V4.2.3 字段继续保留
  status: PASS|FAIL
```

任何 food item 只有组件ID/组件名、份数、散列克重或后台 trace，而患者端没有 `dish_name + ingredient amount + simple_method` 时：

```text
all_patient_food_items_materialized = false
patient_recipe_materialization_complete = false
status = FAIL
```

---

## V4.2.4-4｜Patient View 与 FOOD Trace 必须双向一致

最终校验不能只做：

```text
trace → patient view
```

还必须做：

```text
patient view → trace
```

至少验证：

- 患者端每一道菜在 FOOD trace 中有唯一对象；
- 患者端每种有营养贡献的原料都能对应 ingredient_id 或合法 pending source 对象；
- 患者端显示的 g/ml/个与 trace 的 executable amount 一致；
- 患者端 simple_method 若引入新的油/糖/奶/酱料等营养原料，trace 中也必须存在；
- trace 声明 `all_patient_items_have_executable_portions=true` 时，必须从患者端实际内容重新验证，不得直接沿用生成阶段声明。

若两层不一致：

```yaml
patient_view_matches_food_trace: false
content_validation.status: FAIL
```

---

## V4.2.4-5｜F overlay 专项回归锁

F 的目的只是降低执行复杂度。

允许：

- 减少菜品种类；
- 2–3套固定餐型重复；
- 选择蒸、煮、炖等简单方法；
- 使用更多已审核 STANDARD_COMPONENT。

不允许为了“简单”而删除：

```text
克重
原料展开
菜名
simple_method
```

因此任何 F 病例出现：

```text
杂粮饭1份 / 糙米饭1份 / 鸡胸彩椒 / 香菇油麦菜
```

但没有完整克重和做法，应直接触发 patient recipe materialization FAIL。

---

## V4.2.4-6｜新增 Publication blockers

以下任一存在，患者发布必须阻断：

```text
food_patient_recipe_display_incomplete
food_patient_dish_name_missing
food_patient_ingredient_amount_missing
food_patient_simple_method_missing
food_patient_bare_component_language
food_patient_trace_mismatch
food_simple_method_introduces_untracked_ingredient
```

与旧 blocker 一样，这些状态必须从**最终 artifact**重新计算；修复后不得保留 stale blocker。

---

## V4.2.4-7｜最终 Validator 顺序再次收口

最终固定顺序：

```text
1. 完成 Day1–Day7 患者视图
2. 完成 FOOD / Exercise / Pulmonary root trace
3. 扫描 patient-visible FOOD：dish_name + ingredient amounts + simple_method
4. 校验 patient view ↔ FOOD trace 双向一致
5. 校验 Ingredient Master / allowed scale / min-max-step
6. 校验 FOOD 营养来源
7. 校验份量变化后的营养重算
8. 从 Exercise daily_schedule 反算周次数
9. final_artifact_scan
10. 派生 artifact_manifest
11. 清空中间 blocker
12. Content Validator
13. Safety Validator
14. Publication Validator
15. 输出唯一 final validator snapshot
```

关键原则：

> `FOOD_TRACE = FULL` 只有在后台 root trace 存在、患者端菜谱也完整、且两者一致时才能成立。

---

## V4.2.4-8｜最终一句话

> **最终患者饮食必须同时回答三个问题：吃什么菜、每种原料多少、怎么做。后台 trace 只是证据链，不能替代患者端真实菜谱。任何“trace写FULL但患者菜单还是1份/菜名/散列克重”的结果，一律视为 FAIL。**

---

# 以下完整继承 V4.2.3；与上方 V4.2.4 冲突时，以 V4.2.4 为准

# FINAL OPERATING CONTRACT V4.2.3｜FOOD Ingredient Master + 份量物化 Validator（2026-09-24）

> **版本定位**：V4.2.3 在 V4.2.2 最终产物真值机制之上，新增 FOOD 的 Ingredient Master、组件合法 scale、患者份量物化、营养来源与重算硬校验。它不改变 A–E 主营养方向、F overlay、P1→P4 能量主路径、Exercise V3/V4.2 或 P01–P06 肺预康复规则。
>
> 执行优先级：`临床安全/BLOCK规则 > ACTIVE MDT配置 > ACTIVE Ingredient Master / FOOD组件状态 > 本 V4.2.3 > V4.2.2 > 历史规则 > AI自由编排`。

---

## V4.2.3-0｜01 必须读取 02 FOOD V4.2.2 的最终状态

01 不再只判断“菜单存在/组件存在”，还必须接收：

```yaml
food_knowledge_state:
  ingredient_master_version: V1.2
  component_registry_version: V1.2
  unresolved_ingredient_sources: []
  components_needing_source_recalc: []
```

---

## V4.2.3-1｜新增 `nutrition_portion_materialization_validation`

最终患者方案与医护审核方案必须重新扫描：

```yaml
nutrition_portion_materialization_validation:
  all_patient_food_items_materialized: true|false
  no_bare_component_share_in_patient_view: true|false
  all_standard_components_use_allowed_scale: true|false
  all_component_ingredients_within_min_max: true|false
  all_component_ingredients_match_step_or_discrete_rule: true|false
  all_generated_dishes_have_ingredient_ids: true|false
  all_generated_dishes_have_executable_amounts: true|false
  weight_basis_present_when_needed: true|false
  unresolved_algorithmic_portions: []
  status: PASS|FAIL
```

### 必须 FAIL 的例子

患者/医护最终菜单仍只有：

```text
杂粮饭0.75份
鸡胸彩椒1份
香菇油麦菜半份
```

而没有 g/ml/个的实际执行量。

也必须 FAIL：

- `component_portion_scale` 不属于 02 返回的 `allowed_component_scales`；
- 任一基础食材执行量突破 Ingredient Master 的 min/max；
- 任一执行量不符合 step / 整枚 / 包装规则，且没有完成合法执行化；
- AI 新菜只有菜名，没有结构化 ingredient_id 与 executable amount。

---

## V4.2.3-2｜新增 `food_nutrition_source_validation`

```yaml
food_nutrition_source_validation:
  all_exact_mode_ingredients_active: true|false
  pending_source_ingredients: []
  all_active_components_recalculated_from_ingredient_master: true|false
  components_needing_source_recalc: []
  llm_used_as_nutrition_source: false|true
  status: PASS|FAIL
```

### EXACT 模式

`EXACT_ACTIVE` 或 `EXACT_PROVISIONAL_REVIEW` 下：

- 进入精确营养闭合的基础食材必须为 `ACTIVE_FOR_EXACT`；
- `RULE_APPROVED_SOURCE_PENDING` 只能存在于医护草稿，不得用于声明精确闭合；
- `NEEDS_SOURCE_RECALC` 组件不得贡献正式 kcal/P/C/F；
- LLM 永远不能成为营养数值来源。

### STRUCTURE_ONLY

可保留真实菜名、食材结构和可执行份量，但：

- 不能伪造精确营养闭合；
- pending source 仍必须明确暴露给医护审核；
- 未 ACTIVE 食材不得自动 PUBLISHED 给患者。

---

## V4.2.3-3｜新增 `nutrition_recalculation_validation`

任何份量执行化、取整、替换、配方变化后：

```yaml
nutrition_recalculation_validation:
  portion_changed: true|false
  replacement_occurred: true|false
  recipe_ratio_changed: true|false
  recalculation_required: true|false
  recalculation_completed: true|false|null
  nutrition_source_version_present: true|false|null
  status: PASS|FAIL|NOT_APPLICABLE
```

若 `recalculation_required=true` 且 `recalculation_completed!=true`：

- Content Validator 不得声称营养闭合 PASS；
- Publication Validator 必须产生 blocker。

---

## V4.2.3-4｜STANDARD_COMPONENT 身份保护

组件执行化后，如果只是合法 step 取整且仍可解释为原组件，可继续：

```text
STANDARD_COMPONENT
```

如果为满足边界需要：

- 显著改变食材比例；
- 删除/增加核心食材；
- 将多个组件重构为一个新菜；

必须改标：

```text
AI_GENERATED_DISH
```

并重新生成 `generated_dish_id + structured ingredients + nutrition recalculation`。

---

## V4.2.3-5｜Publication Validator 新增 FOOD blocker

以下任一最终状态存在时，患者发布必须阻断：

```text
food_portion_materialization_failed
food_component_scale_not_allowed
food_ingredient_execution_out_of_bounds
food_ingredient_source_pending
food_component_needs_source_recalc
food_nutrition_recalculation_required
food_generated_dish_missing_ingredient_trace
```

这些 blocker 必须和 V4.2.2 一样从**最终 artifact**重算；问题已经修复后不得残留 stale blocker。

---

## V4.2.3-6｜Validator 合并顺序

最终固定顺序更新为：

```text
1. 完成患者 Day1–Day7
2. 完成 FOOD / Exercise / Pulmonary root trace
3. 运行 FOOD Ingredient Master / scale / 份量物化校验
4. 运行 FOOD 营养来源校验
5. 运行 FOOD 营养重算校验
6. 从 Exercise daily_schedule 反算周次数
7. final_artifact_scan
8. 派生 artifact_manifest
9. 清空中间 blocker
10. Content Validator
11. Safety Validator
12. Publication Validator
13. 输出唯一 final validator snapshot
```

---

## V4.2.3-7｜最终一句话

> **患者看到的不是“份”，而是可执行的 g/ml/个；后台看到的不是第二套组件营养真值，而是 Ingredient Master 驱动的重算链；任何未解决的食材来源、非法 scale 或未重算份量变化都必须在发布前被 Validator 拦截。**

---

# 以下完整继承 V4.2.2；与上方 V4.2.3 冲突时，以 V4.2.3 为准

# FINAL OPERATING CONTRACT V4.2.2｜最终产物真值 + Validator重算 + stale blocker清零（2026-09-23）

> **版本定位**：V4.2.2 是 V4.2.1 的最终机器合同收口补丁。它**不改变** A–E 主营养方向、F complexity overlay、Safety Gate、P1→P4 能量优先级、A/F 的候选能量修补、E 型运动语义、FOOD 生成逻辑、Exercise 动作库或 P01–P06 肺预康复边界。
>
> 本补丁只修复回归测试中最后暴露出的两个后台一致性问题：
>
> 1. `artifact_manifest` / `content_validation` 仍可能在实际 root trace 缺失时错误写成 `FULL/PASS`；
> 2. root trace 已经在最终文件中真实存在后，`publication_validation.blockers` 仍可能残留早期生成阶段的“尚未物化”等 stale blocker。
>
> 执行优先级：`临床安全/BLOCK规则 > ACTIVE MDT配置 > ACTIVE知识库 > 本V4.2.2补丁 > V4.2.1 > V4.2 > V4.1 > 历史源规则 > AI自由编排`。
>
> **Schema兼容性**：继续使用 `FOOD_TRACE_V4_2 / EXERCISE_TRACE_V4_2 / PULMONARY_TRACE_V4_2`。本补丁只改变“最终产物检查、manifest 派生、validator 重算与 blocker 清理”，不新增第四类 validator。

---

## V4.2.2-0｜普通一句“生成第一周个体化方案”默认就是 FULL PLAN PACKAGE

当用户请求属于：

```text
请根据规则生成该患者第一周个体化方案。
```

或语义等价请求时，默认：

```yaml
required_output_profile: FULL_PLAN_PACKAGE
required_artifacts:
  patient_plan_day1_day7: true
  food_trace_full: true
  exercise_trace_full: true
  pulmonary_trace_full: true
  artifact_manifest_derived: true
  validators_final_snapshot: true
  plan_governance: true
```

### 强制规则

- 不能把“患者可读计划已完成，但 trace 未物化”当作本次任务已经完成；
- 不能因为 `STRUCTURE_ONLY` 就省略 FOOD trace；STRUCTURE_ONLY 只表示**不做精确营养闭合**，不表示可以省略 Day1–Day7 meal / food item 对象；
- 不能因为某天是恢复日或没有肺康复任务，就省略该天的 exercise/pulmonary 对象；应显式物化空任务与 reason；
- 如果最终发现必需 artifact 缺失，生成器必须先进入一次**final repair pass**，补齐缺失对象后再做 validator；
- 若由于真实技术/长度限制仍无法补齐，必须把方案状态标成 `GENERATION_INCOMPLETE` / `content_validation: FAIL`，不得伪装成完整最终稿。

---

## V4.2.2-1｜Root object 是唯一真值；manifest 不能反过来证明 root object 存在

最终状态判定必须只读取最终输出中**真实存在的根对象**：

```yaml
required_root_objects:
  food: diet_plan_trace
  exercise: exercise_plan_trace
  pulmonary: pulmonary_rehab_trace
```

### 1.1 物理存在性规则

`artifact_manifest.*.present=true` 只能由对应 root object 的实际存在派生。

`materialization=FULL` 必须同时满足：

```yaml
full_materialization_gate:
  root_object_present: true
  schema_version_valid: true
  day1_to_day7_materialized: true
  patient_plan_mapping_complete: true
  required_child_objects_present: true
```

其中：

- FOOD：7天、所有计划餐次、所有食物对象都实际存在；
- Exercise：7天、每个 session/action 或显式空 sessions+reason 都实际存在；
- Pulmonary：7天、每个 action 或显式空 actions+reason 都实际存在；
- 仅有“FULL”“已生成”“完整追踪实体摘要”“组件ID列表”“selected_action_ids”不能满足物理存在性。

### 1.2 禁止“先写 FULL，再假设对象存在”

以下组合是**结构性非法状态**：

```text
artifact_manifest.food_trace.materialization = FULL
但文件中没有 diet_plan_trace 根对象
```

同理适用于 exercise / pulmonary。

出现此类非法状态时，必须：

1. 将 manifest 暂时降级为 `MISSING` 或 `SUMMARY_ONLY`；
2. 将 `content_validation.status=FAIL`；
3. 进入 final repair pass；
4. 只有真实补齐 root object 后，才允许重新派生 FULL。

---

## V4.2.2-2｜最终 Validator 必须“最后重算”，不能沿用生成中途的判断

### 2.1 固定最终化顺序

最终输出必须遵循：

```text
1. 完成患者 Day1–Day7
2. 完成 diet_plan_trace
3. 完成 exercise_plan_trace
4. 完成 pulmonary_rehab_trace
5. 从 exercise daily_schedule 反算周次数
6. 执行 final_artifact_scan
7. 由 final_artifact_scan 派生 artifact_manifest
8. 清空所有中间阶段 blocker / warning 快照
9. 基于最终产物重新运行 Content Validator
10. 基于最终患者状态重新运行 Safety Validator
11. 基于最终 artifact + ACTIVE/PENDING状态重新运行 Publication Validator
12. 输出唯一 final validator snapshot
```

### 2.2 `final_artifact_scan` 必须机器可读

最终至少派生：

```yaml
final_artifact_scan:
  patient_plan:
    day1_day7_present: true|false

  food:
    root_object_present: true|false
    days_materialized: 0-7
    meals_mapped_complete: true|false
    patient_items_mapped_complete: true|false
    full_eligible: true|false

  exercise:
    root_object_present: true|false
    days_materialized: 0-7
    patient_actions_mapped_complete: true|false
    weekly_schedule_derived_present: true|false
    schedule_consistency_pass: true|false
    full_eligible: true|false

  pulmonary:
    root_object_present: true|false
    days_materialized: 0-7
    patient_actions_mapped_complete: true|false
    p05_p06_gate_recorded: true|false
    full_eligible: true|false
```

`artifact_manifest` 必须完全根据这个 final scan 派生，不得由模型“凭印象填写”。

---

## V4.2.2-3｜Stale blocker 必须在最终重算前清零

在执行最终 Publication Validator 前：

```yaml
validator_state_reset:
  discard_intermediate_content_status: true
  discard_intermediate_manifest: true
  discard_intermediate_blockers: true
  discard_intermediate_missing_trace_warnings: true
  recompute_from_final_artifact_only: true
```

### 3.1 blocker 只能描述最终文件此刻仍然为真的事实

例如最终文件已经有：

```yaml
artifact_manifest:
  food_trace:
    materialization: FULL
    derived_from_root_object: diet_plan_trace
    days_materialized: 7
```

则最终 blocker **禁止**再出现：

```text
food_trace_requires_physical_materialization
food_trace_D3_D6_requires_physical_materialization
FOOD trace 尚未展开
需要补齐7天 FOOD trace
```

这些属于生成中途状态，必须清零。

### 3.2 合法 blocker 示例

即使 FULL trace 已存在，下列 blocker 仍可合法存在：

- `energy_target_PROVISIONAL`
- `protein_target_not_ACTIVE`
- `exercise_dose_not_ACTIVE`
- `pulmonary_dose_not_ACTIVE`
- `clinical_safety_YELLOW_requires_review`
- `clinician_review_pending`
- `nutrition_recalculation_required`
- `knowledge_activation_unverified`

因为这些是**最终 artifact 仍然真实存在的发布条件问题**，不是旧的物化状态。

---

## V4.2.2-4｜Validator 自相矛盾检查：发现矛盾必须自动修正，不能原样出稿

最终再增加一个**属于 Content Validator 内部的 consistency check**，不是第四 validator：

```yaml
validator_consistency_check:
  status: PASS|FAIL
  contradictions: []
```

以下任一组合出现，必须 `FAIL` 并进入 repair：

```text
A. manifest=FULL，但对应 root object 不存在
B. manifest=FULL，但 days_materialized < 7
C. manifest=FULL，但 patient mapping 不完整
D. trace=MISSING/SUMMARY_ONLY，但 content_validation=PASS
E. schedule_consistency_validation=FAIL，但 content_validation=PASS
F. CLOSED_WORLD 检查失败，但 content_validation=PASS
G. final artifact 已 FULL，但 publication blocker 仍写“需要物化该 trace”
H. energy_target=UNAVAILABLE，却输出精确全天 kcal 闭合并当作正式目标
I. energy_target=PROVISIONAL 且候选链完整，却因“未ACTIVE”被再次降成 STRUCTURE_ONLY
```

只有 `contradictions=[]` 才允许最终 `content_validation.status=PASS/PASS_WITH_REVIEW`。

---

## V4.2.2-5｜最终 `artifact_manifest` 和 validators 只能出现一个权威快照

最终稿禁止同时保留多个相互矛盾的 manifest / validator 版本。

允许正文中解释“曾发现缺失并已修复”，但最终机器对象只能保留：

```yaml
final_validation_snapshot:
  stage: FINAL_ARTIFACT_ONLY
  artifact_manifest: {...}
  content_validation: {...}
  clinical_safety_validation: {...}
  publication_validation: {...}
  validator_consistency_check: {...}
```

如果生成过程中曾出现旧判断，不得把旧 YAML 与最终 YAML 一起作为两个“权威状态”输出。

---

## V4.2.2-6｜A / E / F 最终回归预期

### A01

必须同时满足：

```yaml
primary_nutrition_phenotype: A
complexity_overlay: none
energy_target.status: PROVISIONAL
provisional_energy_target_kcal: approximately_1560
food_trace_full: true
exercise_trace_full: true
pulmonary_trace_full: true
no_stale_blocker: true
```

“不会搭配饮食”只进入教育支持，不单独触发 F。

### E01

若仍存在明显摄入下降、体重下降信息不完整、再喂养风险资料不全，可继续：

```yaml
energy_target.status: UNAVAILABLE
diet_generation_mode: STRUCTURE_ONLY
formal_aerobic_days_target: 0  # 仅当个体理由成立
```

但仍必须：

```yaml
food_trace_full: true          # 结构对象要完整；营养闭合可以没有
exercise_trace_full: true
pulmonary_trace_full: true
zero_formal_aerobic_reason_present: true
reassess_next_week: true
```

即：**STRUCTURE_ONLY ≠ SUMMARY_ONLY**。

### F01

必须同时满足：

```yaml
primary_nutrition_phenotype: B
complexity_overlay: F
energy_target.status: PROVISIONAL
provisional_energy_target_kcal: approximately_1446
diet_generation_mode: EXACT_PROVISIONAL_REVIEW
food_trace_full: true
exercise_trace_full: true
pulmonary_trace_full: true
no_food_trace_materialization_blocker_after_full_trace: true
```

F 只降低执行复杂度，不能删除 underlying B 能量链。

---

## V4.2.2-7｜冻结判定

当 A/E/F 重新回归后同时满足：

```yaml
freeze_gate:
  clinical_logic_regression: PASS
  energy_state_regression: PASS
  f_overlay_regression: PASS
  e_exercise_semantics_regression: PASS
  full_trace_physical_presence: PASS
  schedule_consistency: PASS
  closed_world: PASS
  stale_blocker_check: PASS
  validator_consistency_check: PASS
```

即可将 `01 V4.2.2 + 02 V4.2.1 + 03 V4.2.1` 冻结为 Codex/网页实现基线。

---

# FINAL OPERATING CONTRACT V4.2.1｜候选能量链 + F overlay 边界 + E运动语义修补（2026-09-23）

> **版本定位**：V4.2.1 是 V4.2 的小补丁。V4.2 已解决真实 FULL trace、周次数自动对账和 CLOSED-WORLD；本补丁不重做这些能力，也不改变 A–E 主方向、Safety Gate、P1→P4 优先级、FOOD/Exercise/Pulmonary 知识库。本轮只修复六型回归中新发现的三个边界问题：
>
> 1. “没有 ACTIVE 参数”被错误等同于“没有候选能量”，导致 A/F 明明有 P3+BIA/BMR 与候选 PAL，却被降为 `UNAVAILABLE/STRUCTURE_ONLY`；
> 2. “不知道怎么吃/怎么运动”这类普通教育需求被过度解释成 F complexity overlay；
> 3. E 型的功能活动与正式有氧虽然已分开，但需要进一步锁定“E ≠ 默认0天正式有氧”。
>
> 执行优先级：`临床安全/BLOCK规则 > ACTIVE MDT配置 > ACTIVE知识库 > 本V4.2.1补丁 > V4.2 > V4.1 > 历史源规则 > AI自由编排`。
>
> **Schema兼容性**：本补丁不升级 `FOOD_TRACE_V4_2 / EXERCISE_TRACE_V4_2 / PULMONARY_TRACE_V4_2` 的 schema 名称；仅修正上游判定与 validator。现有 V4.2 trace 结构继续使用。

---

## V4.2.1-1｜“没有 ACTIVE”不等于“没有候选能量”

### 1.1 能量状态必须按“是否能形成安全、可追踪的候选链”判断

生成器不得仅因为 REE 公式、PAL、表型比例或最低能量边界尚未 `ACTIVE`，就把 `energy_target` 直接降为 `UNAVAILABLE`。

若同时满足：

```yaml
provisional_energy_chain_eligibility:
  primary_source_available: true          # 例如有效 P3 BIA/BMR_TEMP
  candidate_pal_available: true           # 来自本地规则/既有候选映射，不是AI临时创造
  primary_A_to_E_direction_available: true
  candidate_energy_modifier_available: true  # 对应A–E/Q56/手术窗的既有候选规则
  blocking_energy_safety_issue: false
```

则必须形成：

```yaml
energy_target:
  status: PROVISIONAL
  prescribed_energy_target_kcal: null
  provisional_energy_target_kcal: <candidate single point>
  provisional_target_source: [...]

diet_generation_mode: EXACT_PROVISIONAL_REVIEW
publication_blocked: true
```

### 1.2 下列情况才允许 `UNAVAILABLE + STRUCTURE_ONLY`

至少存在一项真实阻断，例如：

- P1/P2/P3 都无法形成可追踪单点候选；
- 本地规则无法形成候选 PAL，且没有其他可用 TEE 链；
- 没有可用的 underlying A–E/Q56 候选能量方向，不能安全决定单点；
- 本地 Safety/营养规则已经触发“再喂养风险尚未澄清/严重低摄入需先人工评估”的阻断；
- 关键能量来源出现 `DATA_CONFLICT`，且冲突尚不能按本地规则解决；
- MDT/医护显式要求暂不形成单点候选。

**仅“参数还不是 ACTIVE”本身，不是 UNAVAILABLE 的充分理由。**

### 1.3 F overlay 不得删除 underlying A–E 的候选能量链

若：

```yaml
primary_nutrition_phenotype: B
complexity_overlay: F
```

则：

- 能量方向仍读取 B；
- F 只改变菜单复杂度、任务数量、记录方式、动作协调需求和进阶速度；
- F 不得把已经可形成的 B 型 `PROVISIONAL` 候选能量改成 `UNAVAILABLE`；
- `display_phenotype: F` 也不得覆盖后台 underlying B 的能量链。

同理适用于 `A/C/D/E + F`。

### 1.4 E 型不是自动 `UNAVAILABLE`

E 的“近期下降/摄入不足”会提高营养安全优先级，但 E 标签本身不能自动清空能量候选。

- 若本地规则已触发再喂养/严重低摄入阻断，允许 `UNAVAILABLE + STRUCTURE_ONLY`；
- 若摄入、趋势和安全信息足以形成可审核候选链，E 也可以是 `PROVISIONAL + EXACT_PROVISIONAL_REVIEW`；
- 不能仅凭 `phenotype=E` 决定状态。

### 1.5 新增硬 validator

```yaml
energy_state_validation:
  candidate_chain_eligible: true|false
  blocker_present: true|false
  blocker_reasons: []
  expected_energy_state: ACTIVE|PROVISIONAL|UNAVAILABLE
  actual_energy_state: ACTIVE|PROVISIONAL|UNAVAILABLE
  status: PASS|FAIL
```

以下情况必须 FAIL：

```text
candidate_chain_eligible = true
blocker_present = false
actual_energy_state = UNAVAILABLE
```

Content Validator 必须读取 `energy_state_validation`；FAIL 时不得把总内容判 PASS。

---

## V4.2.1-2｜F complexity overlay 收紧：普通教育需求 ≠ F

### 2.1 F 的本质

F 表示**复杂度已经实质改变方案的可执行结构**，例如需要明显减少任务、拆短、坐姿/扶持、降低协调要求、简化记录、增加监督或减慢进阶。

可支持 F 的典型证据包括：

- 多病共存/多专科限制导致任务需要协调；
- 疼痛、低功能、平衡、腰背/关节问题明显影响动作池；
- 明显时间、照护、器材、获取食物/外卖依赖等执行障碍；
- 家庭支持不足或需要持续监督；
- 多个执行障碍叠加，已经需要减少任务数量/频率/复杂度。

### 2.2 下列单独存在时不能触发 F

```text
“不知道怎么吃”
“不知道怎么运动”
第一次接受营养/运动教育
希望拍照记录
需要示范菜单或动作
一般性的健康知识不足
```

若患者功能良好、Safety稳定、家庭支持可用，只是不会安排饮食/运动，应记录为：

```yaml
execution_support_needed: true
education_support_needed: true
complexity_overlay: none
```

仍然可以给更清楚、更简单的患者教育，但不因此改变 phenotype overlay。

### 2.3 F 必须保存触发依据

```yaml
complexity_overlay_trace:
  overlay: F|none
  major_complexity_trigger_present: true|false
  material_execution_burden_present: true|false
  trigger_reasons: []
  education_only: true|false
```

如果 `education_only=true` 且无实质复杂度证据，则 `overlay=F` 为 validator FAIL。

---

## V4.2.1-3｜E 型运动：可以0天正式有氧，但不能默认0天

E 型运动继续遵守“营养恢复、保肌、低门槛、短时、可分段”的方向，但正式有氧天数必须由患者状态决定，而不是由 `phenotype=E` 直接写死。

### 3.1 决策必须读取

- 当前摄入是否仍明显不足；
- 体重是否继续下降；
- 早饱/恶心是否限制完成度；
- 疲劳及次日恢复；
- BORG / 6MWT / 气促；
- Safety 等级；
- 手术窗口及医护审核状态。

### 3.2 允许的结果

```yaml
formal_aerobic_eligibility:
  status: DEFERRED_FOR_NUTRITION_RECOVERY | ALLOWED_LOW_DOSE | NOT_ASSESSED
  reasons: []
```

- 若仍有明显低摄入、继续下降、疲劳/恢复差或其他 Safety 负担，可暂不安排正式有氧，`formal_aerobic_days_target: 0`；此时保留耐受范围内 `FUNCTIONAL_ACTIVITY`，并记录原因。
- 若摄入趋稳、症状可控、功能/恢复允许，则可以安排少量低强度、短时正式有氧；具体频次/剂量仍读取 03/ACTIVE/候选规则，不由本补丁创造新固定数字。
- **禁止把所有 E 型机械写成0天正式有氧。**
- 也禁止把“每天3–10分钟舒适活动”机械计成7天正式有氧。

若 E 型最终选择0天正式有氧，`exercise_plan_trace` 必须有：

```yaml
zero_formal_aerobic_reason:
  allowed: true
  reasons: []
  reassess_next_week: true
```

---

## V4.2.1-4｜本补丁的回归预期

A01–F01 回归时：

- A：若 P3 + candidate PAL + A候选方向完整且无 blocker，应为 `PROVISIONAL`，不能仅因未 ACTIVE 降成 UNAVAILABLE；“不会安排饮食”单独不应触发 F；
- B/C/D：继续保持已验证的 provisional candidate chain；
- E：若本病例仍存在显著摄入下降且再喂养/低摄入安全信息未澄清，可以保持 `UNAVAILABLE + STRUCTURE_ONLY`；运动可因营养恢复负担暂为0天正式有氧，但必须写原因；
- F：后台保持 underlying B + F；若 P3 + candidate PAL + B候选方向完整且无 blocker，应恢复 `PROVISIONAL + EXACT_PROVISIONAL_REVIEW`，F 只负责简化执行。

本补丁不改变 V4.2 已通过的：真实 FULL trace、周次数反算、CLOSED-WORLD、P05/P06 gate、minimum sufficient set、患者端 ID 隐藏和发布阻断。

---

# FINAL OPERATING CONTRACT V4.2｜闭环输出一致性加固（2026-09-23）

> **版本定位**：V4.2 是 V4.1 的小范围收口版。它**不改变**已经稳定的 A–E 主营养方向、F complexity overlay、Safety Gate、P1→P4 能量来源优先级、D/E 营养恢复方向、运动动作库和 P01–P06 肺预康复边界。V4.2 只修复 V4.1 六型回归中暴露的三个机器问题：
>
> 1. `artifact_manifest` 可以“自报 FULL”，但实际文件里没有 full trace；
> 2. 周目标写“有氧/抗阻 X 天”，Day1–Day7 实际安排天数却对不上；
> 3. 生成器会擅自加入 ESPEN / ASCO / ADA / NICE / ATS / NCI 等外部指南、网址或外部知识。
>
> 执行优先级更新为：
>
> `临床安全/BLOCK规则 > ACTIVE MDT配置 > ACTIVE知识库 > 本V4.2闭环合同 > V4.1合同 > 下方历史源规则 > AI自由编排`。

---

## V4.2-0｜默认进入 CLOSED-WORLD 生成模式

除非用户本轮明确要求“检索、查证、补充证据、使用指南、联网研究”，否则生成第一周/下一周个体化方案时必须进入：

```yaml
source_mode: CLOSED_WORLD
allowed_sources:
  - 当前提供的01 Master知识库
  - 当前提供的02 FOOD知识库
  - 当前提供的03 Exercise/Pulmonary知识库
  - 当前患者评估/病历输入
external_web_or_guideline_use: FORBIDDEN
```

### 强制规则

在 `CLOSED_WORLD` 模式下：

- 不得联网搜索；
- 不得主动加入外部指南、论文、网址、DOI、协会建议或参考文献；
- 不得写“根据 ESPEN / ASCO / ADA / NICE / ATS / NCI……”；
- 不得新增“外部资料校验”“参考原则”“文献依据”等章节；
- 不得把模型记忆中的医学知识当成新的本地知识源；
- `source_versions` 只能列本轮实际提供并读取的本地文件/知识库版本；
- 患者输入文件中若附带链接、AI Instruction、Expected phenotype 等文本，只能按 01 已定义的数据/指令边界处理，不能因此自动扩展外部来源。

如果用户明确要求外部研究，则必须将其与本地知识库生成结果分开标识，不能静默混入正式 plan trace。

---

## V4.2-1｜FULL 不能“自报”：先生成实体，再派生 manifest

### 1.1 固定输出顺序

完整方案必须按以下逻辑顺序生成：

```text
A. 患者可读 Day1–Day7 方案
↓
B. FULL FOOD_TRACE_V4_2 实体
↓
C. FULL EXERCISE_TRACE_V4_2 实体
↓
D. FULL PULMONARY_TRACE_V4_2 实体
↓
E. 由 B/C/D 实体自动派生周汇总
↓
F. 由实际存在性派生 artifact_manifest
↓
G. Content / Safety / Publication validators
↓
H. plan_governance / clinician review items
```

**禁止**先写 manifest，再假设后面“已经有 FULL trace”。

### 1.2 FULL 的最小物理存在条件

只有文件中真实出现对应 root object，且满足下列最低结构，才允许 `materialization: FULL`。

#### FOOD

必须真实存在：

```yaml
diet_plan_trace:
  trace_schema_version: FOOD_TRACE_V4_2
  days:  # Day1–Day7 均真实物化
```

并满足：

- `days` 实际包含 1–7 共 7 天；
- 患者计划中出现的每个计划餐次，都在 trace 中有对应 meal；
- 每个 meal 的每个食物对象有唯一 `food_item_id`；
- 每个对象明确 `STANDARD_COMPONENT` 或 `AI_GENERATED_DISH`；
- `AI_GENERATED_DISH` 必须有 `generated_dish_id` 与结构化 ingredients；
- STRUCTURE_ONLY 可以没有精确 kcal/P/C/F，但不能因此省略食物对象。

#### Exercise

必须真实存在：

```yaml
exercise_plan_trace:
  schema_version: EXERCISE_TRACE_V4_2
  daily_schedule:  # Day1–Day7 均真实物化
```

并满足：

- 1–7 天全部存在；
- 休息日也必须以空 sessions + reason 明确物化；
- 患者端每个运动任务都能一对一找到后台 action；
- 每个 session 必须有 `session_role`；
- 每个 action 有 ID、名称、dose status 或显式 unavailable 状态。

#### Pulmonary

必须真实存在：

```yaml
pulmonary_rehab_trace:
  schema_version: PULMONARY_TRACE_V4_2
  daily_schedule:  # Day1–Day7 均真实物化
```

并满足：

- 1–7 天全部存在；
- 无肺康复动作的某天也必须显式写 `actions: []` + reason；
- 患者端每个呼吸/排痰任务均可映射到 P01–P06；
- P05/P06 gate 真实记录。

### 1.3 `artifact_manifest` 必须是派生结果，不是自由文本

V4.2 的 manifest 固定为：

```yaml
artifact_manifest:
  patient_plan:
    present: true|false
    day1_day7_self_contained: true|false

  food_trace:
    present: true|false
    materialization: FULL|SUMMARY_ONLY|MISSING
    schema_version: FOOD_TRACE_V4_2|null
    derived_from_root_object: diet_plan_trace|null
    days_materialized: 0-7
    patient_items_mapped: true|false

  exercise_trace:
    present: true|false
    materialization: FULL|SUMMARY_ONLY|MISSING
    schema_version: EXERCISE_TRACE_V4_2|null
    derived_from_root_object: exercise_plan_trace|null
    days_materialized: 0-7
    patient_actions_mapped: true|false

  pulmonary_trace:
    present: true|false
    materialization: FULL|SUMMARY_ONLY|MISSING
    schema_version: PULMONARY_TRACE_V4_2|null
    derived_from_root_object: pulmonary_rehab_trace|null
    days_materialized: 0-7
    patient_actions_mapped: true|false
```

### 1.4 不得用下列内容证明 FULL

以下均只能是摘要，不能满足 FULL：

```text
FOOD_TRACE_V4_2: FULL        # 只有一句声明
exercise_plan_trace_summary
pulmonary_rehab_trace_summary
component_ids_used: [...]
selected_action_ids: [...]
Day1: A01 + R02
“完整trace已生成”
```

如果 root object 不存在，manifest 必须如实写 `MISSING` 或 `SUMMARY_ONLY`，且：

```yaml
content_validation:
  status: FAIL
```

不得出现“trace 实际缺失但 manifest=FULL 且 content PASS”。

---

## V4.2-2｜Day1–Day7 生成后必须反算周次数并对账

### 2.1 运动角色统一

每个运动 session 必须属于且只属于一个主要角色：

```yaml
session_role:
  FORMAL_AEROBIC
  FUNCTIONAL_ACTIVITY
  RECOVERY
  WARMUP
  RESISTANCE
  FLEXIBILITY
```

其中：

- `WARMUP` 不计正式有氧日；
- `FUNCTIONAL_ACTIVITY` 不计正式有氧日；
- `RECOVERY` 不计正式有氧日；
- 同一天有多个 `FORMAL_AEROBIC` segment，只计 1 个正式有氧日；
- 同一天有一个或多个 `RESISTANCE` session，只计 1 个抗阻日。

### 2.2 周次数必须由 daily_schedule 派生

禁止模型先写“有氧4天/抗阻2天”后再凭感觉编排。

必须在 Day1–Day7 完成后计算：

```yaml
weekly_schedule_derived:
  formal_aerobic_days_actual: <由daily_schedule统计>
  functional_activity_days_actual: <由daily_schedule统计>
  resistance_days_actual: <由daily_schedule统计>
  recovery_days_actual: <由daily_schedule统计>
  flexibility_days_actual: <由daily_schedule统计>

weekly_schedule_declared:
  formal_aerobic_days_target: ...
  resistance_days_target: ...
  functional_activity_days_target: ...

schedule_consistency_validation:
  status: PASS|FAIL
  mismatches: []
```

### 2.3 对账失败时先修计划，不允许带矛盾出稿

若例如：

```text
周目标：抗阻2天
实际 Day1、Day3、Day5：3个抗阻日
```

则在最终输出前必须：

1. 根据患者安全、表型和 03 规则重新决定真正需要 2 天还是 3 天；
2. 修正 Day1–Day7 或修正候选目标；
3. 重新反算；
4. 直到 `schedule_consistency_validation=PASS`。

如果无法自动消除矛盾，则：

```yaml
content_validation:
  status: FAIL
```

不能让患者端、周摘要和 trace 三处出现不同周次数。

---

## V4.2-3｜能量状态与饮食模式再次锁定

为避免 `PROVISIONAL` 能量已经存在但又误写成 `STRUCTURE_ONLY`，V4.2 固定映射：

```text
energy_target.status = ACTIVE
→ diet_generation_mode = EXACT_ACTIVE

energy_target.status = PROVISIONAL
AND provisional_energy_target_kcal != null
→ diet_generation_mode = EXACT_PROVISIONAL_REVIEW

energy_target.status = UNAVAILABLE
OR provisional_energy_target_kcal = null
→ diet_generation_mode = STRUCTURE_ONLY
```

禁止出现：

```text
energy_target = PROVISIONAL + provisional_energy_target_kcal有值
但 diet_generation_mode = STRUCTURE_ONLY
```

`EXACT_PROVISIONAL_REVIEW` 仍然只是医护审核草稿，不能进入 PUBLISHED。

---

## V4.2-4｜最终 Content Validator 新增三项硬检查

```yaml
content_validation:
  artifact_physical_presence_check: PASS|FAIL
  schedule_consistency_check: PASS|FAIL
  closed_world_source_check: PASS|FAIL
```

只有三项均 PASS，且 V4.1 其余内容/可执行性规则也通过，才允许：

```yaml
content_validation:
  status: PASS
```

任何一项 FAIL，最终 `content_validation.status` 必须 FAIL。

### `closed_world_source_check=FAIL` 的典型条件

- 出现用户未要求的外部网址；
- 出现 ESPEN / ASCO / ADA / NICE / ATS / NCI 等本轮未提供来源；
- 出现“我又查阅了指南/文献”的内容；
- `source_versions` 列出了未实际提供的外部来源。

---

## V4.2-5｜V4.2 回归验收标准

用 A01–F01 六型测试时，仅给 01/02/03 V4.2 + 当前患者资料，并只说：

> 请根据规则生成该患者第一周个体化方案。

六例均应满足：

1. 不主动引用任何外部指南/网址；
2. 三个 full trace 在文件中真实存在，不是 manifest 自报；
3. manifest 的 `days_materialized` 均为 7；
4. Day1–Day7 的 formal aerobic / functional activity / resistance / recovery 实际天数与周汇总一致；
5. `schedule_consistency_validation=PASS`；
6. 能量状态与 diet generation mode 映射一致；
7. A–E 主方向与 F overlay 不被本轮机器修订改变；
8. 最终仍为 `AI_GENERATED_PENDING_REVIEW`，Publication Validator 按 ACTIVE/审核状态决定阻断。

---

# 以下完整继承 V4.1

> 从这里开始，V4.1 及更早的所有总控、A–F、能量、安全、患者展示、周复评、发布治理和历史 SOURCE 内容全部保留。若与上方 V4.2 闭环输出规则冲突，以 V4.2 为准。


# FINAL OPERATING CONTRACT V4.1｜六型回归后机器合同加固与内容质量精修（2026-09-23）

> 版本定位：本节是在 A/B/C/D/E/F 六型第一周方案使用 V4 再次回归后形成的**V4.1 最终总控实现合同**。V4.1 不改变 A–E 主营养方向、F complexity overlay、P1→P4 能量主路径、安全优先级和发布状态机；本轮只对**机器合同一致性、完整 trace 物化、患者可执行性、饮食自然度、运动活动语义和肺预康复最小充分集**进行加固。它用于统一 Codex/GPT/Claude/规则引擎的决策顺序、候选参数语义、患者展示与后台审计、周复评和三层 Validator。
>
> 本节**不重写下方原始 V2.0/V2.1 临床规则**，而是解决六型回归中暴露的实现歧义。若与下方源规则发生冲突，执行优先级为：
>
> `临床安全/BLOCK规则 > 已ACTIVE MDT配置 > 已ACTIVE知识库 > 本V4.1实现合同 > A–F/Q56/手术窗口模板 > AI自由编排`。

## 0. 本轮修订范围与明确不扩展项

本 V4.1 继承 V4 并重点加固以下问题：

1. A–F 不能被理解为“六套固定模板”；必须同时读取疾病、摄入、体成分、功能、症状、安全、手术窗口、Q56、执行障碍和偏好。
2. F 型与 A–E 的关系必须明确，避免 F 型患者的营养方向被“复杂度”覆盖。
3. P1–P4 能量来源在 `ACTIVE / PROVISIONAL / UNAVAILABLE` 三种状态下的行为必须统一。
4. `daily_energy_target_kcal = null` 时不得再次暗中生成伪精确热量闭合菜单。
5. 患者可读层与后台 ID/审计层必须分离；患者端不得被 `C004/P015/A01/R02/P01` 等工程 ID 主导。
6. 周复评的数据充分性必须统一，禁止仅比较 Day1 与 Day7 两个体重点就自动调方案。
7. 三层 Validator 的判定边界必须固定，避免不同病例对同一种 trace 缺失出现 PASS/FAIL 不一致。
8. D/E 营养恢复、F 复杂执行的上层总控规则需要明确，但具体 FOOD 组件和运动动作仍由 02/03 文件负责。
9. 完整系统输出必须显式声明 `artifact_manifest`；患者方案、FOOD full trace、Exercise full trace、Pulmonary full trace 中任何一项缺失或只有 summary，都不能 `content_validation=PASS`。
10. `content_validation` 除字段完整性外，必须包含患者可执行性子检查；不能只因“字段齐全”就放过明显组件拼接、跨日引用、工程化份量或任务过载。
11. 运动必须区分 `functional_activity` 与 `formal_aerobic_training`；D/E/F 的日常轻活动不能机械统计为正式有氧训练日。
12. FOOD 允许 AI 动态生成患者专属菜，但凡不是标准组件的原始审核配方，后台必须标记为 `AI_GENERATED_DISH` 并生成独立 `generated_dish_id`，不得伪装成既有组件。
13. 肺预康复遵循 `minimum_sufficient_set`：以当前患者真正需要的最小充分动作集为目标，不以动作越多越“完整”。

**本轮暂不新增**：专门的饮水量评估、饮水处方算法、排尿/尿量/尿色模块、排便频率/便形评分模块、基于二便的自动方案调整。原始知识库中已经存在的脱水、尿量明显减少、腹泻、便秘等**安全/症状提示继续保留**，但不扩展为独立干预模块。

---

# 1. 总决策架构：A–F 只是主方向，不是唯一输入

每次生成第一周方案或下一周新草稿，必须按照以下顺序运行：

```text
Current Assessment / Profile
  ↓
Data-state check（known / missing / explicit_none / uncertain / need_review）
  ↓
Clinical Safety Gate（GREEN / YELLOW / RED）
  ↓
Primary nutrition-metabolic phenotype（A–E）
  ↓
Complexity overlay（F / none）
  ↓
Disease / nutrition / body-composition / function modifiers
  ↓
Surgery-window modifier
  ↓
Q56 goal modifier
  ↓
Execution / preference / family-support modifier
  ↓
Energy & protein state
  ↓
FOOD + Exercise + Pulmonary Rehab generation
  ↓
Patient-facing rendering + full machine audit traces
  ↓
Artifact Completeness Gate（patient plan + 3 full traces）
  ↓
Patient Executability / Content Quality Check
  ↓
Content Validator
  ↓
Clinical Safety Validator
  ↓
Publication Validator
  ↓
Clinician Review
```

## 1.1 最终方案至少必须读取的输入域

A–F 之外，生成器还必须读取并在方案中体现下列与当前患者相关的评估信息：

- **营养/摄入**：近期体重变化、主动/非意愿下降、食欲、摄入完成、早饱、恶心/呕吐、咀嚼/吞咽、过敏/不耐受、蛋白摄入等；
- **体成分/肌肉**：BMI、腰围、体脂/脂肪量、肌肉量、骨骼肌量、SMI，以及可用的肌力/功能资料；
- **代谢/疾病**：高血压、糖代谢、血脂、尿酸、MASLD/脂肪肝、肝弹性、肾功能、贫血及其他当前会改变方案的疾病/实验室信息；
- **功能/症状**：6MWT、BORG、SpO₂变化、活动量、疲劳、气促、疼痛、关节/腰背/平衡限制；
- **手术信息**：预计手术窗口、拟行术式（如已知）、手术时间变化；
- **目标层**：Q56 医护阶段目标；
- **执行层**：Q51障碍、Q52饮食记录偏好、Q53运动偏好、Q54家庭支持、Q55健康目标，以及设备/场地/时间可及性；
- **安全层**：当前 GREEN/YELLOW/RED、触发规则、阻断模块、待人工复核项。

### 强制原则

不得写成：

```text
A型 → 固定A模板
B型 → 固定B模板
...
```

应写成：

```text
主表型决定方向
+ 其他评估项决定强度、食物选择、动作选择、任务复杂度、监测与是否允许进阶
```

---

# 2. A–F 的最终实现语义：A–E 主方向 + F 复杂度叠加

## 2.1 A–E：主要营养-代谢方向

```yaml
primary_nutrition_phenotype: A | B | C | D | E | null
```

- `A`：超重/高体脂，方向为减脂同时保肌；
- `B`：肥胖/高体脂 + 代谢异常，方向为代谢控制 + 减脂保肌；
- `C`：肌肉/功能保护优先，第一周不机械套 A/B 减脂；
- `D`：消瘦/营养风险，方向为营养恢复、体重/肌肉保护；
- `E`：近期非意愿下降 + 摄入不足/功能风险，第一目标为止跌与恢复。

## 2.2 F：复杂共病/执行困难的 overlay

```yaml
complexity_overlay: F | none
```

F 的核心语义是：

- 复杂共病/多专科限制；
- 疼痛、低功能、平衡或器材问题；
- 执行困难、时间不足、不会准备餐食、家庭支持不足；
- 需要减少任务数量、拆短任务、简化记录、降低自动进阶速度。

**F 不应自动覆盖更明确的 A–E 营养方向。**

例如：

```yaml
primary_nutrition_phenotype: B
complexity_overlay: F
```

表示：营养/代谢方向按 B；任务复杂度、运动结构、记录方式和进阶速度按 F 简化。

如果患者确实没有更明确 A–E 方向，才允许：

```yaml
primary_nutrition_phenotype: null
complexity_overlay: F
```

并按源规则使用 F 的保守方向，所有精确能量仍受 ACTIVE 配置控制。

## 2.3 为兼容现有产品界面，保留显示字段

```yaml
display_phenotype: A | B | C | D | E | F
```

如果界面继续要求 A–F 单选：

- 可将复杂度主导患者显示为 `F`；
- 但后台必须同时保存 `primary_nutrition_phenotype` 和 `complexity_overlay`；
- 不得仅凭 `display_phenotype=F` 丢失其 underlying A–E 营养方向。

---

# 3. Modifier 层：哪些评估结果可以覆盖/修正表型默认模板

## 3.1 疾病/代谢 modifier

疾病/实验室信息不是“备注”，而应改变相应模块：

- 高血压：影响食物选择、监测和运动安全；不由 AI 自行修改药物或创造钠阈值；
- 糖尿病/糖代谢异常：影响餐次、主食/加餐选择、运动与低/高血糖安全监测；不得自行改降糖药；
- 血脂异常：影响脂肪来源和蛋白/烹调选择；
- MASLD/脂肪肝/肝弹性风险：可降低强化减脂优先级；显著风险进入 YELLOW/人工复核；
- CKD/肾功能异常：可覆盖通用高蛋白规则；
- 贫血、低白蛋白、维生素/其他实验室异常：进入医护审核或营养恢复修饰，不由 AI 自行开药/补充剂。

## 3.2 摄入/症状 modifier

- 早饱、恶心、食欲下降、摄入不足：优先改变餐次体积、质地、能量密度与进食顺序；
- D/E 型或任何患者若执行不足，先 `BARRIER_FIRST / NUTRITION_RECOVERY`，不得只把 kcal 目标继续调高；
- 明显长期低摄入、重度营养不良、电解质风险：进入再喂养风险路径，不机械使用 115%/120% TEE。

## 3.3 功能/症状 modifier

6MWT、BORG、气促、疲劳、疼痛、关节/腰背/平衡限制必须实际改变：

- 有氧形式与是否分段；
- 抗阻动作池与动作数量；
- 是否采用坐姿/扶持；
- 训练日分布与恢复日；
- 是否冻结自动进阶。

不得仅把这些信息写在患者画像里而不影响方案。

## 3.4 手术窗口 modifier

继续沿用原规则：越接近手术，越强调营养充分、保肌、功能和动作熟练，越不允许激进减重或突然大幅进阶。

## 3.5 Q56 modifier

Q56 只改变阶段目标/模式权重，不得越过 Safety、营养风险、肌肉保护、手术窗口和 ACTIVE 参数边界。

## 3.6 执行/偏好 modifier

Q51–Q55、家庭支持、记录方式、备餐能力、运动偏好、器材/场地/时间可及性必须改变任务设计，例如：

- 任务数量与复杂度；
- 菜品/食材可获得性；
- 记录方式（照片/文字/份量完成率）；
- 训练形式和时间安排；
- 是否需要家属协助。

## 3.7 运动活动语义 modifier：功能活动 ≠ 正式有氧训练

V4.1 强制区分以下活动角色：

```yaml
activity_role: functional_activity | formal_aerobic | warmup | recovery_walk | resistance | flexibility
```

后台周汇总必须至少分开保存：

```yaml
formal_aerobic_training_days_target: null
functional_activity_days_target: null
resistance_training_days_target: null
recovery_days_target: null
```

规则：

- 为维持日常功能而安排的 3–10 分钟舒适轻走、室内走动或恢复性散步，若处方目的不是正式 FITT 有氧训练，应标记为 `functional_activity` 或 `recovery_walk`；
- D/E/F 患者可出现 `functional_activity_days_target=7`，但不得因此自动写成“7天正式有氧训练”；
- 同一天可同时存在功能活动和正式有氧训练，但必须在 trace 中分别标记；
- 患者端可继续显示自然语言“轻走/散步/活动”，工程语义保留在后台。

---

# 4. 能量主路径：P1 → ACTIVE P2 → P3_TEMP → P4_RANGE

六型回归后，能量来源必须按以下机器规则执行，禁止由模型临时挑选主算法。

## 4.1 Primary energy source 状态

### P1｜可靠间接测热

若存在当前有效、可用的间接测热 REE：

```yaml
primary_energy_source: P1_INDIRECT_CALORIMETRY
```

以实测 REE 为主基础；后续 PAL/活动修正仍按项目配置执行。

### P2｜院内批准预测公式

只有当：

```text
REE_FORMULA_ID = ACTIVE
且必要输入完整
```

才允许：

```yaml
primary_energy_source: P2_APPROVED_FORMULA
```

MSJ 或其他公式若仍为 `PENDING/CONFIG`：

- 可以作为**候选/交叉校验**展示给医护；
- 不得被不同 AI 随机当作正式主 REE；
- 不得在 `source_status=ACTIVE` 时伪装成已批准公式。

### P3｜BIA/BMR 临时降级

若 P1 不可用，P2 未 ACTIVE/不可用，而当前 BIA/BMR 数据有效：

```yaml
primary_energy_source: P3_BIA_BMR_TEMP
```

允许用于**医护审核草稿**的临时能量链；必须标记 `TEMP/PROVISIONAL`，不得直接进入 PUBLISHED。

### P4｜25–30 kcal/kg/d 保守参考

若 P1/P2/P3 都不可用：

```yaml
primary_energy_source: P4_KCAL_PER_KG_RANGE
```

只能输出保守范围，不得伪造精确单点目标。

## 4.2 PAL 的状态语义

- `ACTIVE PAL`：可进入正式 TEE 计算；
- `PENDING PAL`：可在**测试/医护审核草稿**中形成 provisional TEE，但必须明确 candidate source，且 publication 必须阻断；
- PAL 缺失且无法合理形成候选：TEE 保持不可用，不得自行创造。

## 4.3 禁止多个算法简单平均

P2/P3/P4 仅作交叉校验，不能为了“看起来稳妥”简单平均。

保存：

```yaml
energy_basis:
  primary_source: P1_INDIRECT_CALORIMETRY | P2_APPROVED_FORMULA | P3_BIA_BMR_TEMP | P4_KCAL_PER_KG_RANGE
  source_status: ACTIVE | PROVISIONAL | UNAVAILABLE
  formula_id: null
  measured_ree_kcal: null
  predicted_ree_kcal: null
  bia_bmr_kcal: null
  pal_value: null
  pal_status: ACTIVE | PENDING | UNAVAILABLE
  tee_base_kcal: null
  tee_reference_range: null
  crosscheck_status: OK | REVIEW | DATA_CONFLICT | NOT_AVAILABLE
```

---

# 5. Energy Target 三态：ACTIVE / PROVISIONAL / UNAVAILABLE

这是本 V4 的强制新合同，用于解决 E 型回归中“target=null 却又生成精确 kcal 菜单”的矛盾。

## 5.1 ACTIVE

只有全部必要参数已 ACTIVE 且无阻断：

```yaml
energy_target:
  status: ACTIVE
  prescribed_energy_target_kcal: 1700
  provisional_energy_target_kcal: null
  provisional_target_source: null
```

可用于正式精确闭合，并进入 publication 的其余检查。

## 5.2 PROVISIONAL

当能量链有明确的审核候选依据，但公式/PAL/表型比例/下限等仍 PENDING：

```yaml
energy_target:
  status: PROVISIONAL
  prescribed_energy_target_kcal: null
  provisional_energy_target_kcal: 1700
  provisional_target_source:
    - P3_BIA_BMR_TEMP
    - PAL_CANDIDATE_1_35
    - D_ENERGY_RATIO_CANDIDATE_1_10
```

允许在**测试/医护审核草稿**中生成 exact-provisional 菜单，用于核对 FOOD 闭合和可执行性；但必须：

- 页面明确为审核草稿；
- 所有数值标记 candidate/provisional；
- `publication_validation.publication_blocked = true`；
- 不得把 `provisional_energy_target_kcal` 写成已批准处方；
- 不得自动生成 plan_task。

## 5.3 UNAVAILABLE

如果：

- P1/P2/P3 均无法形成可信单点；或
- 严重低摄入/再喂养风险尚未澄清；或
- 关键数据冲突导致不能确定安全目标；

必须：

```yaml
energy_target:
  status: UNAVAILABLE
  prescribed_energy_target_kcal: null
  provisional_energy_target_kcal: null
```

此时：

```yaml
diet_generation_mode: STRUCTURE_ONLY
```

只允许生成：

- 餐次结构；
- 小体积/易耐受/蛋白优先等方向；
- 可选食物类型/组件候选；
- 需要人工确认的缺失信息；

**不得再次自行选择一个 1700–1800 kcal 之类的区间并宣称闭合。**

## 5.4 三种饮食生成模式

```yaml
diet_generation_mode:
  EXACT_ACTIVE | EXACT_PROVISIONAL_REVIEW | STRUCTURE_ONLY
```

- `EXACT_ACTIVE`：只读 ACTIVE 目标；
- `EXACT_PROVISIONAL_REVIEW`：允许测试/医护审核草稿使用 provisional target；禁止发布；
- `STRUCTURE_ONLY`：无精确 target，不做伪精确 kcal/P/C/F 全天闭合。

---

# 6. D/E 与 F 的总控补充规则

## 6.1 D/E：营养恢复不是“把普通健康餐机械放大”

Master 层必须向 FOOD 生成器传递：

```yaml
nutrition_generation_flags:
  recovery_priority: true | false
  early_satiety: true | false
  nausea: true | false
  reduced_intake: true | false
  high_energy_density_needed: true | false
  high_protein_density_needed: true | false
  texture_simplification_needed: true | false
  ons_evaluation_needed: true | false
```

D/E 若存在早饱、恶心或明显摄入不足：

- 优先小体积、较高营养密度、易耐受结构；
- 不得仅通过把所有普通组件机械放大到 1.25/1.5 份实现恢复；
- FOOD 知识库不足时应明确 `knowledge_gap`，由营养 MDT 补充组件；
- ONS 可进入“需要医护评估”提示，但 AI 不自行开具体产品/剂量；
- 再喂养风险未排除时，禁止自动套 115%/120% TEE。

## 6.2 F：简化任务，但不丢失 underlying nutrition direction

当 `complexity_overlay=F`：

- FOOD：减少菜品/记录复杂度，优先可获得、可替换、家属可协助的方案；
- Exercise：动作数量减少、短段化、坐姿/扶持优先、完成率优先；
- Pulmonary Rehab：首周优先 1–2 个基础动作，不机械加入全部 P01–P05；
- Monitoring：保留核心记录，减少非关键填表负担；
- 下一周：先看完成率和障碍，不因“体重没变化”直接加码。

---

# 7. 患者展示层与后台审计层必须彻底分离

这是全局输出合同。02/03 文件负责具体字段，但 01 负责强制分层。

## 7.1 Patient-facing plan

患者可读层必须：

- 使用真实菜名、食材、实际可执行份量、简单做法和**菜名形式**的替换；
- 运动使用“缓慢步行、墙壁俯卧撑”等名称；
- 肺预康复使用“缩唇呼吸、腹式呼吸”等名称；
- 不让工程 ID 主导展示；
- Day1–Day7 每天必须自包含，不允许患者去翻前一天找内容。

患者层禁止作为主要展示：

```text
C004×1.25
P015
V003
S002
A01
R02
P01
同Day1早餐
同上
菜单A/菜单B/菜单C
```

ID 可以在医护审核端的次要信息或后台审计中显示，但患者执行页默认隐藏。

## 7.2 Clinician/Audit layer

后台必须保留：

- FOOD component_id / portion / nutrition source / replacement / status；
- Exercise action_id / dose / alternatives / session index；
- Pulmonary action_id / selection reason / dose status；
- source_versions / knowledge_item_ids / config ids；
- Validator 与 clinician review 状态。

## 7.3 可执行份量

Master 要求 FOOD 层区分：

```yaml
algorithmic_portion: ...
executable_portion: ...
```

患者端不得出现明显工程化伪精确份量（例如 37.5 g 鸡蛋、312.5 ml 牛奶、43.75 g 大米）作为默认最终执行量。

算法份量必须先转换为项目允许的可执行份量，再重新计算营养；不得简单四舍五入后沿用原营养数值。

## 7.4 Patient executability：患者方案不能只“数学闭合”

患者方案质量必须同时满足“可解释、可执行、与症状/能力匹配”。详细 FOOD/Exercise/Pulmonary 判据由 02/03 定义，Master 至少强制以下原则：

- 饮食优先形成自然的一餐，而不是为了闭合 kcal/蛋白把多个零碎组件机械拼在一起；
- 当主蛋白不足时，默认优先调整主蛋白菜的合理可执行份量，其次使用计划性蛋白加餐；只有在 02 规则允许且有明确理由时，才额外加入第二个小蛋白组件；
- D/E 伴早饱、恶心或明显摄入下降时，优先保证主蛋白与主食，蔬菜采用较小份、熟软、低体积设计；能量不足优先提高能量密度/拆分加餐，而不是只扩大总体食物体积；
- F overlay 可合理重复 2–3 个简单餐型或动作模式；“重复”本身不能自动判低质量，关键是是否降低执行负担且患者日页面仍自包含；
- 运动任务数、动作复杂度、器材要求和监督要求必须与功能、疼痛、Safety、执行障碍相匹配；
- 肺预康复不以项目数量为质量指标，只要满足当前目的的最小充分动作集即可。

## 7.5 STANDARD_COMPONENT 与 AI_GENERATED_DISH 的身份必须真实

FOOD 生成允许双通道：

```yaml
food_item_type: STANDARD_COMPONENT | AI_GENERATED_DISH
```

身份判断原则：

- 完整沿用 02 中已登记标准组件的原始食材结构/配方边界，可记为 `STANDARD_COMPONENT`；
- 对标准食材进行新的跨组件组合、改变核心配方结构、生成新的患者专属家常菜，必须记为 `AI_GENERATED_DISH`；
- `AI_GENERATED_DISH` 必须具有独立 `generated_dish_id`、结构化 ingredients、executable_portion、nutrition_status 和 review_status；
- 不得因为担心“库外”而把明显的新菜强行映射成旧 component_id；
- 允许 AI 生成新菜不等于允许 AI 自由编造营养值：精确营养必须来自 02 允许的可追溯营养计算路径；未重算时必须使用相应未确认状态。

## 7.6 Pulmonary minimum sufficient set

肺预康复默认追求“最小充分动作集”：

- 无明显呼吸症状、无痰、功能主要限制不在呼吸系统：首周通常只需 1–2 个基础技能，具体由 03 规则决定；
- 有活动气促/呼吸节律问题：优先考虑 P01/P02；
- 胸廓活动或运动-呼吸协调有明确需要时，再考虑 P03/P04；
- 有痰/排痰技能需求时才进入 P05；
- P06 始终受设备 + 适应证/需求 + 医护处方/指导 gate 约束；
- 不得为了“看起来完整”在第一周机械铺满 P01–P06。

---

# 8. 外部来源与生成边界

第一周方案的默认生成只允许依据本次实际提供的知识库和患者资料。

如果用户没有明确要求“查文献/验证指南/使用外部证据”：

- 不主动新增“外部证据核对”章节；
- 不把临时检索到的外部来源混入 `source_versions`；
- `source_versions` 只能列本次实际读取的知识库文件。

外部研究可作为独立研究任务处理，但不得悄悄改变当前项目 ACTIVE/PENDING 配置。

---

# 9. 周复评数据充分性：统一最低要求

继续沿用源文件中的产品候选阈值，直到 MDT 将其结构化为 ACTIVE 配置。

```yaml
weekly_data_sufficiency_candidate:
  weight_valid_morning_days_min: 4
  diet_record_days_min: 5
  task_outcome_coverage_min: 0.80
  symptom_function_days_min: 4
  body_composition_same_condition_days_min: 3   # 设备可得时
  waist_measurements_min: 1                     # A/B/C或适用时
```

## 9.1 体重趋势

- 体重尽量每日晨起、排空后、进食饮水前、同一设备记录；
- 至少 4 个有效晨起日才用于“可评价周”的 7 日均重/趋势判断；
- 不得只拿 Day1 与 Day7 两个点判断减脂/增重效果并自动改方案；
- 单日变化不得触发自动能量调整。

## 9.2 数据不足

若核心数据未达到可评价周要求：

```yaml
weekly_signal: DATA_INSUFFICIENT
```

只能：

- 补数据；
- 维持/保守化；
- 解决记录障碍；
- 必要时转人工。

不得：

- 自动强化减能；
- 自动增加运动量；
- 把“没记录”当成“方案没效果”。

## 9.3 周复评固定顺序

```text
0 手术窗口
1 Safety
2 数据充分性
3 实际执行率/障碍
4 生理反应：7日均重 + 体脂/肌肉/水分 + 腰围 + 功能/症状
5 primary phenotype + complexity overlay
6 Q56轨迹
7 只调整1–3个关键变量
8 生成新的AI_GENERATED_PENDING_REVIEW plan_version
```

---

# 10. 三层 Validator V4.1：完整 artifact + 内容质量 + 安全 + 发布

任何方案末尾必须输出 `artifact_manifest` 与三层 Validator；不得只输出一个笼统 PASS/FAIL。

## 10.0 `artifact_manifest`：content PASS 的硬前置

```yaml
artifact_manifest:
  patient_plan:
    present: true | false
    day1_day7_self_contained: true | false

  food_trace:
    present: true | false
    materialization: FULL | SUMMARY_ONLY | MISSING
    schema_version: FOOD_TRACE_V4_1 | null

  exercise_trace:
    present: true | false
    materialization: FULL | SUMMARY_ONLY | MISSING
    schema_version: EXERCISE_TRACE_V4_1 | null

  pulmonary_trace:
    present: true | false
    materialization: FULL | SUMMARY_ONLY | MISSING
    schema_version: PULMONARY_TRACE_V4_1 | null
```

### 硬规则

只有同时满足以下条件，`content_validation` 才**有资格**进入 PASS 判定：

```text
patient_plan.present = true
AND patient_plan.day1_day7_self_contained = true
AND food_trace.materialization = FULL
AND exercise_trace.materialization = FULL
AND pulmonary_trace.materialization = FULL
```

`SUMMARY_ONLY` 只能作为浏览/医护摘要，**绝不能冒充 full trace**。因此：

- 只有 `diet_plan_trace_summary` → content FAIL；
- 只有 `exercise_plan_trace_summary` → content FAIL；
- 只有 `pulmonary_rehab_trace_summary` → content FAIL；
- B/C 这类“患者内容完整但未物化完整 machine trace”的结果必须 FAIL，而不能因患者页看起来完整就 PASS；
- STRUCTURE_ONLY 也可以生成 FULL trace：营养字段允许为 null，但必须有明确 `nutrition_status/reason`，不能用“目标未知”作为省略完整对象的理由。

## 10.1 三层 Validator 固定结构

```yaml
validation:
  content_validation:
    status: PASS | FAIL
    artifact_completeness: PASS | FAIL
    patient_executability:
      status: PASS | PASS_WITH_REVIEW | FAIL
      failed_items: []
      review_items: []
    failed_items: []
    warnings: []

  clinical_safety_validation:
    status: PASS | PASS_WITH_REVIEW | FAIL
    safety_level: GREEN | YELLOW | RED
    triggered_rule_ids: []
    blocked_modules: []
    replacement_ids: []
    manual_review_reasons: []

  publication_validation:
    publication_ready: true | false
    publication_blocked: true | false
    blocking_reasons: []
    pending_config_ids: []
    non_active_knowledge_items: null | []
    unverified_knowledge_items: []
    knowledge_activation_status: VERIFIED | PARTIALLY_VERIFIED | UNVERIFIED
    clinician_review_status: AI_GENERATED_PENDING_REVIEW | IN_REVIEW | APPROVED_PENDING_PUBLISH | PUBLISHED
```

## 10.2 `content_validation` 判断“完整性 + 一致性 + 可执行性”

至少检查：

- 患者画像和当前数据状态；
- `primary_nutrition_phenotype`、`complexity_overlay`、display phenotype；
- Q56、手术窗口、Safety；
- 能量主来源与 `energy_target.status`；
- 饮食生成模式是否与 energy target 状态一致；
- Day1–Day7 是否完整且患者页每天自包含；
- FOOD 患者可读层是否有菜名/食材/份量/做法/替换；
- FOOD 后台是否物化 02 V4.1 规定的完整 `FOOD_TRACE_V4_1`；
- `STANDARD_COMPONENT` 与 `AI_GENERATED_DISH` 身份是否真实；新菜是否具有 `generated_dish_id`；
- 运动患者层是否有名称，后台是否物化完整 `EXERCISE_TRACE_V4_1`；
- `functional_activity` 与 `formal_aerobic` 是否区分；
- 肺预康复是否物化完整 `PULMONARY_TRACE_V4_1`，且遵守 minimum sufficient set、P05/P06 gate；
- Monitoring / weekly_review / clinician_notes / missing_data / pending items；
- 每日/每周汇总是否可复算，或在 STRUCTURE_ONLY 时明确不可精确复算的原因；
- 患者层与后台层是否一致；
- patient executability 子检查是否通过或仅存在可接受的 REVIEW 项。

### `patient_executability` 至少检查

```yaml
patient_executability_checks:
  patient_view_has_no_backend_ids_as_primary_display: true | false
  no_cross_day_reference: true | false
  portions_are_executable: true | false
  meal_structure_is_realistic: true | false | null
  no_unnecessary_food_fragmentation: true | false | null
  diet_matches_symptoms_and_intake_capacity: true | false | null
  exercise_task_load_matches_function_and_complexity: true | false | null
  formal_vs_functional_activity_semantics_correct: true | false
  pulmonary_minimum_sufficient_set_respected: true | false | null
```

其中 `null` 只用于当前资料不足、无法客观判断的质量项；必须进入 `review_items`，不得当作 true。

### 必须 FAIL 的典型情形

- `artifact_manifest` 任一必需 artifact 缺失，或任一 trace 仅 `SUMMARY_ONLY`；
- `FOOD_TRACE_V4_1` 缺少 02 规定的任一关键必填字段；
- 仅有 `C004@1.0` / `{id,scale}` 这类简化列表，却声称“完整可追溯”；
- 新生成菜明显改变标准组件配方，却仍伪装为 `STANDARD_COMPONENT` 或没有 `generated_dish_id`；
- `energy_target.status=UNAVAILABLE` 却生成精确 kcal 闭合菜单；
- `EXACT_PROVISIONAL_REVIEW` 使用未完成营养重算的 AI_GENERATED_DISH，却仍声称精确闭合；此时必须重算、降级为 STRUCTURE_ONLY，或 FAIL；
- 患者餐单缺餐次/关键份量/做法或跨日用“同Day1/同上/菜单A”代替完整内容；
- 患者端以工程 ID 为主要显示；
- 明显工程化伪精确份量未经执行化转换；
- 菜单明细与全天汇总明显不一致；
- 运动/肺预康复缺必要动作、剂量状态、停止/替代；
- 把连续轻活动机械统计成正式有氧训练日，导致 weekly summary 语义错误；
- 使用不存在/不允许的知识库 ID；
- 必需结构化字段缺失。

### 以下情况不能单独导致 content FAIL

- 配置仍 PENDING；
- 知识项 ACTIVE 状态尚未核实；
- 营养数据库尚未最终批准，但当前模式允许 PROVISIONAL/STRUCTURE_ONLY 且状态标注正确；
- 医护尚未审核；
- F overlay 为降低执行负担而合理重复 2–3 个餐型/动作模式；
- D/E/F 为安全或耐受原因减少训练动作数量，只要 reduction reason 被完整记录；
- 肺预康复只选择 1–2 个动作，只要满足 minimum sufficient set 且选择理由明确。

这些进入 warning/review item + publication blocker；只有违反当前生成模式、结构合同或安全规则时才转为 FAIL。

## 10.3 `clinical_safety_validation`

- `PASS`：无阻断性安全冲突；
- `PASS_WITH_REVIEW`：YELLOW、缺失/不确定、安全阈值/专科项仍需人工确认；
- `FAIL`：RED、明确禁忌或无法通过替代/降阶解决的冲突。

PENDING 本身不自动等于 safety FAIL。

## 10.4 `publication_validation`

发布至少要求：

1. `content_validation = PASS`；
2. `artifact_manifest` 四项均完整，三个 trace 均为 FULL；
3. Safety 已满足发布要求；
4. `energy_target.status = ACTIVE`；
5. 精确蛋白、餐次、运动、肺预康复参数均为 ACTIVE；
6. FOOD / Exercise / Pulmonary knowledge items 达到允许的 ACTIVE 状态；
7. 营养数据源、份量边界、闭合容差通过；
8. 未解决的 pending / missing / conflict 均已处理；
9. clinician review = `APPROVED_PENDING_PUBLISH`；
10. 发布前再次运行 Validator。

`PROVISIONAL` 方案即使内容和临床安全都合理，也必须：

```yaml
publication_ready: false
publication_blocked: true
```

---

# 11. “未确认”与“非ACTIVE”必须分开

### 未核实

```yaml
knowledge_activation_status: UNVERIFIED
non_active_knowledge_items: null
unverified_knowledge_items:
  - FOOD_COMPONENT_ACTIVE_STATUS
```

### 部分核实

```yaml
knowledge_activation_status: PARTIALLY_VERIFIED
non_active_knowledge_items:
  - FOOD_XYZ
unverified_knowledge_items:
  - FOOD_ABC
```

### 全部核实且无非ACTIVE项

```yaml
knowledge_activation_status: VERIFIED
non_active_knowledge_items: []
unverified_knowledge_items: []
```

不得把 `UNCONFIRMED` 写进 `non_active_knowledge_items` 充当已证实非ACTIVE。

---

# 12. 统一状态机与不可变历史

```text
Assessment
  ↓
AI_GENERATED_PENDING_REVIEW
  ↓
IN_REVIEW
  ↓
APPROVED_PENDING_PUBLISH
  ↓
PUBLISHED
  ↓
plan_task
  ↓
patient_record
  ↓
7-day weekly review
  ↓
new AI_GENERATED_PENDING_REVIEW plan_version
```

强制规则：

- 历史 `PUBLISHED` 不覆盖；
- 周调整必须新建 `plan_version`；
- 只有 `PUBLISHED` 才物化 plan_task；
- patient_record 记录实际执行，不重新随机菜品/动作；
- Safety 变化可暂停/降阶/转人工，但不篡改历史处方。

---

# 13. 第一周方案必须同时输出的三层内容

## 13.1 患者可读层

建议顺序：

```text
患者画像与本周重点
→ 本周目标
→ 饮食计划（真实菜名，不显示工程ID）
→ 运动计划（动作名称）
→ 肺预康复（动作名称）
→ 每日记录与安全提示
```

## 13.2 医护审核层

```text
A–E主方向 + F overlay
→ modifier摘要
→ Energy/Protein chain + 状态
→ clinician review items
→ missing_data / pending_config
```

## 13.3 后台审计层

```text
artifact_manifest
diet_plan_trace（FULL）
exercise_plan_trace（FULL）
pulmonary_rehab_trace（FULL）
plan_governance
validation
```

患者可读层不得因为审计需要而被大量 ID、PENDING 字段和 YAML 淹没。

---

# 14. `plan_governance` V4.1 固定合同

```yaml
artifact_manifest:
  patient_plan:
    present: true
    day1_day7_self_contained: true
  food_trace:
    present: true
    materialization: FULL
    schema_version: FOOD_TRACE_V4_1
  exercise_trace:
    present: true
    materialization: FULL
    schema_version: EXERCISE_TRACE_V4_1
  pulmonary_trace:
    present: true
    materialization: FULL
    schema_version: PULMONARY_TRACE_V4_1

plan_governance:
  plan_status: AI_GENERATED_PENDING_REVIEW
  plan_version: ""

  phenotype:
    display_phenotype: A | B | C | D | E | F
    primary_nutrition_phenotype: A | B | C | D | E | null
    complexity_overlay: F | none
    phenotype_evidence: []
    modifiers: []

  knowledge_versions:
    nutrition: V2.0
    food: V2.0
    exercise: V3.0
    pulmonary_rehab: V2.0
    safety: V2.0
    master_contract: V4.1

  source_versions: []

  energy_basis:
    primary_source: P1_INDIRECT_CALORIMETRY | P2_APPROVED_FORMULA | P3_BIA_BMR_TEMP | P4_KCAL_PER_KG_RANGE
    source_status: ACTIVE | PROVISIONAL | UNAVAILABLE
    formula_id: null
    measured_ree_kcal: null
    predicted_ree_kcal: null
    bia_bmr_kcal: null
    pal_value: null
    pal_status: ACTIVE | PENDING | UNAVAILABLE
    tee_base_kcal: null
    crosscheck_status: OK | REVIEW | DATA_CONFLICT | NOT_AVAILABLE

  energy_target:
    status: ACTIVE | PROVISIONAL | UNAVAILABLE
    prescribed_energy_target_kcal: null
    provisional_energy_target_kcal: null
    provisional_target_source: []

  diet_generation_mode: EXACT_ACTIVE | EXACT_PROVISIONAL_REVIEW | STRUCTURE_ONLY

  activity_semantics:
    functional_activity_days_target: null
    formal_aerobic_training_days_target: null
    resistance_training_days_target: null
    recovery_days_target: null

  active_config_ids: []
  pending_config_ids: []

  knowledge_item_ids:
    food: []
    exercise: []
    pulmonary_rehab: []

  knowledge_activation_status: UNVERIFIED
  non_active_knowledge_items: null
  unverified_knowledge_items: []

  weekly_data_sufficiency:
    evaluable_week: false
    confidence: HIGH | MODERATE | LOW | NOT_APPLICABLE
    missing_core_domains: []

  validation:
    content_validation:
      status: PASS | FAIL
      artifact_completeness: PASS | FAIL
      patient_executability:
        status: PASS | PASS_WITH_REVIEW | FAIL
        failed_items: []
        review_items: []
      failed_items: []
      warnings: []

    clinical_safety_validation:
      status: PASS | PASS_WITH_REVIEW | FAIL
      safety_level: GREEN | YELLOW | RED
      triggered_rule_ids: []
      blocked_modules: []
      replacement_ids: []
      manual_review_reasons: []

    publication_validation:
      publication_ready: false
      publication_blocked: true
      blocking_reasons: []
      pending_config_ids: []
      clinician_review_status: AI_GENERATED_PENDING_REVIEW

  clinician_review_required: true
```

### `source_versions` 强制规则

- 只能列本次真实读取的文件；
- 如果只输入 01/02/03 FINAL 文件，就只列这三个；
- 不得自动沿用旧 README、旧 Word 或未实际读取的来源；
- 未知 ID 保持 null/空数组，不得编造。

---

# 15. 六型回归测试的最低验收标准

后续用 A–F 六个 synthetic cases 回归时，应至少满足：

## A
- 减脂保肌方向；
- 其他代谢异常不存在时不误判 B；
- 绿色时可用 A 型周结构；
- 若 P2 未 ACTIVE，主 energy source 不得随机使用候选公式作为正式主路径。

## B
- 肥胖/高体脂 + 代谢异常；
- 疾病/肝弹性/气促等 modifier 能实际降低运动或强化资格；
- 不按目标 kg×7700 倒算。

## C
- 肌肉/功能优先；
- 不因高体脂自动进入 A/B 强化；
- 抗阻与蛋白保护优先。

## D
- 营养恢复/增重方向；
- 早饱/摄入不足时强调小体积、高密度、分餐；
- 不用普通健康餐机械放大作为唯一策略；
- 再喂养风险未明时不自动进阶到更高比例。

## E
- 止跌优先；
- 再喂养风险/低摄入时可使 `energy_target=UNAVAILABLE`；
- `UNAVAILABLE` 时禁止精确闭合菜单；
- 只有明确 provisional target 时才允许审核用 exact-provisional 菜单。

## F
- 必须保存 underlying A–E 营养方向（如存在）；
- F 主要影响任务复杂度、动作数量、记录方式和进阶速度；
- 不因 F 自动抹掉 B/C/D/E 的营养方向。

## 全部病例
- 患者端不以工程 ID 代替名称；
- Day1–Day7 自包含；
- `artifact_manifest` 四项必须显式输出；
- 三个 machine trace 必须物化为 FULL，summary 不能冒充 full trace；
- trace schema 一致；缺任一 full trace 时所有模型都必须 `content_validation=FAIL`；
- patient executability 子检查必须运行：份量可执行、餐食自然、任务负担与患者能力匹配；
- 非标准组件原始配方的新菜必须标为 `AI_GENERATED_DISH` 并生成 `generated_dish_id`；
- functional activity 与 formal aerobic 必须分开统计；
- 肺预康复遵循 minimum sufficient set，不以动作数量作为质量指标；
- Validator 对相同结构缺失给出一致结果；
- PENDING/UNVERIFIED 与 non-ACTIVE 语义分开；
- PROVISIONAL 草稿永远不能直接 PUBLISHED。

---

# 16. V4.1 执行伪代码

```text
1. 读取当前有效 Assessment/Profile/最新Published Plan/Patient Record。
2. 处理 missing/explicit_none/uncertain/need_review；不得把缺失当正常。
3. 先执行 Safety Gate；RED/BLOCK 优先。
4. 确定 primary_nutrition_phenotype A–E；再判断 complexity_overlay F。
5. 应用疾病、摄入、体成分、功能/症状、手术窗口、Q56、执行/偏好 modifiers。
6. 按 P1 → ACTIVE P2 → P3_TEMP → P4_RANGE 确定 primary energy source。
7. 形成 energy_target ACTIVE/PROVISIONAL/UNAVAILABLE。
8. 根据 energy target 状态选择 EXACT_ACTIVE / EXACT_PROVISIONAL_REVIEW / STRUCTURE_ONLY。
9. 调用 02 FOOD：先安全/疾病/过敏/耐受过滤；标准组件能自然组成餐食时可优先使用，否则允许 AI_GENERATED_DISH；新菜必须生成独立ID并进入可追溯营养计算/审核。
10. 调用 03 Exercise/Pulmonary：按表型方向 + modifier + Safety 生成周结构；区分 functional_activity 与 formal_aerobic；肺预康复采用 minimum sufficient set。
11. 生成 Monitoring 与 weekly data sufficiency 计划。
12. 输出 patient-facing + clinician-review + audit 三层内容，并物化 patient plan + FOOD/Exercise/Pulmonary 三个 FULL traces。
13. 生成 artifact_manifest；任一必需 artifact 缺失或 SUMMARY_ONLY，直接令 content_validation FAIL。
14. 运行 patient executability/content quality 子检查。
15. 运行 content_validation。
16. 运行 clinical_safety_validation。
17. 运行 publication_validation。
18. 保持 AI_GENERATED_PENDING_REVIEW，直到有权限医护审核。
19. 只有最终 PUBLISHED 才生成 plan_task。
20. 每7天按 Safety → 数据充分 → 执行 → 生理反应 → phenotype/modifier → Q56 生成新草稿。
```

---

# 17. V4.1 版本结论

V4.1 不改变 V4 的临床主架构。它把六型二次回归暴露出的“**患者内容已经较好，但不同模型对 full trace、summary、PASS/FAIL、轻活动语义和内容自然度理解仍不一致**”收口为可执行合同。

因此后续 AI 生成的个体化方案必须同时体现：

> **表型决定方向，评估决定细节，Safety 决定边界，ACTIVE 决定能否发布；患者端只看可执行内容，后台必须物化完整 trace；字段完整之外还要通过患者可执行性检查；轻活动不等于正式有氧，新菜必须真实标记来源，肺预康复以最小充分集为目标。**

V4.1 的验收重点不是让方案“更长”，而是让不同模型在同一患者和同一知识库下得到**同语义、同结构、同 Validator 结果，并输出更像真实临床执行方案的内容**。

---
# SOURCE: 肺结节患者术前营养与能量计算规则_V2.0_完整版_MDT审阅稿(1).docx

肺结节患者术前营养与能量计算规则

V2.0｜完整版 · MDT审阅稿 · 产品规则底稿 · Codex/AI实现依据

适用范围：肺结节/早期肺癌拟接受肺切除手术的术前多学科代谢健康管理

版本日期：2026-09-12｜基于 V1.0、Q56目标规则、肝弹性规则与能量/周动态调整 V2.0 合并修订

0. 执行摘要

术前营养管理的首要目标不是“尽快减重”，而是：安全 > 营养充分 > 肌肉保护/恢复 > 手术准备与功能 > 合并代谢疾病控制 > 体脂改善 > 体重目标。

方案生成采用“自动生成 + 医护审核”：Q56为选填的医护阶段目标；Q56空缺时，系统必须依 A–F 默认算法直接生成完整方案，不能停在“等待医护逐项设定数值”。

能量算法分为两层：先确定维持能量需要 TEE_base，再根据 A–F、Q56、手术窗口、营养/肌肉风险、肝弹性/肝纤维化风险、疾病状态和上一周真实反馈得到 Energy_target。

体重速度/目标体重属于“疗效轨迹目标”，不是每日 kcal 的直接计算公式。禁止“目标减重kg×7700÷天数”倒算处方能量。

所有精确比例、PAL、蛋白目标、最低能量保护、每周调整步长等必须进入 mdt_config；只有 ACTIVE 参数可进入患者精确方案。

缺失数据不得当正常。选填实验室、BIA、6MWT、肝弹性等缺失不默认阻断保守方案，但不得生成依赖缺失数据的伪精确结论。

0.1 规则状态定义

0.2 V2.0候选默认能量参数（需MDT确认后ACTIVE）

1. 适用范围、边界与权威层级

1.1 适用范围

成年肺结节/早期肺癌拟接受肺叶切除、肺段切除、楔形切除等肺切除术患者，重点覆盖术前数天至数周的代谢健康优化。

适用于规则引擎、Codex原型、后续AI Gateway与MDT审阅；患者端展示的是医护审核发布后的方案。

1.2 需要专科接管或阻断自动精细化的情形

需要肠内/肠外营养处方、明显吞咽障碍/持续呕吐、严重肾功能不全、失代偿肝病、活动性严重感染、重度营养不良/再喂养风险等。

AI不得自行诊断、修改药物、创造医学阈值或把PENDING参数伪装成已确认处方。

1.3 权威层级

2. 证据底座与本项目使用方式

3. 方案生成必须读取的营养相关输入

4. 维持能量 TEE_base：来源优先级 + 交叉校验

4.1 P1–P4来源优先级

4.2 P2预测REE执行细则

后台必须保存 REE_FORMULA_ID、公式版本和责任MDT。V2.0建议把 Mifflin–St Jeor（MSJ）作为候选默认公式供营养科评估；若院内选择其他公式，只切换配置，不改变数据合同。

MSJ候选：男性 REE = 10×体重(kg) + 6.25×身高(cm) − 5×年龄 + 5；女性 REE = 10×体重 + 6.25×身高 − 5×年龄 − 161。它是预测公式，不是肿瘤患者“金标准”。

输入 sex、age、height_cm、weight_kg 必须来自当前有效评估；缺失不得伪造。

4.3 PAL候选映射

明显气促、疼痛、平衡问题、近期疾病变化或实际活动低于问卷频率时，PAL应向下修正。

可穿戴设备步数/活动时间可作交叉信息，但不凭单日步数重算处方。

4.4 TEE_base确定算法

4.5 交叉校验与异常处理

5. 体重基准（weight_basis）

6. A–F型处方能量 Energy_target 规则

6.1 A型：超重/高体脂

Q56为空：候选默认 Energy_target = 0.85 × TEE_base。

Q56=强化减脂且通过全部门槛：0.80 × TEE_base。

肌肉/功能下降、连续摄入不足、食欲下降、手术窗口缩短或肝纤维化风险增加：退出强化或转维持/保肌。

6.2 B型：肥胖/高体脂 + 代谢异常

Q56为空：候选默认 0.80 × TEE_base。

强化且通过门槛：0.75 × TEE_base。

血糖/血压/血脂/尿酸影响食物选择、监测和运动安全；AI不得调整药物。

6.3 C型：高体脂 + 肌少风险

第一周候选默认 1.00 × TEE_base，先确认摄入、肌肉和功能稳定。

7–14天数据充分、营养/蛋白执行充分、肌肉/功能稳定且仍需改善体脂/腰围：可提出95% TEE；再次稳定后最低可评估90%。

任何持续肌肉/功能下降、明显疲劳或摄入不足：冻结进一步减能，回100%或营养恢复。

6.4 D型：消瘦/营养风险

禁止进入减重算法。无明显再喂养风险且可经口进食：候选默认 1.10 × TEE_base。

执行≥80%但体重仍下降/不能稳定，且无水肿/再喂养风险：提出1.15 × TEE；必要时最高自动1.20 × TEE。

执行不足时先处理早饱、恶心、咀嚼/吞咽、餐次、能量密度和ONS，不盲目加处方目标。

6.5 E型：近期非意愿下降 + 摄入不足/肌肉功能下降

第一目标为止跌。无再喂养风险：候选默认 1.15 × TEE_base。

7天后执行≥80%但体重仍持续下降且肌肉/功能未改善：可提出1.20 × TEE；120%作为自动上限。

存在长期低摄入、重度营养不良或电解质风险时，不自动115/120%，进入再喂养安全路径。

6.6 F型：复杂共病/执行困难

F型核心是安全、可执行性和任务简化。

缺乏更明确A–E方向时：候选默认1.00 × TEE_base。

若同时有明显肥胖、高体脂或营养不足，调用更具体A/B/C/D/E方向；F决定复杂度、记录和进阶速度。

6.7 手术时间窗口与肝弹性修正

7. 强化减脂模式（Enhanced Fat Loss）

7.1 进入路径

路径A：Q56明确选择“强化减脂”，并通过全部安全/营养/肌肉门槛。

路径B：Q56为空/标准减脂，但连续2个“可评价周”执行充分、A/B脂肪相关指标无有利趋势；规则引擎可提出标准→强化的新草稿，仍需医护审核。

7.2 强化资格门槛（全部满足）

主表型A或B，非C/D/E主导。

预计手术≥4周。

临床安全绿色，疾病/代谢状态无明显不稳定。

近期无非意愿下降、明显摄入不足或营养风险主导。

肌肉/骨骼肌与功能无持续下降。

食欲基本正常；过去一周饮食执行充分（候选≥80%）。

肝弹性/肝病资料未提示需冻结快速减重。

运动限制、疼痛、气促、头晕等不构成明显进阶障碍。

7.3 退出/降阶

连续3天摄入不足或食欲明显下降。

7天肌肉或功能下降。

新发/加重症状或黄色/红色事件。

手术窗口缩短至<4周。

肝纤维化风险升高/需肝病专科复核。

体重下降较快但同时水分明显下降、肌肉下降或疲劳/气促加重。

8. Q56：能量处方目标与代谢健康管理速度目标分离

8.1 两类变量必须分开保存

8.2 Q56为空/有值时

8.3 为什么禁止“目标kg×7700 kcal”直接倒算

人体脂肪组织并非100%纯脂肪；短期体重变化还包含无脂组织、糖原及结合水、体液和肠内容物。

减重过程中能量消耗会随体重、摄入和适应发生变化，静态7700规则不能代表连续数周的动态生理。

因此禁止：目标减重kg × 7700 ÷ 天数 = 每日必须制造的能量缺口。该做法会把阶段体重目标错误等同于脂肪组织能量，并可能造成术前过度限制。

7700仅保留为历史概念/教学解释，不进入 Energy_target。0.5–1 kg/周、%体重/周或Q56目标只用于疗效轨迹和强度参考，不与15%/20%/25%缺口一一对应。

9. 蛋白质计算与肌肉保护规则

证据底座：癌症临床营养指南支持蛋白>1.0 g/kg/d、可至1.5 g/kg/d；老年疾病状态常见1.2–1.5 g/kg/d；肺癌围手术期资料支持高端蛋白目标。具体默认值与weight_basis仍由本院MDT配置。

10. 三大营养素与膳食模式

V2.0默认禁止自动采用：生酮饮食、极低能量饮食、间歇性禁食（尤其短术前/营养/肌少风险）、成分不明减重/护肝产品、酒精，以及因单餐超量而要求跳过下一餐。

11. 三餐与加餐分配

12. 疾病/风险修正规则（营养层面）

13. 营养支持升级、ONS与再喂养

严重营养不良/高代谢风险患者术前应接受营养治疗；具体是否需要10–14天及是否影响手术时间由胸外科/营养MDT共同决策。

若普通食物不能满足需要，可进入ONS评估；产品、剂量、禁忌和疾病适配必须来自院内审核目录。

D/E、持续摄入不足、快速非意愿下降、明显肌肉下降患者不得继续输出减重型菜单。

再喂养高风险：长期显著低摄入、重度营养不良、电解质风险等，不直接套115%/120%TEE；进入专科路径，逐步增加并监测磷/钾/镁等。

当“处方目标高但实际执行低”时，优先解决食欲、早饱、恶心、吞咽/咀嚼、餐次、体积和能量密度，不把目标kcal无限加高。

14. 营养方案结构化输出合同（Codex/AI）

正式输出必须是可追溯的结构化处方草稿。数值必须能追到ACTIVE参数/规则；缺失值保持null。

diet_plan: {
  energy_basis: {
    primary_source: "indirect_calorimetry | approved_REE_formula | BIA_BMR_TEMP | kcal_per_kg_range",
    formula_id: string|null, measured_REE_kcal: number|null, predicted_REE_kcal: number|null,
    bia_bmr_kcal: number|null, pal_value: number|null, tee_base_kcal: number|null,
    tee_ref_25_30: {low:number|null, high:number|null}, crosscheck_status: "OK|REVIEW|DATA_CONFLICT"
  },
  phenotype: "A|B|C|D|E|F",
  management_mode: "STANDARD|ENHANCED|MAINTENANCE|NUTRITION_RECOVERY|MUSCLE_PRIORITY",
  q56_goal: {...}|null,
  daily_energy_target_kcal: number|null,
  protein_target_g: number|null, protein_target_g_per_kg: number|null,
  carbohydrate_target_g: number|null, fat_target_g: number|null,
  meal_distribution: {breakfast_pct, lunch_pct, dinner_pct, snack_pct},
  meals: [{meal_type, dish_name, ingredients, amount, cooking_method, estimated_energy, protein, carbohydrate, fat, replacement_options, precautions}],
  nutrition_risk_flags: [], missing_data: [], mdt_pending_items: [],
  generation_source: "RULE_ENGINE|AI", clinician_review_required: true
}

14.1 自动校验

daily_energy_target_kcal为null时，下游菜品库不得拼出伪精确总热量。

餐次能量之和必须在配置容差内闭合。

protein_target必须检查weight_basis、CKD/肾功能规则。

D/E不得出现deficit模式；C不得直接进入A/B强化。

手术≤2周不得保持强化减脂；≤1周不得新启减重冲刺。

肝弹性报告不明确时，不用单一LSM自行生成纤维化等级。

糖尿病不因模板强制固定50–60%碳水。

任何PENDING参数写入mdt_pending_items，不进入患者精确任务。

15. 营养执行、周复评与下一周能量调整

15.1 评价前先区分“方案无效”还是“没有执行”

数据是否可靠、连续、同条件？

饮食/蛋白任务是否真正执行？

是否有食欲下降、早饱、恶心、吞咽等摄入障碍？

是否有疾病、用药、手术窗口变化？

体重变化是否主要受水分影响？

体重不变时，体脂/脂肪量、腰围、肌肉、功能是否改善？

15.2 可评价周的产品候选最低要求

15.3 周结论与营养动作

15.4 A–F周调整确定性规则

16. 与营养规则直接相关的数据记录字段

本节只列营养/能量算法需要的记录；完整患者数据记录规范由《能量计算、数据记录与周动态调整规则 V2.0》统一管理。

17. 建议后台 MDT 配置项（V2.0）

18. 推荐给 Codex / 后续 AI 的营养规则执行顺序

读取当前有效 Q1–Q56 Assessment、assessment_result、patient_profile、最新published plan和patient_record，不使用旧缓存/Mock。

检查核心输入与missing/explicit_none/uncertain；先执行红黄绿安全和营养BLOCK规则。

按P1→P2→P3→P4确定primary energy source，计算/得到REE，并按ACTIVE PAL得到TEE_base；完成交叉校验。

确定A–F主表型与修饰标签，读取Q56；Q56空则用A–F默认模式，Q56有值则做目标冲突校验。

应用手术窗口、肝弹性/肝纤维化、CKD、摄入/肌肉/功能等修正，得到Energy_target；禁止kg×7700倒算。

按ACTIVE蛋白和weight_basis得到Protein_target；再确定碳水/脂肪与餐次分配。

从ACTIVE菜品/食物库组合餐食，完成过敏、不耐受、疾病、执行障碍过滤，并做全天能量/宏量闭合校验。

输出Structured Plan Draft + evidence/config IDs + missing_data + mdt_pending_items，状态仅AI_GENERATED_PENDING_REVIEW。

医护审核/修改/批准后PUBLISHED；发布后再物化DIET plan_task，患者记录实际执行。

每7天先判断数据质量和执行，再按A–F/Q56/安全规则生成下一周新草稿；不直接覆盖已发布版本。

19. 必测回归场景

20. V2.0上线前 MDT 必须确认的参数

21. 参考指南与项目内部资料

21.1 外部指南/文献

[R1] 国家卫生健康委. 成人肥胖食养指南（2024年版）及体重管理指导原则（2024年版）.

[R2] 中国营养学会. 中国居民膳食指南（2022）.

[R3] Muscaritoli M, et al. ESPEN practical guideline: Clinical Nutrition in cancer. Clinical Nutrition. 2021;40:2898–2913.

[R4] ESPEN guideline on clinical nutrition in surgery – Update 2025. Clinical Nutrition. 2025.

[R5] Clinical practice guidelines for perioperative multimodality treatment of non-small cell lung cancer. 2025.

[R6] Volkert D, et al. ESPEN practical guideline: Clinical nutrition and hydration in geriatrics. Clinical Nutrition. 2022;41:958–989.

[R7] EASL–EASD–EASO Clinical Practice Guidelines on the Management of MASLD. 2024.

[R8] KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease.

[R9] American Diabetes Association. Standards of Care in Diabetes—2026.

[R10] Wishnofsky M. Caloric equivalents of gained or lost weight. Metabolism. 1958.（7700 kcal/kg历史经验规则来源；本项目不作为处方公式）

21.2 项目内部资料

《肺结节患者术前多学科代谢健康管理｜AI方案生成提示词｜分型·分级·目标·方案·监测·安全｜完整版最新版》

《肝弹性成像与肝脏代谢风险处理规则》

《AI方案生成治理补齐说明》

《肺结节患者术前能量计算、数据记录与周动态调整规则 V2.0｜完整版 MDT审阅稿》

《肺结节患者术前菜品与食谱组件库 V1.0｜MDT审阅_AI调用版》


## Table


文件定位 本文件不是让医护为每位患者逐项手工填写 kcal、蛋白质和餐次参数，而是把一次性由本院 MDT 审核启用的营养算法、能量参数、安全边界与周调整规则结构化。系统/Codex/后续 AI 应根据 Q1–Q56 评估、A–F 分型、手术窗口、疾病与安全修饰因素自动生成完整营养方案草稿；医护负责审核、必要时修改并发布。


## Table


V2.0关键变化 ①补齐 REE/TEE 来源优先级、PAL 与交叉校验；②把 A–F 默认能量比例、强化减脂、手术窗口与肝弹性修正写成可配置规则；③加入 Q56 目标层；④明确“目标kg×7700 kcal”不得直接倒算处方；⑤加入营养执行与7天/14天趋势驱动的下一周调整逻辑；⑥保留 V1.0 的蛋白、宏量营养素、餐次、疾病修正、ONS/再喂养和结构化输出合同。


## Table


状态 | 含义 | 系统行为 | 示例

ACTIVE | 证据与项目逻辑均明确，且已获院内审核 | 允许自动执行 | 缺失≠正常；D/E不得进入减重算法

PENDING / CONFIG | 有证据或项目候选值，但院内数值尚待MDT确认 | 只保留方向/待确认；不得形成精确处方 | PAL、蛋白默认值、能量比例/下限

REVIEW | 存在疾病/风险/数据冲突，需要人工复核 | 可生成保守方案；冻结相关精细化调整 | 肝纤维化风险升高、REE/BIA冲突、已知CKD

BLOCK | 安全条件不允许继续相应自动调整 | 停止相关生成/进阶并转医护 | 严重摄入障碍、再喂养高风险、红色安全事件


## Table


分型/模式 | Q56未填默认 | 可进入下一阶 | 自动化限制

A 超重/高体脂 | 85% TEE | 强化80% TEE | 强化不低于80%；短手术窗关闭

B 肥胖+代谢异常 | 80% TEE | 强化75% TEE | 强化不低于75%；短手术窗关闭

C 高体脂+肌少风险 | 100% TEE | 稳定后95%，再评估90% | 90%为候选下限；肌肉/功能下降冻结减能

D 消瘦/营养风险 | 110% TEE | 115%，最高自动120% | 再喂养/严重摄入障碍不自动套比例

E 非意愿下降/摄入不足 | 115% TEE | 必要时120% | 120%后仍下降→营养科/MDT

F 复杂/执行困难 | 100% TEE | 按更具体A–E营养方向叠加 | 优先简化执行；不自行定义减脂强度


## Table


优先级 | 来源 | 职责

1 | 安全规则 | 红/黄/绿分流、禁忌、停止条件、转人工；任何目标/处方不得突破。

2 | ACTIVE MDT参数 | 能量比例、REE公式、PAL、蛋白、餐次、最低能量边界、周调整步长。

3 | ACTIVE结构化知识库 | 菜品/食物组件、营养标签、替代项、疾病适配。

4 | Q56医护目标（如填写） | 决定阶段目标和管理强度；不能突破1–3层。

5 | A–F默认路径 | Q56为空时提供确定性默认；Q56有值时继续承担表型保护和冲突校验。

6 | AI提示词 | 负责读取、编排、解释；不得发明剂量和阈值。


## Table


证据来源 | 年份 | 支持内容 | 本项目用法

国家卫健委成人肥胖/体重管理相关指南 | 2024 | 一般超重/肥胖可采用限制能量策略；部分指导给出按实际需要量比例或500–1000 kcal/d/约30%等方法。 | 作为A/B默认与强化候选的循证锚点；术前不机械复制大缺口。

中国居民膳食指南 | 2022 | 规律三餐、基础膳食结构与餐次能量分配。 | 餐次分配和食物质量参考。

ESPEN癌症临床营养实践指南 | 2021 | 无法个体测量时能量约25–30 kcal/kg/d；蛋白>1.0至1.5 g/kg/d；持续监测摄入/体重。 | P4能量校验、蛋白范围和监测框架。

ESPEN外科临床营养指南更新 | 2025 | 营养筛查、术前营养治疗、ONS/EN/PN升级和再喂养风险。 | D/E、摄入不足和营养支持升级路径。

NSCLC围手术期多模式临床实践指南 | 2025 | 围手术期预康复和蛋白补充。 | 保肌/预康复的高端蛋白候选支持。

ESPEN老年营养与水化实践指南 | 2022 | 老年人能量/蛋白和避免不必要饮食限制。 | 高龄、虚弱、营养风险修正。

EASL–EASD–EASO MASLD指南 | 2024 | 长期体重/腰围与肝脏代谢改善、膳食质量。 | 长期目标参考；短术前窗口仍服从营养/手术优先级。

KDIGO CKD指南 | 2024 | CKD蛋白摄入需个体化并避免高蛋白风险。 | 已知CKD覆盖常规高蛋白策略。

ADA Standards of Care | 2026 | 糖尿病不存在适用于所有人的固定三大营养素比例。 | 糖代谢异常患者个体化宏量营养素。


## Table


输入域 | 核心字段 | 必需性 | 缺失时行为

基础资料 | 年龄、性别、身高、体重、BMI、腰围 | 身高/体重原则上核心 | 不做伪精确REE/kcal/kg/g/kg；按可用来源降级并提示补充。

体成分 | 体脂率、脂肪量、肌肉量、骨骼肌量、SMI、水分、BMR | 可缺失 | 不阻断基础方案；不得伪判肌肉正常/异常；C型精细化受限。

体重趋势 | 近6个月变化、是否非意愿下降 | 建议核心 | 不自动认为稳定；降低减/增重精确判断。

摄入/症状 | 食欲、进食量、早饱/恶心/吞咽等、过敏/不耐受 | 建议核心 | 未知≠无；影响D/E、再喂养/ONS与食谱适配。

活动/功能 | Q35–Q37、6MWT或替代耐量、活动受限 | PAL映射需要 | 不足时使用保守PAL并标记置信度。

代谢疾病 | 高血压、糖代谢、血脂、尿酸、MASLD等 | 条件必需 | 有病史无指标时保守生成；疾病目标unknown/review。

实验室 | 血糖/HbA1c、脂质、尿酸、ALT/AST、白蛋白、肌酐/eGFR、Hb等 | 选填/条件必需 | 缺失不视正常；不做依赖指标的精确分层。

肝弹性 | 方法、LSM、报告结论、CAP等 | 选填 | 缺失不阻断；仅数值无报告时不自行分纤维化等级。

手术窗口 | ≤2周、2–4周、4–8周、>8周、未确定 | 核心 | 未确定时不启用激进策略。

Q56目标 | 首要目标、目标周期、体重目标、其他重点 | 选填 | 空缺→按A–F默认模式自动完整生成；不能要求医护逐例补数。


## Table


核心原则 “来源优先级”决定主估算值；“交叉校验”用于发现不合理或数据冲突。不同算法不做简单平均，也不由AI临时选择公式。


## Table


优先级 | 来源/算法 | 系统用法 | 状态

P1 | 间接测热得到REE（若有可靠结果） | 作为主基础；结合活动水平得到TEE。 | 循证锚点

P2 | 医院批准的REE预测公式 + PAL | 无实测REE时主算法；公式ID固定配置，不由AI临时挑选。 | 项目候选配置

P3 | BIA/体脂秤/身体成分仪BMR | 辅助估计与交叉校验；P1/P2不可用时可临时降级使用。 | 既有项目规则

P4 | 25–30 kcal/kg/d粗略参考 | 合理性校验/数据不足时保守范围；肥胖可能高估、严重营养不良可能低估。 | 循证锚点


## Table


MDT提示 PAL数值不是指南强制的肺结节分级，而是为了把Q35–Q37、活动受限与功能资料映射成可执行算法的项目候选参数。应由营养/康复MDT审核后ACTIVE。


## Table


PAL候选 | 患者特征（示例） | 主要数据来源

1.20 | 卧床/活动明显受限/日常活动很少 | Q35 + 功能限制 + 医护判断

1.30 | 久坐；当前运动<1次/周 | Q35

1.35 | 1–2次/周，日常生活可独立 | Q35 + 6MWT/耐量

1.45 | ≥3次/周、轻至中等活动且功能良好 | Q35 + 6MWT/耐量

1.55 | 规律较高活动量且无明显限制（术前少见） | 医护/设备数据确认


## Table


确定性算法 P1可用：primary_REE = measured_REE；否则P2字段完整：primary_REE = predicted_REE；P1/P2均不可用但P3有BMR：primary_REE = BIA_BMR_TEMP；前三者均不可用：P4仅输出25–30 kcal/kg/d的保守范围。若以REE为基础，则 TEE_base = primary_REE × ACTIVE PAL。


## Table


字段/派生值 | 来源 | 系统规则

measured_REE_kcal | 间接测热 | 可靠时最高优先级

predicted_REE_kcal | REE_FORMULA_ID+年龄/性别/身高/体重 | P1缺失时主算法

bia_bmr_kcal | BIA/身体成分仪 | 辅助校验；必要时降级使用

pal_value | Q35–Q37、功能/6MWT | 必须来自ACTIVE映射

tee_base_kcal | primary_REE×PAL | A–F/Q56处方计算基准

tee_ref_25_30 | 体重×25至30 | 粗略参考区间，不覆盖主算法

crosscheck_status | P2/P3/P4一致性 | OK / REVIEW / DATA_CONFLICT


## Table


校验项 | 候选规则 | 系统动作

预测REE vs BIA-BMR | 差异>15%→REVIEW；>20%或会改变模式/触及能量下限→DATA_CONFLICT | 核对年龄、性别、身高、体重、测量时间、水分状态、设备；不自动平均。

P4 25–30 kcal/kg/d | 与主TEE明显不一致 | 只降低置信度并提示复核；不覆盖P1/P2。

体重/肌肉趋势 | 执行1–2周后与预计方向明显不符 | 先查执行、测量、水分、症状、药物/疾病变化，再调能量。

Energy_target低于REE或院内最低能量边界 | 低于REE本身不机械阻断；低于ACTIVE最低边界则阻断 | 标记enhanced_restriction并检查营养/肌肉/手术窗口；必要时MDT。

核心数据缺失 | 无可靠REE/BMR或体重不足 | 采用可用的保守估算并记录来源/不确定性，不伪造单点。


## Table


情形 | 建议 | 状态/限制

REE预测公式 | 按所选公式的验证要求使用体重；MSJ候选使用当前实际体重 | 公式ID决定，不由AI自行改用理想体重。

P4 kcal/kg或蛋白g/kg | 需要独立weight_basis规则 | 实际/理想/调整/干体重由MDT配置。

肥胖/高体脂 | 避免机械用实际体重×高端kcal/kg或g/kg | 理想/调整体重公式需院内确认。

水肿/腹水 | 优先干体重或医护确认参考体重 | REVIEW；AI不得自行估干体重。

近期快速非意愿下降 | 同时保留当前体重与既往稳定体重用于营养风险 | 不因当前BMI尚正常就判低风险。


## Table


公式框架 Energy_target = TEE_base × phenotype_mode_ratio，经手术窗口、肝弹性/肝纤维化、营养/肌肉风险和疾病安全修正。所有比例来自ACTIVE配置；AI/Codex不得自行创造百分比。


## Table


修饰因素 | 默认动作

预计手术>4周 | 可按A–F默认；A/B符合条件可强化。

预计手术2–4周 | 关闭自动跨级强化；以当前标准模式、保肌和功能为主。

预计手术≤2周 | 关闭强化；A/B若无Q56特殊目标，候选回95–100% TEE（建议默认100%）；重点营养、保肌、功能、肺预康复。

稳定脂肪肝/低风险肝弹性 | 不单独改变A–F能量方向；优化总能量、精制糖、脂肪质量、体重/腰围。

肝纤维化风险增加 | 降低快速减重优先级；不进入强化；优先营养充分与肌肉。

显著/进展期纤维化或肝硬化可能 | 黄色+肝病/MDT复核；冻结激进减重和自动进阶。


## Table


核心原则 强化模式是预设的确定性模式，不是Codex/AI“自己挑更大缺口”。A/B标准与强化比例必须由MDT预先ACTIVE；AI只能调用。


## Table


表型 | 标准模式 | 强化模式 | 自动最低比例

A | 85% TEE | 80% TEE | 80%

B | 80% TEE | 75% TEE | 75%

C | 100→95→90%阶梯 | 不进入A/B强化 | 90%

D/E/F | 不适用减脂强化 | — | —


## Table


变量 | 含义 | 谁决定 | 是否直接计算每日kcal

prescribed_energy_target_kcal | 本周实际处方能量 | 确定性规则+ACTIVE参数 | 是

management_goal / Q56 | 标准/强化/保肌/营养恢复等阶段目标 | 医护选填；空则A–F默认 | 决定模式，不直接倒算

target_weight_change_kg / target_weight_kg | 周期末目标体重/变化量 | Q56选填 | 否

weekly_weight_trajectory | 目标换算出的比较轨迹 | 系统派生 | 只用于疗效比较

observed_weekly_change | 真实7天趋势 | patient_record | 用于周复评和下一周调整


## Table


场景 | 系统动作

Q56为空 | 取消固定“2/4/8周必须减X%”默认矩阵；直接按A–F默认能量模式生成完整第一周方案。

Q56=标准减脂 | A85%、B80%；C/D/E/F继续按保护规则。

Q56=强化减脂 | 通过资格门槛后A80%、B75%；否则提示冲突并降阶。

Q56填目标体重/变化量 | 生成目标轨迹用于比较；每日kcal仍来自TEE×模式比例和安全修正。

Q56=维持/保肌/营养恢复/增肌等 | 相应改变目标权重，可覆盖A/B减脂默认，但不能越过安全和疾病规则。


## Table


7700 kcal/kg的含义 约7700 kcal/kg来自经典静态减重经验规则（3500 kcal/lb的公制近似），用于近似描述“以脂肪组织储能为主的体重变化”。它不是“1 kg人体体重固定含7700 kcal”，也不是“1 kg纯脂肪=7700 kcal”的精确物理常数。


## Table


患者情形 | 候选方向/范围 | 关键限制 | 系统状态

一般术前癌症患者，无明确肾病 | >1.0至1.5 g/kg/d；项目可评估1.2 g/kg/d作为基础候选 | weight_basis与院内默认值需确认 | PENDING/CONFIG

C型/肌少风险/近期肌肉下降 | 靠近高端，候选1.2–1.5 g/kg/d；配合抗阻 | 肾功能、总能量和耐受必须同时满足 | PENDING/CONFIG

D/E型/营养不足 | 先保证总能量，再保证蛋白；必要时ONS | 摄入极低时先评估再喂养风险 | REVIEW

高龄无CKD | 至少避免低于1.0；疾病时常1.2–1.5 | 结合肾功能与耐受 | CONFIG

已知CKD G3–G5 | 覆盖常规高蛋白逻辑；由肾内/营养科个体化 | 不得因癌症自动升至1.5 | ACTIVE/REVIEW

肝弹性异常/纤维化风险 | 不因“肝功能异常”自动低蛋白 | 专科明确限制优先 | ACTIVE


## Table


实现提醒 肾功能实验室缺失但病史未提示CKD时，不能写“肾功能正常”。如拟使用较高蛋白目标，需按MDT配置决定是否要求近期肌酐/eGFR或医护确认。


## Table


项目 | 基础规则 | 个体化修正

碳水化合物 | 以全谷物、杂豆、薯类等低加工来源为主；一般平衡膳食可参考约50–65%供能。 | 糖尿病/低碳方案个体化；不默认生酮。

蛋白质 | 优先鱼、禽、蛋、奶、大豆/豆制品及适量瘦肉；每餐尽量有蛋白来源。 | 总量优先于百分比；CKD覆盖高蛋白策略。

脂肪 | 优先不饱和脂肪，减少饱和/反式脂肪和油炸。 | MASLD/血脂异常更强调脂肪质量。

膳食纤维/食物质量 | 蔬菜、完整水果、全谷、豆类；减少超加工、精制糖、含糖饮料。 | 进食困难/腹胀时调整质地和体积。


## Table


餐次 | 基础参考 | 有加餐时 | 系统规则

早餐 | 25–30% | 可适度下调 | 不因减重机械漏餐；结合原有习惯与执行能力。

午餐 | 30–40% | 通常保持较大餐次 | 结合工作/外食。

晚餐 | 30–35% | 可适度下调 | 不极端取消晚餐。

加餐 | 无统一必须比例 | 从正餐扣除，不额外叠加 | 5/10/15%等由MDT配置；D/E或进食困难可增加使用率。


## Table


闭合校验 breakfast_kcal + lunch_kcal + dinner_kcal + snack_kcal = daily_energy_target_kcal（允许配置的四舍五入容差）。任何加餐都必须从全天总能量重新分配。


## Table


情况 | 能量修正 | 宏量/食物质量 | 自动化边界

糖尿病/糖代谢异常 | 按总能量和阶段目标个体化 | 不套统一比例；优先全谷、豆类、非淀粉蔬菜、完整水果，减少含糖饮料/精制谷物 | 固定胰岛素/低血糖风险需结合药物计划；AI不改药

MASLD/稳定脂肪肝 | 超重可管理体重，但服从术前优先级 | 类似地中海/高质量膳食；减少超加工、糖饮料、饱和脂肪 | 肝弹性高风险时冻结激进减重

肝纤维化风险增加 | 降低减重优先，优先营养充分和保肌 | 不自动低蛋白；禁酒/不明保健品 | 黄色+MDT/肝病专科复核

CKD G3–G5 | 避免大幅高蛋白减重方案 | 蛋白目标由肾内/营养科确认 | 覆盖癌症常规高蛋白

高血压/血脂异常 | 不单独改变TEE公式，除非同时超重肥胖 | 减少高盐、高饱和脂肪、超加工 | 阈值/盐目标走专科规则

高尿酸/痛风 | 若超重可体重管理，但避免快速减重/脱水 | 水化和嘌呤按专科规则 | 急性期/肾功能异常转专科


## Table


数据域 | 最低要求（候选） | 用途

体重 | ≥4个有效晨起测量日/7天 | 计算7日均重与趋势

体成分 | 设备可得时≥3个同条件测量日 | 解释脂肪/肌肉/水分

饮食 | ≥5天有记录，且多数计划餐有完成度 | 判断执行与摄入不足

症状/功能 | ≥4天简短记录 | 判断代价/安全

腰围 | 适用时每周≥1次 | A/B/C脂肪趋势辅助


## Table


结论code | 判定概要 | 下一周营养动作

MAINTAIN | 安全绿+数据/执行充分+目标方向改善+肌肉/功能稳定 | 维持当前Energy_target与餐次结构。

BARRIER_FIRST | 执行不足/摄入障碍明显 | 不加码；先简化餐次、替换、能量密度、时间安排。

DATA_INSUFFICIENT | 数据不足 | 补记录；不判定方案无效。

PRESERVE_MUSCLE | 体重下降伴肌肉/功能下降或C型风险 | 冻结减能；蛋白/抗阻/营养优先。

NUTRITION_RECOVERY | D/E持续下降、摄入不足、食欲下降 | 停止减脂；能量密度/加餐/ONS评估。

INTENSIFY_CANDIDATE | A/B连续2个可评价周执行充分但脂肪相关指标无有利趋势，且门槛通过 | 标准→强化；生成待审核新草稿。

DEINTENSIFY | 强化后摄入/肌肉/功能/水分或症状不利 | 强化→标准/维持。

SAFETY_REVIEW | 黄色/红色或手术/疾病状态变化 | 冻结相关调整并转医护。


## Table


表型 | 本周结果 | 下一周候选

A/B | 标准有效且肌肉/功能稳定 | 维持85%/80%；不因“越快越好”继续减能。

A/B | 连续2个可评价周执行≥80%，脂肪/腰围/7日均重均无有利趋势，且全部强化门槛通过 | A→80%，B→75%；仍需医护审核。

A/B | 强化后肌肉下降、水分明显下降、疲劳/气促加重或摄入不足 | 退出强化/回标准或保肌。

C | 肌肉/功能稳定或改善 | 维持100%；若连续2周稳定但体脂/腰围仍需改善，可100→95→90。

D | 执行≥80%但仍下降/不能稳定 | 110→115，必要时120；执行<80%先解决障碍。

E | 执行≥80%但仍未止跌 | 115→120；120仍下降→营养科/MDT。

F | 执行困难 | 优先简化路径；不因未达目标自动扩大能量缺口。


## Table


周调整限制 每次建议最多改变1–3个关键变量。能量自动调整候选步长为5个百分点；任何升级只生成新的plan_version草稿，不能直接覆盖PUBLISHED方案。


## Table


字段/问题 | 频率 | 必填性 | 用途

体重kg | 每日晨起 | 核心必填 | 7日均重/能量反应

体脂率、脂肪量、肌肉/骨骼肌、水分 | 设备可得时 | 强烈建议自动采集/不强迫手填 | 解释体重变化、保肌和水分

蛋白质率/蛋白质量、BMR | 设备可得时 | 选填/自动 | 辅助，不代表膳食蛋白完成度

腰围 | A/B/C或Q56相关时每周1次 | 条件必填 | 中央脂肪趋势

每餐计划完成比例 | 每餐 | 必填 | 锚定计划能量，优于单靠照片猜kcal

主蛋白完成比例 | 有蛋白任务餐 | 条件必填 | 估算蛋白执行

是否替换/额外摄入 | 每餐 | 必填；有则展开 | 纠正计划与实际差异

餐食照片 | 每餐可选 | 选填 | 核对食物/份量；不是唯一热量真值

食欲0–10与进食症状 | 每日 | 必填 | 摄入不足原因与D/E风险


## Table


config_key（建议） | 候选值/说明 | 初始状态

ENERGY_SOURCE_PRIORITY | indirect calorimetry > approved REE formula+PAL > BIA_BMR_TEMP > kcal/kg range | PENDING→MDT

REE_FORMULA_ID | MSJ候选；或院内其他批准公式 | PENDING

PAL_MAP | 1.20/1.30/1.35/1.45/1.55候选映射 | PENDING

REE_BIA_DIFF_REVIEW | 15% review / 20% data_conflict候选 | PENDING

ENERGY_A_STANDARD_RATIO | 0.85 | PENDING

ENERGY_B_STANDARD_RATIO | 0.80 | PENDING

ENERGY_A_ENHANCED_RATIO | 0.80 | PENDING

ENERGY_B_ENHANCED_RATIO | 0.75 | PENDING

ENERGY_C_BASE/STEP1/FLOOR | 1.00 / 0.95 / 0.90 | PENDING

ENERGY_D_BASE/STEP/AUTO_CEILING | 1.10 / 1.15 / 1.20 | PENDING

ENERGY_E_BASE/STEP/AUTO_CEILING | 1.15 / 1.20 / 1.20 | PENDING

ENERGY_F_BASE_RATIO | 1.00 | PENDING

WEEKLY_ENERGY_STEP | 0.05（每次最多5个百分点候选） | PENDING

ADEQUATE_ADHERENCE_RATE | 0.80 | PENDING/产品候选

MIN_ENERGY_FLOOR | 本院最低能量保护边界/触发规则 | PENDING

PROTEIN_DEFAULTS_BY_PHENOTYPE | A–F蛋白g/kg及weight_basis | PENDING

MEAL_DISTRIBUTION | 早餐/午餐/晚餐/加餐比例及容差 | PENDING

ONS_REFERRAL_RULE | ONS触发、剂量、疾病适配、院内目录 | PENDING

REFEEDING_SAFETY_RULE | 再喂养风险识别和增量/监测流程 | PENDING


## Table


场景 | 预期结果

A型，Q56空，手术6周，安全绿 | 自动按85% TEE生成完整营养方案；不要求医护逐项填kcal。

B型，Q56强化，手术6周，肌肉稳定 | 通过门槛后75% TEE；仍待医护审核。

B型，Q56=4周减4kg但肌肉下降 | 不按4kg×7700倒算；冻结强化，转保肌/复核。

C型第一周 | 100% TEE，蛋白/肌肉保护优先。

C型连续2个可评价周稳定但体脂/腰围无改善 | 可提出95% TEE；再稳定可评估90%。

D型执行仅50% | 不从110%直接加到120%；先解决进食障碍/能量密度/ONS。

E型有再喂养高风险 | 不直接115%；转专科再喂养路径。

F型执行障碍明显 | 100%或更具体营养方向；优先简化，不加码。

肝弹性提示进展期纤维化可能 | 黄色；冻结强化减脂/自动进阶。

P2预测REE与BIA-BMR差异>20% | DATA_CONFLICT；不取平均，核对数据/设备。

一周记录不足 | DATA_INSUFFICIENT；不改变剂量。

体重下降明显但肌肉/水分同时下降、疲劳加重 | DEINTENSIFY/PRESERVE_MUSCLE，不判“效果优秀”。


## Table


类别 | 本稿候选 | 需要确认

REE/TEE | P1>P2>P3>P4；MSJ候选；PAL 1.20–1.55 | 公式ID、PAL映射、交叉校验阈值。

A/B标准 | A85%、B80% | 是否作为本项目默认ACTIVE值；短手术窗如何降阶。

强化 | A80%、B75% | 是否批准；是否允许连续2周无响应后自动提出。

C/D/E/F | C100→95→90；D110→115→120；E115→120；F100 | 自动上限/下限与本院患者适配。

能量保护 | 低于REE的处理、MIN_ENERGY_FLOOR | 什么条件阻断、什么条件仅review。

执行/周调整 | 执行≥80%；每次5个百分点 | 是否作为自动提出下一周草稿的前提。

蛋白 | >1.0–1.5 g/kg/d范围；分型候选值待定 | A–F具体g/kg、weight_basis、肾功能前置条件。

ONS/再喂养 | D/E升级路径 | 院内阈值、产品目录、监测流程。

Q56 | 选填；目标kg不直接倒算kcal | 是否接受取消固定2/4/8周默认减重矩阵。


## Table


版本结论 V2.0已经把“如何估算TEE、如何按A–F/Q56得到处方能量、什么时候允许强化、为什么不按目标kg×7700倒算、如何根据真实执行与周趋势调整下一周”闭合为一条确定性规则链。下一步应由责任MDT确认PENDING参数并在后端ACTIVE，再用于Codex和后续AI的同一套生成逻辑。

---

# SOURCE: 肺结节患者术前能量计算_数据记录与周动态调整规则_V2.0_完整版_MDT审阅稿(1).docx

肺结节患者术前能量计算、数据记录与周动态调整规则

V2.0｜完整版 · MDT审阅稿 · Codex/AI规则底稿

适用范围：肺结节/早期肺癌拟接受肺切除手术的术前多学科代谢健康管理

版本日期：2026-09-12｜V2.0整合版

0. 执行摘要

方案生成仍采用“自动生成 + 医护审核”模式。Q56为选填医护目标，不是每例必填的处方参数；Q56空缺时系统必须能够按照A–F默认算法完整生成方案。

能量算法分为两层：先得到维持能量需要 TEE_base，再根据A–F、Q56、手术窗口、营养/肌肉风险、肝弹性/肝纤维化风险、疾病状态和上一周真实反馈得到 Energy_target。

体重/减重速度是“疗效与轨迹目标”，不是直接反推能量的公式。禁止用“目标减重kg × 7700 kcal”直接倒算每日处方能量。

周调整必须区分“没有效果”与“没有执行”。每周先判断数据是否充分，再判断饮食/运动/肺预康复执行，再看体重、体脂、脂肪量、肌肉、水分、腰围、症状和功能，最后才决定维持、简化、强化或转营养恢复/保肌路径。

患者数据记录应补齐脂肪量、肌肉量/骨骼肌、水分率（可得时水分量）、蛋白质率/蛋白质量（设备可得时作为辅助）、每周腰围，以及真正用于计算的饮食完成度、运动实际完成量、肺预康复完成量、食欲和症状/功能数据。

0.1 V2.0新增/修订重点

在V1.0基础上，V2.0补齐四类可直接用于后续Codex前后端同步的规则：①P1–P4能量来源的具体执行公式、字段、交叉校验与异常处理；②“7700 kcal/kg”历史来源与禁止直接倒算的解释；③数据记录的必填/条件必填/选填三级规则及患者端提问文案；④周复评如何把真实记录转成下一周方案草稿的确定性决策流程。

V2.0仍属于MDT审阅稿。凡标注【项目候选参数】的公式、PAL、阈值、能量比例和自动调整步长，进入生产前均需由本院责任MDT确认并在mdt_config中ACTIVE。

0.2 本稿建议的默认能量参数（待MDT确认）

1. 规则治理与方案生成总流程

1.1 权威层级

推荐总流程： Q1–Q56评估 → A–F主表型 + 修饰标签 → 安全/疾病风险 → TEE_base → 默认/目标模式 → Energy_target → 食谱/运动/肺预康复自动组合 → Safety Validator → AI_GENERATED_PENDING_REVIEW → 医护审核/修改 → PUBLISHED → plan_task → patient_record → 7天周复评 → 下一周新草稿。

1.2 Q56在算法中的位置

Q56为空：系统不得停在“待医护设定目标”，而应调用A–F默认模式自动生成完整方案。

Q56填写“标准减脂/强化减脂/维持/营养恢复/增肌/代谢控制/功能/肺功能/综合准备”等：改变目标权重或调用预先批准的模式，但不直接让AI自由创造能量比例。

Q56填写目标体重或“X周下降/增加Y kg”：该值作为阶段轨迹与疗效评价目标；系统只用它判断目标强度和达成度，不用kg×7700 kcal直接倒算能量。

目标冲突：Safety、营养充分、肌肉保护、手术准备优先于Q56。例如C/D/E型或肝纤维化高风险患者即使填写强化减脂，也应冻结/降阶并提示医护复核。

2. 维持能量 TEE_base：来源优先级 + 交叉校验

2.1 能量来源优先级

循证依据： ESPEN癌症营养指南建议，若TEE未个体测量，可大致按25–30 kcal/kg/d估计；TEE可由标准REE公式和PAL估算，更准确时可用间接测热；后续必须根据体重和肌肉的临床效果调整。[2]

2.2 PAL（身体活动水平）候选映射

若患者存在明显气促、疼痛、平衡问题、近期疾病变化或活动实际明显低于问卷频率，PAL应向下修正。

若可接入可穿戴设备，步数/活动时间可作为PAL交叉信息，但不能单靠单日步数重算处方。

2.3 交叉校验规则

2.4 P2预测REE执行细则（V2.0新增）

P2不是“AI自己选公式”。后台必须保存REE_FORMULA_ID及版本。V2.0建议把Mifflin–St Jeor（MSJ）作为【项目候选默认公式】供MDT评估；若本院营养科选择Harris–Benedict、FAO/WHO/UNU或其他院内认可公式，只需切换配置，不改变数据合同。

MSJ候选公式：男性 REE = 10×体重(kg) + 6.25×身高(cm) − 5×年龄(岁) + 5；女性 REE = 10×体重 + 6.25×身高 − 5×年龄 − 161。该公式是一般成人预测公式示例，不视为肺结节/肿瘤患者的“金标准”；间接测热仍为更高优先级。

输入字段必须来自已审核评估：sex、age、height_cm、weight_kg。任何字段缺失时不得伪造；可临时降级到P3 BIA_BMR或P4粗估，并写入energy_source与missing_data。

2.5 TEE_base确定算法

若P1可用：primary_REE = measured_REE；若P1不可用而P2字段完整：primary_REE = predicted_REE；若P1/P2均不可用而P3有设备BMR：primary_REE = BIA_BMR_TEMP；若前三者均不可用：采用P4 25–30 kcal/kg/d作为保守粗估范围，不输出伪精确单点。

TEE_base = primary_REE × PAL。PAL必须来自ACTIVE映射规则；系统同时计算P3/P4校验值，但不把多个结果简单取平均。最终必须保存primary_source、formula_id、PAL_value、TEE_base、crosscheck_status。

2.6 P2/P3/P4交叉校验与异常处理

【项目候选】若predicted_REE与BIA_BMR差异>15%，标记REVIEW；>20%或差异会导致处方跨模式/触及最低能量边界时，标记DATA_CONFLICT并要求核对年龄、性别、身高、体重、测量时间、水分状态、设备和PAL。系统不得把两个值简单取平均。

P4 25–30 kcal/kg/d仅作粗略合理性校验：肥胖/高体脂患者按实际体重可能高估，严重营养不良/水肿等情况下也可能失真。P4与主算法不一致时只降低置信度并提示复核，不自动覆盖P1/P2。

3. A–F型处方能量 Energy_target 规则

3.1 A型：超重/高体脂，无明显营养/肌少主导

【循证锚点】成人超重食养指南可按实际能量需要量的85%作为减重摄入标准。[1]

【项目默认】Q56为空 → Energy_target = 0.85 × TEE_base。

若Q56=强化减脂且通过强化资格门槛 → 0.80 × TEE_base。

若出现肌肉/功能下降、连续摄入不足、食欲下降、肝纤维化风险增加、手术窗口缩短 → 退出强化或回到维持/保肌路径。

3.2 B型：肥胖/高体脂 + 代谢异常

【循证锚点】成人肥胖食养指南可按实际能量需要量的80%作为减重摄入标准。[1]

【项目默认】Q56为空 → Energy_target = 0.80 × TEE_base。

【项目强化】Q56=强化减脂或满足自动升级条件 → 0.75 × TEE_base。

代谢疾病目标（血压/血糖/血脂/尿酸等）影响食物选择、监测和运动安全，不允许AI自行调整药物。

3.3 C型：高体脂 + 肌肉减少/肌少风险

【既有项目规则】肌肉保护优先于减重；避免过快下降，抗阻和蛋白优先。

【项目默认】第一周 = 1.00 × TEE_base。目的：先验证摄入、肌肉和功能能否稳定。

【项目候选阶梯】若7–14天数据充分、饮食/蛋白执行≥80%、肌肉/功能稳定、无营养风险且仍需改善体脂/腰围，可提出95% TEE新草稿；再次稳定后最低可评估90% TEE。

任何持续肌肉下降、功能下降、明显疲劳/摄入不足 → 立即冻结进一步减能，回到100%或营养恢复路径。

3.4 D型：消瘦/营养风险

【既有项目规则】禁止进入减重型能量逻辑；目标为恢复摄入、体重/肌肉和功能。

【项目默认】无明显再喂养风险且可经口进食 → 1.10 × TEE_base。

若连续7–14天摄入执行≥80%但体重仍下降/不能稳定，且无水肿/再喂养风险 → 提出1.15 × TEE；必要时最高自动1.20 × TEE，超过后必须营养科/MDT复核。

若实际摄入<80%，不应只把“处方目标”从110%提高到120%；应先解决早饱、恶心、咀嚼/吞咽、餐次、能量密度、ONS评估等执行问题。

3.5 E型：近期非意愿下降 + 摄入不足/肌肉功能下降

【既有项目规则】第一目标是“止跌”，随后才是恢复体重/肌肉。

【项目默认】无再喂养风险 → 1.15 × TEE_base。

若7天后摄入≥80%但体重仍持续下降且肌肉/功能未改善 → 可提出1.20 × TEE新草稿；120%作为自动上限，继续下降则营养科/MDT接管。

若存在明显长期低摄入、重度营养不良、电解质风险等再喂养高风险特征，不自动执行115%/120%，进入再喂养风险路径，按专科方案逐步增加能量并监测磷/钾/镁等。[4]

3.6 F型：复杂共病/执行困难

F型的核心不是“某个固定能量百分比”，而是安全、可执行性和任务简化。

【项目默认】若缺乏更明确A–E营养方向 → 1.00 × TEE_base。

若同时存在明显肥胖/高体脂或营养不足证据，应调用更具体的A/B/C/D/E方向，但F型障碍决定任务复杂度、记录方式和进阶速度。

执行率低时优先简化方案，不因为“没有效果”自动加大缺口或增加训练量。

3.7 手术窗口与肝弹性修正

4. 强化减脂模式（Enhanced Fat Loss）候选规则

4.1 候选参数

4.2 进入强化模式的两条路径

路径A｜Q56基线明确：医护选择“强化减脂”，且所有安全/营养/肌肉门槛通过。

路径B｜自动提出升级：Q56为空或标准减脂，但连续2个“可评价周”执行充分且A/B脂肪相关指标无有利趋势；规则引擎可提出从标准→强化的新草稿，仍需医护审核后发布。

4.3 强化资格门槛（全部满足）

主表型为A或B；不是C/D/E主导。

预计手术时间≥4周。

当前临床安全为绿色；疾病/代谢状态无明显不稳定。

近期无非意愿体重下降、无明显摄入不足、无营养风险主导。

肌肉量/骨骼肌和功能无持续下降趋势。

食欲基本正常，过去一周饮食计划执行充分（项目候选：≥80%）。

肝弹性/肝病资料未提示需要冻结快速减重的高风险情形。

运动限制、疼痛、气促、头晕等不构成明显进阶障碍。

4.4 退出/降阶规则

连续3天摄入不足或食欲明显下降 → 冻结能量限制和运动进阶，回到标准/营养恢复草稿。

7天肌肉或功能趋势下降 → 冻结进一步减能；转保肌优先。

新发/加重症状、黄色/红色事件 → 暂停相关强化，按安全流程处理。

手术窗口缩短至<4周 → 强化模式自动失效，生成术前保守草稿。

明显肝纤维化风险升高或结果需肝病专科复核 → 退出强化。

体重下降很快但同时水分明显下降、肌肉下降、疲劳/气促加重 → 不判定为“效果好”，必须降阶。

5. 能量目标 vs 代谢健康管理速度目标

5.1 两个变量必须分开保存

5.2 为什么禁止“目标kg×7700”直接倒算

“7700 kcal/kg”来源于Wishnofsky经典静态减重经验规则（3500 kcal/lb，换算约7700 kcal/kg）。它建立在“减重主要来自脂肪组织/脂肪储备”的历史假设和当时的人体减重研究基础上，并不是“1 kg人体体重固定含7700 kcal”，也不是“1 kg纯脂肪=7700 kcal”的精确物理常数。

脂肪组织并非100%纯脂肪；更重要的是，真实短期体重下降同时包含脂肪、无脂组织、糖原及其结合水、体液和肠内容物变化。随着体重下降，能量消耗还会适应性改变，因此“每减少1 kg体重必定对应7700 kcal赤字”的静态假设并不成立。

因此本项目禁止“目标减重kg × 7700 ÷ 天数 = 每日必须制造的能量缺口”作为处方公式。该做法会把“阶段体重目标”错误等同于“脂肪组织能量”，并可能为了追体重数字造成过大能量限制，违背术前安全、营养充分、保肌、功能和手术准备优先级。

本系统仅允许把7700 kcal/kg用于历史概念解释或粗略教学，不进入Energy_target计算。0.5–1 kg/周、%体重/周或Q56目标只作为疗效轨迹/强度参考；它们不与15%/20%/25%能量缺口一一对应。

5.3 Q56为空与有值时的处理

6. 数据记录模块：为周复评补齐真正可计算的数据

6.1 每日体重/体成分

测量条件建议统一：晨起、排空后、进食饮水前、尽量同一设备和相近衣着；BIA单日波动不用于诊断或直接改处方。

蛋白质率/蛋白质量是设备估算，不代表“今天膳食蛋白吃够没吃够”；膳食蛋白完成度应从餐次执行另算。

6.2 每周围度/功能

6.3 饮食执行：不要只依赖照片猜热量

核心思路：患者已有“计划餐”，所以系统应以计划值为锚点，患者只需报告实际完成比例、替换和额外摄入；照片主要用于核对食物/份量，不把AI识别的单餐kcal当成绝对真值。

候选计算： planned_energy × meal_completion_fraction + 替换/额外摄入的近似修正 = estimated_actual_energy。该值必须标记estimated，不输出伪精确到个位数kcal。蛋白完成度优先结合“主蛋白完成比例 + 替换食物”估算。

6.4 运动执行

运动完成率应基于已发布plan_task的“计划剂量 vs 实际剂量”，不是让患者重新描述今天做了什么。

6.5 肺预康复执行

6.6 每日晚间简短功能/症状

6.7 数据充分性（产品候选阈值）

不足则结论=data_insufficient：补数据，不判定方案无效，不自动强化。

6.8 数据记录字段等级：必填、条件必填、选填（V2.0新增）

为了避免前端把患者变成“填表机器”，V2.0采用三级规则：R=必填（Required，缺失则该条记录不能完成）；CR=条件必填（Conditional Required，仅在相应设备/任务/回答触发时显示并要求填写）；O=选填/自动采集（Optional，不阻断提交和整体方案）；D=系统派生，不由患者填写。

记录提交与“可评价周”是两个层级：单条记录只检查R/CR字段；周复评则按体重天数、饮食记录天数、任务结果覆盖率、症状天数等判断数据充分度。O字段缺失不得阻断整体方案，但会降低趋势判断置信度。

建议周复评置信度：HIGH＝核心数据充分且有同条件体成分/腰围辅助；MODERATE＝核心数据充分但体成分或腰围缺失；LOW＝核心数据不足。LOW状态不允许自动升级能量限制或运动进阶，只能补数/维持/转人工。

7. 7天周复评：如何具体决定下一周方案

7.1 周复评固定顺序

Step 1｜安全：是否出现红/黄事件、新发/加重症状、疾病不稳定、肝病/营养高风险？有则先处理安全，不进入“效果不足→加码”。

Step 2｜数据充分：是否达到可评价周最低要求？不足则补数，不改剂量。

Step 3｜执行：饮食、蛋白、运动、肺预康复是否真正执行？执行不足先解决障碍。

Step 4｜生理反应：比较7天平均体重、体脂/脂肪量、肌肉、骨骼肌、水分、腰围、功能/症状；不能只看第1天和第7天两个点。

Step 5｜分型目标：A/B看脂肪/腰围改善同时保肌；C先看肌肉/功能；D/E先看止跌、摄入和肌肉；F先看安全和任务完成。

Step 6｜Q56：如有医护目标，与实际轨迹比较；如无Q56，不人为制造“必须每周减Xkg”的目标。

Step 7｜调整：只改变1–3个关键变量，形成下一周AI草稿，再医护审核发布。

7.2 周结论分类

7.3 A/B型下一周规则

7.4 C型下一周规则

7.5 D/E型下一周规则

7.6 F型下一周规则

优先评价核心任务完成率、症状和安全，而不是追求体重数字。

若完成率低：减少任务数、改时间、改记录方式、调用家庭支持/替代动作；不先改能量比例。

若F同时存在明确营养方向（肥胖/肌少/营养不足），在执行路径简化后叠加A–E中最安全的对应能量规则。

7.7 周调整步长与审计

能量比例每次自动建议最多改变5个百分点（如85%→80%、100%→95%、110%→115%），除非医护主动修改。【项目候选参数】

每次只改变1–3个关键变量，便于判断因果与耐受；这是既有项目规则。

任何周调整生成新的plan_version；不得直接覆盖PUBLISHED方案；旧任务与patient_record保留。

系统输出必须同时写明“为什么维持/为什么调整、使用了哪些数据、哪些数据缺失、哪些规则触发”。

7.8 下一周方案确定算法（V2.0完整闭环）

每周日/设定复评日，系统必须先生成weekly_signal，再生成next_week_draft。不得把“某一天体重掉得少/多”直接转成能量变化。固定执行顺序如下：

A/B自动强化候选：至少连续2个“可评价周”，饮食/任务执行充分（项目候选≥80%），安全绿色，肌肉/功能稳定，手术窗口≥4周，且7日均重、体脂/脂肪量、腰围均未出现一致有利趋势；才可从A85→80、B80→75提出新草稿。单周无变化不升级。

A/B降阶候选：出现肌肉/功能下降、连续摄入不足、食欲下降、明显疲劳/气促加重、异常水分下降、手术窗口缩短或肝纤维化风险升级时，强化立即失效；能量比例按5个百分点回退或直接转100%/营养恢复路径，具体由触发规则和MDT审核决定。

C型：100% TEE为首周默认。连续2个可评价周肌肉/功能稳定且仍需改善脂肪/腰围，可100→95；再次连续稳定后可95→90。任何肌肉/功能不利趋势立即停止减能。

D/E型：若处方能量较高但实际完成<80%，优先处理早饱、恶心、餐次、口味、咀嚼/吞咽、能量密度和ONS评估，不盲目再加处方目标；若实际完成≥80%而仍持续下降/未止跌，且无再喂养/水肿风险，可每次提高5个百分点，自动上限按本稿D120%/E120%候选。

周复评不得只根据体重速度决定。即使体重下降“达标”，若肌肉下降、功能变差、饮食完成度下降或水分异常，也必须判为需要降阶/保肌；反之体重下降较慢但腰围/脂肪下降、肌肉稳定、功能改善，可判为有效并维持。

8. 周复评输出合同（供后端/医护端）

9. 前端“数据记录”建议新增/修改

9.1 体脂秤记录卡

当前已有：体重、体脂率。

建议补充显示/保存：脂肪量、肌肉量/骨骼肌、水分率（可得时水分量）；蛋白质率/蛋白质量和BMR作为“更多指标/辅助”，不要求患者手填。

如果体脂秤截图包含这些数据，患者只需上传；系统识别后允许人工校正，并保存source/raw_payload。

9.2 饮食记录卡

从“上传照片”升级为“计划餐执行记录”：照片 + 完成比例 + 主蛋白完成比例 + 替换 + 额外摄入。

结果展示以“约完成X% / 估算区间”为主，避免给患者伪精确到个位数kcal。

9.3 运动/肺预康复记录卡

必须与plan_task绑定；计划值只读，患者填“实际完成值”。

运动：实际分钟、组数/次数、RPE/BORG、症状、未完成原因。

肺预康复：实际分钟/组数、是否完成、症状、P05按需痰液/排痰情况。

9.4 每日晚间恢复状态

疲劳0–10、气促0–10、疼痛0–10、活动能力更好/相同/更差。

新发胸痛/胸闷、明显气促、头晕/晕厥、咯血、意识异常等直接走安全规则，不等待周复评。

9.5 每周固定记录

腰围每周1次；C/D/E或医护指定时可加小腿围。

周日自动生成周报告，不要求患者再次填写已经自动汇总的数据，只补充“本周最大困难”和“下周最希望改善什么”两个简短问题即可。

9.6 患者端最小提问集（供后续Codex前端直接实现）

前端原则：患者不填写“估算热量”“蛋白质克数”“完成率百分比”等系统可派生数据；前端只收集患者能可靠回答的事实（吃了多少、是否替换、是否完成、实际时长、症状）。系统根据已发布plan_task和知识库自动派生estimated_actual_energy、estimated_protein、task_completion_rate等。

餐食照片为证据和核对手段，不作为唯一热量计算来源。识别出的菜品/份量应展示给患者确认或允许纠正，并保存source、raw_payload/原图引用和confidence；无法确认时保持“估算/不确定”，不得伪精确到个位数kcal。

10. 后端建议新增/更新的配置项（暂不等于Codex指令）

10.1 建议新增patient_record字段组

字段应同时保存required_level（R/CR/O/D）、source、recorded_at、plan_task_id（如适用）、measurement_context和confidence。后端验证器只对当前条件下的R/CR报错；O缺失不得阻断记录保存，也不得被AI补值。

建议新增派生字段：valid_measurement、estimated_actual_energy_kcal_range、estimated_protein_completion、diet_completion_rate、exercise_completion_rate、pulmonary_completion_rate、weekly_data_confidence、weekly_response_class、next_week_action_code。所有派生结果保留算法版本。

11. 从既有聊天/规则中必须一并保留的约束

明确“无”≠缺失/null/unknown；选填数据缺失不阻断整体方案，但依赖该数据的风险/分级不得伪精确。

肝弹性：不单独改变A–F；优先报告结论，不以单次LSM自诊F0–F4；纤维化高风险降低快速减重优先级。

安全等级与疾病等级分开；红色>黄色>绿色；红色不能由AI凭“感觉好转”自动解除。

药物/固定治疗只提醒和记录，AI不得加减停换药或改剂量/时间。

手术越近，越强调营养、保肌、功能、肺预康复，不为了体重目标自动增加节食或运动。

每日随访不直接重写已发布方案；周复评命中规则只生成新的待审核草稿。

菜品、运动、P01–P06只从ACTIVE知识库调用；未审核剂量不得形成患者数值任务。

食谱最终必须闭合总能量和蛋白，并支持替换；运动必须有目的、姿势、步骤、剂量、强度、休息、注意事项、停止条件和替代动作。

数据记录保留单位、来源（patient_entered/clinician_entered/device/report/derived）和时间戳，便于审计。

12. 建议用于Codex/AI回归测试的关键场景

13. 参考依据与项目来源

[1] 国家卫生健康委办公厅. 成人肥胖食养指南（2024年版）及编制说明。核心参考：超重/肥胖可分别按实际能量需要量85%/80%作为一种能量负平衡方法；其他更大限能量方案并非本术前项目的默认值。

[2] Muscaritoli M, et al. ESPEN practical guideline: Clinical Nutrition in cancer. Clinical Nutrition. 2021;40:2898–2913. 核心参考：未个体测量时TEE约25–30 kcal/kg/d；可由REE公式+PAL估算；更准确可用间接测热；后续根据体重和肌肉效果调整。

[3] Weimann A, et al. ESPEN guideline on clinical nutrition in surgery – Update 2025. Clinical Nutrition. 2025;53:222–261. 核心参考：营养风险、术前营养治疗、肌少/衰弱评估和风险分层预康复。

[4] da Silva JSV, et al. ASPEN Consensus Recommendations for Refeeding Syndrome. Nutr Clin Pract. 2020;35(2):178–195. 核心参考：再喂养风险识别、分层与逐步营养支持。

[项目源A]《肺结节患者术前多学科代谢健康管理｜AI方案生成提示词｜完整版最新版》：A–F、疾病风险、执行能力、手术窗口、目标优先级、趋势分析、安全和发布流程。

[项目源B]《肝弹性成像与肝脏代谢风险处理规则》：Q50肝弹性作为修饰标签、纤维化风险对能量/运动/安全的影响。

[项目源C]《AI方案生成治理补齐说明》：Safety → MDT配置 → ACTIVE知识库 → 模板 → Prompt；PENDING不得形成精确患者任务；周调整只生成新草稿。

[项目源D]《患者数据字典V1.0/数据库结构V1.0》：已存在fat_mass、muscle_mass、water、protein等体成分字段与来源追溯设计。

13.1 V2.0新增参考：7700 kcal/kg规则的来源与局限

[5] Heymsfield SB, Gonzalez MCC, Shen W, Redman L, Thomas D. Time to correctly predict the amount of weight loss with dieting / related critical reviews of Wishnofsky’s rule. 该系列工作回顾3500 kcal/lb（约7700 kcal/kg）经验规则的历史假设，并指出真实体重变化包含糖原、蛋白、水和脂肪，静态规则不能准确描述减重动力学。

[6] Hall KD. What is the required energy deficit per unit weight loss? Int J Obes (Lond). 2008;32(3):573–576；Hall KD, et al. Quantification of the effect of energy imbalance on bodyweight. Lancet. 2011;378:826–837。说明固定3500 kcal/lb（约7700 kcal/kg）规则受初始体脂、体组成变化和代谢适应影响，不宜用于直接反推个体处方。

13.2 V2.0版本变更摘要

明确P1–P4不改变原优先级框架，但补齐P2预测REE公式接口、PAL、降级路径、交叉校验和数据来源字段。

明确“TEE_base”和“处方能量Energy_target”是两层变量：TEE_base估计维持需要；Energy_target由A–F/Q56/安全/手术窗口修正。

纠正“低于REE即禁止”的过度简化：是否允许低于REE由ACTIVE最低能量下限和安全规则决定，而非机械以REE作硬地板。

解释7700 kcal/kg的Wishnofsky历史来源，明确其不是1 kg体重或1 kg纯脂肪的固定热量，并禁止用目标kg×7700倒算本项目处方。

新增数据记录R/CR/O/D分级、患者端最小提问集、照片识别的估算属性和周复评置信度。

补齐下一周方案的确定性周决策流程，明确A/B强化、C减能、D/E增能、F简化路径及降阶规则。

14. MDT待确认清单

— 结束 —


## Table


文件定位 本文件不是患者处方，也不是让医护为每位患者手工填写能量/蛋白/运动数值。其作用是把一次性由MDT审核启用的“全局算法参数、数据采集规则、周复评规则”结构化。系统/Codex/后续AI根据患者Q1–Q56评估、A–F分型、手术窗口、疾病与安全修饰因素自动生成完整方案草稿；医护负责审核、必要时修改并发布。


## Table


参数状态说明 文中标注【循证锚点】的内容可追溯至指南/共识；标注【既有项目规则】来自当前AI方案生成提示词、肝弹性规则和后端治理规则；标注【项目候选参数】是为产品确定性计算提出的数值，必须由本院MDT审核后才能在后端由PENDING变为ACTIVE。


## Table


分型/模式 | Q56未填默认 | 进入下一阶的方向 | 自动化上限/限制

A 超重/高体脂 | 85% TEE | 必要时80% TEE | 强化不低于80% TEE；短手术窗关闭强化

B 肥胖+代谢异常 | 80% TEE | 必要时75% TEE | 强化不低于75% TEE；短手术窗关闭强化

C 高体脂+肌少风险 | 100% TEE | 稳定后95%，再评估90% | 90%为候选下限；肌肉/功能下降立即冻结减能

D 消瘦/营养风险 | 110% TEE | 必要时115%，最高自动120% | 再喂养/严重摄入障碍不自动套比例

E 非意愿下降/摄入不足 | 115% TEE | 必要时120% | 120%后仍未止跌→营养科/MDT；再喂养风险走专门路径

F 复杂/执行困难 | 100% TEE | 优先简化执行路径 | F不自行定义减脂强度；按更具体营养方向叠加规则


## Table


优先级 | 来源 | 系统职责

1 | 安全规则 | 红/黄/绿分流、禁忌、停止条件、转人工；任何目标和处方不得突破。

2 | ACTIVE MDT参数 | 能量比例、蛋白、餐次、运动剂量、肺预康复剂量、数据充分阈值与周调整步长。

3 | ACTIVE结构化知识库 | 菜品组件、运动动作、P01–P06、替代项、视频与适用/禁忌。

4 | Q56医护目标（如填写） | 决定“阶段想达到什么”和管理强度；不能突破1–3层。

5 | A–F默认目标/模板 | Q56为空时提供确定性默认路径；Q56有值时作为表型保护与冲突校验。

6 | AI提示词 | 读取上下文、编排、解释理由；不得发明阈值和剂量。


## Table


核心原则 “来源优先级”用于确定主估算值；“交叉校验”只用于发现不合理或数据冲突，不应机械用第二种算法覆盖第一种算法。


## Table


优先级 | 来源/算法 | 系统用法 | 状态建议

P1 | 间接测热得到REE（若有可靠结果） | 作为主基础；结合活动水平得到TEE。 | 【循证锚点】

P2 | 医院批准的REE预测公式 + PAL（V2.0建议配置公式ID；不由AI临时选择） | 无实测REE时的主算法。系统读取年龄、性别、身高、体重等评估字段计算predicted_REE，再乘ACTIVE PAL得到TEE_base；若医院最终采用其他公式，仅切换配置ID，不改生成流程。 | 【项目候选配置】

P3 | BIA/体脂秤BMR | 作为辅助估计和趋势字段，不自动当作“金标准TEE”。 | 【既有项目规则】

P4 | 25–30 kcal/kg/d粗略参考 | 用于合理性校验/数据不足时的保守估算；肥胖可能高估、严重营养不良可能低估。 | 【循证锚点】


## Table


注意 下表不是指南固定分级，而是为了把Q35运动频率、活动受限和功能资料转成可执行算法提出的【项目候选参数】。建议后续由康复/营养MDT审核后ACTIVE。


## Table


候选PAL | 患者特征（示例） | 数据来源

1.20 | 卧床/活动明显受限/日常活动很少 | Q35 + 功能限制 + 医护判断

1.30 | 久坐；当前运动<1次/周 | Q35

1.35 | 1–2次/周，日常生活可独立完成 | Q35 + 6MWT/耐量

1.45 | ≥3次/周、轻至中等活动且功能良好 | Q35 + 6MWT/耐量

1.55 | 规律较高活动量且无明显限制（术前患者较少见） | 医护/设备数据确认


## Table


字段/派生值 | 来源 | 系统规则 | 必需性

measured_REE_kcal | 间接测热报告 | 存在可靠结果时优先 | 条件必需

predicted_REE_kcal | REE_FORMULA_ID + 年龄/性别/身高/体重 | P1缺失时主算法 | 条件必需

bia_bmr_kcal | 体脂秤/身体成分仪 | 交叉校验；P1/P2不可用时可临时降级使用 | 条件可用

pal_value | Q35–Q37、功能/6MWT、活动受限等映射 | 必须来自ACTIVE配置 | 必需

tee_base_kcal | primary_REE × PAL | 后续A–F/Q56处方计算的基准 | 派生必需

tee_ref_25_30 | 体重×25 至 30 | 粗略参考区间；不覆盖主算法 | 派生辅助

crosscheck_status | P2/P3/P4一致性 | OK / REVIEW / DATA_CONFLICT | 派生必需


## Table


校验项 | 候选规则 | 系统动作

REE/BMR一致性 | 主算法所得REE与BIA-BMR差异明显（候选>15%） | 标记data_conflict，不自动平均；优先使用更高等级来源。

25–30 kcal/kg/d校验 | 与主TEE差异较大 | 提示“粗估与主算法不一致”，不直接覆盖。

体重/肌肉趋势校验 | 按处方执行1–2周后体重/肌肉变化与预计方向明显不符 | 先查执行、测量、水分、症状、药物/疾病变化，再考虑调整。

最低能量保护/低摄入标记 | 计算出的Energy_target低于REE/BMR或低于医院ACTIVE最低能量下限 | “低于REE”本身不是绝对禁忌，不机械阻断；系统应标记enhanced_restriction，并检查ACTIVE最低能量下限、营养/肌肉/手术窗口和安全规则。若低于医院批准下限则阻断并转MDT。

数据缺失 | 无可靠REE/BMR或体重资料不足 | 使用可获得的保守估算并标注来源/不确定性，不伪造精确值。


## Table


修饰因素 | 默认动作

预计手术>4周 | 可按A–F默认规则；A/B符合条件可进入强化模式。

预计手术2–4周 | 关闭自动“跨级”强化；以当前标准模式、保肌和功能为主；异常时优先降阶。

预计手术≤2周 | 【项目候选】关闭强化减脂；A/B若Q56无明确特殊目标，默认回到95–100% TEE（建议默认100%），重点转为营养、保肌、功能和肺预康复。

稳定脂肪肝/低风险肝弹性 | 不单独改变A–F能量方向；优化总能量、精制糖、脂肪质量、体重/腰围。

肝纤维化风险增加 | 降低快速减重优先级；不进入强化模式；保证营养与肌肉。

报告提示显著/进展期纤维化或肝硬化可能 | 黄色+肝病/MDT复核；冻结激进减重和自动运动进阶。


## Table


核心原则 强化模式是“预设的确定性规则”，不是Codex/AI自由挑一个更大缺口。所有百分比必须先在mdt_config中ACTIVE；AI只能调用。


## Table


表型 | 标准模式 | 强化模式 | 自动最低比例

A | 85% TEE | 80% TEE | 80%

B | 80% TEE | 75% TEE | 75%

C | 100%→95%→90%阶梯 | 不进入A/B强化模式 | 90%

D/E/F | 不适用减脂强化 | — | —


## Table


变量 | 含义 | 谁决定 | 是否直接用于算每日kcal

prescribed_energy_target_kcal | 本周实际处方能量 | 确定性规则（ACTIVE参数） | 是

management_goal / Q56 | 本阶段想达到什么：标准/强化/保肌/营养恢复等 | 医护可选填；空则系统默认 | 决定模式，不直接倒算

target_weight_change_kg / target_weight_kg | 医护希望周期末达到的体重目标 | Q56选填 | 否

weekly_weight_trajectory | 由Q56目标换算出的比较轨迹 | 系统派生 | 只用于疗效比较

observed_weekly_change | 真实7天趋势 | patient_record | 用于周复评和下一周调整


## Table


容易误写的说法 | V2.0规定的正确表述

“1 kg体重 = 7700 kcal” | 错误。7700是经典静态经验规则的公制近似，不是体重的固定能量密度。

“1 kg纯脂肪 = 7700 kcal” | 不准确。纯脂肪能量密度更高；Wishnofsky规则面向的是以脂肪组织为主的体重变化近似。

“想减4 kg，就按4×7700倒算每日缺口” | 禁止用于本项目处方。目标kg只用于轨迹比较，处方能量来自TEE_base×ACTIVE模式比例。


## Table


场景 | 系统动作

Q56为空 | 不设置固定“2/4/8周必须减多少kg”的默认矩阵；直接按A–F默认能量模式生成第一周完整方案，并用趋势方向评价。

Q56=标准减脂 | A调用85%，B调用80%；C/D/E/F按自身保护规则。

Q56=强化减脂 | 通过资格门槛后，A调用80%，B调用75%；否则提示目标冲突并降阶。

Q56填目标体重/变化量 | 生成目标轨迹用于比较，但每日kcal仍来自模式和安全规则。

Q56=维持/保肌/营养恢复等 | 相应覆盖A/B减脂默认，但仍受安全、疾病和手术窗口修正。


## Table


现状与差距 当前项目的数据字典已经设计了fat_mass_kg、muscle_mass_kg、skeletal_muscle_mass_kg、water_pct/water_mass_kg、protein_pct/protein_mass_kg等字段，但当前前端“数据记录”页面没有完整呈现这些字段，也缺少饮食/运动/症状的结构化执行问题。本稿建议补齐前端采集和patient_record映射。


## Table


字段 | 频率 | 获取方式 | 周复评地位

体重 kg | 每日晨起 | 体脂秤/手动/截图识别 | 核心

体脂率 % | 每日（同条件） | 体脂秤 | 核心趋势

脂肪量 kg | 设备可得时每日 | 体脂秤 | 核心辅助；比单纯体脂率更直观

肌肉量 kg | 设备可得时每日 | 体脂秤 | 核心保护指标

骨骼肌量 kg/% | 设备可得时每日 | 体脂秤 | 核心/辅助，依设备字段

水分率/水分量 | 设备可得时每日 | 体脂秤 | 重要解释变量；用于识别短期水分变化

蛋白质率/蛋白质量 | 设备可得时自动保存 | 体脂秤 | 辅助，不单独触发处方调整

BMR | 设备可得时自动保存 | 体脂秤 | 能量估算辅助，不作为趋势疗效核心


## Table


项目 | 建议频率 | 备注

腰围 | 每周1次 | 核心；同一时间/方法测量。

小腿围 | C/D/E或医护指定每周1次 | 肌肉/营养辅助；非所有患者强制。

6MWT | 基线 + 阶段性复评/医护指定 | 不建议每天或机械每周；由条件和资源决定。

快速功能自评 | 每日1次 | “今天活动能力比平时：更好/差不多/更差”，用于周趋势。


## Table


时间点 | 患者端建议问题 | 系统用途

每餐后 | ①这餐完成多少：100% / 约75% / 约50% / 约25% / 几乎没吃；②主蛋白食物完成多少（同档）；③是否替换计划食物；④是否额外吃/喝；⑤上传照片（可选/按偏好） | 估算meal_completion、protein_food_completion、substitution、extra_intake；锚定计划能量和蛋白。

每日晚间 | 今天总体食欲0–10分；是否有早饱/恶心/呕吐/腹胀/腹泻/便秘/吞咽或咀嚼困难；今天总体能完成计划饮食多少 | 判断摄入不足原因和营养风险。

异常时 | “今天为什么没吃够？”可多选：没时间/不饿/早饱/恶心/不喜欢/外出/其他 | 直接回写执行障碍画像，而不是简单判定方案失败。


## Table


每次任务结束问题 | 字段

是否完成？全部 / 部分 / 未完成 | task_completion_status

实际完成多少分钟？ | actual_duration_min

抗阻：实际组数/次数（若有） | actual_sets / actual_reps

主观强度RPE/BORG 0–10 | rpe_borg

过程中是否有气促、胸痛/胸闷、头晕、心悸、明显疲劳、关节/腰背痛？ | exercise_symptoms

未完成原因 | barrier_reason


## Table


问题 | 字段

完成/部分/未完成 | pr_completion_status

实际分钟/组数/次数 | actual_duration / sets / reps

是否出现气促、头晕、胸痛或不适 | pr_symptoms

P05有效咳嗽：是否有痰/排痰困难（按需） | sputum_need

未完成原因 | barrier_reason


## Table


问题 | 建议选项

今天疲劳程度？ | 0–10

今天气促程度？ | 0–10

今天疼痛程度？ | 0–10

今天整体活动能力比平时？ | 更好 / 差不多 / 更差

今天是否出现头晕、明显乏力、胸痛/胸闷、心悸、咯血或其他新症状？ | 无 / 有（有则展开安全流程）

今天是否有治疗/用药变化或明显不良反应？ | 无 / 有；只记录并转医护，不由AI改药


## Table


说明 以下是为了让系统知道“这一周是否够资格自动评价/调整”的产品阈值，不是临床指南阈值。建议作为mdt_config/产品配置审核。


## Table


数据域 | 可评价周候选最低要求

体重 | ≥4个有效晨起测量日/7天

体成分 | ≥3个同条件有效测量日/7天（设备可得时）

饮食 | ≥5天有记录，且多数计划餐有完成度信息

运动/肺预康复 | 计划任务中≥80%有“完成/部分/未完成”结果记录

症状/功能 | ≥4天晚间简短记录

腰围 | 每周至少1次（如适用）


## Table


数据模块 | 字段/问题 | 等级 | 前端规则/用途

体重/体成分 | 测量日期时间、体重kg | R | 体重记录提交必须有；时间自动记录。

体重/体成分 | 是否晨起排空后、未进食饮水/是否同一设备 | CR | 手动录入或周趋势数据质量校验时显示；用于valid_measurement。

体重/体成分 | 体脂率% | CR | 设备/截图可提供时采集；家庭设备不支持时不阻断。

体重/体成分 | 脂肪量、肌肉量、骨骼肌量、水分率/量 | O（强烈建议自动采集） | 用于解释体重变化、保肌和水分波动；不要求患者逐项手填。

体重/体成分 | 蛋白质率/蛋白质量、BMR、内脏脂肪等 | O | 仅辅助趋势/能量校验，不代表膳食蛋白完成度。

饮食-每餐 | 计划餐完成比例 | R | 100/75/50/25%/几乎未吃。

饮食-每餐 | 是否替换计划食物、是否有额外摄入 | R | 只问是/否；若“是”再展开。

饮食-每餐 | 替换内容、额外摄入内容 | CR | 仅当上题为“是”；允许文字/拍照/快捷选择。

饮食-每餐 | 主蛋白食物完成比例 | CR | 该餐存在明确蛋白质任务时要求；用于protein_food_completion。

饮食-每餐 | 餐食照片 | O | 用于核对食物/份量；不作为唯一热量真值。

饮食-每日 | 食欲0–10、是否有影响进食症状 | R | 每日一次；若有症状再展开类型。

运动 | 完成/部分/未完成、症状有/无 | R | 每个plan_task必须记录结果。

运动 | 实际分钟、RPE/BORG | CR | 完成/部分时要求；未执行时不填。

运动 | 实际组数/次数 | CR | 抗阻/次数型任务才显示。

运动 | 未完成/部分完成原因 | CR | 状态不是“全部完成”时要求。

肺预康复 | 完成/部分/未完成、症状有/无 | R | 每个肺预康复任务必须有结果。

肺预康复 | 实际分钟/组数/次数 | CR | 对应任务有剂量时显示。

肺预康复 | 痰液/排痰困难 | CR | P05或有痰相关任务时显示。

每日恢复 | 疲劳0–10、气促0–10、疼痛0–10、活动能力更好/相同/更差 | R | 每日一次，用于周复评和安全趋势。

每日安全 | 是否出现胸痛/明显加重气促/晕厥或近晕厥/咯血/意识异常等 | R | 默认“无”；选择任一异常立即进入安全流程。

每周围度 | 腰围 | CR | A/B/C或Q56含腰围/减脂目标时每周1次；D/E/F无相关目标时可选。

每周围度 | 小腿围 | CR/O | C/D/E或医护指定时条件必填；其他患者选填。

功能 | 6MWT/握力/坐站等 | O/医护指定CR | 基线或阶段复评，不要求每日/每周机械填写。

固定治疗 | 完成/未完成 | CR | 只有存在医护确认的治疗任务时要求；未完成原因条件必填。


## Table


结论code | 判定概要 | 下一步

MAINTAIN | 安全绿 + 数据充分 + 执行充分 + 目标方向改善 + 肌肉/功能稳定 | 维持当前能量和主要训练变量。

BARRIER_FIRST | 执行不足/主要障碍明显 | 不加码；优先简化餐次、替换食物、调整时间、减少任务复杂度。

DATA_INSUFFICIENT | 数据不足 | 补记录；不判定无效。

PRESERVE_MUSCLE | 体重下降伴肌肉/功能下降，或C型出现肌肉风险 | 冻结减能/有氧进阶；提高保肌和抗阻/蛋白优先级。

NUTRITION_RECOVERY | D/E持续下降、连续摄入不足、食欲下降 | 停止减脂逻辑；能量密度/餐次/ONS评估；必要时营养科。

INTENSIFY_CANDIDATE | A/B连续2个可评价周执行充分但脂肪相关指标无有利趋势，且所有强化门槛通过 | 标准→强化的确定性下一阶；生成待审核新草稿。

DEINTENSIFY | 强化后出现摄入、肌肉、功能、水分或症状不利趋势 | 强化→标准/维持；必要时黄色复核。

SAFETY_REVIEW | 黄色/红色或疾病/手术状态变化 | 冻结相关模块并转医护。


## Table


本周结果 | 下一周候选动作

标准模式有效：脂肪/腰围/7日均重至少有有利趋势，肌肉/功能稳定，执行充分 | 维持85%(A)/80%(B)，不要因“越快越好”自动继续降能。

连续2个可评价周执行≥80%，但体重/体脂/脂肪量/腰围均无有利趋势；安全绿、肌肉稳定、手术≥4周 | 提出强化：A 80%，B 75%。

Q56从第一周即为强化且资格通过 | 直接按A80%/B75%生成第一周；周末若稳定则维持，不自动再低于80/75%。

体重下降较快，但肌肉稳定、功能稳定、水分无明显异常、食欲/摄入正常 | 记录为快速响应，不因单纯“掉得快”自动惩罚；继续严密观察。

体重下降 + 肌肉下降/水分明显下降/疲劳气促加重/摄入不足 | 判定过度/可能分解代谢，退出强化或回维持/保肌。


## Table


本周结果 | 下一周候选动作

肌肉/功能稳定或改善，摄入/蛋白充分 | 维持100% TEE；若体脂/腰围已改善，无需减能。

连续2个可评价周肌肉稳定、功能稳定、无营养风险，但体脂/腰围不改善且仍需减脂 | 100%→95% TEE。

95%后继续稳定且仍无脂肪改善 | 可评估90% TEE；不得自动低于90%。

任何肌肉/功能持续下降 | 回100%（必要时更高）并转保肌；冻结进一步减能。


## Table


情景 | D型 | E型

执行充分且目标方向改善 | 维持110% | 维持115%

执行≥80%，仍下降/未止跌，无再喂养/水肿风险 | 110%→115%；必要时120% | 115%→120%

执行<80% | 先解决进食障碍、餐次、能量密度、ONS评估，不盲目提高处方目标 | 同左；尤其关注食欲/恶心/早饱/吞咽等

水分/水肿明显增加但体重上升 | 不把体重上涨自动判定为营养成功；需临床评估 | 同左

达到120%仍持续下降 | 营养科/MDT复核；不继续自动加码 | 营养科/MDT复核；不继续自动加码


## Table


顺序 | 判定 | 满足时动作

0 手术窗口 | 预计手术日期是否变化；是否进入≤4周或≤2周 | 手术临近优先关闭强化、保肌、功能、肺预康复。

1 安全门 | 红/黄事件、新发/加重症状、疾病不稳定、肝纤维化/营养高风险 | 先处理安全；红色暂停相关任务，黄色冻结相关进阶。

2 数据质量 | 核心数据是否达到可评价周；是否存在BIA水分异常/测量条件差 | LOW置信度：补数或维持，不自动升级。

3 执行率 | 饮食、蛋白食物、运动、肺预康复是否实际执行 | 执行不足先BARRIER_FIRST；不把“未执行”误判为“方案无效”。

4 生理反应 | 7日均重、体脂/脂肪量、肌肉/骨骼肌、水分、腰围、症状/功能 | 判定改善/稳定/不利趋势；水分异常时降低体重解释权重。

5 分型目标 | A/B减脂保肌；C保肌优先；D/E止跌恢复；F安全和可执行性 | 按表型决定“什么才算有效”。

6 Q56轨迹 | 有Q56则比较当前轨迹与医护目标；无Q56则只看默认方向 | Q56不能越过安全和ACTIVE参数边界。

7 选择调整类型 | MAINTAIN / BARRIER_FIRST / PRESERVE_MUSCLE / NUTRITION_RECOVERY / INTENSIFY_CANDIDATE / DEINTENSIFY / SAFETY_REVIEW | 只改变1–3个关键变量，生成新plan_version草稿。


## Table


模块 | 必须输出

数据完整度 | weight_days、bodycomp_days、diet_record_days、task_record_rate、symptom_days、waist_available

体重/体成分 | 7日平均体重 vs 上周/基线；体脂/脂肪量趋势；肌肉/骨骼肌趋势；水分趋势；BIA解释提示

营养执行 | 计划能量 vs 估算实际完成；主蛋白完成；食欲；影响进食症状；额外摄入/替换

运动/肺预康复 | 计划任务数、完成率、实际时长/组数、RPE/BORG、异常症状、未完成原因

功能/症状 | 疲劳、气促、疼痛趋势；活动能力更好/相同/更差；新发异常

疾病/治疗 | 仅对已有疾病：血压/血糖等趋势、治疗完成和药物/治疗变化；AI不改药

目标评价 | Q56目标（如有）的轨迹；无Q56则只评价A–F方向性目标

周结论 | MAINTAIN / BARRIER_FIRST / DATA_INSUFFICIENT / PRESERVE_MUSCLE / NUTRITION_RECOVERY / INTENSIFY_CANDIDATE / DEINTENSIFY / SAFETY_REVIEW

下一周草稿 | 新的Energy_target、食谱调整、运动/肺预康复变化、1–3个关键变化、依据和mdt_pending_items


## Table


场景 | 患者看到的问题 | 必填逻辑

每餐后 | 这餐大约吃了计划的多少？ 100% / 75% / 50% / 25% / 几乎没吃 | R

每餐后 | 这餐有没有换掉计划中的食物？ 无 / 有 | R；有→展开替换内容

每餐后 | 除计划外有没有额外吃/喝？ 无 / 有 | R；有→展开快捷选择/文字/照片

含蛋白任务的餐 | 主蛋白食物（肉/鱼/蛋/奶/豆制品等）大约吃了多少？ 100/75/50/25%/几乎没吃 | CR

每日晚间 | 今天总体食欲怎么样？ 0–10分 | R

每日晚间 | 今天有没有早饱、恶心、呕吐、腹胀、腹泻、便秘、吞咽/咀嚼困难等影响进食？ 无 / 有 | R；有→多选

运动任务后 | 今天这项运动完成了吗？ 全部 / 部分 / 未完成 | R

运动任务后 | 实际完成多少分钟？主观强度0–10？ | CR：全部/部分时显示

运动任务后 | 运动中有没有胸痛、明显气促、头晕、心悸、明显疼痛等？ 无 / 有 | R；有→立即安全分流

肺预康复后 | 完成了吗？ 全部 / 部分 / 未完成；实际分钟/次数？ | R+CR

每日恢复 | 疲劳0–10；气促0–10；疼痛0–10；今天活动能力比平时更好/差不多/更差 | R

每日安全快筛 | 今天是否出现胸痛/胸闷明显加重、明显加重气促、晕厥/近晕厥、咯血、意识异常？ 无 / 有 | R；有→不等待周复评

周日 | 本周影响你执行方案最大的困难是什么？ | O；用于解释低执行率

周日 | 下周最希望改善什么？ | O；用于个性化交互，不直接改变医学参数


## Table


config_key（建议） | 候选值/说明 | 状态

ENERGY_A_STANDARD_RATIO | 0.85 | PENDING→MDT确认

ENERGY_B_STANDARD_RATIO | 0.80 | PENDING→MDT确认

ENERGY_A_ENHANCED_RATIO | 0.80 | PENDING→MDT确认

ENERGY_B_ENHANCED_RATIO | 0.75 | PENDING→MDT确认

ENERGY_C_BASE/STEP1/FLOOR | 1.00 / 0.95 / 0.90 | PENDING

ENERGY_D_BASE/STEP/AUTO_CEILING | 1.10 / 1.15 / 1.20 | PENDING

ENERGY_E_BASE/STEP/AUTO_CEILING | 1.15 / 1.20 / 1.20 | PENDING

ENERGY_F_BASE_RATIO | 1.00 | PENDING

WEEKLY_ENERGY_STEP | 0.05（每次建议最多5个百分点） | PENDING

ADEQUATE_ADHERENCE_RATE | 0.80 | 产品候选

DATA_MIN_WEIGHT_DAYS | 4/7 | 产品候选

DATA_MIN_BODYCOMP_DAYS | 3/7 | 产品候选

DATA_MIN_DIET_DAYS | 5/7 | 产品候选

DATA_MIN_SYMPTOM_DAYS | 4/7 | 产品候选

PAL_MAP | 1.20/1.30/1.35/1.45/1.55候选映射 | PENDING

ENERGY_SOURCE_PRIORITY | indirect_calorimetry > approved_REE_formula+PAL > BIA_BMR(aux) > kcal/kg cross-check | PENDING/结构规则


## Table


域 | 建议字段

body_composition | weight_kg, body_fat_pct, fat_mass_kg, muscle_mass_kg, skeletal_muscle_mass_kg, skeletal_muscle_pct, water_pct, water_mass_kg, protein_pct, protein_mass_kg, bmr, source, measured_at

diet_record | plan_task_id, meal_type, completion_fraction, protein_food_completion_fraction, substitution_json, extra_intake_json, photo_ref, estimated_actual_kcal, estimated_actual_protein_g, appetite_score, nutrition_impact_symptoms

exercise_record | plan_task_id, status, actual_duration_min, actual_sets, actual_reps, rpe_borg, symptom_json, barrier_reason

pulmonary_record | plan_task_id, status, actual_duration_min, actual_sets_reps, symptom_json, sputum_need, barrier_reason

daily_status | fatigue_0_10, dyspnea_0_10, pain_0_10, activity_change, new_symptoms_json, treatment_change_flag

weekly_measurement | waist_cm, calf_cm_optional, recorded_at


## Table


场景 | 预期结果

A型，Q56空，手术6周，安全绿 | 85% TEE自动完整生成；不要求医护逐项填数。

B型，Q56=强化，手术6周，肌肉稳定 | 通过门槛后75% TEE；仍需医护审核。

B型，Q56=4周减4kg但肌肉下降 | 不得按4kg倒算；冻结强化，转保肌/复核。

C型，第一周 | 100% TEE；抗阻/蛋白优先。

C型连续2周稳定但体脂/腰围不改善 | 可提出95% TEE；后续最低90%。

D型，摄入执行仅50% | 不从110%直接加到120%；先解决进食障碍/能量密度/ONS。

E型有再喂养高风险 | 不得直接115%；转专科再喂养路径。

F型执行障碍明显 | 100%或更具体营养方向；先简化任务，不加码。

肝弹性提示进展期纤维化可能 | 黄色；冻结强化减脂/自动进阶。

一周数据不足 | DATA_INSUFFICIENT，不改变剂量。

体重下降1.5kg但肌肉/水分同时下降、疲劳加重 | DEINTENSIFY/PRESERVE_MUSCLE，不判“效果优秀”。

体重变化小但腰围/体脂改善、肌肉稳定 | MAINTAIN，不因体重没变自动强化。


## Table


类别 | 本稿候选 | 需要确认的问题

A/B标准能量 | A85%、B80% | 是否作为本项目默认ACTIVE值；短手术窗如何降阶。

强化模式 | A80%、B75% | 是否批准；是否只允许Q56触发或也允许连续2周无响应后自动提出。

C/D/E/F比例 | C100→95→90；D110→115→120；E115→120；F100 | 是否符合本院术前人群；自动上限是否调整。

PAL映射 | 1.20/1.30/1.35/1.45/1.55 | 与Q35和6MWT/功能如何映射。

数据充分阈值 | 体重4天、体成分3天、饮食5天、症状4天、任务记录80% | 作为产品可评价周标准是否合适。

执行充分阈值 | ≥80% | 是否作为周调整前提。

每周能量调整步长 | 5个百分点 | 是否允许；哪些场景必须人工而不能自动提出。

再喂养/ONS | D/E特殊升级路径 | 由营养科补齐本院具体阈值和流程。

Q56 | 选填，目标kg不直接倒算kcal | 是否接受：Q56为空时取消固定减重kg矩阵，改用A–F默认能量模式+趋势评价。

---

# SOURCE: 肺结节患者术前A-F分型参数配置候选值_V2.0_完整版_MDT评估稿(1).docx

肺结节患者术前 A–F 分型参数配置候选值 V2.0

完整版｜MDT评估稿

用于 Codex 规则引擎与后续 AI 方案生成的同一套可审核参数配置

版本：V2.0｜建议由营养科、内分泌科、康复医学科、胸外科及相关专科联合审阅

一、文件目的与权威边界

参数层负责确定性计算：能量来源、PAL、A–F能量比例、蛋白候选值、餐次比例、运动/肺预康复剂量、周调整步长与准入条件。

知识库层负责可调用内容：菜品/食谱组件、动作ID、P01–P06、替代项与视频。

方案模板负责输出结构；AI/提示词负责在许可范围内组合与解释，不能自行发明能量缺口、蛋白g/kg、运动剂量或安全阈值。

患者个体方案仍需：AI_GENERATED_PENDING_REVIEW → 医护审核/编辑 → APPROVED_PENDING_PUBLISH → PUBLISHED。

二、A–F基础表型与V2.0默认管理方向

三、生成前必须读取的输入与Q56位置

四、统一能量估算引擎：来源优先级 + 交叉校验

ENERGY-BASE-01｜TEE基础计算

若使用REE路径：TEE_base = primary_REE × ACTIVE PAL。P1可用则primary_REE=measured_REE；否则P2字段完整则用predicted_REE；P1/P2不可用但P3有BMR时，允许降级为BIA_BMR_TEMP；前三者均不可用时，P4只输出保守范围，不伪造单点。

ENERGY-XCHECK-01｜交叉校验

P2预测REE与BIA-BMR差异>15%候选标记REVIEW；>20%或差异足以改变处方模式/触及最低能量边界时标记DATA_CONFLICT。系统核对年龄、性别、身高、体重、设备、水分与测量时间，不对不同来源简单取平均。

五、PAL活动水平候选映射

六、A–F核心参数V2.0：Q56为空时的默认自动模式

七、A–F各型参数逻辑、覆盖条件与退出条件

八、A/B强化减脂模式：预设参数，不由Codex/AI自由选缺口

8.1 强化准入条件（建议全部满足）

主表型为A或B，且Q56明确选择“强化减脂”或由连续周复评提出强化候选。

预计手术时间≥4周；安全等级绿色；无近期非意愿体重下降。

无D/E营养风险主导、无C型肌少/肌肉保护主导。

饮食摄入和蛋白执行基本稳定，肌肉/功能趋势稳定，无明显疲劳、气促等不利变化。

无肝纤维化风险增加/显著纤维化、再喂养风险、重大疾病不稳定等限制。

ACTIVE最低能量边界允许；强化仍只生成待医护审核草稿。

8.2 强化退出/降阶条件

肌肉/骨骼肌或功能出现不利趋势。

摄入不足、食欲明显下降、连续餐次完成度下降。

水分明显下降并伴快速体重下降，不能确认主要为脂肪变化。

疲劳、气促、头晕、疼痛等影响执行或安全。

手术窗口缩短至<4周，或出现黄色/红色事件。

肝弹性/肝病风险升级或其他专科规则要求。

九、Q56管理目标与参数调用规则

十、为什么删除固定2/4/8周默认减重百分比矩阵

V1.0曾给A/B配置较保守的周体重趋势候选，并与手术窗口绑定；V2.0进一步把“处方能量”和“体重目标”彻底分离。

Q56未填时，系统按A–F默认能量模式管理，不承诺2/4/8周必须达到某个统一减重百分比。

Q56可选填目标体重/变化量，系统将其转换为比较轨迹，用于随访评价，但每日kcal仍由TEE×ACTIVE模式比例及安全修正决定。

十一、手术时间窗口与肝弹性修饰

11.1 Q50肝弹性叠加

稳定脂肪肝/低风险：不单独改变A–F能量方向；优化总能量、精制糖、脂肪质量、体重/腰围。

肝纤维化风险增加：降低快速减重优先级；不进入强化；优先营养充分和肌肉保护。

显著/进展期纤维化或肝硬化可能：黄色+MDT/肝病专科复核；冻结激进减重和运动自动进阶。

仅有LSM数值无方法/报告结论：标记数据不足，不自行诊断F0–F4或肝硬化。

十二、宏量营养素与餐次候选参数

MACRO-01｜脂肪候选

若无疾病专属限制，可将脂肪约30%总能量作为项目基础候选；重点同时看脂肪质量，不用单一供能比例解决代谢病。

MACRO-02｜碳水计算

总能量和蛋白确定后，可用剩余能量反算碳水；糖代谢异常患者不强制统一50–60%，具体分配服从疾病规则和药物安全。

MEAL-01｜餐次闭合

早餐+午餐+晚餐+加餐=每日处方总能量；加餐必须从全天总能量中重新分配，不得作为额外叠加。

十三、A–F第一周运动参数候选（与运动库V1.x联动）

十四、肺预康复基础池：表型影响耐受，不机械按A–F拆成完全不同路径

十五、周复评所需数据与“下一周方案”参数调整

15.1 能量周调整候选步长

十六、与前端数据记录联动的最低字段（参数引擎需要）

十七、建议映射到后端的config_key（V2.0）

十八、回归测试场景（用于Codex/AI一致性验证）

十九、MDT需要最终确认的参数清单

二十、证据边界与来源关系

二十一、主要参考依据与内部依赖文档

1. 国家卫生健康委办公厅：《成人肥胖食养指南（2024年版）》；《体重管理指导原则（2024年版）》；《肥胖症诊疗指南（2024年版）》。

2. Muscaritoli M, et al. ESPEN practical guideline: Clinical Nutrition in cancer. Clinical Nutrition. 2021;40:2898–2913.

3. Weimann A, et al. ESPEN guideline on clinical nutrition in surgery – Update 2025. Clinical Nutrition. 2025;53:222–261.

4. Ligibel JA, et al. Exercise, Diet, and Weight Management During Cancer Treatment: ASCO Guideline. J Clin Oncol. 2022;40:2491–2507.

5. 肺癌围手术期肺康复训练中国专家共识（2024）及项目采用的术前运动/肺预康复知识库。

6. 项目内部：《AI方案生成提示词（最新版）》《术前营养与能量计算规则V2.0》《术前菜品与食谱组件库V1.0》《术前运动处方生成规则与动作库V1.0》《术前肺预康复知识库V1.0》《AI方案生成安全规则与禁忌替代引擎V1.0》《肝弹性成像与肝脏代谢风险处理规则》。


## Table


文件定位：本文件不是临床指南，也不是可直接跳过审核的患者处方。它把 A–F 分型需要的“数值参数、调用条件、覆盖条件、周调整逻辑”整理成可由 MDT 审核并写入后台 mdt_config 的候选值。只有状态由 PENDING 审核为 ACTIVE 的参数，才允许进入患者个体化方案。

V2.0 关键升级：取消 A/B/C 的固定 2/4/8 周默认体重减重百分比矩阵；改为“能量处方参数”和“代谢健康管理目标”分离。Q56 为选填的医护指导目标：不填时系统仍按 A–F 默认模式自动生成完整方案；填写时用于决定目标方向/标准或强化模式，但目标 kg 不直接倒算每日 kcal。


## Table


冲突优先级：安全规则 > ACTIVE MDT配置 > 已审核知识库 > 方案模板 > AI提示词。Q56属于患者个体管理目标输入，不能突破安全规则和ACTIVE处方边界。


## Table


表型 | 名称 | 核心识别特征 | V2.0默认管理方向

A | 超重/高体脂型 | 超重或高体脂；无明显营养风险/肌少主导 | 标准减脂 + 保肌 + 术前功能

B | 肥胖+代谢异常型 | 肥胖/高体脂并伴糖代谢、血脂、血压、尿酸、MASLD等 | 减脂 + 保肌 + 代谢疾病管理

C | 高体脂+肌少/肌肉风险型 | 高体脂并伴肌肉量/SMI/功能下降或风险 | 保肌/增肌优先 + 功能 + 温和体脂改善

D | 消瘦/营养风险型 | 低体重、低摄入或营养风险，无E型近期快速下降主导 | 营养恢复 + 适度增重 + 保/增肌

E | 近期非意愿下降/肌肉功能风险型 | 近期非意愿体重下降、摄入不足、肌肉/功能下降 | 先止跌 + 营养恢复 + 保/增肌 + 功能恢复

F | 复杂共病/执行困难型 | 多病共存、运动受限或执行障碍明显 | 安全 + 可执行性；营养方向按叠加表型/问题修正


## Table


重要：F型不是固定的“肥胖/消瘦营养表型”。若F同时存在D/E型营养问题，营养方向应继承D/E保护逻辑；若仅为执行困难且同时A/B特征明确，可在安全门槛内继承A/B较保守模式。


## Table


输入域 | 字段 | 系统要求

基础/体成分 | 年龄、性别、身高、体重、BMI、腰围；体脂率、脂肪量、肌肉/骨骼肌、SMI、水分、BMR（若有） | 核心/可缺失并降级

营养风险 | 近6个月体重变化、是否非意愿下降、食欲、进食量、早饱/恶心/吞咽等 | 建议核心

活动/功能 | Q35–Q37、6MWT或替代耐量、疼痛/平衡/关节限制 | PAL/运动需要

代谢疾病 | 高血压、糖代谢、血脂、尿酸、MASLD等及相关指标/治疗 | 条件读取

手术窗口 | ≤2周、2–4周、4–8周、>8周、未确定 | 一级变量

Q50肝弹性 | 方法、LSM、报告结论、CAP等 | 选填；修饰标签

Q56管理目标 | 首要目标、目标周期、体重目标、其他重点 | 选填；不填不阻断


## Table


Q56规则：Q56为空时，不要求医护逐例补热量或蛋白数值，系统按A–F默认模式自动生成完整方案；Q56填写时，可改变“标准/强化/维持/保肌/营养恢复”等目标模式，但仍由确定性算法计算每日处方。


## Table


优先级 | 来源/算法 | 系统用法 | 状态

P1 | 间接测热REE（若有可靠结果） | 作为最高优先级主基础；结合ACTIVE PAL得到TEE | 循证锚点

P2 | 医院批准的REE预测公式 + PAL | 无实测REE时主算法；公式ID固定配置，不由AI挑选 | 项目配置

P3 | BIA/体脂秤/身体成分仪BMR | 辅助估计与交叉校验；P1/P2不可用时可降级使用 | 项目规则

P4 | 25–30 kcal/kg/d粗略参考 | 合理性校验/数据不足时保守参考；不覆盖P1/P2 | 循证锚点


## Table


PAL候选 | 患者特征（示例） | 主要数据来源

1.20 | 卧床/活动明显受限/日常活动很少 | Q35 + 功能限制 + 医护判断

1.30 | 久坐；当前运动<1次/周 | Q35

1.35 | 1–2次/周，日常生活可独立 | Q35 + 6MWT/耐量

1.45 | ≥3次/周、轻至中等活动且功能良好 | Q35 + 6MWT/耐量

1.55 | 规律较高活动量且无明显限制（术前少见） | 医护/设备数据确认


## Table


状态：PAL数值是项目候选参数，不是肺结节指南直接给出的统一分层。建议营养/康复MDT审核后ACTIVE；患者资料不足时使用保守档并降低置信度。


## Table


表型 | 默认模式 | 第一周能量 | 方向 | 蛋白默认* | 餐次 | 说明

A | 标准减脂 | 85% TEE | 15%缺口 | 1.2 g/kg/d候选 | 3+1 | 不设固定周减重%作为处方驱动

B | 标准减脂 | 80% TEE | 20%缺口 | 1.2 g/kg/d候选 | 3+1 | 同步疾病饮食/监测规则

C | 保肌优先 | 100% TEE | 第一周0%缺口 | 1.5 g/kg/d候选 | 3+1 | 稳定后可100→95→90%阶梯

D | 营养恢复 | 110% TEE | 10%盈余 | 1.3 g/kg/d候选 | 3+2 | 执行充分仍下降时可115→120%

E | 止跌/恢复 | 115% TEE | 15%盈余 | 1.5 g/kg/d候选 | 3+2 | 第一目标=停止下降；高再喂养风险退出自动算法

F | 安全/可执行 | 100% TEE默认 | 0%默认 | 1.2 g/kg/d候选 | 简化3餐 | 由叠加营养问题覆盖；不设统一体重速度


## Table


蛋白参数说明：A/B/C/D/E/F 的1.2/1.2/1.5/1.3/1.5/1.2 g/kg/d沿用V1.0作为“MDT候选默认值”，但V2.0明确要求与weight_basis、总能量、肾功能/专科限制一起审核；目前均保持PENDING，不应被理解为指南统一固定处方。


## Table


表型 | V2.0参数逻辑 | 覆盖/退出条件

A | 超重/高体脂且无营养/肌少主导。标准85% TEE。 | Q56维持/保肌可覆盖减脂；肌肉/功能下降→C保护；≤2周手术关闭强化。

B | 肥胖+代谢异常。标准80% TEE，并叠加疾病饮食与监测。 | 药物不自动调整；肝纤维化风险/肌肉下降/营养不足→降阶。

C | 第一周100% TEE，抗阻和蛋白优先。连续稳定后才允许95%→90%。 | 出现肌肉/功能下降、摄入不足、症状加重→回100%/保肌复核。

D | 110% TEE恢复能量与体重，强调高营养密度和3+2。 | 若高再喂养风险、严重摄入不足或专科限制→退出自动增量。

E | 115% TEE候选，首要是止跌。执行充分仍下降才可120%。 | 再喂养风险、明显胃肠症状、持续下降→营养科/MDT。

F | 默认100% TEE；优先简化任务与提高执行率。 | 按D/E/A/B等叠加营养问题覆盖，不能因F而忽略营养风险。


## Table


表型 | 标准模式 | 强化模式 | 自动最低比例候选

A | 85% TEE | 80% TEE | 80% TEE

B | 80% TEE | 75% TEE | 75% TEE

C | 100→95→90% | 不进入A/B强化 | 90% TEE

D/E/F | 非减脂强化路径 | 不适用 | —


## Table


Q56状态/目标 | 参数动作 | 边界

Q56为空 | 按A–F默认模式自动生成完整方案 | 不要求医护逐例填写kcal/蛋白/运动剂量

标准减脂 | A85%；B80% | C/D/E/F继续走保护规则

强化减脂 | 门槛通过后A80%；B75% | 不通过则提示冲突并降阶，不自由发明百分比

体重维持/保肌 | 可覆盖A/B默认减脂 | 通常100% TEE附近，具体由ACTIVE规则

营养恢复/增重/停止下降 | 调用D/E保护逻辑 | 禁止继续A/B负能量模式

增肌 | 提高保肌/抗阻/蛋白优先级 | 不以体重下降作为主效果

代谢控制 | 能量依A–F，叠加疾病规则 | 药物/疾病阈值不由AI改变

提高运动能力/改善肺功能/综合准备 | 能量按A–F安全方向，运动/肺预康复优先级上调 | 不因功能目标扩大热量缺口


## Table


7700 kcal/kg：约7700 kcal/kg是经典静态减重经验中对“以脂肪组织储能为主的体重变化”的近似，不是1 kg人体体重固定含7700 kcal，也不是1 kg纯脂肪的精确物理常数。因此禁止用“目标kg × 7700 ÷ 天数”直接倒算患者每日能量缺口。


## Table


手术窗口 | 能量修正 | 运动原则 | 肺预康复

>8周 | A/B可标准；符合条件可强化；C/D/E按表型 | 可完整渐进 | 基础P01–P04，条件性P05/P06

4–8周 | 按表型默认；A/B强化需Q56/周复评+门槛 | 主要改善窗口 | 完整基础训练

2–4周 | 不自动跨级强化；A/B以标准或更保守为主 | 一次只改一个变量 | 动作正确/规律性优先

≤2周 | 关闭强化；A/B候选回95–100% TEE，默认100%待MDT确认 | 不新启陌生高负荷 | 技能熟练，不突击加量

未确定 | 保守模式；A/B/C/F原则不强化 | 基础/不进阶 | P01/P02 + 低量P03/P04


## Table


表型 | 蛋白候选* | 餐次候选 | 说明

A | 1.2 g/kg/d | 25/35/30/10（3+1） | 减脂不取消蛋白

B | 1.2 g/kg/d | 25/35/30/10（3+1） | 叠加糖脂压尿酸/MASLD规则

C | 1.5 g/kg/d | 25/35/30/10（3+1） | 肌肉保护优先；总能量不能被高蛋白挤压

D | 1.3 g/kg/d | 20/30/25/12.5/12.5（3+2） | 提高能量密度、减少单餐体积

E | 1.5 g/kg/d | 20/30/25/12.5/12.5（3+2） | 再喂养高风险时退出自动高能量/高蛋白

F | 1.2 g/kg/d默认 | 30/40/30；必要时3+1 | 按叠加营养问题覆盖


## Table


weight_basis：蛋白g/kg和kcal/kg的参考体重不能由AI临时决定。实际体重/理想体重/调整体重/干体重应作为独立ACTIVE配置；水肿/腹水、明显肥胖、CKD/肝病等情况需专科覆盖。


## Table


表型 | 有氧第一周 | 抗阻第一周 | 强度候选 | 关键规则

A | A02快走20min×4次/周 | 4动作；2组×12次；2次/周 | RPE4–5/10 | 无疼痛/平衡限制时采用；强化不等于无限加有氧

B | A02快走20min×5次/周 | 4动作；2组×12次；2次/周 | RPE3–5/10 | 疾病监测规则覆盖；异常不自动加量

C | 15min×3次/周（A02/A04） | 5动作；2组×10–12次；3次/周 | RPE4–5/10 | 抗阻优先，不以大量有氧换体重下降

D | A01缓慢步行10min×5次/周，可分段 | 4动作；1–2组×10次；2次/周 | RPE2–4/10 | 恢复活动/肌力，不以消耗热量为目标

E | A01 5–10min×5次/周，优先分段 | 3动作；1组×8–10次；2次/周 | RPE2–3/10 | 摄入不足/疲劳时先减运动

F | A01/A03 5–10min小段×5天/周 | 1–2动作；1组×8–10次；2天/周 | RPE2–3/10 | 减少复杂度；第一周核心任务完成率候选≥70%


## Table


状态：以上FITT和RPE均为项目候选值，需康复医学科/胸外科审核。正式动作必须从已审核运动知识库中按ID调用；剂量为空或未ACTIVE时不得形成带精确数值的患者任务。


## Table


项目 | 稳定患者候选 | 低耐受D/E/F候选 | 条件/停止

P01 缩唇呼吸 | 3min/次×2次/日 | 2–3min×2次/日 | 气促可额外用于呼吸控制；过度换气/头晕停

P02 腹式呼吸 | 5min/次×2次/日 | 5min×1–2次/日 | 不强迫深吸

P03 胸廓扩张 | 10次×1组/日 | 5次×1组/日 | 肩痛/胸痛/明显气促时减量/停

P04 呼吸-上肢协同 | 10次×1组，3天/周 | 5次×1组，2–3天/周 | 疼痛/头晕时改坐姿或取消

P05 有效咳嗽 | 无痰仅技能学习；有痰按需 | 同左，按耐受缩短 | 咯血/鲜血痰等禁止

P06 OPEP | 不作为基础任务 | 不作为基础任务 | 痰多/排痰困难+设备+医护指导同时满足才调用


## Table


数据域 | 最低要求（候选） | 用途

体重 | ≥4个有效晨起测量日/7天 | 7日均重与趋势

体成分 | 设备可得时≥3个同条件测量日 | 脂肪/肌肉/水分解释；不强迫手填

腰围 | A/B/C或Q56相关时每周≥1次 | 中央脂肪趋势

饮食执行 | ≥5天记录；多数计划餐有完成度 | 区分“没效果”与“没执行”

运动/肺预康复 | 按任务记录实际分钟/组数/完成情况 | 执行与耐受

症状/功能 | ≥4天简短记录 | 疲劳、气促、疼痛、活动能力等


## Table


结论code | 判定概要 | 下一周动作

MAINTAIN | 安全绿+数据/执行充分+目标方向改善+肌肉/功能稳定 | 维持当前能量与任务，不因“越快越好”继续加码

BARRIER_FIRST | 执行不足/摄入障碍明显 | 先简化/解决障碍，不强化

DATA_INSUFFICIENT | 数据不足 | 补记录，不判方案无效

PRESERVE_MUSCLE | 体重下降伴肌肉/功能下降或C型风险 | 冻结减能，蛋白/抗阻/营养优先

NUTRITION_RECOVERY | D/E持续下降、摄入不足、食欲下降 | 提高能量密度/加餐/ONS评估

INTENSIFY_CANDIDATE | A/B连续2个可评价周执行充分但脂肪相关指标无有利趋势且门槛通过 | 标准→强化，生成待审核新草稿

DEINTENSIFY | 强化后摄入/肌肉/功能/水分或症状不利 | 强化→标准/维持

SAFETY_REVIEW | 黄色/红色或手术/疾病状态变化 | 冻结相关调整并转医护


## Table


表型 | 周复评结果 | 下一周候选能量

A/B | 标准有效且肌肉/功能稳定 | 维持85%/80%

A/B | 连续2个可评价周执行≥80%，脂肪/腰围/7日均重均无有利趋势，且全部强化门槛通过 | A→80%；B→75%

A/B | 强化后肌肉/水分/功能/症状不利 | 退出强化，回标准或保肌

C | 连续2周肌肉/功能稳定但体脂/腰围仍需改善 | 100→95%；再稳定可评估90%

D | 执行≥80%但仍下降/不能稳定 | 110→115%；必要时120%

E | 执行≥80%但仍未止跌 | 115→120%；仍下降→MDT

F | 执行困难 | 优先简化；不因未达目标自动加缺口


## Table


周调整限制：每次建议最多改变1–3个关键变量；能量自动调整候选步长为5个百分点。任何升级只生成新的plan_version草稿，不能直接覆盖PUBLISHED方案。


## Table


字段/问题 | 频率 | 必填性 | 用途

体重kg | 每日晨起 | 核心必填 | 7日均重/能量反应

体脂率、脂肪量、肌肉/骨骼肌、水分 | 设备可得时 | 自动采集优先/不强迫手填 | 解释体重变化和保肌

蛋白质率/蛋白质量、BMR | 设备可得时 | 选填/自动 | 辅助，不代表膳食蛋白完成度

腰围 | A/B/C或Q56相关时每周1次 | 条件必填 | 中央脂肪趋势

每餐计划完成比例 | 每餐 | 必填 | 比照片猜kcal更可靠地估计执行

主蛋白完成比例 | 有蛋白任务餐 | 条件必填 | 估计蛋白执行

替换/额外摄入 | 每餐 | 必填；有则展开 | 纠正计划与实际

餐食照片 | 每餐可选 | 选填 | 核对食物/份量，不作为唯一热量真值

食欲/进食症状 | 每日 | 必填 | D/E风险和摄入不足原因

运动实际完成量+RPE/症状 | 每次任务 | 条件必填 | 周进退阶


## Table


config_key（建议） | V2.0候选值/说明

ENERGY_SOURCE_PRIORITY | indirect calorimetry > approved REE formula+PAL > BIA_BMR_TEMP > kcal/kg range

REE_FORMULA_ID | MSJ候选或院内其他批准公式

PAL_MAP | 1.20/1.30/1.35/1.45/1.55候选映射

REE_BIA_DIFF_REVIEW | 15% review / 20% data_conflict候选

ENERGY_A_STANDARD_RATIO | 0.85

ENERGY_B_STANDARD_RATIO | 0.80

ENERGY_A_ENHANCED_RATIO | 0.80

ENERGY_B_ENHANCED_RATIO | 0.75

ENERGY_C_BASE/STEP1/FLOOR | 1.00 / 0.95 / 0.90

ENERGY_D_BASE/STEP/AUTO_CEILING | 1.10 / 1.15 / 1.20

ENERGY_E_BASE/STEP/AUTO_CEILING | 1.15 / 1.20 / 1.20

ENERGY_F_BASE_RATIO | 1.00

WEEKLY_ENERGY_STEP | 0.05

ADEQUATE_ADHERENCE_RATE | 0.80

PROTEIN_DEFAULTS_BY_PHENOTYPE | A/B/C/D/E/F = 1.2/1.2/1.5/1.3/1.5/1.2 g/kg候选 + weight_basis

MEAL_DISTRIBUTION_ABC/DE/F | ABC 25/35/30/10；DE 20/30/25/12.5/12.5；F 30/40/30候选

MIN_ENERGY_FLOOR | 本院最低能量保护边界/触发规则

ONS_REFERRAL_RULE | ONS触发、剂量、疾病适配、院内目录

REFEEDING_SAFETY_RULE | 再喂养风险识别、增量和监测流程


## Table


状态要求：上述精确数值默认PENDING。MDT确认后写入value_json并ACTIVE；AI/Codex只读取ACTIVE值。若某关键参数仍PENDING，系统不得把它作为正式患者数值任务。


## Table


场景 | V2.0预期结果

A型，Q56空，手术6周，安全绿 | 85% TEE自动生成完整方案；不要求医护逐项填kcal。

B型，Q56强化，手术6周，肌肉稳定 | 门槛通过后75% TEE；仍待医护审核。

B型，Q56=4周减4kg但肌肉下降 | 不按4kg×7700倒算；冻结强化，转保肌/复核。

C型第一周 | 100% TEE；蛋白/抗阻优先。

C型连续2个可评价周稳定，体脂/腰围仍需改善 | 提出95% TEE；再稳定才可评估90%。

D型执行仅50% | 不直接110→120%；先解决进食障碍/能量密度/ONS。

E型高再喂养风险 | 不直接115%；转专科再喂养路径。

F型执行障碍明显 | 100%或叠加营养方向；优先简化，不加码。

肝弹性提示进展期纤维化可能 | 黄色；冻结强化减脂/自动进阶。

预测REE与BIA-BMR差异>20% | DATA_CONFLICT；不取平均，核对数据/设备。

一周记录不足 | DATA_INSUFFICIENT；不改变剂量。

体重下降明显但肌肉/水分同时下降、疲劳加重 | DEINTENSIFY/PRESERVE_MUSCLE，不判“效果优秀”。


## Table


类别 | 需确认内容

REE/TEE | P1>P2>P3>P4；REE公式ID；PAL 1.20–1.55；15%/20%交叉校验阈值

A/B标准 | A85%、B80%是否作为默认ACTIVE；短手术窗口是否回100%

A/B强化 | A80%、B75%的准入/退出条件和最低能量边界

C/D/E/F | C100→95→90；D110→115→120；E115→120；F100的自动上/下限

蛋白 | A–F 1.2/1.2/1.5/1.3/1.5/1.2 g/kg候选；weight_basis；肾功能前置条件

餐次/宏量 | 餐次比例、脂肪30%候选、碳水反算边界

执行/周调整 | 执行≥80%、能量每次5个百分点、连续2周无响应后提出强化

运动/肺预康复 | 第一周FITT、RPE、P01–P05剂量、P06条件

ONS/再喂养 | 院内ONS目录、触发阈值、再喂养安全流程

Q56 | 接受“选填；空则按A–F默认；取消固定2/4/8周默认减重百分比矩阵”


## Table


类别 | V2.0处理

循证/指南锚点 | 癌症患者能量25–30 kcal/kg/d粗估；蛋白>1.0至1.5 g/kg/d范围；超重/肥胖限制能量方向；围术期营养筛查与预康复；有氧+抗阻方向。

项目候选配置 | PAL具体值；A/B/C/D/E/F精确TEE比例；A/B强化比例；A–F具体蛋白g/kg；餐次比例；运动FITT；执行80%；5个百分点周调整等。

疾病专科覆盖 | CKD蛋白、血糖/血压/尿酸、肝病、再喂养、SpO₂等由对应专科规则覆盖。

运行治理 | 所有项目精确值PENDING→MDT审核→ACTIVE；只有ACTIVE参数可进入AI/Codex权威上下文。


## Table


版本结论：V2.0已经将“能量来源→A–F默认模式→Q56覆盖→强化准入→手术/肝弹性修饰→宏量/运动/肺预康复候选→周复评→下一周调整”闭合为一套可审核、可配置、可回归测试的确定性参数体系。下一步应由责任MDT逐项确认PENDING参数，再由Codex和后续AI共同读取同一套ACTIVE配置。

---

# SOURCE: AI方案生成安全规则与禁忌替代引擎_V2.0_完整版_MDT审阅稿(1).docx

AI方案生成安全规则与禁忌替代引擎 V2.0

肺结节患者术前多学科代谢健康管理

完整版｜MDT审阅稿｜Codex / 规则引擎 / 后续AI共同调用

版本：V2.0（2026-09）

适用：术前方案生成、食谱/运动/肺预康复筛选、周复评、方案验证、人工升级与发布前校验。

目录

0. 执行摘要与V2.0变更

1. 总体治理、权威链与安全模型

2. 数据语义、缺失数据与Q56安全位置

3. 全局安全门与绿黄红状态

4. A–F/Q56/手术窗口的冲突与覆盖规则

5. 营养、能量与食谱安全规则

6. 运动安全规则与动作替代引擎

7. 肺预康复安全规则与替代引擎

8. 肝弹性及疾病/特殊状态修饰

9. 周随访趋势安全与下一周方案

10. Safety Validator：AI/Codex生成后强制校验

11. Plan / PlanTask / PatientRecord与前端记录边界

12. 后端数据合同、配置键与审计

13. 最低回归测试与验收用例

14. MDT待确认清单与参考来源

0. 执行摘要与V2.0变更

V2.0在V1.0安全骨架上，吸收当前已经完成的营养与能量V2.0、A–F参数V2.0、菜品组件库V2.0、运动动作库V2.0、肺预康复V2.0、Q50肝弹性规则、Q56医护目标和7天周复评闭环。

系统仍应“自动生成完整方案草稿，医护审核”，不是要求医护逐例手工填写kcal、蛋白、步行分钟和呼吸训练剂量。

Q56为选填。为空时按A–F默认模式自动生成；填写时改变目标模式/强度，但不能突破安全或ACTIVE参数。

A/B强化减脂被定义为预设模式，不允许Codex/AI自由选择更大能量缺口或无限增加有氧。

新增周随访安全门：先判断数据充分性、执行率、肌肉/功能/水分/症状，再决定维持、保肌、营养恢复、强化候选或降阶。

禁忌替代从“中文提示”升级为结构化 replacement_ids / blocked_modules / machine_action，便于后端确定性执行。

患者端实际记录成为安全判断输入：体重/体成分、饮食完成度、主蛋白完成、运动实际量、RPE/BORG、肺预康复完成度、症状/功能、围度等。

1. 总体治理、权威链与安全模型

1.1 唯一权威链

1.2 三种风险/等级必须分离

2. 数据语义、缺失数据与Q56安全位置

2.1 Missing Data前置规则

没有6MWT ≠ 功能正常；没有Q50报告结论 ≠ 低肝纤维化风险；没有肾功能 ≠ 可以自由提高蛋白。缺失数据通常不阻断基础方案，但会阻断依赖该数据的精确分级或进阶。

2.2 Q56在安全引擎中的位置

3. 全局安全门与绿黄红状态

3.1 生成前全局Safety Gate

规范化Q1–Q56、身体成分、实验室、Q50肝弹性、手术窗口、固定用药/治疗和上一周记录。

应用missing_data_policy，保留null/uncertain/explicit_none。

计算/读取A–F、疾病风险、执行能力、当前clinical_safety_level。

识别红/黄触发、Q56冲突、强化准入、手术窗口限制、肝弹性/营养/肌少保护规则。

输出 allowed_components / blocked_modules / replacement_ids / pending_config_ids 后，才允许规则生成器或AI组装方案。

3.2 绿黄红状态

4. A–F/Q56/手术窗口的冲突与覆盖规则

4.1 分型保护优先于追体重

4.2 强化减脂安全准入

仅A/B主表型；Q56明确“强化减脂”，或连续2个可评价周满足项目后续“强化候选”路径（是否允许后者由MDT决定）。

预计手术≥4周；clinical_safety_level=GREEN；无C主导肌少风险；无D/E营养风险或近期非意愿下降。

摄入基本正常、肌肉/功能稳定、疾病状态允许；无显著/进展期肝纤维化风险等限制。

只能调用ACTIVE强化参数：A候选80% TEE、B候选75% TEE；不能自动低于该边界。

运动只允许在ACTIVE动作库上限内进阶一个变量；抗阻必须保留；肺预康复不能用于“增加消耗”。

4.3 强化退出/降阶

5. 营养、能量与食谱安全规则

5.1 能量安全：先算基准，再套模式

TEE_base来源顺序：P1 间接测热REE（如有可靠结果） > P2院内批准REE预测公式+PAL > P3 BIA/体脂秤BMR辅助 > P4 25–30 kcal/kg/d粗略交叉校验。P3/P4不是“金标准TEE”，发生明显不一致时应标记一致性问题并复核。

5.2 营养安全规则

5.3 食谱与菜品禁忌替代引擎

6. 运动安全规则与动作替代引擎

6.1 运动红黄规则

6.2 动作替代矩阵（必须按ID过滤）

6.3 强化减脂运动限制

强化只允许在标准模式基础上把1个有氧变量推至ACTIVE上限/进阶一级，不同时大幅增加频率、时长和强度。

抗阻训练必须保留；“强化减脂”不等于“只做更多有氧”。

若7天肌肉/功能下降、次日恢复变差、食欲/摄入下降或出现黄/红信号，立即冻结强化进阶。

RPE/BORG、SpO₂、HR、BP、血糖等具体阈值均从ACTIVE配置读取；AI不得生成临时阈值。

7. 肺预康复安全规则与替代引擎

Q56“改善肺功能/提高运动能力”只提高肺预康复模块优先级和监测强度，不允许突破ACTIVE剂量；“强化减脂”不得把呼吸训练当作增加热量消耗工具。

8. 肝弹性及疾病/特殊状态修饰

9. 周随访趋势安全与下一周方案

9.1 周复评先后顺序

手术窗口：是否进入≤4周或≤2周；临近手术先关闭强化、保肌/功能/肺预康复优先。

安全门：红/黄事件、新发/加重症状、疾病不稳定、肝纤维化/营养高风险。

数据充分性：体重/体成分、饮食、运动、肺预康复、症状/功能等是否足以评价。

执行率：先区分“方案没效果”还是“患者没执行”；执行不足先BARRIER_FIRST。

生理反应：7日均重、体脂/脂肪量、肌肉、体水分、腰围、症状、功能。

A–F目标与Q56轨迹：Q56有值则比较轨迹，无值只评价默认方向；Q56不得越过安全和ACTIVE边界。

每次仅调整1–3个关键变量，生成新plan_version草稿，医护审核后发布。

9.2 周结论与安全动作

10. Safety Validator：AI/Codex生成后强制校验

11. Plan / PlanTask / PatientRecord与前端记录边界

11.1 安全判断真正需要的患者端记录

照片用于识别食物与份量的辅助核对，不应作为唯一热量真值；优先以“计划值×完成比例+替换+额外摄入”计算实际执行。

12. 后端数据合同、配置键与审计

12.1 Safety Rule Contract

12.2 建议新增/更新的配置键

12.3 每次生成必须保存

patient_id、assessment_id/version、question_schema_version、profile/A–F、Q56快照、surgery_window。

safety_snapshot、triggered_rule_ids、blocked_modules、replacement_ids、pending_config_ids。

active_config_ids、knowledge_item_ids/source_version、generation_source（RULE_BASED/AI）、model/prompt version。

validation结果、clinician_review状态、plan_id/version、后续SafetyEvent解除记录。

13. 最低回归测试与验收用例

14. MDT待确认清单与参考来源

14.1 上线前必须由责任MDT确认

SpO₂、HR、BP、血糖、BORG/RPE等运动/肺康复黄色/红色阈值与解除规则。

A/B强化模式：A80%、B75%、准入/退出，以及是否允许“连续2个可评价周无响应”自动提出强化候选。

手术≤2周时A/B回退95–100% TEE的最终数值（当前建议默认100%为项目候选）。

C/D/E/F候选能量比例、蛋白参数、再喂养路径及肾功能/肝病覆盖规则。

周复评执行充分阈值（当前候选≥80%）、数据充分性阈值、能量5个百分点步长。

动作库所有剂量、强度、停止条件和视频版本；P03/P04标准动作定义；P06设备/处方确认字段。

过敏、吞咽、误吸、红色急症事件的院内升级路径和人工解除权限。

菜品营养值的数据源、正式重算服务与正餐完整性Validator落地方式。

14.2 本文件主要项目来源

1. 《AI方案生成安全规则与禁忌替代引擎 V1.0 MDT审阅稿》：V2.0直接继承的安全规则骨架。

2. 《肺结节患者术前能量计算、数据记录与周动态调整规则 V2.0》：能量模式、Q56、周复评与数据闭环。

3. 《肺结节患者术前营养与能量计算规则 V2.0》：TEE来源、A–F能量、强化模式、营养支持与营养Validator。

4. 《肺结节患者术前A–F分型参数配置候选值 V2.0》：A–F候选参数和Q56调用规则。

5. 《肺结节患者术前菜品与食谱组件库 V2.0》：food_id、适用/慎用/替代、食谱输出结构与执行记录。

6. 《肺结节患者术前运动处方生成规则与动作库 V2.0》：A01–A06、U/L/R/C、S01–S08、动作替代、FITT与周复评。

7. 《肺结节患者术前肺预康复知识库 V2.0》：P01–P06、安全停止、Q56/手术窗口、执行记录与周调整。

8. 《肝弹性成像与肝脏代谢风险处理规则》：Q50肝纤维化风险修饰和红黄升级。

9. 《AI方案生成治理补齐说明》：ACTIVE/PENDING、knowledge_item、adaptive_rule、Safety Validator、审核发布链。

14.3 V1.0已采用的外部依据（沿用，不在本次V2.0中重新扩展阈值）

1. 中国专家共识：肺癌围手术期肺康复训练（2024）。

2. ASCO Guideline: Exercise, Diet, and Weight Management During Cancer Treatment（2022）。

3. ESPEN Clinical Nutrition in Surgery – Update 2025。

4. ESMO Clinical Practice Guideline: Cancer cachexia in adult patients（2021）。

5. ADA Standards of Care in Diabetes—2026；2024 ESC高血压指南等专科规则来源。

6. 国家卫生健康委成人肥胖及相关食养指南（2023–2024）等。


## Table


V2.0定位：本文件不是新的医学处方库，而是把营养、菜品、运动、肺预康复、Q56、手术窗口、肝弹性、随访趋势与发布治理统一到一个确定性安全闸门中。系统先过滤风险与禁忌，再把“允许集合”交给规则生成器/Codex/后续AI编排。


## Table


最重要边界：安全规则 > ACTIVE MDT配置 > ACTIVE知识库 > A–F/Q56模板 > AI提示词。Q56属于患者个体管理目标输入，不能突破安全规则或ACTIVE处方边界；任何PENDING数值不得被Codex/AI自行补成精确剂量。


## Table


领域 | V1.0 | V2.0新增

目标层 | A–F/疾病/执行能力 | 加入Q56选填目标；目标kg仅作轨迹，不用kg×7700倒算能量

营养 | 保护低摄入/营养风险 | 加入A85/B80、A强化80/B强化75、C/D/E/F候选能量边界的安全校验接口

食谱 | 过敏/吞咽/疾病修饰 | 与菜品V2.0联动；正餐缺克重/重量口径可判方案不完整

运动 | 红黄灯+基础替代 | 与A01–A06、U/L/R/C、S01–S08的ID与替代关系联动

肺预康复 | P01–P06安全 | 加入Q56、周复评、动作降阶；P06仍需设备+医护确认

动态调整 | 冻结/转人工 | 加入MAINTAIN等周结论和“每次只改1–3个关键变量”的安全限制


## Table


优先级 | 来源 | 职责 | 不得被谁覆盖

1 | 安全规则/院内急症流程 | 绿黄红、停止、阻断、转人工、替代 | 任何配置、模板或AI

2 | ACTIVE MDT配置 | 能量/蛋白/餐次、运动FITT、肺预康复剂量、疾病阈值 | 知识库/模板/AI

3 | ACTIVE知识库 | 菜品、动作、P01–P06、替代项、视频 | 模板/AI

4 | A–F/Q56/手术窗口模板 | 决定目标权重、模式和组合 | AI自由发挥

5 | AI/Codex编排提示词 | 把允许组件编排成完整草稿并解释 | 不得发明上层未批准数值


## Table


维度 | 含义 | 示例 | AI权限

clinical_safety_level | 当前是否可继续居家执行/自动进阶 | green / yellow / red | 只读；由确定性规则和医护状态决定

disease_risk | 各疾病本身的风险/控制程度 | 高血压、糖代谢、肝病等各自分层 | 缺数据不得伪分级；AI不改

execution_ability | 患者能否完成任务 | 障碍、支持、依从性 | 可据此简化路径，但不能当临床安全


## Table


硬约束：页面/API/数据库不得只用一个 risk_level 混合三种语义。疾病风险较高不等于当前红色；疾病分级不高也可能因新发胸痛、咯血等直接进入红色。


## Table


数据状态 | 定义 | 允许行为 | 禁止行为

known_data | 有明确值/结论 | 参与规则计算和方案生成 | 不得被AI覆盖

explicit_none | 明确“无/没有” | 作为已知阴性信息 | 不得转成missing

missing_data | 应有但未提供/未测 | 可继续不依赖该项的保守方案 | 不得补值、插值、假设正常

uncertain_items | 报告不清楚/结果冲突 | 保留不确定并复核 | 不得自动选一个结论当真

need_clinician_review | 规则判定必须人工复核 | 冻结相关敏感调整 | 不得因AI“看起来合理”解除


## Table


Q56状态 | 系统安全动作 | 禁止行为

为空 | 按A–F默认模式自动生成，不视为缺失 | 不得停在“等待医护逐项设数值”

标准减脂 | 调用A/B标准ACTIVE模式；C/D/E/F按自身保护规则 | 不能为了“减重”突破表型保护

强化减脂 | 先跑强化资格门槛；通过后才调用A80%/B75%候选ACTIVE配置 | Codex/AI不得自由挑22%、28%等缺口

目标体重/变化量 | 换算成阶段轨迹用于随访比较 | 禁止“目标kg×7700÷天数”倒算每日能量

维持/保肌/营养恢复/增肌等 | 可覆盖A/B默认减脂方向 | 仍受疾病、手术窗口和安全规则约束


## Table


等级 | 典型条件 | 方案生成 | 任务执行 | 解除

GREEN | 无新发/加重危险症状；已知资料足以支持当前方案；体重/肌肉/摄入/功能趋势总体稳定 | 正常生成，仍受知识库与疾病修饰 | 执行PUBLISHED任务；按周复评 | 随新数据动态评估

YELLOW | 耐受下降、数据冲突、持续摄入不足、减重伴肌肉下降、轻中度症状影响执行、肝纤维化风险需复核等 | 受影响模块降阶/冻结进阶；可生成未受影响模块；标记复核 | 相关任务暂停/降阶/替代；加强记录 | 稳定后按规则或医护确认；不得仅凭一次正常值自动解除

RED | 胸痛/明显呼吸困难、晕厥、意识异常、咯血、严重过敏、达到院内红色阈值等 | 停止受影响模块自动生成/进阶；进入人工/急症流程 | 冻结相关任务；不得给“坚持/再试”建议 | 必须医护确认解除；患者自述“好了”不足以自动恢复


## Table


分型 | 默认方向 | 安全硬边界

A | 标准减脂+保肌；Q56可强化 | 不得删除抗阻/蛋白保护；≤2周关闭强化候选

B | 标准减脂+保肌+代谢管理；Q56可强化 | 疾病监测覆盖；不能靠自动加量代替疾病管理

C | 保肌优先；第一周约100% TEE候选 | 不进入A/B强化；肌肉/功能下降冻结减能与有氧进阶

D | 营养恢复；约110% TEE候选 | 禁止减重逻辑；再喂养风险优先专科路径

E | 先止跌/恢复；约115% TEE候选 | 摄入不足/快速下降时禁止强化训练；再喂养风险阻断机械加能

F | 安全与执行优先；默认约100% TEE候选或继承叠加表型 | 不因“复杂”自动减能；先简化任务和解决障碍


## Table


触发 | 安全动作

摄入不足、食欲下降或连续多日计划完成明显不足 | 冻结强化；进入BARRIER_FIRST/NUTRITION_RECOVERY评估

体重下降同时肌肉/功能下降、水分明显下降或疲劳/气促加重 | PRESERVE_MUSCLE / DEINTENSIFY；回标准或维持

手术窗口缩短至<4周或≤2周 | 关闭强化；≤2周候选回95–100% TEE，默认100%待MDT确认

黄色/红色安全信号或疾病状态不稳定 | 冻结相关模块并SAFETY_REVIEW

肝弹性提示显著/进展期纤维化或肝硬化可能 | 黄色复核；冻结激进减重和自动运动进阶


## Table


处方边界：Q56的目标kg/速度只是阶段轨迹与疗效比较变量；每日Energy_target必须来自TEE_base×ACTIVE模式比例及安全修正。7700 kcal/kg是以脂肪组织减重为核心的历史静态近似，不能代表1 kg体重恒等于7700 kcal，也不能用于直接倒算术前患者的每日处方缺口。


## Table


Rule ID | 触发 | 等级 | 系统动作 | 禁止AI/Codex行为

NUT-SAFE-001 | D/E型、近期非意愿下降、明显摄入不足/营养风险 | Y | 禁止减重/扩大缺口；营养恢复+保肌；必要时营养科复核 | 少吃一顿补偿/继续强化

NUT-SAFE-002 | 严重过敏表现：全身风团、口唇/舌咽肿胀、声音嘶哑、呼吸困难等 | R | 停相关食物；急症/人工升级 | 同食材或未确认交叉过敏替代

NUT-SAFE-003 | 反复呕吐、无法保留饮水/食物、明显脱水 | Y/R | 冻结自动能量调整；评估；严重者急症流程 | 强行补餐或加练

NUT-SAFE-004 | 明显吞咽困难、呛咳/疑误吸 | Y/R | 停止普通质地；转吞咽/营养评估 | 自行给特殊稠度治疗处方

NUT-SAFE-005 | 持续腹泻、严重腹痛/腹胀、黑便/血便 | Y/R | 暂停相关自动饮食调整并转医护 | 用加纤维/继续减脂“纠正”

NUT-SAFE-006 | 快速体重下降伴乏力、功能下降或摄入不足 | Y | 冻结减重与高消耗运动；保营养/保肌 | 判定为“减重效果好”

NUT-SAFE-007 | 明显水肿、尿量减少或已有液体/蛋白限制医嘱 | Y/R | 冻结相关营养参数；专科复核 | 自动高蛋白/高液体

NUT-SAFE-008 | 肝纤维化风险增加/资料冲突 | Y | 降低快速减重；保营养/肌肉；复核 | 自行低蛋白；仅凭单次LSM定F0–F4

NUT-SAFE-009 | 糖尿病/降糖治疗出现低/高血糖症状或达院内阈值 | Y/R | 按专科规则暂停/调整相关任务并转医护 | 改药剂量


## Table


情况 | 硬阻断/限制 | 优先替代/处理 | 备注

明确食物过敏 | 阻断对应food_id及含该食材组件 | 同类营养目标的无过敏组件 | 过敏优先于菜谱多样性

乳糖不耐 | 限制普通乳制品；按耐受与知识库标签处理 | 无乳糖/无糖豆浆等已审核组件 | 不是“牛奶过敏”同义词

咀嚼困难/食欲差 | 避免难嚼、大体积低能量结构 | 软食/小份高营养密度模板 | D/E不以大量蔬菜挤占主食/蛋白

A/B标准或强化 | 不能优先削减主蛋白；控制油、精制糖、额外饮料/零食和主食份量 | 强化模板T13等ACTIVE组件 | 每餐应保留蛋白质结构

C保肌 | 禁止通过削蛋白实现能量限制 | C型保肌模板，主蛋白1–1.25份候选 | 体重不降但腰围/肌肉改善可判有效

F执行困难 | 避免每天过度复杂不同菜单 | 固定2–3套可执行菜单轮换 | 完成率优先


## Table


正式食谱完整性校验：任一正餐若缺少主食重量/重量口径、主要蛋白食材重量、主要蔬菜重量或无法计算/追溯营养值，应标记 nutrition_plan_validation=FAIL 或进入待补齐状态，不应作为完整患者执行餐单发布。


## Table


Rule ID | 触发 | 等级 | 系统动作

EX-SAFE-001 | 新发/明显加重胸痛胸闷，尤其伴出汗、恶心、呼吸困难或放射不适 | R | 立即停练；人工/急症升级

EX-SAFE-002 | 明显或快速加重呼吸困难，静息仍难恢复 | R | 停止运动/进阶；人工评估

EX-SAFE-003 | 晕厥/近晕厥、明显头晕或站立不稳 | R | 停止；禁止站立/无支撑替代

EX-SAFE-004 | 明显心悸并伴胸闷、头晕、乏力等 | R | 停止并转医护

EX-SAFE-005 | 新发明显神经症状：肢体无力、言语/意识异常 | R | 立即停止并紧急升级

EX-SAFE-006 | 咯血/鲜红血痰或明显出血 | R | 停止运动与咳嗽类训练；人工升级

EX-SAFE-007 | 紫绀/意识改变；或SpO₂/HR/BP/血糖达ACTIVE停止阈值 | R | 停止；按专科/急症流程

EX-SAFE-008 | 突发明显腿痛/腿肿、严重关节痛或疑急性损伤 | Y/R | 停止受累肢体训练；评估

EX-SAFE-009 | 持续恶心、呕吐、极度乏力，休息后不缓解 | Y/R | 停止；评估营养/疾病状态


## Table


情况 | 避免/暂停 | 优先替代 | 升级条件

膝/髋痛 | L01半蹲、L02半蹲横移、L06靠墙静蹲等高膝负荷 | A01平地缓走、A04固定自行车（若耐受）、R04坐姿腿屈伸、R05坐姿提踵 | 急性明显疼痛/肿胀：不替代，转评估

腰背痛 | L03屈腿硬拉、C02等增加腰背负荷动作 | A01步行、R03坐姿划船、R04坐姿腿屈伸等 | 伴神经症状：按红/黄规则

平衡差/头晕史 | 无支撑站立抗阻、横移类动作 | R03坐姿划船、R04坐姿腿屈伸、扶持L05、R02墙壁俯卧撑 | 当日明显头晕：暂停，不强行替代

低体能/功能数据不足 | 直接套A02快走高剂量/多动作高负荷 | A01、A03短时多段、R01–R05低负荷坐姿/扶持动作 | 补充功能数据后再进阶

活动后气促/节律乱 | 连续中高强度有氧 | 有氧降一级/间歇；联动P01/P02；缩短单段 | 明显或快速加重：RED

肌少/肌肉下降 | 长时间单纯有氧减重 | 抗阻优先+低冲击有氧+营养联动 | 冻结减能和有氧进阶

D/E或摄入不足 | 高消耗训练、强化运动 | 短时低-中强度功能训练、低负荷抗阻 | 训练后关注进食和疲劳恢复


## Table


Rule ID | 触发 | 等级 | 系统动作/替代

PR-SAFE-001 | 练习中胸痛、明显胸闷或呼吸困难迅速加重 | R | 立即停止P01–P06及相关运动；转医护

PR-SAFE-002 | 咯血/鲜血痰 | R | 停止P05及呼吸训练；人工升级

PR-SAFE-003 | 反复深呼吸后头晕、手足麻木、过度换气不适 | Y | 停练，恢复自然呼吸；复评动作/剂量

PR-SAFE-004 | P05导致明显胸痛或无法恢复平静呼吸 | Y/R | 停止P05；评估；无痰者本不应高频固定P05

PR-SAFE-005 | SpO₂达到ACTIVE停止阈值或持续明显下降 | R | 停止并进入人工流程

PR-SAFE-006 | 喘鸣明显加重、意识异常或紫绀 | R | 停止并紧急升级

PR-SAFE-007 | 痰多/排痰困难但无设备或无医护处方 | Y | 可P05；P06/OPEP不得自动启用

PR-SAFE-008 | 肩痛/胸部牵拉影响P03/P04动作质量 | Y | 减量或替换为P01/P02等不诱发症状动作

PR-SAFE-009 | 缺肺功能/6MWT等功能数据 | G/Y | 可基础P01–P04；耐量相关进阶待评估


## Table


P项目 | 核心安全边界 | 替代/降阶

P01 缩唇呼吸 | 胸痛/明显气促加重/过度换气不适时停 | 恢复自然呼吸或改P02，经评估后再继续

P02 腹式呼吸 | 避免过度深快呼吸；头晕/麻木即停 | 自然呼吸，缩短时长

P03 胸廓扩张 | 肩胸疼痛/活动受限时不强迫幅度 | P01/P02；必要时低量P04

P04 呼吸-上肢协同 | 肩胸牵拉/疼痛影响动作质量时降阶 | P01/P02或低幅度动作

P05 有效咳嗽 | 无痰不作高频固定任务；咯血/胸痛停止 | 按需使用；痰多但不适则转医护

P06 OPEP | 仅“设备已具备+医护处方/指导已确认”才能调用 | 无条件时用P05等基础技术


## Table


状态 | 安全修饰 | 系统边界

Q50未做/资料缺失 | 不阻断基础方案；标记未评估 | 不得推断低纤维化风险

稳定脂肪肝/低风险肝病 | 按代谢表型优化能量、糖饮料、脂肪质量、腰围 | 不自动限制运动；不单独改变A–F

肝纤维化风险增加 | 降低快速减重优先级；保营养/肌肉；运动进阶更谨慎 | 不进入强化模式；不自行低蛋白

显著/进展期纤维化或肝硬化可能、肝功持续异常、资料明显不一致 | YELLOW；MDT/肝病专科复核；冻结激进减重/运动进阶 | 仅凭单次LSM不得诊断F0–F4

意识改变、进行性黄疸、明显腹胀/腹水、消化道出血表现等严重肝病症状 | RED | 停止AI自主调整并立即转医护

肾功能异常/疑异常 | 蛋白/液体/电解质按专科规则 | 无肾功能数据不自动限蛋白；有医嘱则医嘱优先

糖尿病/降糖治疗 | 调用血糖监测/运动规则 | AI不改药

高血压/心血管病 | 症状+ACTIVE血压/心率阈值优先 | AI不把通用指南阈值直接写成项目阈值

高尿酸/痛风 | 急性关节痛时降低受累关节负荷；饮食个体化 | 不一刀切禁蛋白

药物/固定治疗 | 仅提醒和记录 | 不得新增、停用、换药、改剂量/疗程


## Table


周结论 | 典型触发 | 下一周安全动作

MAINTAIN | 安全绿+数据充分+执行充分+目标方向改善+肌肉/功能稳定 | 维持能量/主要训练变量；只做同类轮换/时间优化

BARRIER_FIRST | 完成率低或主要执行障碍明确 | 不加码；简化菜单/动作、分段、调整时段/提醒/家属协助

DATA_INSUFFICIENT | 关键记录不足 | 补数；保持/保守化，不判“方案无效”

PRESERVE_MUSCLE | 体重下降伴肌肉/功能下降；C型风险 | 冻结减能和有氧进阶；蛋白/抗阻/营养优先

NUTRITION_RECOVERY | 持续摄入不足、食欲差、D/E风险 | 停止减脂；提高能量密度/加餐/ONS评估；运动降负荷

INTENSIFY_CANDIDATE | A/B连续2个可评价周执行充分但脂肪相关指标无有利趋势，且全部门槛通过 | 标准→强化候选；仅生成待审核草稿

DEINTENSIFY | 强化后摄入/肌肉/水分/功能/症状不利 | 强化→标准/维持；必要时黄色复核

SAFETY_REVIEW | 黄色/红色、手术/疾病状态变化 | 冻结相关模块，转人工；不自动解除


## Table


趋势判断重点：体重不是唯一效果指标。体重下降但肌肉/水分同时下降、疲劳加重，应判“可能过度/分解代谢风险”，不是“效果优秀”；体重变化小但腰围/体脂改善、肌肉稳定，可MAINTAIN。


## Table


Validator | 检查 | 通过条件 | 失败动作

VAL-001 | 结构完整性 | Plan Contract一级模块齐全；schema合法 | 拒绝保存draft

VAL-002 | 确定性结果保护 | A–F、安全等级、疾病风险、missing语义未被覆盖 | 拒绝保存

VAL-003 | 缺失数据保护 | missing/null/uncertain未被AI补成正常/具体值 | 拒绝保存

VAL-004 | ACTIVE来源 | 食谱/动作/P01–P06来自允许且ACTIVE库 | 未知/DRAFT/PENDING项目拒绝

VAL-005 | 剂量权限 | 数值来自ACTIVE配置；未确认保持null/mdt_pending | AI擅自给阈值/剂量则拒绝

VAL-006 | 禁忌冲突 | 当前患者无forbidden食物/动作/模式 | 替换后重验；高风险冲突整份失败

VAL-007 | Q56冲突 | 目标模式未突破A–F保护、手术窗、肝弹性和安全边界 | 降阶/require_review

VAL-008 | 强化模式 | 仅合格A/B使用ACTIVE强化；未低于自动最低比例 | 失败则回标准/复核

VAL-009 | 药物权限 | 无新增/停用/改剂量/改疗程 | 发现即失败

VAL-010 | 红色状态 | RED时未继续生成被阻断模块/鼓励执行 | 失败并人工升级

VAL-011 | 停止条件 | 运动/肺预康复任务含stop_rule引用 | 缺失不可发布

VAL-012 | 食谱完整性 | 正餐含食材克重/重量口径、营养估算、替换信息 | 不完整则FAIL/待补齐

VAL-013 | 周调整边界 | 只改1–3变量；数据不足不强化；执行不足先BARRIER | 失败则不生成新版本

VAL-014 | 版本/来源审计 | 记录source_version/config_ids/rule_ids/model_prompt_version | 缺失则不可进入正式审核


## Table


对象 | 含义 | 安全规则

Plan | 医护审核后的“应该做什么” | RED/YELLOW不静默覆盖当前PUBLISHED；调整必须新plan_version

PlanTask | 从最终PUBLISHED Plan结构化出的执行任务 | 仅物化已发布内容；安全事件可暂停/降阶状态，但不改历史处方

PatientRecord | 患者实际做了什么 | 记录完成度、实际量、症状、不适、原因；作为周复评输入

SafetyEvent | 规则触发事件 | 保存触发规则、时间、数据快照、受影响模块、升级状态和解除人


## Table


数据 | 必填性 | 安全用途

每日体重 | 核心必填 | 7日均重；识别过快下降/营养风险

体脂率、肌肉/骨骼肌、水分率/水分量 | 有设备时优先自动采集；部分可条件必填 | 区分脂肪下降、水分波动和肌肉损失

蛋白质率/蛋白质量、BMR | 选填/自动保存 | 辅助趋势，不单独触发处方

腰围 | A/B/C或Q56含减脂/腰围目标时每周条件必填 | 中央脂肪趋势

每餐计划完成比例 | 必填 | 比照片猜kcal更可靠地估计执行

主蛋白完成比例 | 有蛋白任务餐条件必填 | 保肌/蛋白执行

替换/额外摄入 | 必填；有则展开 | 纠正计划与实际

食欲/进食症状 | 每日必填 | D/E风险、摄入不足原因

运动完成/实际时长或组数/RPE/不适 | 完成或部分完成时条件必填 | 判断是否可进阶/需降阶

肺预康复完成/实际量/不适 | 有任务时条件必填 | 耐受和周调整

疲劳/气促/疼痛/活动能力 | 每日简短必填 | 过度训练、功能下降、安全触发


## Table


字段 | 说明 | 示例

rule_id | 唯一规则编号 | EX-SAFE-001

domain | global/nutrition/food/exercise/pulmonary/disease | exercise

trigger | 结构化触发条件 | new_or_worsening_chest_pain=true

severity | green/yellow/red | red

scope | 影响模块/动作 | exercise + pulmonary

machine_action | block/pause/freeze/downgrade/substitute/review/urgent_escalation | pause + urgent_escalation

forbidden_output | 绝对不能生成内容 | 继续加量/坚持完成

allowed_output | 仍允许的安全内容 | 停止训练+人工评估提示

replacement_ids | 可替代知识库ID | R04;R05 / P01;P02

requires_manual_release | 是否需医护解除 | true

source_version | 规则来源版本 | Safety V2.0 + Exercise V2.0


## Table


Config | 内容 | 责任MDT

SAFE-CFG-001 | 运动/肺康复SpO₂黄色/红色阈值、相对基线下降规则 | 胸外科+康复+呼吸

SAFE-CFG-002 | 运动前/中BP、HR停止/复评阈值 | 心血管+康复

SAFE-CFG-003 | 血糖触发规则及运动/饮食边界 | 内分泌

SAFE-CFG-004 | BORG/RPE目标区间与分层映射 | 康复

SAFE-CFG-005 | YELLOW→GREEN恢复观察规则/人工确认条件 | 胸外科+护理+康复

SAFE-CFG-006 | 红色事件“立即急症”vs普通人工消息的院内路径 | 急诊/胸外科/医院安全

SAFE-CFG-007 | 肾功能/电解质触发营养限制阈值 | 肾内+营养

SAFE-CFG-008 | 营养风险/快速下降冻结减重的量化条件 | 营养

SAFE-CFG-009 | 过敏/吞咽/误吸院内升级路径 | 营养+护理+相关专科

SAFE-CFG-010 | Q56标准/强化/维持/保肌/营养恢复目标冲突矩阵 | 营养+康复+胸外科

SAFE-CFG-011 | A/B强化准入/退出、A80/B75自动最低比例及≤2周回退策略 | 营养+胸外科

SAFE-CFG-012 | 周调整：执行≥80%、连续2周、5个百分点步长等候选值 | 营养+康复+护理

SAFE-CFG-013 | 肝弹性显著风险时冻结哪些模块/复核路径 | 肝病/消化+营养+胸外科

SAFE-CFG-014 | SafetyEvent人工解除权限与审计要求 | 项目治理/医院安全


## Table


ID | 场景 | 预期

T01 | Q56空，A型，4–8周，安全绿 | 按A默认模式自动生成完整草稿；不要求医护逐项填数；可用菜品/动作/P01–P04

T02 | B型，Q56=强化，≥4周，肌肉/功能稳定 | 只有强化门槛全通过才可调用A/B强化ACTIVE配置；抗阻保留

T03 | B型，Q56=4周减4kg但肌肉下降 | 不得kg×7700倒算；PRESERVE_MUSCLE/冻结强化

T04 | C型第一周 | 不进入强化；保肌/抗阻优先；能量按C候选保护路径

T05 | D/E摄入不足/近期下降 | 冻结减重和高消耗运动；NUTRITION_RECOVERY

T06 | E型高再喂养风险 | 不得机械115% TEE；转专科再喂养路径

T07 | F型执行困难+膝痛+平衡差 | 简化任务；过滤L01/L02/L06；使用坐姿/扶持替代

T08 | 稳定A型无痰、Q56空 | P01–P04按需1–3项；不固定高频P05；无P06

T09 | 无设备/无医护处方但痰多 | 允许P05；必须阻断P06

T10 | 肝弹性提示进展期纤维化可能 | YELLOW；冻结强化减脂/运动自动进阶；MDT/肝病复核

T11 | 一周记录不足 | DATA_INSUFFICIENT；不改变剂量/不自动强化

T12 | 饮食完成低但体重未变 | BARRIER_FIRST；不是“方案无效”

T13 | 体重下降但肌肉/水分下降、疲劳加重 | DEINTENSIFY/PRESERVE_MUSCLE；不可判“效果优秀”

T14 | 新发胸痛或咯血 | RED；停止相关任务；人工/急症升级；患者自述好转不能自动解除

T15 | 疑严重食物过敏 | RED；停食材/组件；人工/急症流程

T16 | 正餐缺主食/蛋白/蔬菜重量口径 | VAL-012失败；不得作为完整患者餐单发布

T17 | AI生成未知动作ID/自创P07 | VAL-004失败；拒绝或删除未知项目

T18 | PENDING剂量被AI写成精确数值 | VAL-005失败；不得保存为可审核草稿


## Table


V2.0结论：本安全引擎的核心任务不是替代MDT，而是确保Codex规则生成器和后续AI都只能在同一套ACTIVE参数、知识库和患者安全状态内工作：先阻断风险，再提供允许集合，再生成完整草稿，最后Safety Validator再次验证并进入医护审核。

---

# SOURCE: 肺结节患者术前第一周执行方案_V2.1_完整优化模板_MDT审阅稿(1).docx

肺结节患者术前多学科代谢健康管理计划

患者端 · 第一周执行方案 V2.1（完整优化模板）

用于规则引擎 / Codex / AI 的统一结构化输出、医护审核与患者执行

V2.1 核心更新

一、我的方案状态

二、我的健康画像与本周重点

三、Q56医护目标与第一周阶段目标

四、个体化参数计算摘要（医护审核区）

患者端可只展示最终能量与简短理由；医护端保留完整计算链。目标体重/目标kg只用于管理轨迹，不使用“目标kg×7700”直接反推每日能量。

五、每日营养目标

六、第一周完整饮食处方（7天）

系统生成时必须展开7天、每餐完整明细。周总览不能替代单餐克重。每个正餐至少包含主食、主要蛋白食物、蔬菜及烹调油/脂肪来源（如适用）的明确份量；若缺关键重量或重量口径，nutrition_plan_validation = FAIL。

周一

周二

周三

周四

周五

周六

周日

饮食计划发布前校验

七、第一周运动处方

运动动作详情卡（系统按所选动作自动展开）

八、第一周肺预康复计划

P01–P06按Q56目标、呼吸症状、痰液/排痰、A–F、功能和手术窗口选择；不要求所有患者做全部项目。P06仅在已有设备且医护处方/指导时调用。

肺预康复周安排

九、每日执行与数据记录（前端必填/选填规则）

患者端最小提问集（建议直接实现）

十、监测与安全

十一、周日复评与第二周调整

周结论与第二周草稿状态

十二、固定治疗提醒

□ 降压药  □ 降糖药  □ 胰岛素  □ 调脂药  □ 降尿酸药  □ GLP-1药物  □ 甲状腺药  □ 营养治疗  □ 康复/理疗  □ 针灸/埋线  □ 其他：____

系统只按医护确认的治疗档案提醒和记录，不自行新增、停用、换药、改剂量或改时间。

十三、资料不足、冲突与MDT待确认项

十四、版本管理与审核

十五、Codex / AI 结构化输出合同（开发附录）

该附录用于开发和联调，患者端可不直接展示。RULE_BASED_GENERATOR与AI_GENERATOR必须输出同一结构；Safety Validator通过并经医护审核发布后，PUBLISHED方案才可物化为plan_task。

发布前模板完整性校验


## Table


说明：本模板不预设固定处方。所有精确能量、蛋白质、食谱、运动和肺预康复剂量，均由“当前有效评估 + ACTIVE MDT参数 + 已审核知识库 + 安全规则”生成后填入。AI/Codex不得自行创造未启用的阈值或剂量。


## Table


Q56目标层 | 新增“医护指导的本阶段术前健康管理目标”来源、首要目标、目标周期、体重目标和其他重点；Q56为空时按A–F默认规则自动生成。

能量可解释链 | 显示REE/TEE来源优先级、预测公式/PAL、TEE_base、能量模式与最终处方能量；目标kg不直接倒算每日kcal。

完整7天食谱 | 所有早餐/午餐/晚餐/加餐必须写菜名、食材克重/份数、重量口径、做法、估算营养与替换；正餐缺重量即校验失败。

运动结构化 | 按动作ID生成周计划和动作详情，包含目的、姿势、步骤、剂量、强度、休息、停止条件与替代动作。

肺预康复结构化 | P01–P06按症状、Q56、A–F和手术窗口选择，记录剂量、理由、停止与替代。

数据记录分级 | 明确R=必填、CR=条件必填、O=选填/自动采集、D=系统派生，并给出患者端最小提问集。

周复评闭环 | 7天后先判断安全与数据充分度，再判断执行、生理反应和目标轨迹，生成下一周新草稿，不直接改写已发布方案。

安全与审计 | 纳入绿/黄/红、Q50肝弹性、强化减脂准入/退出、缺失数据、Safety Validator与版本追踪。

 | 


## Table


方案名称 | 肺结节患者术前多学科代谢健康管理计划

当前状态 | □ AI/规则已生成待审核  □ 审核中  □ 审核通过待发布  □ 已发布

方案版本 | V____    生成日期：____年__月__日    发布日期：____年__月__日

患者ID | ____________

评估版本 | Assessment Questionnaire：Q1–Q56 / schema version：____________

当前术前窗口 | □ ≤2周  □ 2–4周  □ 4–8周  □ >8周  □ 未确定

主A–F表型 | □ A  □ B  □ C  □ D  □ E  □ F

疾病/代谢风险 | ____________________________

执行能力 | □ 绿  □ 黄  □ 红 / 主要障碍：________________

安全等级 | □ 绿色  □ 黄色  □ 红色

审核团队 | 胸外科 / 营养科 / 康复医学科 / 内分泌科 / 心血管内科 / 中医科（按需联合其他专科）


## Table


关键项目 | 当前结果 | 对本周方案的影响

体重 / BMI | ____ kg / ____ kg/m² | ________________

体脂 / 脂肪量 | ____ % / ____ kg | ________________

腰围 | ____ cm | ________________

肌肉量 / 骨骼肌量 / SMI | ____ kg / ____ kg / ____ kg/m² | ________________

水分率/水分量 | ____ % / ____ kg | 用于解释短期体重与BIA波动

6MWT / 功能 | ____ m；BORG ____；SpO₂ ____→____% | ________________

近期体重与摄入 | □稳定 □主动减/增 □非意愿下降；食欲____；摄入____ | ________________

主要代谢疾病/用药 | ________________ | ________________

Q50肝弹性/肝脏修饰 | □未做 □稳定低风险 □需复核/黄色；摘要：________ | ________________

活动限制/症状 | ________________ | ________________

主要执行障碍 | ________________ | ________________


## Table


说明：Q56为选填。若医护未设定，目标来源记为“系统默认”，系统按A–F、手术窗口和安全规则自动生成完整方案；若填写Q56，Q56决定阶段目标/强度，但不得突破安全与ACTIVE MDT参数。


## Table


目标来源 | □ Q56医护设定  □ Q56为空，系统默认

首要目标 | □ 标准减脂  □ 强化减脂  □ 体重维持/保肌  □ 营养恢复/增重  □ 停止继续下降  □ 增肌  □ 代谢控制  □ 提高运动能力  □ 改善肺功能  □ 术前综合准备

目标周期 | 自动读取Q6：□ ≤2周  □ 2–4周  □ 4–8周  □ >8周  □ 未确定

体重目标 | □ 不设具体目标  □ 目标体重____kg  □ ____周内 □下降/□增加 ____kg

其他重点 | □ 肌肉不下降  □ 体脂下降  □ 腰围下降  □ 控糖  □ 降脂  □ 降尿酸  □ 提高运动能力  □ 改善肺功能  □ 其他____

目标轨迹 | 系统派生，仅用于比较：________________

目标与安全是否冲突 | □ 否  □ 是→已降阶/待医护复核

本周最重要的3件事 | ①________________  ②________________  ③________________

第一周目标摘要 | ____________________________


## Table


参数 | 输入/来源 | 计算结果 | 审核/状态

REE来源优先级 | □P1间接测热 □P2院内预测公式 □P3 BIA/BMR辅助 □P4 25–30 kcal/kg参考 | 最终采用：____ | □一致 □需复核

预测公式/设备来源 | formula_id/设备：________ | REE/BMR ____ kcal/d | □ACTIVE □辅助

PAL | 由Q35、日常活动、功能/6MWT映射 | ____ | □ACTIVE

TEE_base | REE × PAL / 实测与校验 | ____ kcal/d | □可用 □需复核

P4交叉校验 | 25–30 kcal/kg/d：____–____ kcal/d | 与TEE差异：____% | □合理 □差异大

能量模式 | A–F + Q56 + 手术窗口 + 安全 | □标准 □强化 □维持/保肌 □恢复 | □ACTIVE

能量系数 | 例如85%/80%/100%等，以ACTIVE配置为准 | ____% | □ACTIVE

处方能量 | TEE_base × 系数 | ____ kcal/d | □医护确认

蛋白质 | weight_basis × g/kg/d | ____ g/d | □ACTIVE

碳水化合物 | 按总能量与配置分配 | ____ g/d | □ACTIVE

脂肪 | 按总能量与配置分配 | ____ g/d | □ACTIVE

餐次分配 | 早餐____% 午餐____% 晚餐____% 加餐____% | 3餐 / 3+1 / 3+2 | □确认


## Table


说明：若P2/P3/P4结果差异明显、BIA测量状态异常、关键身高/体重/活动信息不足，系统应降低估算置信度、提示补充/复核，不应在不可靠数据上生成极端处方。


## Table


项目 | 每日目标 | 患者端说明

总能量 | ____ kcal | 本周实际处方目标，不等于TEE

蛋白质 | ____ g | 分散到三餐/加餐，优先保护肌肉

碳水化合物 | ____ g | 按全天总量分配，不跳餐补偿

脂肪 | ____ g | 优先少油烹饪和适量优质脂肪

餐次 | □3餐 □3+1 □3+2 | 根据目标和执行能力自动选择

饮水/液体 | 按医护建议：________ | 肾/心功能等有特殊限制时按专科规则

特殊饮食修饰 | □控糖 □控盐 □血脂 □尿酸 □肝脏 □其他 | 只调用已审核疾病规则


## Table


说明：重量口径必须明确：每个食材均标“生重/熟重/干重/可食部/份数”。系统不得只写“鱼100g”而不说明口径。


## Table


餐次 | 菜品与主要食材（必须写克重/份数+重量口径） | 烹饪方式/简要做法 | 估算营养 | 同类替换/备注

早餐 | 菜名：________ 主食：____g（□生/□熟/□干） 蛋白/奶豆：____g/ml/个 水果/蔬菜：____g | ________ | ____ kcal P____g C____g F____g | ________

午餐 | 菜名：________ 主食：____g（□生/□熟/□干） 主蛋白：____g（□生/□熟） 蔬菜：____g（□生/□熟） 油：____g | ________ | ____ kcal P____g C____g F____g | ________

加餐 | 食物/菜名：________ 数量：____g/ml/份 | ________ | ____ kcal P____g C____g F____g | □无加餐 / ________

晚餐 | 菜名：________ 主食：____g（□生/□熟/□干） 主蛋白：____g（□生/□熟） 蔬菜：____g（□生/□熟） 油：____g | ________ | ____ kcal P____g C____g F____g | ________


## Table


餐次 | 菜品与主要食材（必须写克重/份数+重量口径） | 烹饪方式/简要做法 | 估算营养 | 同类替换/备注

早餐 | 菜名：________ 主食：____g（□生/□熟/□干） 蛋白/奶豆：____g/ml/个 水果/蔬菜：____g | ________ | ____ kcal P____g C____g F____g | ________

午餐 | 菜名：________ 主食：____g（□生/□熟/□干） 主蛋白：____g（□生/□熟） 蔬菜：____g（□生/□熟） 油：____g | ________ | ____ kcal P____g C____g F____g | ________

加餐 | 食物/菜名：________ 数量：____g/ml/份 | ________ | ____ kcal P____g C____g F____g | □无加餐 / ________

晚餐 | 菜名：________ 主食：____g（□生/□熟/□干） 主蛋白：____g（□生/□熟） 蔬菜：____g（□生/□熟） 油：____g | ________ | ____ kcal P____g C____g F____g | ________


## Table


餐次 | 菜品与主要食材（必须写克重/份数+重量口径） | 烹饪方式/简要做法 | 估算营养 | 同类替换/备注

早餐 | 菜名：________ 主食：____g（□生/□熟/□干） 蛋白/奶豆：____g/ml/个 水果/蔬菜：____g | ________ | ____ kcal P____g C____g F____g | ________

午餐 | 菜名：________ 主食：____g（□生/□熟/□干） 主蛋白：____g（□生/□熟） 蔬菜：____g（□生/□熟） 油：____g | ________ | ____ kcal P____g C____g F____g | ________

加餐 | 食物/菜名：________ 数量：____g/ml/份 | ________ | ____ kcal P____g C____g F____g | □无加餐 / ________

晚餐 | 菜名：________ 主食：____g（□生/□熟/□干） 主蛋白：____g（□生/□熟） 蔬菜：____g（□生/□熟） 油：____g | ________ | ____ kcal P____g C____g F____g | ________


## Table


餐次 | 菜品与主要食材（必须写克重/份数+重量口径） | 烹饪方式/简要做法 | 估算营养 | 同类替换/备注

早餐 | 菜名：________ 主食：____g（□生/□熟/□干） 蛋白/奶豆：____g/ml/个 水果/蔬菜：____g | ________ | ____ kcal P____g C____g F____g | ________

午餐 | 菜名：________ 主食：____g（□生/□熟/□干） 主蛋白：____g（□生/□熟） 蔬菜：____g（□生/□熟） 油：____g | ________ | ____ kcal P____g C____g F____g | ________

加餐 | 食物/菜名：________ 数量：____g/ml/份 | ________ | ____ kcal P____g C____g F____g | □无加餐 / ________

晚餐 | 菜名：________ 主食：____g（□生/□熟/□干） 主蛋白：____g（□生/□熟） 蔬菜：____g（□生/□熟） 油：____g | ________ | ____ kcal P____g C____g F____g | ________


## Table


餐次 | 菜品与主要食材（必须写克重/份数+重量口径） | 烹饪方式/简要做法 | 估算营养 | 同类替换/备注

早餐 | 菜名：________ 主食：____g（□生/□熟/□干） 蛋白/奶豆：____g/ml/个 水果/蔬菜：____g | ________ | ____ kcal P____g C____g F____g | ________

午餐 | 菜名：________ 主食：____g（□生/□熟/□干） 主蛋白：____g（□生/□熟） 蔬菜：____g（□生/□熟） 油：____g | ________ | ____ kcal P____g C____g F____g | ________

加餐 | 食物/菜名：________ 数量：____g/ml/份 | ________ | ____ kcal P____g C____g F____g | □无加餐 / ________

晚餐 | 菜名：________ 主食：____g（□生/□熟/□干） 主蛋白：____g（□生/□熟） 蔬菜：____g（□生/□熟） 油：____g | ________ | ____ kcal P____g C____g F____g | ________


## Table


餐次 | 菜品与主要食材（必须写克重/份数+重量口径） | 烹饪方式/简要做法 | 估算营养 | 同类替换/备注

早餐 | 菜名：________ 主食：____g（□生/□熟/□干） 蛋白/奶豆：____g/ml/个 水果/蔬菜：____g | ________ | ____ kcal P____g C____g F____g | ________

午餐 | 菜名：________ 主食：____g（□生/□熟/□干） 主蛋白：____g（□生/□熟） 蔬菜：____g（□生/□熟） 油：____g | ________ | ____ kcal P____g C____g F____g | ________

加餐 | 食物/菜名：________ 数量：____g/ml/份 | ________ | ____ kcal P____g C____g F____g | □无加餐 / ________

晚餐 | 菜名：________ 主食：____g（□生/□熟/□干） 主蛋白：____g（□生/□熟） 蔬菜：____g（□生/□熟） 油：____g | ________ | ____ kcal P____g C____g F____g | ________


## Table


餐次 | 菜品与主要食材（必须写克重/份数+重量口径） | 烹饪方式/简要做法 | 估算营养 | 同类替换/备注

早餐 | 菜名：________ 主食：____g（□生/□熟/□干） 蛋白/奶豆：____g/ml/个 水果/蔬菜：____g | ________ | ____ kcal P____g C____g F____g | ________

午餐 | 菜名：________ 主食：____g（□生/□熟/□干） 主蛋白：____g（□生/□熟） 蔬菜：____g（□生/□熟） 油：____g | ________ | ____ kcal P____g C____g F____g | ________

加餐 | 食物/菜名：________ 数量：____g/ml/份 | ________ | ____ kcal P____g C____g F____g | □无加餐 / ________

晚餐 | 菜名：________ 主食：____g（□生/□熟/□干） 主蛋白：____g（□生/□熟） 蔬菜：____g（□生/□熟） 油：____g | ________ | ____ kcal P____g C____g F____g | ________


## Table


7天完整性 | □ 7天均有早餐/午餐/晚餐；加餐按计划需要显示

正餐重量 | □ 主食/蛋白/蔬菜/油（如适用）均有明确重量或份数

重量口径 | □ 生重/熟重/干重/可食部已明确

营养估算 | □ 每餐有kcal/P/C/F，全天与目标在允许误差内

替换规则 | □ 替换后重新估算全天营养；过敏/不耐受已过滤

疾病/肝弹性 | □ 对应修饰规则已应用

强化减脂 | □ 仅在资格通过且ACTIVE参数下使用

安全结果 | □ VAL营养相关校验全部通过


## Table


说明：运动不是用于“追赶体重数字”。系统应基于A–F、Q56、6MWT/功能、疼痛/平衡、手术窗口和安全等级，从已审核动作库按ID调用；强化减脂也不得无限增加有氧。


## Table


星期 | 有氧 | 抗阻/功能 | 柔韧/整理 | 当日总要求

周一 | ID/名称：____ ____min；RPE____ | ID：____ / ____ ____次×____组 | ID：____ ____秒×____ | □训练日 □恢复日

周二 | ID/名称：____ ____min；RPE____ | ID：____ / ____ ____次×____组 | ID：____ ____秒×____ | □训练日 □恢复日

周三 | ID/名称：____ ____min；RPE____ | ID：____ / ____ ____次×____组 | ID：____ ____秒×____ | □训练日 □恢复日

周四 | ID/名称：____ ____min；RPE____ | ID：____ / ____ ____次×____组 | ID：____ ____秒×____ | □训练日 □恢复日

周五 | ID/名称：____ ____min；RPE____ | ID：____ / ____ ____次×____组 | ID：____ ____秒×____ | □训练日 □恢复日

周六 | ID/名称：____ ____min；RPE____ | ID：____ / ____ ____次×____组 | ID：____ ____秒×____ | □训练日 □恢复日

周日 | ID/名称：____ ____min；RPE____ | ID：____ / ____ ____次×____组 | ID：____ ____秒×____ | □训练日 □恢复日


## Table


动作ID / 名称 | ____ / ____________________

训练目的 | ____________________

准备姿势 | ____________________

动作步骤 | 1.____  2.____  3.____

剂量 | 时间/次数____；组数____；频率____

强度 | RPE/BORG____；其他ACTIVE强度指标____

组间/动作间休息 | ____

注意事项 | ____________________

停止条件 | ____________________

替代动作 | ID____ / 名称____；替代理由____


## Table


动作ID | 动作名称 | 本周选择 | 剂量 | 选择/不选择理由 | 停止/替代

P01 | 缩唇呼吸 | □是 □否 | ____min/次；____次/日 | ____ | ____

P02 | 腹式呼吸 | □是 □否 | ____min/次；____次/日 | ____ | ____

P03 | 胸廓扩张 | □是 □否 | ____次×____组/日 | ____ | ____

P04 | 呼吸-上肢协同 | □是 □否 | ____次×____组/日 | ____ | ____

P05 | 有效咳嗽 | □是 □否 | ____循环/按需 | ____ | ____

P06 | OPEP排痰 | □是 □否 | 按设备/医护处方 | ____ | ____


## Table


星期 | 计划动作 | 剂量 | 当日备注

周一 | P__ + P__ | ________________ | ________________

周二 | P__ + P__ | ________________ | ________________

周三 | P__ + P__ | ________________ | ________________

周四 | P__ + P__ | ________________ | ________________

周五 | P__ + P__ | ________________ | ________________

周六 | P__ + P__ | ________________ | ________________

周日 | P__ + P__ | ________________ | ________________


## Table


说明：R=必填；CR=条件必填；O=选填/自动采集；D=系统派生。患者端只要求填写真正影响安全、完成率和下一周调整的数据；设备能够自动读取的字段不得要求患者重复手填。


## Table


数据模块 | 字段/患者问题 | 等级 | 前端规则/用途

体重/体成分 | 测量日期时间、体重kg | R | 提交体重记录必须有；时间自动记录。

体重/体成分 | 是否晨起排空后、未进食饮水/是否同一设备 | CR | 手动录入或周趋势质量校验时显示。

体重/体成分 | 体脂率% | CR | 设备/截图可提供时采集；设备不支持不阻断。

体重/体成分 | 脂肪量、肌肉量、骨骼肌量、水分率/量 | O（强烈建议自动采集） | 用于解释体重变化、保肌和水分波动；不要求逐项手填。

体重/体成分 | 蛋白质率/蛋白质量、BMR、内脏脂肪等 | O | 辅助趋势/能量校验，不代表膳食蛋白完成度。

饮食-每餐 | 这餐完成多少？100/75/50/25%/几乎没吃 | R | 计算meal_completion。

饮食-每餐 | 是否替换计划食物？是否有额外摄入？ | R | 是/否；选择“是”再展开。

饮食-每餐 | 替换内容、额外摄入内容 | CR | 允许快捷选择/文字/照片。

饮食-每餐 | 主蛋白食物完成比例 | CR | 该餐有明确蛋白任务时显示。

饮食-每餐 | 餐食照片 | O | 辅助核对食物/份量，不作为唯一热量真值。

饮食-每日 | 食欲0–10、是否有影响进食症状 | R | 每日一次；有症状再展开。

运动 | 完成/部分/未完成、症状有/无 | R | 每个运动plan_task必须记录。

运动 | 实际分钟、RPE/BORG | CR | 完成/部分时要求。

运动 | 实际组数/次数 | CR | 抗阻/次数型任务才显示。

运动 | 未完成/部分完成原因 | CR | 状态不是全部完成时要求。

肺预康复 | 完成/部分/未完成、症状有/无 | R | 每个肺预康复任务必须记录。

肺预康复 | 实际分钟/组数/次数 | CR | 对应任务有剂量时显示。

肺预康复 | 痰液/排痰困难 | CR | P05或痰相关任务时显示。

每日恢复 | 疲劳0–10、气促0–10、疼痛0–10、活动能力更好/相同/更差 | R | 用于周复评和安全趋势。

每日安全 | 胸痛/明显加重气促/晕厥或近晕厥/咯血/意识异常等 | R | 默认无；任一异常立即走安全流程。

每周围度 | 腰围 | CR | A/B/C或Q56含腰围/减脂目标时每周1次。

每周围度 | 小腿围 | CR/O | C/D/E或医护指定时条件必填；其他选填。

功能 | 6MWT/握力/坐站等 | O/医护指定CR | 基线或阶段复评，不要求机械每日/每周。

固定治疗 | 完成/未完成 | CR | 存在医护确认治疗任务时要求；未完成原因条件必填。


## Table


时间点 | 患者看到的问题 | 逻辑

每餐后 | 这餐大约吃了计划的多少？100% / 75% / 50% / 25% / 几乎没吃 | R

每餐后 | 有没有换计划食物？除计划外有没有额外吃/喝？ | R；是→展开

含蛋白任务的餐 | 主蛋白食物大约吃了多少？100/75/50/25%/几乎没吃 | CR

每日晚间 | 今天总体食欲怎么样？0–10分；是否有早饱/恶心/呕吐/腹胀/腹泻/便秘/吞咽或咀嚼困难？ | R

运动任务后 | 完成了吗？全部/部分/未完成；实际分钟；RPE 0–10 | R+CR

运动任务后 | 有没有胸痛、明显气促、头晕、心悸、明显疼痛等？ | R；有→立即安全分流

肺预康复后 | 完成了吗？全部/部分/未完成；实际分钟/次数；有无不适 | R+CR

每日恢复 | 疲劳0–10；气促0–10；疼痛0–10；活动能力更好/差不多/更差 | R

每日安全快筛 | 今天是否出现胸痛/胸闷明显加重、明显加重气促、晕厥/近晕厥、咯血、意识异常？ | R；有→不等待周复评


## Table


层级 | 触发示例 | 系统处理

绿色 | 无明显新发/加重症状；执行和指标总体稳定；数据可评价 | 继续当前计划，常规记录和周复评

黄色 | 连续摄入不足、减重伴肌肉/功能下降、轻中度症状影响执行、指标持续偏离目标、肝弹性/肝功能需复核等 | 冻结与异常直接相关的自动进阶；提示医护复核；其他安全模块可继续

红色 | 明显/进行性胸痛胸闷、明显加重呼吸困难、晕厥/近晕厥、咯血、意识异常、严重过敏/其他急症 | 立即停止相关任务和自动调整；高优先级转医护/紧急流程；红色仅医护可解除


## Table


说明：周复评顺序固定：安全 → 数据充分度 → 执行率/障碍 → 生理反应（体重/脂肪/肌肉/水分/腰围/功能） → A–F目标 → Q56轨迹 → 下一周草稿。任何规则命中只生成新草稿，不能直接覆盖已发布方案。


## Table


评价维度 | 本周结果 | 是否可评价 | 下周动作

数据完整度 | 体重____天；体成分____天；饮食____天；任务记录____% | □高 □中 □低 | 数据不足→先补数据

核心任务完成率 | ____% | □充分 □不足 | 不足→BARRIER_FIRST

7日平均体重趋势 | ________________ | □可靠 □受水分影响 | ________________

体脂/脂肪量趋势 | ________________ | □可靠 □不充分 | ________________

肌肉/骨骼肌趋势 | ________________ | □稳定 □下降 □上升 | 下降→PRESERVE_MUSCLE

水分趋势 | ________________ | □稳定 □波动明显 | 解释体重，避免误判

腰围趋势 | ________________ | □有利 □稳定 □不利 | ________________

功能/运动耐受 | ________________ | □稳定/改善 □下降 | 下降→冻结进阶

摄入/食欲/症状 | ________________ | □正常 □不足/异常 | 不足→NUTRITION_RECOVERY

Q56目标轨迹 | 目标：____；观察：____ | □符合 □偏离 □无Q56目标 | 只用于比较，不倒算kcal


## Table


周结论 | □ MAINTAIN  □ BARRIER_FIRST  □ DATA_INSUFFICIENT  □ PRESERVE_MUSCLE  □ NUTRITION_RECOVERY  □ INTENSIFY_CANDIDATE  □ DEINTENSIFY  □ SAFETY_REVIEW

能量调整 | □不变  □候选+5个百分点  □候选-5个百分点  □冻结减能/强化  □人工决定

饮食调整 | ________________

运动调整 | ________________

肺预康复调整 | ________________

计划改变变量数 | 本次只改变____项（原则1–3项）

第二周草稿 | □已生成待审核  □暂不生成/先补数据  □仅人工复核

审核责任 | ________________

 | 


## Table


类型 | 项目 | 处理原则

缺失数据 | ________________ | 不等于正常；安全允许时可继续保守方案

不确定数据 | ________________ | 保留“不确定/需复核”，不得伪精确分级

Q56目标冲突 | ________________ | 安全/A–F保护优先；降阶或转医护复核

MDT待确认参数 | ________________ | 未ACTIVE前不得进入精确处方任务

专科复核 | ________________ | 按对应专科/MDT流程处理


## Table


plan_version | V____

生成来源 | □ RULE_BASED_GENERATOR  □ AI_GENERATOR  □ 人工草稿

生成时间 | ____年__月__日 __:__

审核状态 | □ AI_GENERATED_PENDING_REVIEW  □ IN_REVIEW  □ APPROVED_PENDING_PUBLISH  □ PUBLISHED

审核日期 | ____年__月__日

审核人员/团队 | ________________

发布日期 | ____年__月__日

知识库版本 | 营养V2.0 / 食谱V2.0 / 运动V2.0 / 肺预康复V2.0 / 安全V2.0 / 其他____

MDT配置版本 | ________________

Safety Validator | □ PASS  □ FAIL（原因：________）

上一版本 | V____；变更摘要：________________


## Table


management_period stage_goals   - goal_source: Q56 | SYSTEM_DEFAULT   - primary_goal / secondary_goals / target_trajectory diet_plan   - energy_estimation / prescribed_energy / macros / meal_distribution   - seven_day_meals[] (dish, ingredients, gram_weight, weight_basis, cooking, kcal, protein, carbohydrate, fat, replacements) exercise_plan   - weekly_schedule[] / action_cards[] (item_id, purpose, position, steps, dose, intensity, rest, precautions, stop_rule, alternative) pulmonary_prehab_plan   - selected_items[] P01–P06 / weekly_schedule / dose / rationale / stop_rule / alternative monitoring_plan   - R / CR / O fields and patient_record mapping safety_rules clinician_notes missing_data mdt_pending_items weekly_review   - data_confidence / adherence / physiologic_trends / weekly_outcome / next_week_changes


## Table


目标层 | Q56来源/默认来源明确；目标与安全冲突已处理

能量 | REE/TEE来源、模式、处方能量和状态可追溯

食谱 | 7天完整；每个正餐克重+重量口径+营养+替换完整

运动 | 每个选中动作有ID、步骤、剂量、强度、休息、停止与替代

肺预康复 | P01–P06选择理由、剂量、停止与替代完整；P06资格满足

记录 | R/CR/O逻辑可执行，患者无需重复手填设备数据

安全 | 绿黄红、Q50、强化准入/退出、红色人工解除已校验

周复评 | 已定义数据充分度、执行率、趋势与下一周动作

版本 | 知识库/配置/生成器/审核/发布版本完整

发布门槛 | Safety Validator=PASS + 医护审核通过

 | 