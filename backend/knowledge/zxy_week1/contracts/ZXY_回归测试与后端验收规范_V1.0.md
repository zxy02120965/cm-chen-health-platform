# ZXY 回归测试与后端验收规范

版本：V1.0  
日期：2026-09-24  
用途：Codex / 后端开发 / 回归测试 / 发布前验收  
性质：**工程测试与验收规范，不属于临床知识库，不面向患者展示，不并入 01/02/03。**

---

## 1. 目的

本规范用于把已经稳定的临床规则转成**可重复、可自动化、可判定 PASS/FAIL 的后端测试合同**。

它解决的不是“模型能不能写出一份看起来合理的方案”，而是以下问题：

1. 相同患者输入是否稳定得到相同的表型与能量状态；
2. FOOD 是否始终落到合法的最终执行克重，而不是算法中间量；
3. 患者端、Root Trace、Ingredient Master 是否三重一致；
4. `diet_plan_trace`、`exercise_plan_trace`、`pulmonary_rehab_trace` 是否真实存在；
5. `artifact_manifest` 是否由真实 Root Trace 派生，而不是 AI 自报；
6. 临床安全、医护审核与发布阻断是否稳定执行；
7. A–F 回归病例是否在代码更新后保持预期状态。

---

## 2. 当前冻结基线

本规范默认以下文件为当前临床/生成规则基线：

- `01_ZXY_MASTER_AGENT_KNOWLEDGE_BASE_FINAL_V4_2_5.md`
- `02_ZXY_NUTRITION_COMPONENT_LIBRARY_FINAL_V4_2_4.md`
- `03_ZXY_EXERCISE_PULMONARY_REHAB_LIBRARY_FINAL_V4_2_1.md`
- `ZXY_基础食材层_Ingredient_Master_MDT定稿版_V1.2.xlsx`
- `ZXY_FOOD_49组件_份量执行化_MDT定稿版_V1.2.xlsx`

规则优先级：

```text
临床安全 / BLOCK
> ACTIVE MDT 配置
> ACTIVE Ingredient Master / FOOD / Exercise / Pulmonary Rehab
> 01 / 02 / 03 当前冻结版本
> AI 生成与自由编排
```

### 2.1 本规范不是新的临床规则

若回归测试失败：

```text
优先判断：
1. 后端实现错误？
2. serializer / validator 错误？
3. AI 生成层没有服从现有规则？

只有确认现有 01/02/03 缺少规则时，才修改临床知识库。
```

不得因为一次模型输出波动，就继续向 01/02 重复添加同义规则。

---

## 3. 正式系统分层

生产环境应分成两层。

### 3.1 患者 / 医护可见层

包括：

- 患者画像；
- 综合评估；
- 本周目标；
- 能量与营养依据；
- Day1–Day7 饮食；
- Day1–Day7 运动；
- Day1–Day7 肺预康复；
- 监测；
- 安全规则；
- 周复评；
- 医护审核与发布。

FOOD 患者显示必须是：

```text
菜名 + 最终执行食材克重/容量/个数 + 简单做法
```

### 3.2 后台机器层

必须保存：

```text
energy_state
diet_plan_trace
exercise_plan_trace
pulmonary_rehab_trace
food_execution_grid_validation
energy_state_validation
schedule_consistency_validation
physical_root_trace_validation
patient_view_root_trace_consistency
clinical_safety_validation
publication_validation
artifact_manifest
```

这些对象原则上**不直接展示给患者**。

---

## 4. 能量状态机：唯一合法映射

后端必须由确定性状态机决定能量模式，不允许由 LLM 自由命名。

### 4.1 ACTIVE

只有当正式能量来源与所需参数均已 ACTIVE，并满足临床发布条件时：

```yaml
energy_target:
  status: ACTIVE

diet_generation_mode: EXACT_ACTIVE
```

### 4.2 PROVISIONAL

若：

```text
存在可用 P3 BIA/BMR
AND 存在可追踪的 candidate PAL
AND 存在 underlying A–E 的 candidate energy direction
AND 不存在真实 energy blocker
```

则：

```yaml
energy_target:
  status: PROVISIONAL
  prescribed_energy_target_kcal: null
  provisional_energy_target_kcal: <single_point_candidate>

diet_generation_mode: EXACT_PROVISIONAL_REVIEW
publication_blocked: true
```

### 4.3 UNAVAILABLE

若存在以下情况之一：

- 没有可信单点能量候选；
- PAL 无法形成；
- 临床资料严重冲突；
- 明显低摄入 / 持续体重下降且再喂养风险未澄清；
- 其他明确临床 blocker。

则：

```yaml
energy_target:
  status: UNAVAILABLE
  prescribed_energy_target_kcal: null
  provisional_energy_target_kcal: null

diet_generation_mode: STRUCTURE_ONLY
publication_blocked: true
```

### 4.4 非法状态组合

以下必须直接 FAIL：

```text
PROVISIONAL + EXACT_ACTIVE
PROVISIONAL + STRUCTURE_ONLY
UNAVAILABLE + EXACT_PROVISIONAL_REVIEW
UNAVAILABLE + EXACT_ACTIVE
ACTIVE + STRUCTURE_ONLY
```

---

## 5. A–F 固定回归病例期望值

以下不是所有真实患者的固定处方，而是**回归测试 fixture**。

| Case | 主表型 | F overlay | 安全色 | 能量预期 | 模式预期 |
|---|---|---|---|---|---|
| SYN-A01 | A | none | GREEN | BMR 1360 × PAL 1.35 × 0.85 ≈ 1561 kcal/d | `PROVISIONAL + EXACT_PROVISIONAL_REVIEW` |
| SYN-B01 | B | none | YELLOW | BMR 1770 × PAL 1.30 × 0.80 ≈ 1840 kcal/d | `PROVISIONAL + EXACT_PROVISIONAL_REVIEW` |
| SYN-C01 | C | none | YELLOW | BMR 1280 × PAL 1.35 × 1.00 ≈ 1728 kcal/d | `PROVISIONAL + EXACT_PROVISIONAL_REVIEW` |
| SYN-D01 | D | none | YELLOW | BMR 1120 × PAL 1.35 × 1.10 ≈ 1660 kcal/d | `PROVISIONAL + EXACT_PROVISIONAL_REVIEW` |
| SYN-E01 | E | none | YELLOW | 不形成精确单点目标 | `UNAVAILABLE + STRUCTURE_ONLY` |
| SYN-F01 | B | F | YELLOW | BMR 1390 × PAL 1.30 × 0.80 ≈ 1446 kcal/d | `PROVISIONAL + EXACT_PROVISIONAL_REVIEW` |

### 5.1 F 的特殊断言

F 只能改变：

- 任务数量；
- 菜谱复杂度；
- 支持方式；
- 分段方式；
- 进阶速度；
- 执行负担。

F 不得删除 underlying A–E 的能量方向。

SYN-F01 必须：

```yaml
display_phenotype: F
primary_nutrition_phenotype: B
complexity_overlay: F

energy_target:
  status: PROVISIONAL
  provisional_energy_target_kcal: 1446

diet_generation_mode: EXACT_PROVISIONAL_REVIEW
```

### 5.2 E 的特殊断言

SYN-E01 当前 fixture 包括：

```text
近期非意愿体重下降
进食量约下降 50%
明显食欲下降
早饱
恶心
再喂养风险未澄清
黄色安全状态
```

因此必须：

```yaml
energy_target:
  status: UNAVAILABLE

diet_generation_mode: STRUCTURE_ONLY
```

禁止：

```text
自动使用 P4 生成 1800 kcal/d 等单点目标
自动生成正式蛋白处方
自动转 EXACT_PROVISIONAL_REVIEW
```

---

## 6. FOOD Materializer 硬合同

### 6.1 两种份量必须严格分开

```yaml
algorithmic_amount:
  patient_visible: false

executable_amount:
  patient_visible: true
```

患者端永远只能显示 `executable_amount`。

### 6.2 STANDARD_COMPONENT

后端必须：

```text
component_id
+ selected allowed scale
→ 读取 component execution mapping
→ 获得最终 executable ingredients
```

禁止：

```text
base_amount × scale
→ 直接显示给患者
```

### 6.3 AI_GENERATED_DISH

每一个 Ingredient 必须：

```text
在 candidate_min / candidate_max 内
AND 符合 candidate_step
OR 符合 discrete/package rule
```

### 6.4 必须 FAIL 的示例

```text
植物油 step=1g，却输出 1.5g / 2.5g
冬瓜 step=10g，却输出 125g / 188g
鸡蛋应按整枚执行，却输出 63g 作为 1.25× 数学结果
患者端 executable_amount=1.25, unit=standard portion
患者端 executable_amount=0.5, unit=standard portion
```

### 6.5 患者端不得出现工程份量

以下均不能作为患者主要份量：

```text
0.5份
0.75份
1份
1.25份
1.5份
standard portion
component_portion_scale
```

后台 audit 中允许保留：

```yaml
component_id: C001
component_portion_scale: 1.0
```

但必须同时有合法最终克重。

### 6.6 单位一致性

执行单位必须来自 Ingredient Master。

禁止未经批准自动转换：

```text
g ↔ ml
```

尤其是奶、酸奶、豆浆等产品型食材，必须依照项目确认的产品/标签口径。

---

## 7. 患者 FOOD 最小对象合同

每一个患者可见 food item 至少包含：

```yaml
dish_name: 非空
ingredients:
  - ingredient_id: ING...
    ingredient_name: ...
    executable_amount: 数值
    execution_unit: g|ml|个
    weight_basis: ...
simple_method: 非空
```

后台 audit 另外保存：

```yaml
food_item_type: STANDARD_COMPONENT|AI_GENERATED_DISH
component_id: ...
generated_dish_id: ...
component_portion_scale: ...
nutrition_status: ...
materialization_source: ...
```

### 7.1 STANDARD_COMPONENT

还必须：

```yaml
canonical_component_match: true
```

若为了执行网格而实质改变核心配方比例：

```text
不得继续冒充 STANDARD_COMPONENT
→ 转 AI_GENERATED_DISH
```

---

## 8. Nutrition Source 状态

### 8.1 ACTIVE_FOR_EXACT

只有 ACTIVE_FOR_EXACT ingredient / ACTIVE_RECALCULATED component 才能参与正式精确营养闭合。

### 8.2 PENDING_MDT / NEEDS_SOURCE_RECALC

允许：

```text
出现在医护审核草稿
```

但必须：

```text
publication_blocked = true
不得贡献正式 exact kcal/P/C/F closure
```

### 8.3 STRUCTURE_ONLY

允许：

```text
planned_nutrition = null
```

但不允许：

```text
非法克重
非法 step
非法单位
缺失菜名
缺失做法
缺失 root trace
```

---

## 9. 三个 Root Trace 的最低合同

### 9.1 diet_plan_trace

必须真实存在：

```yaml
diet_plan_trace:
  days:
    Day1:
    Day2:
    Day3:
    Day4:
    Day5:
    Day6:
    Day7:
```

每个实际患者 food item 必须拥有：

```text
dish_name
ingredients
executable_amount / execution_unit
simple_method
food_item_type
component_id 或 generated_dish_id
nutrition_status
```

不得使用：

```text
参见上表
materialized_above=true
food_root_days: [菜名列表]
summary only
```

代替真实 item。

### 9.2 exercise_plan_trace

必须真实存在：

```yaml
exercise_plan_trace:
  daily_schedule:
    Day1:
    ...
    Day7:
```

每个 session/action 至少：

```text
session_role
action_id
patient_action_name
dose
dose_status / status
stop_conditions
```

周频次必须从 Day1–Day7 实际 schedule **反算**，不得只声明目标次数。

### 9.3 pulmonary_rehab_trace

必须真实存在：

```yaml
pulmonary_rehab_trace:
  daily_schedule:
    Day1:
    ...
    Day7:
```

每个 action 至少：

```text
action_id
patient_action_name
dose
status
stop_conditions
```

同时必须记录：

```text
P05 使用原因或不使用原因
P06 gate 结果
minimum sufficient set
```

---

## 10. Root 物理扫描与 FULL 规则

只有同时满足：

```text
root object physically exists
AND Day1–Day7 physically exist
AND each required item/session physically exists
AND root is not summary-only
```

才能：

```yaml
materialization: FULL
```

### 10.1 physical_root_trace_validation

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

---

## 11. 三重一致性 Validator

必须逐项比较：

```text
Patient View
↕
Root Trace
↕
Ingredient Master / Component Execution Mapping
```

### 11.1 food_three_way_consistency_validation

```yaml
food_three_way_consistency_validation:
  patient_view_recipe_complete: true|false
  root_trace_physically_complete: true|false
  patient_view_matches_root_trace: true|false
  root_trace_matches_execution_grid: true|false
  patient_view_matches_execution_grid: true|false
  status: PASS|FAIL
```

任何一项 false：

```text
FOOD content_validation = FAIL
publication_blocked = true
```

---

## 12. Energy State Validator

建议后端实现：

```python
def derive_energy_state(case):
    if case.has_active_energy_source_and_required_active_params:
        return "ACTIVE", "EXACT_ACTIVE"

    if (
        case.has_valid_p3_bia_bmr
        and case.has_candidate_pal
        and case.has_underlying_candidate_energy_direction
        and not case.has_true_energy_blocker
    ):
        return "PROVISIONAL", "EXACT_PROVISIONAL_REVIEW"

    return "UNAVAILABLE", "STRUCTURE_ONLY"
```

并额外硬编码回归断言：

```text
C01 != STRUCTURE_ONLY
D01 != EXACT_ACTIVE
E01 != EXACT_PROVISIONAL_REVIEW
F01 != STRUCTURE_ONLY
```

---

## 13. FOOD Validator

建议后端逐 item 运行：

```python
for item in patient_food_items:
    assert item.dish_name
    assert item.simple_method
    assert len(item.ingredients) > 0

    for ing in item.ingredients:
        assert ing.executable_amount is not None
        assert ing.execution_unit in allowed_units
        assert within_min_max(ing)
        assert matches_step_or_discrete_rule(ing)

    assert no_patient_visible_component_share(item)
```

STANDARD_COMPONENT 再加：

```python
assert component_scale_is_allowed(item.component_id, item.component_scale)
assert item.ingredients == execution_mapping(item.component_id, item.component_scale)
```

---

## 14. Exercise Validator

至少检查：

```text
所有 action_id 均来自允许动作库
session_role 合法
每日 schedule 完整
周正式有氧天数按日程反算
周抗阻天数按日程反算
同日多个正式有氧片段只计 1 个正式有氧日
FUNCTIONAL_ACTIVITY 不得计为 FORMAL_AEROBIC
RECOVERY 不得计为 FORMAL_AEROBIC
黄色状态不得自动进阶
停止条件存在
```

---

## 15. Pulmonary Rehab Validator

至少检查：

```text
所有 action_id ∈ P01–P06
P05 无痰时不得机械高频安排
P06 必须同时满足：
  airway clearance need
  device available
  clinician order/guidance
minimum sufficient set
Day1–Day7 materialized
每个 action 有 dose/status/stop conditions
```

---

## 16. Artifact Manifest 生成顺序

必须：

```text
1. 生成 Patient View
2. 生成 diet_plan_trace
3. 生成 exercise_plan_trace
4. 生成 pulmonary_rehab_trace
5. 扫描三个真实 root
6. 跑 execution / consistency / schedule / safety validators
7. 最后生成 artifact_manifest
```

禁止：

```text
先生成 artifact_manifest:
  materialization: FULL
再假设 root 存在
```

### 16.1 manifest 必须是派生对象

```yaml
artifact_manifest:
  derived_only_from:
    - diet_plan_trace
    - exercise_plan_trace
    - pulmonary_rehab_trace
```

---

## 17. Publication Gate

只有以下全部满足才可进入 READY_TO_PUBLISH / PUBLISHED：

```text
最新 plan version
医护 APPROVED
validator PASS
安全允许
营养校验通过
运动校验通过
肺康复校验通过
无阻断缺失
publication_blocked = false
```

历史 PUBLISHED 不覆盖。

### 17.1 当前 A–F fixture

当前回归测试默认：

```text
全部是 AI_GENERATED_PENDING_REVIEW
不是正式处方
不应直接 PUBLISHED
```

所以即使 machine contract PASS：

```text
publication_validation 仍可 BLOCKED / CLINICIAN_REVIEW_REQUIRED
```

---

## 18. Known Regression Locks

以下是当前已发现并必须锁死的历史回归。

### 18.1 C01

错误：

```yaml
energy_state: PROVISIONAL
food_generation_mode: STRUCTURE_ONLY_REVIEW
```

正确：

```yaml
energy_target.status: PROVISIONAL
diet_generation_mode: EXACT_PROVISIONAL_REVIEW
```

### 18.2 D01

错误：

```yaml
diet_generation_mode: EXACT_ACTIVE
```

正确：

```yaml
energy_target.status: PROVISIONAL
diet_generation_mode: EXACT_PROVISIONAL_REVIEW
publication_blocked: true
```

### 18.3 E01

错误：

```text
自动使用 P4 形成 1800 kcal/d
自动形成 78g/d 蛋白目标
PROVISIONAL_REVIEW
```

正确：

```yaml
energy_target.status: UNAVAILABLE
diet_generation_mode: STRUCTURE_ONLY
publication_blocked: true
```

同时必须防止：

```text
0.5 / 0.75 / 1.25 standard portion
植物油 1.5g / 2.5g
鸡蛋 63g
冬瓜 188g
```

### 18.4 F01

错误：

```text
B+F
→ 因配置未 ACTIVE
→ STRUCTURE_ONLY
```

正确：

```text
B+F
→ valid P3 + candidate PAL + B candidate ratio
→ PROVISIONAL + EXACT_PROVISIONAL_REVIEW
```

---

## 19. A–F 自动化测试建议

建议建立固定 fixtures：

```text
tests/fixtures/SYN-A01.json
tests/fixtures/SYN-B01.json
tests/fixtures/SYN-C01.json
tests/fixtures/SYN-D01.json
tests/fixtures/SYN-E01.json
tests/fixtures/SYN-F01.json
```

### 19.1 每个 fixture 至少断言

```python
assert phenotype
assert complexity_overlay
assert safety_level
assert energy_status
assert diet_generation_mode
assert publication_blocked

assert patient_food_contract_pass
assert execution_grid_pass
assert no_component_share_leak

assert diet_root_pass
assert exercise_root_pass
assert pulmonary_root_pass

assert patient_root_consistency_pass
assert manifest_is_derived_after_roots
```

### 19.2 数值建议使用容差

回归测试能量值可允许：

```text
± 1–5 kcal
```

用于处理四舍五入，不允许状态改变。

---

## 20. Hard Fail 与 Review 的区别

### Hard FAIL

以下直接 FAIL：

- 非法 energy status/mode 组合；
- E01 被自动生成精确目标；
- F01 被错误降成 STRUCTURE_ONLY；
- 患者端出现 component share；
- executable amount 不符合 min/max/step；
- STANDARD_COMPONENT 与 canonical execution mapping 不一致；
- 三个 root 任一缺失；
- root 只有 summary；
- manifest 早于 root；
- Patient View 与 root 不一致；
- P06 条件不满足却被安排；
- 红色安全信号仍自动继续任务。

### PASS_WITH_REVIEW

以下通常是审核项，不一定是机器 FAIL：

- 能量目标是 PROVISIONAL；
- 蛋白 weight_basis 待 MDT；
- 运动剂量待 ACTIVE；
- 肺康复剂量待 ACTIVE；
- 黄色安全状态；
- pending nutrition source 仅用于审核草稿且已正确阻断发布。

---

## 21. Closed-world 回归测试要求

回归模式必须：

```text
只使用：
患者 fixture
01
02
03
Ingredient Master
FOOD Component Library
```

不得：

```text
联网补充指南
自行引用外部文献
自行创建新的临床参数
自行修改患者事实
自行引入新的动作或食材
```

生产环境需要外部指南更新时，另走知识库更新流程。

---

## 22. 测试模式与生产模式分离

### REGRESSION_TEST

允许输出：

```text
患者/医护方案
+ 完整三个 Root Trace
+ Validators
+ artifact_manifest
```

用于工程验收。

### PRODUCTION

后台仍生成并保存完整结构化对象，但 UI 默认只展示：

```text
患者/医护可读方案
```

不把大段 YAML Root Trace 展示给患者。

---

## 23. 与医生端 11 模块的关系

本规范不改变医生端固定 11 模块：

1. 患者关键画像与当前管理状态
2. 综合评估结果
3. 本周管理目标
4. 能量与营养依据
5. 第一周饮食方案
6. 第一周运动方案
7. 第一周肺预康复
8. 监测与记录
9. 安全规则 / 暂停与升级条件
10. 第7天周复评 / 下一周计划
11. 医护审核与发布

Root Trace 与 Validator 由后台支撑这些模块，不新增患者/医生顶层模块。

---

## 24. 当前范围边界

本阶段继续保持：

```text
不新增饮水量专项评估模块
不新增排尿模块
不新增排便模块
```

已有通用安全性补液/摄入提醒可保留，但不扩展成新的方案生成系统。

---

## 25. Definition of Done

当以下条件全部满足时，可认为当前第一周方案生成链达到工程冻结条件：

```yaml
definition_of_done:
  A01: PASS
  B01: PASS
  C01: PASS
  D01: PASS
  E01: PASS
  F01: PASS

  energy_state_machine: PASS
  food_materializer: PASS
  food_execution_grid_validator: PASS
  diet_trace_serializer: PASS
  exercise_trace_serializer: PASS
  pulmonary_trace_serializer: PASS
  three_way_consistency_validator: PASS
  safety_validator: PASS
  publication_gate: PASS

  no_known_regression_lock_failure: true
```

此时：

```text
01 V4.2.5
02 V4.2.4
03 V4.2.1
```

可继续作为当前冻结临床规则版本。

后续若出现失败，应优先修复：

```text
代码 / serializer / materializer / validator / state engine
```

而不是默认继续加厚 01/02。

---

## 26. 给 Codex 的实现顺序

推荐：

```text
Step 1  实现 energy_state_engine
Step 2  实现 food_materializer
Step 3  实现 diet_plan_trace serializer
Step 4  实现 exercise_plan_trace serializer
Step 5  实现 pulmonary_rehab_trace serializer
Step 6  实现 execution grid validator
Step 7  实现 Patient View ↔ Root ↔ Ingredient Master consistency validator
Step 8  实现 artifact_manifest 派生
Step 9  实现 publication gate
Step 10 接入 A–F fixtures，跑自动回归
Step 11 再接医生端固定 11 模块和患者端视图
```

不要先修改患者 UI 来绕过后端状态问题。

---

## 27. 最终原则

> **AI 负责个体化编排；确定性代码负责状态、克重执行化、Root Trace、Validator 与发布门控。**

> **临床知识库说明“应该怎么做”；后端测试合同确保系统“每次都这样做”。**
