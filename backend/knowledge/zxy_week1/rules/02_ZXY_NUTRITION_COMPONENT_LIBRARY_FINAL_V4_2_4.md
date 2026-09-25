# 02_ZXY_NUTRITION_COMPONENT_LIBRARY_FINAL

本文件整合 ZXY FOOD 标准组件库、Ingredient Master 基础食材层、AI 约束式动态食谱生成、患者可执行菜谱、营养计算追踪、替换逻辑、D/E 营养恢复策略与发布审计。

版本：FINAL V4.2.4｜最终执行量网格 + Root Trace物理化硬合同｜2026-09-24

---

# FINAL FOOD GENERATION & TRACEABILITY CONTRACT V4.2.4｜最终执行量网格 + Root Trace物理化硬合同（2026-09-24）

> **版本定位**：V4.2.4 在 V4.2.3“菜名 + 克重 + 简单做法”的基础上继续收口两件事：
>
> 1. 患者看到的克重必须是经过 Ingredient Master `min/max/step/discrete/package rule` 执行化后的**最终执行量**，不能是 `base × scale` 的数学中间量；
> 2. `FULL FOOD trace` 必须在最终文件中真实写出 `diet_plan_trace` Day1–Day7 根对象，不能只写一个 `food_trace: materialization: FULL` 摘要。
>
> 本补丁不改变 Ingredient Master V1.2、49个 STANDARD_COMPONENT 的医学分类、营养来源状态或 D/E/F 临床方向。
>
> 执行优先级：`临床安全/BLOCK规则 > ACTIVE MDT配置 > ACTIVE Ingredient Master > 本V4.2.4 > V4.2.3 > V4.2.2 > 历史 FOOD 规则 > AI自由编排`。

---

## V4.2.4-FOOD-1｜algorithmic amount ≠ executable amount

统一术语：

```yaml
algorithmic_amount:
  meaning: 算法缩放后的数学中间量
  patient_visible: false

executable_amount:
  meaning: 经过 min/max/step/discrete/package rule 执行化后的最终患者量
  patient_visible: true
```

患者端和医护执行端只能显示 `executable_amount`。

---

## V4.2.4-FOOD-2｜STANDARD_COMPONENT 必须读取预计算 execution mapping

对于：

```yaml
food_item_type: STANDARD_COMPONENT
component_id: ...
component_portion_scale: ...
```

生成器不得自行重新计算：

```text
base ingredient amount × scale
```

作为患者最终克重。

必须直接读取：

```text
49组件 V1.2 中
component_id + allowed scale
→ 每种原料 final execution mapping
```

### 强制规则

```yaml
standard_component_materialization:
  selected_scale_in_allowed_component_scales: true
  mapped_ingredient_amounts_loaded: true
  patient_amounts_equal_mapped_executable_amounts: true
```

任一为 false：

```text
STANDARD_COMPONENT_MATERIALIZATION_FAIL
```

### 示例

若某组件 0.5× 的数学结果为：

```text
植物油 2.5 g
```

但 Ingredient Master：

```text
step = 1 g
```

且预计算执行映射为：

```text
植物油 3 g
```

则患者端和 root trace 都必须使用：

```text
3 g
```

不能继续显示 `2.5 g`。

---

## V4.2.4-FOOD-3｜AI_GENERATED_DISH 必须先落到执行网格

每一个 AI_GENERATED_DISH 原料必须满足：

```yaml
ingredient_execution_validation:
  ingredient_id: ING...
  candidate_min: ...
  candidate_max: ...
  candidate_step: ...
  algorithmic_amount: ...
  executable_amount: ...
  execution_rule_status: PASS|FAIL
```

### 连续克重类

若 step 为 `s`：

```text
executable_amount 必须落在项目批准的 step 网格
```

示例：

```text
植物油 step=1 g
2.5 g -> invalid

冬瓜 step=10 g
125 g -> invalid
```

生成器必须先执行化为合法候选量，再进入 patient-facing recipe。

### 离散/包装类

鸡蛋：

```text
只允许整枚对应的批准克重
```

牛奶/豆浆/酸奶等包装类：

```text
按批准包装/量具单位及步长
```

不得输出：

```text
0.75个鸡蛋
187.5 ml牛奶
```

除非 Ingredient Master/产品规则明确允许。

---

## V4.2.4-FOOD-4｜执行化函数只处理“候选”，不越过身份保护

执行化后如果仍然保持原标准菜身份和合理比例：

```text
STANDARD_COMPONENT
```

若为了满足网格需要实质改变：

- 核心食材比例；
- 核心食材集合；
- 菜品结构；

则：

```text
转 AI_GENERATED_DISH
```

不能为了保留原 component_id 而强行扭曲配方。

---

## V4.2.4-FOOD-5｜任何 execution materialization 后都触发营养重算语义

```yaml
portion_materialization_result:
  algorithmic_amounts_changed: true|false
  nutrition_recalculation_required: true|false
  nutrition_recalculation_status: COMPLETED|PENDING|NOT_APPLICABLE
```

### EXACT_ACTIVE

必须：

```text
recalculation COMPLETED
```

才能进入正式营养闭合。

### EXACT_PROVISIONAL_REVIEW

可在医护审核草稿中保留：

```text
PENDING
```

但不能把未重算值宣称为已经完成精确闭合。

### STRUCTURE_ONLY

允许：

```text
planned_nutrition = null
```

但患者量仍必须合法，且 trace 要保存 `recalculation_required` 状态。

---

## V4.2.4-FOOD-6｜patient recipe contract 更新

每一个患者可见 food item 的最终最低合同：

```yaml
patient_food_item:
  dish_name: ...
  ingredients:
    - ingredient_id: ING...
      ingredient_name: ...
      executable_amount: ...
      execution_unit: g|ml|个
      weight_basis: ...
  simple_method: ...
```

禁止使用：

```yaml
algorithmic_amount
portion_scale
component_id
```

作为患者主要份量表达。

这些只保留在 audit 层。

---

## V4.2.4-FOOD-7｜真实 `diet_plan_trace` 是 FULL 的唯一来源

最终 artifact 必须真实写出：

```yaml
diet_plan_trace:
  trace_schema_version: FOOD_TRACE_V4_2
  generation_context: ...
  days:
    Day1:
      meals:
        ...
    Day2:
      meals:
        ...
    Day3:
      meals:
        ...
    Day4:
      meals:
        ...
    Day5:
      meals:
        ...
    Day6:
      meals:
        ...
    Day7:
      meals:
        ...
```

### 每个 food item root 实体至少包含

STANDARD_COMPONENT：

```yaml
- dish_name: ...
  ingredients:
    - ingredient_id: ...
      executable_amount: ...
      execution_unit: ...
  simple_method: ...
  audit:
    food_item_type: STANDARD_COMPONENT
    component_id: ...
    component_portion_scale: ...
    materialization_source: COMPONENT_EXECUTION_MAPPING_V1_2
    nutrition_status: ACTIVE_RECALCULATED|NEEDS_SOURCE_RECALC|STRUCTURE_ONLY_...
```

AI_GENERATED_DISH：

```yaml
- dish_name: ...
  ingredients:
    - ingredient_id: ...
      executable_amount: ...
      execution_unit: ...
  simple_method: ...
  audit:
    food_item_type: AI_GENERATED_DISH
    generated_dish_id: ...
    nutrition_status: CALCULATED|NEEDS_RECALC|STRUCTURE_ONLY_...
```

---

## V4.2.4-FOOD-8｜`food_trace` summary 不能替代 root

以下只是摘要：

```yaml
food_trace:
  materialization: FULL
  days_present: 7
```

它本身**没有资格**证明 FULL。

只有实际 `diet_plan_trace.days.Day1...Day7` 物理存在并通过扫描后，才能派生：

```yaml
food_trace:
  materialization: FULL
```

顺序必须是：

```text
先写 root
→ 扫描 root
→ 再派生 summary/manifest
```

禁止：

```text
先宣称 FULL
→ 实际不写 root
```

---

## V4.2.4-FOOD-9｜Patient View ↔ Root Trace ↔ Ingredient Master 三重核对

新增：

```yaml
food_execution_trace_validation:
  all_patient_items_have_root_match: true|false
  all_root_items_have_patient_match: true|false
  all_patient_amounts_equal_root_amounts: true|false
  all_root_amounts_equal_final_execution_mapping_or_grid: true|false
  all_methods_match: true|false
  orphan_patient_items: []
  orphan_root_items: []
  invalid_execution_items: []
  status: PASS|FAIL
```

必须按最终 artifact 重新计算。

---

## V4.2.4-FOOD-10｜STRUCTURE_ONLY 的正确含义

STRUCTURE_ONLY：

```text
允许没有正式 kcal/P/C/F 全天闭合
```

但仍要求：

```text
菜名真实
原料真实
最终执行量合法
做法可执行
root trace真实
pending source状态真实
```

因此以下组合非法：

```text
STRUCTURE_ONLY
+ 植物油2.5g（step=1g）
+ content PASS
```

或：

```text
STRUCTURE_ONLY
+ 只有 food_trace summary
+ root不存在
+ materialization FULL
```

---

## V4.2.4-FOOD-11｜F overlay 与 FOOD 的关系

F overlay 可以：

- 复用较少餐型；
- 减少同时操作的菜品数量；
- 采用更简单做法；
- 用家庭备餐/外带方案；
- 减少选择负担。

F overlay 不可以：

- 删除 underlying A–E 的能量链；
- 跳过 Ingredient Master execution grid；
- 用“1份”代替克重；
- 用非法克重简化执行；
- 省略 `diet_plan_trace` root。

---

## V4.2.4-FOOD-12｜最终 Validator 触发码

新增/强化：

```text
food_algorithmic_amount_leaked_to_patient_view
food_execution_amount_not_on_grid
food_execution_amount_out_of_bounds
food_discrete_or_package_rule_violation
food_standard_component_mapping_mismatch
food_root_trace_missing
food_root_trace_summary_only
food_patient_root_mismatch
food_root_execution_grid_mismatch
```

任一存在：

```yaml
food_content_validation:
  status: FAIL
```

---

## V4.2.4-FOOD-13｜最终一句话

> **患者看到的每一个克重都必须是最终执行量；STANDARD_COMPONENT 必须从正式 execution mapping 取值，AI_GENERATED_DISH 必须先通过 Ingredient Master 网格；FULL 只能由最终文件中真实存在的 Day1–Day7 `diet_plan_trace` 派生。**

---

# 以下完整继承 V4.2.3；与上方 V4.2.4 冲突时，以 V4.2.4 为准

# FINAL FOOD GENERATION & TRACEABILITY CONTRACT V4.2.3｜患者端菜谱物化 + 患者视图/Trace一致性（2026-09-24）

> **版本定位**：V4.2.3 在 V4.2.2“Ingredient Master 单一事实来源 + 组件份量物化”的基础上，进一步规定患者端 Day1–Day7 饮食不能只显示食材清单，也不能重新退化为“某菜1份”。每一道实际执行食物必须形成可读、可做、可追踪的 `dish_name + ingredients/executable_amount + simple_method`。
>
> 本补丁优先于下方 V4.2.2/V4.2.1/V4.2/V4.1 中任何允许患者端仅显示组件名、份数或只有克重而没有菜品组织形式的旧表述。
>
> 执行优先级：`临床安全/BLOCK规则 > ACTIVE MDT配置 > ACTIVE Ingredient Master > 本 V4.2.3 > V4.2.2 > 历史 FOOD 规则 > AI自由编排`。
>
> **不改变** Ingredient Master V1.2、49个 STANDARD_COMPONENT 的合法 scale、营养来源状态、D/E营养恢复方向，也不扩大饮水/尿便等既定范围。

---

## V4.2.3-FOOD-1｜患者端固定输出单位：一道菜 = 菜名 + 原料克重 + 简单做法

患者端和医护审核端的 Day1–Day7 菜单，每个实际食物条目必须至少包含：

```yaml
patient_food_item:
  dish_name: string
  ingredients:
    - ingredient_name: string
      executable_amount: number
      execution_unit: g|ml|个
  simple_method: string
```

### 三个字段均为必填

1. `dish_name`：患者能理解的真实菜名/食物名；
2. `ingredients[].executable_amount`：最终可执行的 g/ml/个；
3. `simple_method`：1句为主、最多2句的家庭可执行做法。

患者端不需要看：

```text
component_id
ingredient_id
component_portion_scale
algorithmic_amount
nutrition_source_status
```

这些继续留在后台 trace。

---

## V4.2.3-FOOD-2｜什么算“合格菜谱”

### STANDARD_COMPONENT

标准组件必须展开为：

```yaml
food_item_type: STANDARD_COMPONENT
component_id: P011
component_portion_scale: 1.0
patient_display:
  dish_name: 鸡胸彩椒
  ingredients:
    - 鸡胸肉 80 g
    - 彩椒 150 g
    - 植物油 5 g
  simple_method: 鸡胸切片，与彩椒少油炒熟。
```

患者端应呈现为类似：

```text
鸡胸彩椒：鸡胸肉80g + 彩椒150g + 植物油5g；鸡胸切片，与彩椒少油炒熟。
```

而不是：

```text
鸡胸彩椒1份
P011@1.0
鸡胸肉80g + 彩椒150g + 油5g   # 只有原料，没有菜名/做法
```

### AI_GENERATED_DISH

动态新菜同样必须：

```yaml
food_item_type: AI_GENERATED_DISH
generated_dish_id: GD-...
dish_name: 山药鸡肉蒸蛋
ingredients:
  - ingredient_id: ...
    ingredient_name: 山药
    executable_grams: 80
  - ingredient_id: ...
    ingredient_name: 鸡胸肉
    executable_grams: 60
  - ingredient_id: ...
    ingredient_name: 鸡蛋
    executable_grams: 50
simple_method: 山药切小块，鸡肉切碎，与蛋液混合后蒸熟。
```

营养值仍必须由认可营养计算源按最终执行克重计算，不能由 `simple_method` 或 LLM 估算替代。

---

## V4.2.3-FOOD-3｜单一食物也必须患者可执行

水果、鸡蛋、蒸红薯等单一食物允许只含1个 ingredient，但仍要形成患者可执行对象。

例如：

```yaml
dish_name: 水煮蛋
ingredients:
  - 鸡蛋 1个（约50g可食部）
simple_method: 煮熟后食用。
```

```yaml
dish_name: 苹果
ingredients:
  - 苹果 150g可食部
simple_method: 洗净后直接食用。
```

不能因为是单一食物而只在餐次中留下无结构的 `鸡蛋50g`、`苹果150g` 字符串后就宣称“菜谱已物化”。

---

## V4.2.3-FOOD-4｜simple_method 的生成边界

`simple_method` 只用于提高执行性，不得成为新的临床或营养信息来源。

允许使用的原则：

- 优先继承标准组件已有做法/菜名语义；
- 没有固定做法时，只能在当前方案允许的家庭烹调方式内生成简短方法，如 `蒸、煮、炖、焯后少油炒、焖至熟软`；
- 不凭空添加未计入营养计算的食材或大量调味料；
- 如果简单做法引入新的油、糖、奶、酱料或其他有营养贡献的原料，必须把它加入 ingredients 并重新计算；
- 若患者有早饱、恶心、吞咽/咀嚼、乳糖不耐受等限制，做法必须服从已存在的患者约束；
- 对来源未确认的产品，不得通过菜谱文字把它伪装成已确认食材。

建议后台增加：

```yaml
simple_method_status: CANONICAL | GENERATED_WITHIN_ALLOWED_METHODS | NEEDS_REVIEW
```

`NEEDS_REVIEW` 可以存在于医护草稿，但不能在缺少必要审核时自动发布。

---

## V4.2.3-FOOD-5｜患者端“餐次”应由菜组成，而不是由组件名或散列原料组成

推荐患者端结构：

```yaml
Day1:
  breakfast:
    - dish_name: 燕麦鸡蛋早餐碗
      ingredients: [...]
      simple_method: ...
  lunch:
    - dish_name: 杂粮饭
      ingredients: [...]
      simple_method: ...
    - dish_name: 清蒸鲈鱼
      ingredients: [...]
      simple_method: ...
    - dish_name: 西兰花胡萝卜双蔬
      ingredients: [...]
      simple_method: ...
```

### 强制要求

- 主食也必须写清真实原料克重，例如“杂粮饭：大米35g+糙米15g+赤小豆10g（干重）”；
- 复合菜必须列出主要食材与油的执行量；
- 菜名不能替代克重；克重也不能替代菜名；
- 不要求写成长篇烹饪教程，`simple_method` 简短、可执行即可。

---

## V4.2.3-FOOD-6｜F overlay 只能简化任务，不能简化掉克重和菜谱

F 型复杂度叠加允许：

- 减少每天不同菜品数量；
- 2–3套简单餐型重复轮换；
- 使用更短、更容易备餐的做法；
- 更多使用可提前准备的 STANDARD_COMPONENT。

但 F **不允许**退化成：

```text
杂粮饭1份
糙米饭1份
鸡胸彩椒
香菇油麦菜
```

即使后台 trace 已有 `C003@1.0 / P011@1.0 / V003@1.0`，患者端仍必须展开成实际克重和简单做法。

---

## V4.2.3-FOOD-7｜FOOD trace 新增患者菜谱物化字段

每个患者可见 food item 需要与后台对象一一对应：

```yaml
patient_recipe_materialization:
  dish_name: ...
  ingredients:
    - ingredient_id: ING...
      ingredient_name: ...
      executable_amount: ...
      execution_unit: g|ml|个
  simple_method: ...
  simple_method_status: CANONICAL|GENERATED_WITHIN_ALLOWED_METHODS|NEEDS_REVIEW
```

`diet_plan_trace.trace_validation` 增加：

```yaml
all_patient_food_items_have_dish_name: true|false
all_patient_food_items_have_ingredient_amounts: true|false
all_patient_food_items_have_simple_method: true|false
no_bare_component_share_in_patient_view: true|false
patient_view_matches_food_trace: true|false
```

只要上述任一关键字段为 false，不能声称 FOOD patient materialization = FULL。

---

## V4.2.3-FOOD-8｜最终展示例

合格：

```text
午餐
- 杂粮饭：大米35g + 糙米15g + 赤小豆10g（均为干重）；淘洗后一起煮熟。
- 清蒸鲈鱼：鲈鱼100g + 植物油3g；鲈鱼蒸熟，出锅后按计划用油调味。
- 西兰花胡萝卜双蔬：西兰花150g + 胡萝卜80g + 植物油5g；焯后少油翻炒至熟。
```

不合格：

```text
午餐：杂粮饭1份 + 清蒸鲈鱼100g + 西兰花胡萝卜双蔬
```

也不充分：

```text
午餐：大米35g + 糙米15g + 赤小豆10g + 鲈鱼100g + 西兰花150g + 胡萝卜80g
```

第二种虽然有克重，但缺少真实菜品组织和做法，不能作为最终患者菜谱视图。

---

## V4.2.3-FOOD-9｜最终一句话

> **患者端 FOOD 的最小合格单位不是“组件”也不是“食材列表”，而是“菜名 + 每种原料的可执行克重/容量/个数 + 简短做法”。后台继续保留 component/ingredient/scale/trace；两层必须一一对应。**

---

# 以下完整继承 02 V4.2.2；与上方 V4.2.3 冲突时，以 V4.2.3 为准

# FINAL FOOD GENERATION & TRACEABILITY CONTRACT V4.2.2｜Ingredient Master 单一事实来源 + 组件份量物化定稿（2026-09-24）

> **版本定位**：本补丁依据 MDT 已确认的统一处理原则，将 `Ingredient Master V1.2` 设为 FOOD 的基础食材单一事实来源，并把 49 个 `STANDARD_COMPONENT` 的营养真值、合法 scale 与 `AI_GENERATED_DISH` 的食材级生成约束统一收口。
>
> 本补丁**优先于**下方 V4.2.1 / V4.2 / V4.1 / V4 / V2.0 中所有与“固定 0.5/0.75/1/1.25/1.5 全局 scale”“旧组件独立营养值”“患者端份数”“AI 自行估克重/营养值”冲突的历史规则。
>
> 执行优先级：`临床安全/BLOCK规则 > ACTIVE MDT配置 > ACTIVE Ingredient Master > 本 V4.2.2 > 01 Master > V4.2.1 > V4.2 > V4.1 > 历史 FOOD 规则 > AI自由编排`。
>
> **重要**：本补丁不扩大饮水、尿便评估或其他此前明确不纳入的模块。

---

## V4.2.2-FOOD-1｜Ingredient Master 是食材层唯一事实来源

所有 `STANDARD_COMPONENT` 和 `AI_GENERATED_DISH` 的基础食材必须映射到 `ingredient_id`。

每个基础食材至少读取：

```yaml
ingredient_id: ING...
ingredient_name: ...
final_decision: ACTIVE_FOR_EXACT | RULE_APPROVED_SOURCE_PENDING
nutrition_source_status: ...
nutrition_basis: per_100g | per_100ml
weight_basis: ...
execution_unit: g | ml
candidate_min: number
candidate_max: number
candidate_step: number
```

### 使用规则

- `ACTIVE_FOR_EXACT`：可以进入 EXACT 营养计算；
- `RULE_APPROVED_SOURCE_PENDING`：重量口径、min/max/step 已按 MDT 原则确认，但产品标签、身份、品种或精确营养源尚未完成；可以存在于医护草稿，**不得用于正式 EXACT 营养闭合或直接 PUBLISHED**；
- LLM 不能用自身知识把 pending 食材补成 ACTIVE；
- 任何新基础食材先进入 `PLAN_LOCAL_INGREDIENT_CANDIDATE / PENDING_REVIEW`，不能绕过 Ingredient Master。

---

## V4.2.2-FOOD-2｜算法 scale 与患者执行量彻底分离

`component_portion_scale` 只允许存在于后台算法层。

最终患者/医生执行方案必须物化为：

```text
g / ml / 个
```

复合菜必须能追踪到主要食材执行量。

以下患者端输出均视为未完成物化：

```text
杂粮饭 0.75份
鸡胸彩椒 1份
西兰花半份
糙米饭 1.25份
```

### 组件 scale 不再使用全局统一集合

历史规则：

```text
每个组件固定允许 0.5 / 0.75 / 1 / 1.25 / 1.5
```

自 V4.2.2 起废止。

实际合法 scale 必须由该组件所有基础食材的：

```text
candidate_min
candidate_max
candidate_step
discrete/package rule
```

逐项执行化后反推。

若某个 scale：

- 取整后仍在所有食材边界内 → 可保留；
- 任一食材低于 min 或高于 max → 禁用该 scale；
- 只有通过明显改变食材比例才能勉强合法 → 不再视为原 `STANDARD_COMPONENT`，转 `AI_GENERATED_DISH`。

---

## V4.2.2-FOOD-3｜执行化后必须重算营养

任何：

```text
scale
克重取整
包装量映射
整枚鸡蛋处理
食材替换
食材比例改变
```

发生后，都必须按照最终 `executable_grams/ml` 重新计算：

```text
kcal
protein_g
carbohydrate_g
fat_g
```

旧组件营养值只用于历史追溯，不再与 Ingredient Master 形成第二套并行真值。

### 营养源优先级

```text
实际产品标签 / 院内指定产品
> ACTIVE 的中国疾控精确条目
> MDT 确认的项目参考值
> 未确认候选
```

最后一级不能用于正式 EXACT 闭合。

---

## V4.2.2-FOOD-4｜STANDARD_COMPONENT 最终合同

```yaml
food_item_type: STANDARD_COMPONENT
component_id: C/P/V/S...
component_portion_scale: number
allowed_component_scales: [...]
ingredients:
  - ingredient_id: ING...
    algorithmic_amount: number
    executable_amount: number
    execution_unit: g|ml
    weight_basis: ...
nutrition_status: ACTIVE_RECALCULATED | NEEDS_SOURCE_RECALC
planned_nutrition:
  kcal: number|null
  protein_g: number|null
  carbohydrate_g: number|null
  fat_g: number|null
```

硬规则：

- `component_portion_scale` 必须属于该组件 `allowed_component_scales`；
- `ACTIVE_RECALCULATED` 才可把组件营养值作为正式计算输入；
- `NEEDS_SOURCE_RECALC` 可保留菜单结构供医护审核，但不能声称精确营养闭合；
- 患者端不显示 component id 或 scale 作为主要份量表达。

---

## V4.2.2-FOOD-5｜AI_GENERATED_DISH 最终合同

AI 可以生成 49 组件以外的患者专属家常菜，但必须是“受 Ingredient Master 约束的候选生成”。

```yaml
food_item_type: AI_GENERATED_DISH
generated_dish_id: GD-...
dish_name: ...
ingredients:
  - ingredient_id: ING...
    ingredient_name: ...
    algorithmic_grams: ...
    executable_grams: ...
    weight_basis: ...
    ingredient_final_decision: ACTIVE_FOR_EXACT|RULE_APPROVED_SOURCE_PENDING
nutrition_status: CALCULATED | NEEDS_RECALC
plan_item_review_status: PENDING_REVIEW | APPROVED_FOR_PLAN | REJECTED
```

AI 只负责：

1. 选择符合患者约束的食材；
2. 在 Ingredient Master 的 min/max/step 内提出候选克重；
3. 形成真实可执行的菜品结构。

AI 不负责：

- 自行创造正式食材营养真值；
- 越过 min/max/step；
- 把 pending 食材伪装成 ACTIVE；
- 用 LLM 估算替代营养计算服务。

---

## V4.2.2-FOOD-6｜Ingredient Master V1.2 机器注册表

> 下表为本版本运行时注册表。数值营养仅在 `ACTIVE_FOR_EXACT` 行作为正式计算输入；pending 行的营养候选不得用于正式 EXACT 闭合。

| ingredient_id | 食材 | final_decision | source_status | nutrition_basis | weight_basis | unit | min | max | step | kcal | P | C | F |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ING001 | 全麦面包 | RULE_APPROVED_SOURCE_PENDING | PRODUCT_LABEL_REQUIRED | per_100g | ready_to_eat_net_weight（成品净重） | g | 25 | 100 | 5 |  |  |  |  |
| ING002 | 全麦面粉 | RULE_APPROVED_SOURCE_PENDING | PROJECT_REFERENCE_PENDING_MDT | per_100g | dry_weight（干/生重） | g | 15 | 80 | 5 |  |  |  |  |
| ING003 | 大米 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | dry_weight（干/生重） | g | 15 | 80 | 5 | 349.9 | 7.7 | 77.4 | 0.6 |
| ING004 | 小米 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | dry_weight（干/生重） | g | 15 | 80 | 5 | 365.7 | 9 | 75.1 | 3.1 |
| ING005 | 山药 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 50 | 250 | 10 | 58.1 | 1.9 | 12.4 | 0.2 |
| ING006 | 燕麦片 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | dry_weight（干/生重） | g | 15 | 80 | 5 | 380.7 | 15 | 66.9 | 6.7 |
| ING007 | 玉米鲜 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 50 | 200 | 10 | 113.3 | 4 | 22.8 | 1.2 |
| ING008 | 糙米 | RULE_APPROVED_SOURCE_PENDING | PROJECT_REFERENCE_PENDING_MDT | per_100g | dry_weight（干/生重） | g | 15 | 80 | 5 |  |  |  |  |
| ING009 | 红薯 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 50 | 250 | 10 | 103.3 | 1.1 | 24.7 | 0.2 |
| ING010 | 荞麦面干 | RULE_APPROVED_SOURCE_PENDING | PROJECT_REFERENCE_PENDING_MDT | per_100g | dry_weight（干/生重） | g | 15 | 80 | 5 |  |  |  |  |
| ING011 | 赤小豆干 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | dry_weight（干/生重） | g | 5 | 30 | 5 | 328.4 | 20.2 | 63.4 | 0.6 |
| ING012 | 猪里脊 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 150 | 5 | 154.9 | 20.2 | 0.7 | 7.9 |
| ING013 | 瘦牛肉 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 150 | 5 | 107.3 | 20.2 | 1.2 | 2.3 |
| ING014 | 虾仁 | RULE_APPROVED_SOURCE_PENDING | SPECIES_MATCH_REQUIRED | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 120 | 5 |  |  |  |  |
| ING015 | 鲈鱼 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 40 | 150 | 5 | 105.6 | 18.6 | 0 | 3.4 |
| ING016 | 鳕鱼 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 40 | 150 | 5 | 89.4 | 20.4 | 0.5 | 0.5 |
| ING017 | 鸡胸肉 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 150 | 5 | 133.1 | 19.4 | 2.5 | 5 |
| ING018 | 鸡腿肉去皮 | RULE_APPROVED_SOURCE_PENDING | DERIVED_PROJECT_CANDIDATE_PENDING_MDT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 150 | 5 |  |  |  |  |
| ING019 | 鸡蛋 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | whole_unit + edible_weight（整枚+可食部） | g | 50 | 100 | 50 | 143.2 | 13.3 | 2.8 | 8.8 |
| ING020 | 北豆腐 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 50 | 200 | 10 | 99.2 | 12.2 | 2 | 4.8 |
| ING021 | 低脂牛奶 | RULE_APPROVED_SOURCE_PENDING | PRODUCT_LABEL_REQUIRED | per_100ml | package_volume（包装/量具容量） | ml | 100 | 300 | 50 |  |  |  |  |
| ING022 | 无糖酸奶 | RULE_APPROVED_SOURCE_PENDING | PRODUCT_LABEL_REQUIRED | per_100g | package_net_weight（包装净含量；建议用g） | g | 100 | 200 | 50 |  |  |  |  |
| ING023 | 无糖豆浆 | RULE_APPROVED_SOURCE_PENDING | PRODUCT_LABEL_REQUIRED | per_100ml | package_volume（包装/量具容量） | ml | 150 | 300 | 50 |  |  |  |  |
| ING024 | 冬瓜 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 250 | 10 | 12.4 | 0.4 | 2.6 | 0.2 |
| ING025 | 圆白菜 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 250 | 10 | 24.4 | 1.5 | 4.6 | 0.2 |
| ING026 | 彩椒 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 250 | 10 | 26.1 | 1.3 | 6.4 | 0.2 |
| ING027 | 木耳鲜 | RULE_APPROVED_SOURCE_PENDING | IDENTITY_REVIEW_REQUIRED | per_100g | hydrated_edible_weight（建议按水发可食部；身份待确认） | g | 20 | 100 | 10 |  |  |  |  |
| ING028 | 杏鲍菇 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 20 | 150 | 10 | 35.4 | 1.3 | 8.3 | 0.1 |
| ING029 | 油麦菜 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 250 | 10 | 16.5 | 1.4 | 2.1 | 0.4 |
| ING030 | 生菜 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 250 | 10 | 14.6 | 1.3 | 2 | 0.3 |
| ING031 | 番茄 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 250 | 10 | 20.6 | 0.9 | 4 | 0.2 |
| ING032 | 胡萝卜 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 250 | 10 | 39.2 | 1 | 8.8 | 0.2 |
| ING033 | 芹菜 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 250 | 10 | 17 | 0.8 | 3.9 | 0.1 |
| ING034 | 茄子 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 250 | 10 | 23.4 | 1.1 | 4.9 | 0.2 |
| ING035 | 菠菜 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 250 | 10 | 27.7 | 2.6 | 4.5 | 0.3 |
| ING036 | 西兰花 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 250 | 10 | 36.1 | 4.1 | 4.3 | 0.6 |
| ING037 | 西葫芦 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 250 | 10 | 19.1 | 0.8 | 3.8 | 0.2 |
| ING038 | 香菇鲜 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 20 | 150 | 10 | 25.6 | 2.2 | 5.2 | 0.3 |
| ING039 | 黄瓜 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 30 | 250 | 10 | 15.8 | 0.8 | 2.9 | 0.2 |
| ING040 | 梨 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 50 | 200 | 10 | 50.7 | 0.4 | 13.3 | 0.2 |
| ING041 | 橙 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 50 | 200 | 10 | 48.8 | 0.8 | 11.1 | 0.2 |
| ING042 | 猕猴桃 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 50 | 200 | 10 | 61.9 | 0.8 | 14.5 | 0.6 |
| ING043 | 苹果 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 50 | 200 | 10 | 54.7 | 0.2 | 13.5 | 0.2 |
| ING044 | 草莓 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 50 | 200 | 10 | 32.3 | 1 | 7.1 | 0.2 |
| ING045 | 香蕉 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | raw_edible_weight（烹调前可食部） | g | 50 | 150 | 10 | 94.2 | 1.4 | 22 | 0.2 |
| ING046 | 杏仁 | RULE_APPROVED_SOURCE_PENDING | IDENTITY_REVIEW_REQUIRED | per_100g | edible_kernel_weight（可食仁净重） | g | 5 | 20 | 5 |  |  |  |  |
| ING047 | 核桃 | ACTIVE_FOR_EXACT | CDC_EXACT | per_100g | edible_kernel_weight（可食仁净重） | g | 5 | 20 | 5 | 637.7 | 14.9 | 19.1 | 58.8 |
| ING048 | 植物油 | ACTIVE_FOR_EXACT | STANDARD_DERIVED_GENERIC | per_100g | added_weight（实际加入量） | g | 1 | 10 | 1 | 900 | 0 | 0 | 100 |

---

## V4.2.2-FOOD-7｜49 个 STANDARD_COMPONENT V1.2 运行状态

> `ACTIVE_RECALCULATED`：组件可用于正式营养重算。  
> `NEEDS_SOURCE_RECALC`：组件结构和份量规则已确认，但所含基础食材仍有来源/产品/身份未决；不得用于正式 EXACT 闭合。

| component_id | 组件 | nutrition_status | allowed_component_scales | pending_source_items | kcal | P | C | F |
|---|---|---|---|---|---:|---:|---:|---:|
| C001 | 白米饭基础份 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25,1.5 |  | 174.9 | 3.9 | 38.7 | 0.3 |
| C002 | 糙米饭基础份 | NEEDS_SOURCE_RECALC | 0.5,0.75,1,1.25,1.5 | 糙米 | 174 | 3.9 | 37.5 | 1.4 |
| C003 | 杂粮饭基础份 | NEEDS_SOURCE_RECALC | 1,1.25,1.5 | 糙米 | 207.5 | 5.9 | 44.7 | 0.7 |
| C004 | 燕麦早餐份 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25,1.5 |  | 152.3 | 6 | 26.8 | 2.7 |
| C005 | 全麦馒头基础份 | NEEDS_SOURCE_RECALC | 0.5,0.75,1,1.25 | 全麦面粉 | 203 | 7.2 | 41.4 | 1.5 |
| C006 | 鲜玉米基础份 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25 |  | 169.9 | 6 | 34.2 | 1.8 |
| C007 | 蒸红薯基础份 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25,1.5 |  | 154.9 | 1.6 | 37 | 0.3 |
| C008 | 荞麦面基础份 | NEEDS_SOURCE_RECALC | 0.5,0.75,1,1.25 | 荞麦面干 | 204 | 7.2 | 40.8 | 1.5 |
| C009 | 小米粥基础份 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25,1.5 |  | 146.3 | 3.6 | 30 | 1.2 |
| C010 | 红豆小米粥 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25,1.5 |  | 142.6 | 4.7 | 28.9 | 1 |
| C011 | 全麦面包基础份 | NEEDS_SOURCE_RECALC | 0.5,0.75,1,1.25 | 全麦面包 | 172 | 6.3 | 28.7 | 2.9 |
| C012 | 山药主食份 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25 |  | 116.2 | 3.8 | 24.8 | 0.4 |
| P001 | 清蒸鲈鱼 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25,1.5 |  | 132.6 | 18.6 | 0 | 6.4 |
| P002 | 清蒸鳕鱼 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25,1.5 |  | 116.4 | 20.4 | 0.5 | 3.5 |
| P003 | 香草/葱姜鸡胸 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25,1.5 |  | 178.1 | 19.4 | 2.5 | 10 |
| P004 | 去皮鸡腿肉炖菇 | NEEDS_SOURCE_RECALC | 0.5,0.75,1,1.25,1.5 | 鸡腿肉去皮 | 203 | 22 | 4.2 | 11.2 |
| P005 | 番茄炖瘦牛肉 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25,1.5 |  | 161.7 | 17.5 | 7 | 7.1 |
| P006 | 芹菜木耳里脊 | NEEDS_SOURCE_RECALC | 0.5,0.75,1,1.25,1.5 | 木耳鲜 | 199.3 | 17.7 | 7.5 | 11.5 |
| P007 | 虾仁蒸蛋 | NEEDS_SOURCE_RECALC | 1 | 虾仁 | 137.4 | 16.7 | 2.3 | 6.8 |
| P008 | 香菇烧北豆腐 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25 |  | 214.3 | 20.1 | 7.2 | 12.4 |
| P009 | 番茄炒蛋（少油版） | ACTIVE_RECALCULATED | 0.5,1 |  | 229.4 | 15.1 | 10.8 | 14.2 |
| P010 | 西兰花虾仁 | NEEDS_SOURCE_RECALC | 0.5,0.75,1,1.25,1.5 | 虾仁 | 162.8 | 19.6 | 7.7 | 6.4 |
| P011 | 鸡胸彩椒 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25,1.5 |  | 190.6 | 17.5 | 11.6 | 9.3 |
| P012 | 牛肉西葫芦 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25,1.5 |  | 159.5 | 17.4 | 6.7 | 7.1 |
| P013 | 冬瓜豆腐虾仁汤 | NEEDS_SOURCE_RECALC | 0.75,1,1.25 | 虾仁 | 181.8 | 21.4 | 8 | 7.5 |
| P014 | 鸡蛋豆腐羹 | ACTIVE_RECALCULATED | 1 |  | 188.8 | 18.9 | 3.4 | 11.2 |
| P015 | 低脂奶蛋组合 | NEEDS_SOURCE_RECALC | 1 | 低脂牛奶 | 180.3 | 13.9 | 13.9 | 7.7 |
| V001 | 蒜香西兰花 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25 |  | 117.2 | 8.2 | 8.6 | 6.2 |
| V002 | 清炒菠菜 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25 |  | 100.4 | 5.2 | 9 | 5.6 |
| V003 | 香菇油麦菜 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25 |  | 95.2 | 4.3 | 7.9 | 6 |
| V004 | 清炒圆白菜 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25 |  | 93.8 | 3 | 9.2 | 5.4 |
| V005 | 芹菜木耳 | NEEDS_SOURCE_RECALC | 0.5,0.75,1,1.25 | 木耳鲜 | 91.9 | 2.4 | 10.6 | 5.3 |
| V006 | 番茄黄瓜双拼 | ACTIVE_RECALCULATED | 0.5,0.75,1 |  | 81.6 | 2.5 | 10.3 | 3.6 |
| V007 | 彩椒杏鲍菇 | ACTIVE_RECALCULATED | 0.5,0.75,1 |  | 124.2 | 3.2 | 18.9 | 5.3 |
| V008 | 胡萝卜西葫芦 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25 |  | 110.7 | 2.2 | 13.9 | 5.5 |
| V009 | 冬瓜香菇 | ACTIVE_RECALCULATED | 0.5,0.75,1 |  | 82.4 | 2.3 | 9.6 | 4.7 |
| V010 | 少油烧茄子 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25 |  | 100.8 | 2.2 | 9.8 | 6.4 |
| V011 | 生菜番茄沙拉（中式清拌） | ACTIVE_RECALCULATED | 0.5,0.75,1 |  | 79.8 | 3.3 | 9 | 3.8 |
| V012 | 西兰花胡萝卜双蔬 | ACTIVE_RECALCULATED | 0.5,0.75,1,1.25 |  | 130.5 | 7 | 13.5 | 6.1 |
| S001 | 低脂奶+苹果 | NEEDS_SOURCE_RECALC | 1 | 低脂牛奶 | 152.6 | 6 | 26.2 | 2.8 |
| S002 | 无糖酸奶+草莓 | NEEDS_SOURCE_RECALC | 1 | 无糖酸奶 |  |  |  |  |
| S003 | 无糖豆浆+梨 | NEEDS_SOURCE_RECALC | 1 | 无糖豆浆 | 99.6 | 5 | 18.7 | 2 |
| S004 | 低脂奶+小香蕉 | NEEDS_SOURCE_RECALC | 1 | 低脂牛奶 | 162.4 | 6.9 | 27.6 | 2.8 |
| S005 | 无糖酸奶+核桃 | NEEDS_SOURCE_RECALC | 1 | 无糖酸奶 |  |  |  |  |
| S006 | 低脂奶+橙 | NEEDS_SOURCE_RECALC | 1 | 低脂牛奶 | 160.2 | 7 | 26.6 | 2.9 |
| S007 | 苹果+杏仁 | NEEDS_SOURCE_RECALC | 1 | 杏仁 | 139.3 | 2.5 | 22.6 | 4.8 |
| S008 | 鲜玉米+低脂奶 | NEEDS_SOURCE_RECALC | 1 | 低脂牛奶 | 178.6 | 8.3 | 30.3 | 3.1 |
| S009 | 水煮蛋+小番茄 | ACTIVE_RECALCULATED | 1 |  | 102.5 | 8 | 7.4 | 4.7 |
| S010 | 猕猴桃+无糖酸奶 | NEEDS_SOURCE_RECALC | 1 | 无糖酸奶 |  |  |  |  |

---

## V4.2.2-FOOD-8｜最终一句话

> **Ingredient Master 是食材真值；STANDARD_COMPONENT 是可复用标准菜；AI_GENERATED_DISH 是受控动态菜。AI 可以生成候选克重，但不能生成未经知识库与营养计算服务确认的正式营养真值。所有执行量最终以 g/ml/个落地，任何变化后重新计算营养。**

---

# 以下完整继承 02 V4.2.1；与上方 V4.2.2 冲突时，以 V4.2.2 为准

# FINAL FOOD GENERATION & TRACEABILITY CONTRACT V4.2.1｜继承 Master 能量状态，不擅自降级（2026-09-23）

> **版本定位**：02 V4.2.1 不改变 FOOD 组件库、AI_GENERATED_DISH、meal realism、D/E 小体积恢复、F 简化、营养重算或 FULL trace schema。本补丁只修正 02 对 01 Master 能量状态的消费方式，避免“Master 已可形成 PROVISIONAL 候选链，但 FOOD 又因为参数未 ACTIVE 自行降成 STRUCTURE_ONLY”。
>
> 执行优先级：`临床安全/BLOCK规则 > ACTIVE MDT配置 > 01 Master V4.2.1 > 本02 V4.2.1 > 02 V4.2 > 02 V4.1 > 已批准营养数据源 > 历史FOOD规则`。
>
> **Schema兼容性**：继续使用 `FOOD_TRACE_V4_2`，不创建新的 trace schema 名称。

---

## V4.2.1-FOOD-1｜02 只能消费 Master 能量状态，不能自行把 PROVISIONAL 降级

02 接收：

```yaml
energy_state_received_from_master:
  status: ACTIVE|PROVISIONAL|UNAVAILABLE
  prescribed_energy_target_kcal: null|number
  provisional_energy_target_kcal: null|number
  blocker_present: true|false
  blocker_reasons: []
```

模式映射固定为：

```text
ACTIVE + prescribed target
→ EXACT_ACTIVE

PROVISIONAL + provisional target
→ EXACT_PROVISIONAL_REVIEW

UNAVAILABLE
→ STRUCTURE_ONLY
```

**禁止**因为 PAL/比例/蛋白参数还不是 ACTIVE，就在 02 内把 Master 已判定的 `PROVISIONAL` 再改成 `UNAVAILABLE`。

若 02 发现新的真实营养安全冲突，只能：

1. 返回 `nutrition_blocker_detected=true` 与原因；
2. 请求 01 重新计算 energy state；
3. 不得静默自行重写上游状态。

---

## V4.2.1-FOOD-2｜F overlay 只简化执行，不删除营养目标

如果：

```yaml
primary_nutrition_phenotype: B
complexity_overlay: F
energy_target.status: PROVISIONAL
```

则 FOOD 可以：

- 减少餐型数量；
- 合理重复 2–3 个简单模式；
- 优先家常/外卖可执行选择；
- 简化记录和替换规则；

但不得：

- 因 `display_phenotype=F` 删除 B 的 provisional kcal；
- 把 `EXACT_PROVISIONAL_REVIEW` 改成 `STRUCTURE_ONLY`；
- 用“任务复杂”作为不做营养闭合审核的理由。

---

## V4.2.1-FOOD-3｜FOOD 不负责把普通教育需求判成 F

以下信息可以触发患者教育/菜单解释，但**不能由 02 自行判定 `complexity_overlay=F`**：

```text
不知道怎么搭配饮食
第一次看营养菜单
需要照片记录提示
需要示范份量
```

02 必须直接使用 01 返回的 `complexity_overlay`。若 01 为 `none`，02 仍可通过 `execution_support_needed` 提供简化说明，但不能自行升级 F。

---

## V4.2.1-FOOD-4｜新增模式一致性返回字段

```yaml
food_energy_mode_validation:
  master_energy_state: ACTIVE|PROVISIONAL|UNAVAILABLE
  master_target_present: true|false
  food_generation_mode: EXACT_ACTIVE|EXACT_PROVISIONAL_REVIEW|STRUCTURE_ONLY
  matches_master: true|false
  status: PASS|FAIL
```

若 `PROVISIONAL + target present` 却生成 `STRUCTURE_ONLY`，必须 FAIL。

---

# FINAL FOOD GENERATION & TRACEABILITY CONTRACT V4.2｜真实 FULL TRACE + CLOSED-WORLD + 模式一致性（2026-09-23）

> V4.2 是 02 V4.1 的小范围收口，不改变标准组件库、AI_GENERATED_DISH 双通道、meal realism、D/E 小体积营养恢复、F 简化执行、替换重算和营养来源优先级。本轮只把“完整 trace 是否真实存在、饮食模式是否与 energy state 一致、默认不使用外部知识”锁死。
>
> 执行优先级：`临床安全/BLOCK规则 > ACTIVE MDT配置 > 01 Master V4.2 > 本02 V4.2 > 02 V4.1 > 已批准营养数据源 > 历史FOOD规则`。

---

## V4.2-FOOD-0｜CLOSED-WORLD 营养生成

默认：

```yaml
source_mode: CLOSED_WORLD
```

除非用户明确要求外部研究，否则 02 不得：

- 主动引用外部营养指南、论文、网页、URL、DOI；
- 用外部文献替代本项目未 ACTIVE 的能量/蛋白/疾病参数；
- 因“常识上应该如此”而补一个本地知识库没有的精确阈值；
- 在患者方案末尾新增“外部资料校验/参考文献”。

营养计算来源仍只允许 02 已定义的院内认可服务/数据库/组件估算层级；LLM 本身永远不是营养数值来源。

---

## V4.2-FOOD-1｜`FOOD_TRACE_V4_2` 必须在文件中真实物化

### 1.1 固定 root object

```yaml
diet_plan_trace:
  trace_schema_version: FOOD_TRACE_V4_2
  generation_context: ...
  week_targets: ...
  days:
    - day: 1
      meals: [...]
    ...
    - day: 7
      meals: [...]
```

### 1.2 FULL 的硬条件

`materialization: FULL` 只有在以下条件全部成立时才允许：

- `diet_plan_trace` root object 实际出现；
- Day1–Day7 全部展开；
- 患者计划中的每个计划餐次都有对应 meal；
- 每个 food item 都有唯一 `food_item_id`；
- 每个对象都明确 `STANDARD_COMPONENT` 或 `AI_GENERATED_DISH`；
- 标准组件有 `component_id`；
- AI 新菜有 `generated_dish_id` + 结构化 ingredients；
- 每个对象有 patient display name 和 executable portion；
- STRUCTURE_ONLY 时营养数值允许 null，但对象本身不能省略；
- 发生替换/执行份量调整时，按 02 V4.1 规则记录重算状态。

### 1.3 summary 永远不能升级成 FULL

下列情况只能算 `SUMMARY_ONLY`：

```text
component_ids_used: [...]
Day1 = C004 + P015 + ...
7-day menu present = true
food_trace summary
“已生成完整trace”
```

02 向 01 返回的 artifact 状态必须来自 `diet_plan_trace` 的真实存在性，而不是语言声明。

---

## V4.2-FOOD-2｜Energy state 与 FOOD mode 强制一一对应

```text
ACTIVE + prescribed_energy_target_kcal != null
→ EXACT_ACTIVE

PROVISIONAL + provisional_energy_target_kcal != null
→ EXACT_PROVISIONAL_REVIEW

UNAVAILABLE 或没有任何可用单点候选目标
→ STRUCTURE_ONLY
```

禁止：

```text
PROVISIONAL target 有明确候选 kcal
却生成 STRUCTURE_ONLY
```

也禁止：

```text
UNAVAILABLE
却宣称 7天精确能量闭合 PASS
```

### 2.1 STRUCTURE_ONLY 的正确含义

STRUCTURE_ONLY 并不等于“什么份量都不能写”。它允许：

- 使用标准组件已有的可执行基础份量；
- 为早饱/恶心等症状给出临床可执行的小份结构；
- 给菜名、食材、做法和替换方向。

但不得：

- 宣称全天 kcal/P/C/F 已精确闭合；
- 用模型猜测营养数值；
- 把未 ACTIVE 的比例当正式处方。

---

## V4.2-FOOD-3｜AI_GENERATED_DISH 身份必须在 FULL trace 中落地

凡患者端出现的菜名/组合不再真实对应一个标准 component 原始配方，都必须在 `diet_plan_trace` 中明确：

```yaml
food_item_type: AI_GENERATED_DISH
generated_dish_id: GD-...
component_id: null
dish_name: ...
ingredients:
  - ingredient_name: ...
    executable_grams: ...
nutrition_status: CALCULATED | NEEDS_RECALC | null
plan_item_review_status: PENDING_REVIEW | APPROVED_FOR_PLAN | REJECTED
```

典型需要检查的名称包括但不限于：

```text
豆腐鸡肉丸
软烩鸡丝
山药肉末豆腐软饭
患者专属软饭/焖饭/蒸蛋组合
```

不能患者端生成了新菜，而后台完全没有身份对象。

---

## V4.2-FOOD-4｜FOOD trace 自检字段

`diet_plan_trace` 末尾必须包含：

```yaml
trace_validation:
  all_7_days_materialized: true|false
  all_patient_meals_mapped: true|false
  all_food_items_have_unique_id: true|false
  all_food_items_have_explicit_type: true|false
  all_generated_dishes_have_generated_dish_id: true|false
  all_generated_dishes_have_structured_ingredients: true|false
  patient_menu_matches_trace: true|false
  energy_mode_matches_energy_state: true|false
  no_external_unrequested_sources: true|false
```

只要任一关键字段为 false，02 必须向 01 返回 `food_trace.materialization != FULL` 或 content fail reason，不得让总控误判 PASS。

---

# 以下完整继承 02 V4.1

> V4.1 的 meal realism、STANDARD_COMPONENT/AI_GENERATED_DISH 身份规则、D/E 小体积营养恢复、F 简化、患者份量表达、替换和营养来源规则全部保留；与上方 V4.2 冲突时以 V4.2 为准。


# FINAL FOOD GENERATION & TRACEABILITY CONTRACT V4.1｜机器合同加固 + 食谱临床可执行性精修（2026-09-23）

> 本节是 02 FOOD 的最高优先级执行合同。下方 V4 与更早 FOOD V2.0 内容继续作为组件库、疾病标签、营养估算、替换与历史规则来源；**凡与本 V4.1 冲突，以本节为准**。
>
> V4.1 不改变 01 Master 已冻结的 A–E 主营养方向、F complexity overlay、P1→P2→P3→P4 能量主路径和 ACTIVE / PROVISIONAL / UNAVAILABLE 三态。此次只解决六型回归后剩余的两类问题：
>
> 1. **机器合同不够硬**：完整 FOOD trace、summary、标准组件与 AI 新菜身份曾被不同生成器解释不一致；
> 2. **患者食谱仍有“组件拼图感”**：为了闭合能量/蛋白，出现正餐碎片化、额外小块蛋白、标准组件被强行缩放、D/E 食物总体积仍偏大等问题。
>
> 执行优先级：`临床安全/BLOCK规则 > ACTIVE MDT配置 > 01 Master V4.1 > 本02 V4.1 > 已批准营养数据源 > 下方V4/FOOD V2.0 > AI生成偏好`。

---

## V4.1-0｜本轮目标：让“营养数学正确”同时变成“患者真的会这样吃”

V4.1 的 FOOD 生成不再只追求：

```text
能量接近目标
蛋白接近目标
Day1–Day7字段完整
```

还必须同时满足：

```text
营养方向正确
+ 患者禁忌/症状过滤正确
+ 每餐结构自然
+ 食物体积与症状匹配
+ 份量可执行
+ 菜名像真实饮食
+ 七日计划不过度机械
+ 后台对象身份真实
+ 完整trace可审计
```

因此，**“营养闭合成功”不能覆盖“患者不可执行/不自然”的失败。**

---

# V4.1-1｜STANDARD_COMPONENT 与 AI_GENERATED_DISH 身份判定必须确定化

## 1.1 标准组件何时仍可保持 `STANDARD_COMPONENT`

只有同时满足以下条件时，计划食物对象才可以继续标记为 `STANDARD_COMPONENT`：

1. 使用的核心食材结构与该 component 原始定义一致；
2. 主要烹饪方式与原始定义一致；
3. 份量调整仅属于该组件允许的执行化/份量变化；
4. 没有把多个标准组件重新包装成一个全新的综合菜名；
5. 没有通过明显改变食材比例来制造新的营养结构；
6. 患者可读名称仍能真实对应这个标准组件。

允许的例子：

```yaml
food_item_type: STANDARD_COMPONENT
component_id: P003
patient_display_name: 葱姜鸡胸肉
executable_portion: 鸡胸肉100g，少油烹调
```

## 1.2 下列情况必须改标 `AI_GENERATED_DISH`

只要出现以下任一情况，不得为了复用旧营养值继续假装是标准组件：

- 把两个或以上标准组件整合成一道人类意义上的新菜；
- 标准组件被大幅改配方、改食材比例或改烹饪结构；
- 为患者症状专门设计新的软饭、焖饭、蒸蛋、肉末豆腐组合等；
- 为避免碎片化而把“主食+蛋白+配菜”重构成一个综合菜；
- 菜名已经是库中不存在的患者专属家常菜；
- 原组件营养值不能直接代表改造后的新组合。

例如：

```text
大米 + 山药 + 肉末 + 豆腐
```

如果患者端显示为：

```text
“山药肉末豆腐软饭”
```

则后台必须保存：

```yaml
food_item_type: AI_GENERATED_DISH
generated_dish_id: GD-...
```

而不是把它拆成若干旧 component 后，在患者端伪装成一道人类新菜。

## 1.3 身份误标是内容错误

以下情形必须导致 FOOD content validation FAIL：

```text
患者端明显是新菜
但后台仍标 STANDARD_COMPONENT
且无法由单一原component配方解释
```

新增：

```yaml
food_identity_validation:
  all_standard_components_match_canonical_recipe: true | false
  all_new_dishes_have_generated_dish_id: true | false
  generated_dish_misclassified_as_component: false | true
```

---

# V4.1-2｜标准组件不是默认优先于真实可执行性

V4 中允许双通道；V4.1 进一步明确**何时应该主动切换到 AI_GENERATED_DISH**。

生成器先尝试使用标准组件，但如果标准组件组合导致以下任一问题，应优先考虑患者专属新菜，而不是强行拼49项：

```text
同一餐组件过碎
为了蛋白闭合额外塞一个50g肉/鱼小块
出现两个功能高度重复的蔬菜菜
标准份缩放后变成难执行份量
D/E为了增能量只能把普通组件全部放大
患者偏好/质地/早饱/恶心与现有组件不匹配
外食/家庭场景下组件组合不现实
```

推荐决策：

```text
标准组件能自然组成真实餐食
→ 使用 STANDARD_COMPONENT

标准组件会造成碎片化或症状不匹配
→ 生成 AI_GENERATED_DISH
→ 食材级结构化
→ 营养服务重算
→ 医护审核
```

**“能从49项拼出来”不等于“必须从49项拼”。**

---

# V4.1-3｜Meal Realism Contract：每餐先像一顿真实饭，再谈闭合

## 3.1 午/晚餐默认自然结构

在没有特殊医学/执行理由时，优先形成：

```text
1个主食来源
+ 1个主要蛋白菜
+ 1–2个非淀粉蔬菜/配菜
```

早餐可按患者习惯使用：

```text
主食 + 蛋白/奶豆 + 按需水果/蔬菜
```

加餐应承担明确功能：

```text
蛋白补充
营养恢复
早饱分餐
运动前后支持
或执行便利
```

不得为了“让表格看起来丰富”机械增加加餐或配菜。

## 3.2 禁止“微型蛋白补丁”作为默认闭合手段

如果全天或某餐蛋白不足，不得默认这样处理：

```text
已有主蛋白菜
+ 再追加鸡胸50g
```

或：

```text
已有鱼/鸡腿/豆腐
+ 再追加鳕鱼50g
```

除非存在明确临床/执行理由并记录在 `meal_rationale`。

蛋白不足时按以下优先级处理：

```text
1. 调整主要蛋白菜到合理可执行份量
2. 调整全天餐次分配
3. 使用计划性蛋白加餐
4. 生成更高蛋白密度的 AI_GENERATED_DISH
5. 最后才考虑第二个独立小蛋白对象
```

新增：

```yaml
meal_realism:
  primary_protein_item_count: 1
  secondary_protein_item_present: false
  secondary_protein_rationale: null
  protein_patch_for_numeric_closure: false
```

若：

```yaml
protein_patch_for_numeric_closure: true
```

且无临床/执行理由，则必须重新生成该餐，不能直接进入患者方案。

## 3.3 避免无意义的食物碎片化

同一餐出现以下模式应重新检查：

- 两个以上独立主蛋白菜，但没有明确目的；
- 两到三个功能高度相似的蔬菜菜，只为凑能量/纤维；
- 需要患者同时称量很多小份食材，而可以整合成更自然家常菜；
- 每餐看起来像“组件清单”而不是菜谱。

新增：

```yaml
meal_realism:
  coherent_meal_structure: true | false
  unnecessary_fragmentation: false | true
  redundant_side_dishes: false | true
  household_execution_burden: LOW | MODERATE | HIGH
```

`unnecessary_fragmentation=true` 时，优先重构成：

```text
更完整的标准菜
或 AI_GENERATED_DISH
```

---

# V4.1-4｜患者份量语言：生活语言优先，算法语言留在后台

## 4.1 患者端优先表达

患者端优先：

```text
鸡蛋1个
牛奶1杯/约200–250ml
米饭约1小碗，同时保留需要时的生重/干重说明
鸡胸肉约1掌心厚度的一份，并在需要精确执行时给出克重
```

后台仍保存：

```yaml
algorithmic_portion: ...
planned_grams: ...
portion_scale: ...
```

### 禁止患者端直接暴露

```text
1.25份
1¼标准组件
62.5g鸡蛋
43.75g大米
312.5ml牛奶
```

除非该项目已经明确验证这就是患者实际使用的包装/称量单位。

## 4.2 家庭量只是辅助，不替代可追踪克重

如果患者端写：

```text
约1小碗米饭
```

后台应尽可能仍保存：

```yaml
planned_grams: ...
weight_basis: cooked_weight | dry_weight
```

不能只有模糊家庭量而失去机器追踪。

---

# V4.1-5｜D/E 早饱、恶心、摄入不足：由“小份化”升级为“体积-密度匹配”

V4 已要求少量多餐；V4.1 再加一层质量合同。

## 5.1 生成顺序

当存在：

```yaml
early_satiety: true
# 或
nausea: true
# 或
reduced_intake: true
```

每餐优先级：

```text
1. 软嫩/耐受好的主要蛋白
2. 易入口主食或综合软饭
3. 小份熟软蔬菜
4. 必要时将部分能量/蛋白移到小加餐
```

而不是：

```text
主食 + 蛋白 + 大份蔬菜 + 水果 + 大杯饮品
```

## 5.2 蔬菜和水果不能挤占主食/蛋白

D/E 患者如果出现早饱/恶心/摄入下降：

- 蔬菜继续保留，但更强调**小份、熟软、低体积、耐受**；
- 水果优先放到独立加餐，不默认与正餐叠加；
- 大杯汤水、清汤和低能量高体积食物不应成为正餐主体；
- 不能用“健康餐蔬菜越多越好”的逻辑覆盖营养恢复目标。

本合同**不自行规定固定蔬菜克数上限**；具体克数由营养科/项目配置和患者耐受决定。

## 5.3 提高能量/蛋白时优先提高密度，不优先扩大总体积

优先：

```text
更高营养密度的主食/综合菜
软蛋白
适量烹调油
蛋/豆制品
小体积蛋白加餐
AI_GENERATED_DISH
```

而不是：

```text
所有组件 ×1.25/1.5
大量水果
大量豆浆/牛奶
大量低能量蔬菜
```

新增内部检查：

```yaml
recovery_meal_quality:
  volume_burden: LOW | MODERATE | HIGH
  protein_starch_prioritized: true | false
  vegetables_soft_and_volume_appropriate: true | false | null
  liquid_volume_competes_with_meal: false | true
  density_increased_without_excess_volume: true | false | null
```

若早饱患者 `volume_burden=HIGH`，应重构，不得仅加“分次吃”作为补救。

---

# V4.1-6｜七日多样性：A–E避免机械重复，F允许有目的地重复

## 6.1 A–E

在患者接受、食材可获得且不增加不必要复杂度的前提下：

- 主蛋白来源应适度轮换；
- 主食可在米饭、杂粮、面、薯类等允许范围内轮换；
- 不连续机械复制完全相同的三餐结构；
- 不为了“多样化”引入禁忌、难买或患者不喜欢的食物。

## 6.2 F complexity overlay

F 可以明确使用：

```text
2–3套固定餐型轮换
```

因为“减少决策负担、提高完成率”本身就是个体化目标。

但患者 Day1–Day7 页面仍必须完整展开，不能只写：

```text
Day4 = 餐型A
Day5 = 餐型B
```

后台可以记录模板引用：

```yaml
meal_template_id: TEMPLATE-A
```

患者页面必须展开实际菜名、份量和做法。

新增：

```yaml
weekly_menu_quality:
  repetition_is_intentional: true | false
  repetition_rationale: null | execution_simplification | preference | tolerance | availability
  unnecessary_mechanical_repetition: false | true
```

---

# V4.1-7｜AI_GENERATED_DISH 的营养计算与审核继续严格，但“生成”本身不应被49项阻断

V4.1 保持：

```text
AI负责设计
营养服务负责计算
医护负责批准
```

## 7.1 新菜可以先生成结构，再等待营养计算

允许：

```yaml
food_item_type: AI_GENERATED_DISH
nutrition_status: NEEDS_RECALC
planned_nutrition: null
plan_item_review_status: PENDING_REVIEW
```

这时可以作为医护审核草稿存在。

## 7.2 但 EXACT 模式不能用“LLM估算”冒充正式计算

如果没有允许的营养数据源：

```text
不能为了凑目标而让语言模型填精确kcal/P/C/F
```

`EXACT_PROVISIONAL_REVIEW` 若使用库内标准组件估算，可标：

```yaml
nutrition_status: PROVISIONAL_SOURCE_ESTIMATE
```

AI 新菜若未映射营养数据源，则必须：

```yaml
nutrition_status: NEEDS_RECALC
```

不能从相似标准菜“猜一个数”直接闭合。

---

# V4.1-8｜FOOD_TRACE_V4.1：必须 FULL MATERIALIZATION，summary 永远不等于 full trace

V4.1 在 V4 trace 基础上新增物化状态：

```yaml
diet_plan_trace:
  trace_schema_version: FOOD_TRACE_V4_1
  trace_materialization_status: FULL | SUMMARY_ONLY | MISSING
  food_trace_full: true | false
```

只有：

```yaml
trace_materialization_status: FULL
food_trace_full: true
```

才可满足 01 Master V4.1 的完整 FOOD trace 要求。

以下都只能算 `SUMMARY_ONLY`：

```text
component_ids_used: [...]
C004@1.0
Day1: breakfast=C004+P015
menu_rotation=[A,B,C,A...]
diet_plan_trace_summary
```

即使患者页面已经写得很完整，后台没有逐日、逐餐、逐食物对象 FULL trace，仍不能 `content_validation: PASS`。

## 8.1 每个 meal 增加真实性字段

```yaml
meals:
  - meal_slot: lunch
    patient_meal_name: "杂粮饭配清蒸鱼和双蔬"
    meal_rationale: "B型代谢控制；标准主蛋白+主食+蔬菜"
    meal_realism:
      coherent_meal_structure: true
      primary_protein_item_count: 1
      secondary_protein_item_present: false
      secondary_protein_rationale: null
      protein_patch_for_numeric_closure: false
      unnecessary_fragmentation: false
      redundant_side_dishes: false
      household_execution_burden: LOW
    food_items: [...]
```

## 8.2 AI 新菜增加身份验证字段

```yaml
food_items:
  - food_item_type: AI_GENERATED_DISH
    generated_dish_id: GD-...
    canonical_component_match: null
    generated_dish_reason:
      - avoid_component_fragmentation
      - early_satiety_adaptation
    ingredients: [...]
```

标准组件：

```yaml
food_items:
  - food_item_type: STANDARD_COMPONENT
    component_id: P003
    canonical_component_match: true
```

## 8.3 trace_validation 增加

```yaml
trace_validation:
  trace_materialization_status: FULL | SUMMARY_ONLY | MISSING
  food_trace_full: true | false

  all_days_present: true | false
  all_meals_present: true | false
  all_patient_meals_have_names: true | false
  all_food_items_have_ids: true | false
  all_food_items_traceable: true | false
  all_food_items_have_executable_portions: true | false
  all_required_ingredients_structured: true | false

  all_standard_components_match_canonical_recipe: true | false
  all_new_dishes_have_generated_dish_id: true | false
  generated_dish_misclassified_as_component: false | true

  all_meals_have_realism_check: true | false
  all_meals_coherent: true | false
  no_unnecessary_fragmentation: true | false
  no_unjustified_numeric_protein_patches: true | false
  weekly_menu_repetition_appropriate: true | false

  patient_menu_matches_trace: true | false
  nutrition_totals_reproducible: true | false | null
  nutrition_recalculated_after_portion_adjustment: true | false | null
  nutrition_recalculated_after_replacement: true | false | null
```

---

# V4.1-9｜FOOD Validator V4.1：结构、真实性、患者执行性一起检查

02 必须向 01 返回：

```yaml
food_validation_result:
  trace_schema_version: FOOD_TRACE_V4_1

  trace_contract:
    trace_materialization_status: FULL | SUMMARY_ONLY | MISSING
    food_trace_full: true | false

  structural:
    all_days_present: true | false
    all_meals_present: true | false
    all_patient_meals_have_names: true | false
    all_food_items_have_ids: true | false
    all_food_items_traceable: true | false
    patient_menu_matches_trace: true | false

  food_identity_validation:
    all_standard_components_match_canonical_recipe: true | false
    all_new_dishes_have_generated_dish_id: true | false
    generated_dish_misclassified_as_component: false | true

  patient_executability:
    all_food_items_have_executable_portions: true | false
    no_engineering_portions_in_patient_view: true | false
    all_days_self_contained: true | false
    no_cross_day_reference: true | false

  meal_realism_validation:
    all_meals_have_realism_check: true | false
    all_meals_coherent: true | false
    no_unnecessary_fragmentation: true | false
    no_unjustified_numeric_protein_patches: true | false
    d_e_volume_density_match: true | false | null
    weekly_menu_repetition_appropriate: true | false

  nutrition:
    diet_generation_mode: EXACT_ACTIVE | EXACT_PROVISIONAL_REVIEW | STRUCTURE_ONLY
    daily_nutrition_closed: true | false | null
    nutrition_totals_reproducible: true | false | null
    portion_adjustment_integrity_pass: true | false | null
    replacement_integrity_pass: true | false | null
    nutrition_source_versions: []

  generated_dish_validation:
    generated_dish_count: 0
    all_generated_dishes_safety_filtered: true | false | null
    all_generated_dishes_nutrition_calculated: true | false | null
    all_generated_dishes_reviewed_for_plan: true | false | null
    generated_dishes_pending_review: []
    generated_dishes_needing_recalc: []

  publication_blockers: []
```

## 9.1 V4.1 必须导致 FOOD content FAIL 的情况

在 V4 原有 FAIL 条件基础上，再增加：

- `trace_materialization_status != FULL`；
- `food_trace_full != true`；
- 只有 summary / used IDs / menu rotation；
- 患者端明显为新菜，后台却错误标记为旧标准 component；
- AI 新菜缺 `generated_dish_id`；
- 患者端仍出现工程份量如 `1.25份 / 62.5g鸡蛋 / 312.5ml牛奶`；
- 正餐存在明显无理由碎片化，且生成器未重构；
- 为了数值闭合额外增加小份第二蛋白，却没有 clinical/execution rationale；
- D/E 有明确早饱/摄入下降，但方案仍以明显高体积、低密度食物挤占主食/蛋白；
- 患者 Day1–Day7 使用“同上/同Day1/菜单A”而未展开。

## 9.2 可以 PASS + warning 的情况

- 患者餐食结构自然，但仍使用较多标准组件；
- F 因执行复杂度有目的地重复2–3套餐型；
- AI 新菜结构完整、安全过滤完成，但营养仍待重算：此时若模式为 `STRUCTURE_ONLY` 可内容PASS；若为 `EXACT_*` 则不能声称营养闭合；
- 标准组件 ACTIVE 状态未核实，但 trace 与患者菜单完整；
- 宏量比例/餐次比例仍为 PROVISIONAL。

---

# V4.1-10｜患者端 FOOD 输出模板：最终应像“人吃的饭”，不是对象清单

推荐患者端：

```text
午餐｜南瓜鸡肉软饭 + 清炒小白菜

南瓜鸡肉软饭：
大米50g（干重）、南瓜80g、鸡胸肉80g、植物油适量；软焖至易咀嚼。

清炒小白菜：
小白菜约100–150g，少油炒软。

如果今天早饱明显：
先完成软饭中的鸡肉和主食，青菜可减量；不要用大量汤水占胃。
```

而不是：

```text
C001×1 + P003×0.8 + V002×0.5
```

也不是：

```text
米饭 + 鸡胸80g + 鳕鱼50g + 豆腐50g + 2个蔬菜组件
```

除非确有临床理由。

---

# V4.1-11｜回归验收规则：A–F 再跑时重点看什么

| 场景 | V4.1 预期 |
|---|---|
| A 普通减脂保肌 | 餐食自然；不靠额外50g肉补蛋白；患者份量无工程小数 |
| B 代谢异常 | 疾病过滤+自然餐结构；标准组件可用但不机械堆菜 |
| C 低肌量/保肌 | 主蛋白菜份量优先调整；蛋白加餐优先于“正餐再塞50g鸡胸” |
| D 低BMI+早饱 | 小体积、软食、高密度；必要时主动生成 AI_GENERATED_DISH |
| E 非意愿下降+摄入显著不足 | 若 target unavailable 仍保持 STRUCTURE_ONLY；体积负担低；不伪精确闭合 |
| F complexity overlay | 允许2–3套餐型重复；患者每天仍完整展开；不因追求多样性增加负担 |
| 任何病例 | FULL FOOD_TRACE_V4_1；summary不能PASS |
| 新菜 | 必须 generated_dish_id + ingredients；未重算不得伪造营养数值 |

---

# V4.1-12｜最终一句话执行规则

> **先决定患者能吃什么，再决定一顿饭怎么自然地组成；标准组件能自然解决就用标准组件，不能自然解决就生成患者专属菜。任何营养闭合都不得以牺牲餐食真实性、症状耐受和患者可执行性为代价。患者看家常菜，医护看审核依据，后台看 FULL trace。**

---

# BASELINE FOOD CONTRACT V4｜保留底层组件库、疾病标签与原始追踪定义（仅在不与V4.1冲突时适用）

> 版本定位：本节依据 A/B/C/D/E/F 六型第一周方案回归结果，对 FOOD V2.0/V3 追踪合同进行结构性收口。它不删除下方原 49 个组件、扩展候选池、疾病标签和营养估算资料，而是重新定义 AI 如何使用这些资料生成患者真实可执行的食谱。
>
> **核心变化：现有 49 个组件不再是 AI 唯一可选菜品。** AI 可以在患者评估、安全约束和营养计算边界内生成新的患者专属家常菜，但新菜必须以计划内 `AI_GENERATED_DISH` 对象保存，经过营养重算、Safety/Content Validator 和医护审核后才可发布给该患者。
>
> 执行优先级：`临床安全/BLOCK规则 > 已ACTIVE MDT配置 > 已批准营养数据源 > 01 Master V4 > 本02 V4合同 > 下方 FOOD V2.0 原始规则/示例 > AI自由生成`。
>
> 因此，下方源规则中“AI/Codex 不自行发明未审核菜品”“库外普通家常菜只能作为DRAFT候选”等旧表述，在 V4 中解释为：**AI可以生成计划级 DRAFT 新菜供医护审核，但在审核前不得直接 PUBLISHED；无需先把每道新菜人工录入全局49组件库。**

---

## 0. 本轮修改范围与明确不扩展项

本 V4 解决六型回归中暴露的以下问题：

1. 49 个固定组件导致 A–F 菜单重复、D/E 只能机械放大份量；
2. 患者端出现 `C004×1.25 / P015 / V003` 等工程编号，影响可读性和执行；
3. 37.5 g 鸡蛋、312.5 ml 牛奶、43.75 g 大米等算法份量直接暴露给患者；
4. “同Day1早餐 / 同上 / 菜单A/B/C”等跨日引用使患者计划不自包含；
5. A/B/C/D/E/F 对 `diet_plan_trace` 的输出深度不一致，导致同类缺失有时 PASS、有时 FAIL；
6. D/E 早饱、恶心、摄入不足时，普通健康餐机械放大并不能真正实现“小体积、高营养密度”；
7. F/复杂度叠加时，应简化菜单与记录，不应丢失 underlying A–E 营养方向；
8. AI 新菜的安全、营养计算、医护审核和知识沉淀路径需要明确。

**本轮仍不新增**：专门饮水量评估、饮水处方算法、排尿/尿量/尿色模块、排便频率/便形评分模块、基于二便的自动饮食调整。原规则中已经存在的脱水、呕吐、腹泻、便秘、尿量明显减少等安全信号继续保留，但不扩展为独立 FOOD 生成模块。

---

# 1. FOOD 的最终角色：不是固定菜库，而是“受约束的食谱生成系统”

01 Master V4 决定：患者的主要营养方向、Safety、能量/蛋白状态、疾病/症状/执行 modifier 和 `diet_generation_mode`。

02 FOOD V4 负责：

```text
患者可吃什么 / 不能吃什么
        ↓
使用标准组件还是生成患者专属新菜
        ↓
具体菜名、食材、克重、做法、餐次
        ↓
算法份量 → 可执行份量
        ↓
营养计算/重算
        ↓
全天闭合与替换
        ↓
患者可读菜单 + 医护审核信息 + 后台完整 trace
```

### 1.1 49 个组件的最终定位

原 49 个 `C/P/V/S` 组件继续保留，作为：

- 已有标准化菜品/食物模板；
- 营养计算与回归测试锚点；
- 高风险患者的保守候选；
- 同类替换与份量校准基础；
- AI 动态生成新菜时的结构参考；
- 经 MDT 审核后可进入正式 `ACTIVE` 的标准知识项。

**不得再把“只允许从49项选择”作为 FOOD 生成器的硬限制。**

### 1.2 双通道生成

```yaml
food_generation_channels:
  - STANDARD_COMPONENT
  - AI_GENERATED_DISH
```

- `STANDARD_COMPONENT`：使用现有或未来已建立的标准 FOOD component；
- `AI_GENERATED_DISH`：AI 根据患者约束动态生成计划级新菜，不要求预先存在于49组件库。

两条通道可在同一天、同一餐混合使用，但都必须通过相同的安全过滤、营养计算和医护审核逻辑。

---

# 2. FOOD 生成前必须读取的输入合同

每次生成 Day1–Day7 前，至少读取：

```yaml
food_generation_context:
  phenotype:
    primary_nutrition_phenotype: A | B | C | D | E | null
    complexity_overlay: F | none

  q56_goal: null
  surgery_window: null
  safety_level: GREEN | YELLOW | RED

  energy_target:
    status: ACTIVE | PROVISIONAL | UNAVAILABLE
    prescribed_energy_target_kcal: null
    provisional_energy_target_kcal: null
    provisional_target_source: []

  diet_generation_mode: EXACT_ACTIVE | EXACT_PROVISIONAL_REVIEW | STRUCTURE_ONLY

  protein_target:
    status: ACTIVE | PROVISIONAL | UNAVAILABLE
    target_g: null
    weight_basis: null

  meal_distribution:
    status: ACTIVE | PROVISIONAL | UNAVAILABLE
    pattern: null

  nutrition_generation_flags:
    recovery_priority: false
    early_satiety: false
    nausea: false
    reduced_intake: false
    high_energy_density_needed: false
    high_protein_density_needed: false
    texture_simplification_needed: false
    ons_evaluation_needed: false

  food_constraints:
    allergies: []
    intolerances: []
    swallowing_or_chewing_limits: []
    disease_modifiers: []
    blocked_ingredients: []
    caution_ingredients: []
    required_texture: null

  execution_context:
    cooking_ability: null
    family_support: null
    meal_source: home | takeaway | cafeteria | mixed | unknown
    food_preferences: []
    disliked_foods: []
    record_preference: photo | text | portion | mixed | unknown
    time_or_cost_barriers: []
```

### 强制原则

- 过敏/不耐受/疾病/质地限制必须在**生成前过滤**，不能等菜生成后才写“如过敏请勿食”；
- 缺失数据不得当正常；
- Q56 只改变目标/排序，不得突破 Safety、营养风险、肌肉保护、手术窗口和 ACTIVE 边界；
- F overlay 主要改变菜单复杂度、可获得性和记录负担，不自动覆盖 underlying A–E 营养方向。

---

# 3. 能量状态决定 FOOD 可以生成到什么精度

必须与 01 Master V4 完全一致。

## 3.1 `EXACT_ACTIVE`

```text
energy_target.status = ACTIVE
```

允许：

- 精确日目标闭合；
- 精确 kcal/P/C/F 汇总；
- ACTIVE 标准组件；
- 经允许流程生成并完成营养计算、医护批准的计划级 AI 菜品。

## 3.2 `EXACT_PROVISIONAL_REVIEW`

```text
energy_target.status = PROVISIONAL
```

允许在**测试/医护审核草稿**中：

- 按 provisional target 生成完整 7 日菜单；
- 进行营养闭合、可执行性和多样性检查；
- 使用标准组件或 AI 生成菜；
- 所有数值必须标记 `PROVISIONAL/CANDIDATE`；
- `publication_validation` 必须 blocked，直到 Master 要求的参数和医护审核满足。

## 3.3 `STRUCTURE_ONLY`

```text
energy_target.status = UNAVAILABLE
```

只允许生成：

- 餐次结构；
- 蛋白优先/少量多餐/软食/早饱友好等方向；
- 允许食材/菜品候选；
- 需要补充的数据和人工审核点。

禁止：

- AI 自行选一个“1700–1800 kcal”作为事实目标；
- 宣称精确全天 kcal/P/C/F 闭合；
- 为了完成表格而伪造营养数字。

---

# 4. 患者端、医护端、后台审计端三层彻底分离

## 4.1 Patient-facing：患者只看“人能执行的食谱”

患者端每一餐必须完整显示：

```text
餐次
菜名
主要食材
实际可执行份量/家庭份量
简单做法
必要的执行提示
菜名形式的替换
```

当营养状态允许时，可附：

```text
该餐估算 kcal / P / C / F
全天估算 kcal / P / C / F
```

### 患者端禁止作为主要显示

```text
C004×1.25
P015
V003
S002
GD-SYN-E01-W1-D3-L01
replacement_component_ids
component_status
nutrition_source_version
```

患者端替换必须写成：

```text
“清蒸鲈鱼可换为葱姜鸡胸肉或香菇北豆腐”
```

而不是：

```text
P001 → P003/P008
```

### Day1–Day7 必须自包含

患者端禁止：

```text
同Day1早餐
同昨日午餐
同上
菜单A
菜单B
菜单C
```

即使后台复用同一组合，每天每餐也必须在患者页面完整展开。

## 4.2 Clinician-facing：可看到来源与审核点

医护审核端可额外显示：

- FOOD source type；
- 标准 component ID 或 generated dish ID；
- 算法份量与患者执行份量的差异；
- 营养数据来源；
- 过敏/疾病/症状过滤结果；
- nutrition recalculation 状态；
- plan-item review 状态；
- 替换候选与闭合影响。

## 4.3 Audit layer：完整机器追踪

所有标准组件与 AI 新菜必须进入 `diet_plan_trace`，不能只在正文出现菜名或ID。

---

# 5. 通道一：STANDARD_COMPONENT 标准组件

标准组件仍使用既有结构：

```yaml
standard_component_item:
  food_item_type: STANDARD_COMPONENT
  food_item_id: C001
  component_id: C001
  generated_dish_id: null
  component_name: "米饭"
  patient_display_name: "米饭"
  category: staple | protein | vegetable | snack | template
  portion_scale: 1.0
  algorithmic_portion: "大米50g（干重）"
  executable_portion: "大米50g（干重）"
  planned_grams: 50
  weight_basis: dry_weight
  ingredients: []
  planned_nutrition:
    kcal: null
    protein_g: null
    carbohydrate_g: null
    fat_g: null
  nutrition_source_version: ""
  nutrition_status: CALCULATED | LIBRARY_ESTIMATE | NEEDS_RECALC
  replacement_group: ""
  replacement_food_item_ids: []
  knowledge_status: ACTIVE | DRAFT | RETIRED | UNVERIFIED
  plan_item_review_status: NOT_REQUIRED | PENDING_REVIEW | APPROVED_FOR_PLAN | REJECTED
```

### 标准组件约束

- `component_id` 必须来自当前标准库；
- `portion_scale` 可作为算法尺度，但不能直接导致患者端出现难执行的伪精确量；
- 组件 `UNVERIFIED` 不等于 NON-ACTIVE；
- 标准组件是否允许 PUBLISHED 继续由 Master Publication Validator 决定。

---

# 6. 通道二：AI_GENERATED_DISH 患者专属动态菜品

AI 可以生成当前标准库中不存在的普通家常菜，但必须是**约束式生成**，不是自由编造医学处方。

## 6.1 允许生成的前提

生成前必须已经完成：

1. Safety Gate；
2. 过敏/不耐受过滤；
3. 疾病/实验室/肝弹性 modifier；
4. 咀嚼/吞咽/质地限制；
5. D/E 早饱、恶心、摄入不足等症状修饰；
6. F/执行复杂度修饰；
7. 当前能量/蛋白状态；
8. 家庭/外食/时间/烹饪能力等执行条件。

## 6.2 AI 新菜必须结构化到“食材级”

```yaml
ai_generated_dish:
  food_item_type: AI_GENERATED_DISH
  food_item_id: GD-<plan_id>-D<day>-<meal_slot>-<seq>
  component_id: null
  generated_dish_id: GD-<plan_id>-D<day>-<meal_slot>-<seq>

  dish_name: "南瓜鸡肉软饭"
  patient_display_name: "南瓜鸡肉软饭"
  category: mixed_dish
  meal_slot: lunch

  generation_rationale:
    phenotype: E
    modifiers:
      - early_satiety
      - reduced_intake
      - high_protein_density_needed

  ingredients:
    - ingredient_name: 大米
      nutrition_db_food_id: null
      algorithmic_grams: 50
      executable_grams: 50
      weight_basis: dry_weight
      allergy_tags: []
    - ingredient_name: 南瓜
      nutrition_db_food_id: null
      algorithmic_grams: 80
      executable_grams: 80
      weight_basis: raw_edible_weight
      allergy_tags: []
    - ingredient_name: 鸡胸肉
      nutrition_db_food_id: null
      algorithmic_grams: 70
      executable_grams: 70
      weight_basis: raw_edible_weight
      allergy_tags: []
    - ingredient_name: 植物油
      nutrition_db_food_id: null
      algorithmic_grams: 8
      executable_grams: 8
      weight_basis: raw_weight
      allergy_tags: []

  cooking_method: "软焖/煮至易咀嚼"
  algorithmic_portion: "1份"
  executable_portion: "1小碗"

  planned_nutrition:
    kcal: null
    protein_g: null
    carbohydrate_g: null
    fat_g: null

  nutrition_source_version: null
  nutrition_status: NEEDS_RECALC

  safety_filter_result:
    allergy_pass: true
    intolerance_pass: true
    disease_pass: true
    texture_pass: true
    blocked_ingredient_hits: []
    caution_items: []

  replacement_food_item_ids: []

  knowledge_status: DRAFT
  plan_item_review_status: PENDING_REVIEW
  knowledge_promotion_candidate: false
```

## 6.3 AI 不能自己“估一个营养值”当真值

AI 负责：

```text
设计菜名、食材组合、初始克重、做法、患者可执行方式
```

营养计算服务负责：

```text
kcal / protein / carbohydrate / fat
```

正式计算优先使用：

```text
院内认可营养数据库/计算服务
→ 已批准食物成分数据库
→ 现有组件库估算（仅原型/回归用途）
```

如果 AI 新菜的食材无法映射到可追溯营养数据源：

```yaml
nutrition_status: NEEDS_RECALC
planned_nutrition: null
```

不得由语言模型自行填入伪精确 kcal/P/C/F。

## 6.4 AI 新菜不要求立刻进入全局 ACTIVE 知识库

AI 新菜是**计划级对象**，不是自动创建新的全局知识项。

发布给单个患者的最低逻辑为：

```text
AI_GENERATED_DISH
→ 食材级安全过滤PASS
→ 营养计算完成且来源可追溯
→ 全天闭合/结构校验PASS
→ clinician plan-item review = APPROVED_FOR_PLAN
→ Master publication validator 其余条件通过
→ 可随该患者PUBLISHED计划发布
```

这道菜即使被批准用于某一个患者，也仍可保持：

```yaml
knowledge_status: DRAFT
plan_item_review_status: APPROVED_FOR_PLAN
```

**“批准用于当前计划”不等于“已成为全院 ACTIVE 标准菜品”。**

若某 AI 菜被反复使用、营养稳定且 MDT 希望沉淀，可进入后续知识库标准化流程：

```text
plan-local generated dish
→ repeated clinician approval
→ knowledge_promotion_candidate=true
→ nutrition/MDT standardization
→ 分配正式 component_id
→ ACTIVE standard component
```

---

# 7. 生成前安全过滤：先形成 Allowed / Blocked / Caution 食材空间

AI 生成具体菜前，应先产生内部过滤结果：

```yaml
ingredient_constraint_result:
  allowed_categories: []
  blocked_ingredients: []
  blocked_reasons: {}
  caution_ingredients: []
  caution_reasons: {}
  required_texture: null
  disease_constraints_applied: []
  allergy_constraints_applied: []
  intolerance_constraints_applied: []
```

### 硬性规则

- 明确过敏食物不得进入生成候选；
- 明确不耐受按对应替换规则处理；
- 疾病限制在生成前应用，而不是生成后加免责声明；
- 禁止生成减肥茶、排毒产品、不明保健品、未经项目批准的药物/补充剂作为 FOOD 方案；
- ONS 仍由营养支持/医护审核路径管理，AI 可以提示 `ONS_EVALUATION_RECOMMENDED`，不得自行指定产品和剂量；
- 若患者存在吞咽、咀嚼、严重恶心或其他影响质地的问题，必须在菜品结构和做法中实际体现。

---

# 8. 算法份量 → 可执行份量：必须有“执行化”步骤

六型回归证明，直接把 `0.75 / 1.25 / 1.5` 乘到复合组件会产生难执行份量。

因此每个计划食物对象必须区分：

```yaml
algorithmic_portion: ""
executable_portion: ""
portion_adjustment_required: true | false
portion_adjustment_reason: null
nutrition_recalculated_after_portion_adjustment: true | false | null
```

## 8.1 默认禁止直接展示的伪精确例子

```text
鸡蛋 37.5 g / 62.5 g
牛奶 312.5 ml
大米 43.75 g
酸奶 187.5 ml
```

这些数字可以存在于算法中间层，但不得默认直接成为患者执行量。

## 8.2 执行化原则

- 鸡蛋等离散食物优先转换成“1个/2个”等可执行单位，并保存近似可食克重；
- 奶/酸奶/豆浆优先映射到项目认可的常见包装/杯量；
- 谷物、肉类、蔬菜使用 MDT 允许的称重步长；
- 调整一个食材后，不允许只四舍五入显示数字，必须重新计算该餐和全天营养；
- 若执行化后无法满足目标，应通过其他食材/餐次重新组合，而不是返回难执行的小数份量。

### 复合标准组件的特别规则

若一个标准组件包含多个离散食材，例如“牛奶+鸡蛋”，禁止简单把整个组合乘 `1.25` 后生成“牛奶312.5 ml + 鸡蛋62.5 g”。

应：

```text
拆解组件食材
→ 先执行化各食材
→ 用其他允许食材补足差异
→ 重新计算整餐
```

---

# 9. D/E 营养恢复生成器：不能只放大普通健康餐

当 01 Master 传入：

```yaml
nutrition_generation_flags:
  recovery_priority: true
```

FOOD 生成器必须启用恢复优先逻辑。

## 9.1 优先标签

```text
RECOVERY_DENSE
HIGH_PROTEIN_DENSITY
HIGH_ENERGY_DENSITY
EARLY_SATIETY_FRIENDLY
NAUSEA_FRIENDLY
SOFT_EASY_TO_EAT
SMALL_VOLUME_SNACK
```

## 9.2 早饱/摄入不足

优先：

- 减少单餐体积；
- 增加有效餐次/小加餐；
- 优先蛋白与主食；
- 避免用大量低能量蔬菜、水果或汤水占据胃容量；
- 同等耐受下提高单位体积的能量/蛋白密度；
- 允许 AI 动态生成更适合的软饭、蒸蛋、肉末/豆腐组合、小体积加餐等。

禁止：

```text
仅通过所有普通组件 ×1.25 / ×1.5 来完成“营养恢复”
```

## 9.3 恶心/气味敏感

- 优先温凉、清淡、少油烟、少强烈气味的烹调；
- 鱼虾等气味可能加重恶心时，使用已允许的禽肉、蛋、豆腐等替代；
- 不以“必须完成某一道菜”为优先，完成率与耐受优先。

## 9.4 组件不足时的处理

V4 不再要求“组件不足就停止生成”。

正确流程：

```text
标准组件不足
→ 尝试 AI_GENERATED_DISH
→ 安全过滤
→ 营养计算/重算
→ 医护审核
```

只有在以下情况才进入 `knowledge_gap/manual_review_required`：

- 缺乏安全可用食材；
- 无法可靠计算营养；
- 疾病/再喂养风险需要专科决定；
- 质地/吞咽等超出当前 FOOD 能力边界。

---

# 10. F complexity overlay：简化“怎么吃”，不改变 underlying 营养方向

当：

```yaml
complexity_overlay: F
```

FOOD 优先：

- 每日菜品数量不过度复杂；
- 食材重复可以适度增加，以换取完成率；
- 优先患者能购买/能做/家属能协助的菜；
- 外卖患者优先输出可识别的点餐结构和菜名，而不是要求复杂称重烹调；
- 记录以完成比例、主蛋白、替换、额外摄入为核心；
- 不能为了“多样性”强行增加执行负担。

例如：

```text
primary_nutrition_phenotype = B
complexity_overlay = F
```

营养方向仍按 B 的代谢控制/减脂保肌；F 只负责简化菜单、记录和替换路径。

---

# 11. 替换规则：标准组件与 AI 新菜都必须“换菜 + 重算”

患者端显示菜名替换，后台保存机器映射。

统一流程：

```text
planned food item
  ↓
allergy / intolerance / disease / texture / symptom filter
  ↓
allowed replacement foods/dishes
  ↓
patient/clinician selects replacement
  ↓
recalculate meal nutrition
  ↓
recalculate daily kcal/P/C/F
  ↓
save actual item + actual portion
```

### replacement 对象

```yaml
replacement_option:
  food_item_type: STANDARD_COMPONENT | AI_GENERATED_DISH
  food_item_id: ""
  patient_display_name: ""
  executable_portion: ""
  nutrition_after_replacement:
    kcal: null
    protein_g: null
    carbohydrate_g: null
    fat_g: null
  recalculation_status: CALCULATED | NEEDS_RECALC
```

### 强制约束

- 不允许仅换自然语言菜名而不保存实际替换对象；
- 替换后必须重新计算；
- 同餐、同功能、目标相近优先，但 D/E 症状耐受可优先于“严格同类”；
- PUBLISHED 后系统不得自动随机换菜；患者实际替换进入 `patient_record`。

---

# 12. 营养计算与来源：AI 设计，计算引擎算数

## 12.1 nutrition_source 优先级

```text
院内认可营养计算服务
→ 已批准食物成分数据库
→ 本库标准组件营养估算（原型/回归用途）
→ 无可追溯来源：NEEDS_RECALC / null
```

每个计划项必须保存：

```yaml
nutrition_source:
  source_type: HOSPITAL_SERVICE | APPROVED_DATABASE | LIBRARY_ESTIMATE | NONE
  source_version: null
  calculation_timestamp: null
  nutrition_status: CALCULATED | LIBRARY_ESTIMATE | NEEDS_RECALC
```

## 12.2 语言模型不得成为营养数据源

禁止：

```yaml
nutrition_source:
  source_type: LLM_GUESS
```

如果没有可追溯数据源，数值必须 `null` 或明确为待重算，不能为了输出完整而编造。

## 12.3 全天闭合

在 `EXACT_ACTIVE / EXACT_PROVISIONAL_REVIEW` 中：

- 每餐营养必须能由计划项复算；
- 全天总量必须等于各餐之和；
- 7日平均必须能由 Day1–Day7 复算；
- 份量执行化、替换后均需重算；
- 闭合容差只能来自 ACTIVE/PROVISIONAL 项目配置，AI 不自行发明百分比。

---

# 13. `diet_plan_trace` V4：统一支持标准组件和 AI 动态菜品

从 V4 开始，`diet_plan_trace` 是固定必填合同。**仅输出一串 `C004@1.0` 或 used IDs 不能算完整 trace。**

## 13.1 固定结构

```yaml
diet_plan_trace:
  trace_schema_version: FOOD_TRACE_V4

  generation_context:
    primary_nutrition_phenotype: A | B | C | D | E | null
    complexity_overlay: F | none
    safety_level: GREEN | YELLOW | RED
    diet_generation_mode: EXACT_ACTIVE | EXACT_PROVISIONAL_REVIEW | STRUCTURE_ONLY

  nutrition_source_versions: []

  week_targets:
    energy_target_status: ACTIVE | PROVISIONAL | UNAVAILABLE
    prescribed_energy_kcal: null
    provisional_energy_kcal: null
    protein_target_status: ACTIVE | PROVISIONAL | UNAVAILABLE
    protein_target_g: null
    carbohydrate_target_g: null
    fat_target_g: null
    meal_distribution: null

  days:
    - day: 1
      meals:
        - meal_slot: breakfast
          patient_meal_name: "燕麦鸡蛋早餐"

          food_items:
            - food_item_type: STANDARD_COMPONENT
              food_item_id: C004
              component_id: C004
              generated_dish_id: null
              component_name: 燕麦早餐份
              patient_display_name: 燕麦粥
              category: staple
              portion_scale: 1.0
              algorithmic_portion: "燕麦40g"
              executable_portion: "燕麦40g（干重）"
              planned_grams: 40
              weight_basis: dry_weight
              ingredients: []
              planned_nutrition:
                kcal: null
                protein_g: null
                carbohydrate_g: null
                fat_g: null
              nutrition_source_version: null
              nutrition_status: NEEDS_RECALC
              replacement_food_item_ids: []
              knowledge_status: UNVERIFIED
              plan_item_review_status: NOT_REQUIRED

            - food_item_type: AI_GENERATED_DISH
              food_item_id: GD-PLAN-D1-breakfast-01
              component_id: null
              generated_dish_id: GD-PLAN-D1-breakfast-01
              component_name: null
              patient_display_name: 山药鸡肉蒸蛋
              category: mixed_dish
              portion_scale: null
              algorithmic_portion: "1份"
              executable_portion: "1小碗"
              planned_grams: null
              weight_basis: mixed
              ingredients:
                - ingredient_name: 山药
                  nutrition_db_food_id: null
                  algorithmic_grams: 80
                  executable_grams: 80
                  weight_basis: raw_edible_weight
                - ingredient_name: 鸡胸肉
                  nutrition_db_food_id: null
                  algorithmic_grams: 60
                  executable_grams: 60
                  weight_basis: raw_edible_weight
                - ingredient_name: 鸡蛋
                  nutrition_db_food_id: null
                  algorithmic_grams: 50
                  executable_grams: 50
                  weight_basis: raw_edible_weight
              planned_nutrition:
                kcal: null
                protein_g: null
                carbohydrate_g: null
                fat_g: null
              nutrition_source_version: null
              nutrition_status: NEEDS_RECALC
              replacement_food_item_ids: []
              knowledge_status: DRAFT
              plan_item_review_status: PENDING_REVIEW

          planned_meal_total:
            kcal: null
            protein_g: null
            carbohydrate_g: null
            fat_g: null

      planned_daily_total:
        kcal: null
        protein_g: null
        carbohydrate_g: null
        fat_g: null

      food_item_ids_used: []
      component_ids_used: []
      generated_dish_ids_used: []

  seven_day_summary:
    mean_kcal: null
    mean_protein_g: null
    mean_carbohydrate_g: null
    mean_fat_g: null
    food_item_ids_used: []
    component_ids_used: []
    generated_dish_ids_used: []
    food_item_use_counts: {}
    nutrition_source_versions: []

  trace_validation:
    all_days_present: true | false
    all_meals_present: true | false
    all_patient_meals_have_names: true | false
    all_food_items_have_ids: true | false
    all_food_items_traceable: true | false
    all_food_items_have_executable_portions: true | false
    all_required_ingredients_structured: true | false
    all_generated_dishes_safety_filtered: true | false | null
    all_generated_dishes_nutrition_calculated: true | false | null
    all_generated_dishes_reviewed_for_plan: true | false | null
    patient_menu_matches_trace: true | false
    nutrition_totals_reproducible: true | false | null
    nutrition_recalculated_after_portion_adjustment: true | false | null
    nutrition_recalculated_after_replacement: true | false | null
    all_standard_component_statuses_known: true | false | null
    all_standard_components_active: true | false | null
```

## 13.2 强制要求

- `days` 覆盖 Day1–Day7；
- 每餐必须有 `patient_meal_name`；
- 每个实际食物对象单独记录；
- 每个对象必须有唯一 `food_item_id`；
- 标准组件使用 `component_id`；AI 新菜使用 `generated_dish_id`；
- 患者端食材/份量必须与 trace 一致；
- 每个对象必须保存 `executable_portion`；
- AI 新菜必须保存结构化 `ingredients`；
- `EXACT_*` 模式下营养数值必须有可追溯来源并可复算；
- `STRUCTURE_ONLY` 模式允许营养值为 null，但必须明确模式，不能伪装精确闭合；
- AI 新菜若仍 `PENDING_REVIEW`，可以存在于审核草稿，但 publication 必须阻断；
- 不允许仅写 `breakfast: [C004@1.0, P015@1.25]` 后声称 trace 完整。

---

# 14. Plan 与 Actual：执行记录继续分开

`plan_task` 保存“计划吃什么”，`patient_record` 保存“实际吃了什么”。

统一执行对象：

```yaml
actual_food_record:
  meal_slot: breakfast | lunch | dinner | snack

  planned_food_item_type: STANDARD_COMPONENT | AI_GENERATED_DISH
  planned_food_item_id: ""
  actual_food_item_type: STANDARD_COMPONENT | AI_GENERATED_DISH | OUTSIDE_FOOD
  actual_food_item_id: ""

  planned_executable_portion: ""
  actual_portion_description: ""
  completion_ratio: 1.0
  main_protein_completion_ratio: null

  replacement_used: false
  replacement_from_id: null
  replacement_to_id: null

  extra_intake: []

  actual_nutrition_estimate:
    kcal: null
    protein_g: null
    carbohydrate_g: null
    fat_g: null

  estimate: false
  patient_confirmed: false
  photo_ref: null
```

照片仍只是辅助；实际摄入优先依据患者确认的完成比例、替换和额外摄入。

---

# 15. FOOD Validator V4：内容完整性与发布资格分开

本文件向 Master 返回：

```yaml
food_validation_result:
  trace_schema_version: FOOD_TRACE_V4

  structural:
    all_days_present: true | false
    all_meals_present: true | false
    all_patient_meals_have_names: true | false
    all_food_items_have_ids: true | false
    all_food_items_traceable: true | false
    all_food_items_have_executable_portions: true | false
    all_required_ingredients_structured: true | false
    patient_menu_matches_trace: true | false
    nutrition_totals_reproducible: true | false | null

  generated_dish_validation:
    generated_dish_count: 0
    all_generated_dishes_safety_filtered: true | false | null
    all_generated_dishes_nutrition_calculated: true | false | null
    all_generated_dishes_reviewed_for_plan: true | false | null
    generated_dishes_pending_review: []
    generated_dishes_needing_recalc: []

  standard_component_validation:
    knowledge_activation_status: VERIFIED | PARTIALLY_VERIFIED | UNVERIFIED
    all_component_statuses_known: true | false | null
    all_components_active: true | false | null
    non_active_component_ids: null | []
    unverified_component_ids: []

  nutrition:
    diet_generation_mode: EXACT_ACTIVE | EXACT_PROVISIONAL_REVIEW | STRUCTURE_ONLY
    daily_nutrition_closed: true | false | null
    portion_adjustment_integrity_pass: true | false | null
    replacement_integrity_pass: true | false | null
    nutrition_source_versions: []

  publication_blockers: []
```

## 15.1 必须导致 `content_validation = FAIL`

- Day1–Day7 缺失；
- 患者菜单缺餐次、菜名、食材或可执行份量；
- 患者端使用“同Day1/同上/菜单A”等代替完整内容；
- 关键食物对象没有唯一 ID；
- AI 新菜没有结构化食材；
- trace 与患者菜单不一致；
- `EXACT_*` 模式下全天营养无法由明细复算；
- 执行化份量发生变化但没有重算营养；
- 替换后没有重算；
- `STRUCTURE_ONLY` 却宣称精确 kcal/P/C/F 闭合；
- 过敏/禁忌食材实际进入菜单且未被安全规则阻断；
- 仅输出 `C004@1.0` 等简化摘要，却声明完整 trace。

## 15.2 以下情况可以 `content PASS + warning`，但可能阻断发布

- 标准组件 ACTIVE 状态未核实；
- 营养数据库版本尚待院内最终批准；
- `energy_target=PROVISIONAL`；
- AI 新菜营养已算清、结构完整，但尚待 clinician plan-item review；
- 计划仍是 `AI_GENERATED_PENDING_REVIEW`。

## 15.3 Publication 对 AI 新菜的特别规则

AI 新菜不要求先晋升为全局 ACTIVE component，但发布前必须满足：

```text
safety_filter_result PASS
+ nutrition_status = CALCULATED（使用允许数据源）
+ executable portion 已确定
+ patient menu 与 trace 一致
+ plan_item_review_status = APPROVED_FOR_PLAN
+ Master 其余 publication 条件通过
```

若任一 AI 新菜仍：

```text
PENDING_REVIEW
NEEDS_RECALC
REJECTED
```

则：

```yaml
publication_ready: false
publication_blocked: true
```

---

# 16. FOOD 知识库自增长：审核通过的 AI 菜可以沉淀，但不是自动学习

为了避免把全局 FOOD 库人工扩到几百/几千道菜，允许建立“计划级生成 → 人工审核 → 候选沉淀”的治理流程。

```text
AI生成患者专属菜
→ 当前患者方案审核通过
→ 保存 plan-local dish + 实际执行反馈
→ 多次被医护认可/患者执行良好
→ 标记 knowledge_promotion_candidate
→ 营养/MDT标准化
→ 分配正式 component_id
→ ACTIVE 标准组件
```

**禁止**模型因为某一次审核通过，就自行把菜写入全局 ACTIVE 知识库。

建议后续沉淀时保存：

- 标准菜名；
- 标准食材与克重；
- 可执行份量；
- 营养数据源；
- phenotype / goal / disease / texture 标签；
- 替换组；
- 审核责任人/版本；
- 患者执行反馈摘要。

---

# 17. 第一周方案推荐输出顺序

AI 生成完整第一周方案时，FOOD 部分推荐顺序：

```text
营养目标/状态摘要
→ 患者可读 Day1–Day7 完整食谱
→ 每餐菜名/食材/可执行份量/做法/菜名替换
→ 每日营养汇总（仅在允许模式下）
→ 医护审核提示
→ diet_plan_trace FOOD_TRACE_V4
→ food_validation_result
→ 交给 Master 三层 Validator
```

患者可读区不得被 YAML、组件 ID、PENDING 字段淹没。

---

# 18. 六型回归后的 FOOD 最低验收用例

| 场景 | V4 预期 |
|---|---|
| A 型，能量 provisional，安全绿 | 可生成审核用完整菜单；患者端无 C/P/V/S 编号；publication blocked |
| B 型 + 高血压/糖脂异常 | 生成前应用疾病过滤；可混用标准组件和 AI 新菜；不生成被禁食材 |
| C 型肌肉优先 | 每餐主蛋白明确；不为追体重下降牺牲蛋白/抗阻支持 |
| D 型 + 早饱 | 小体积高营养密度优先；不得只把普通组件全部 ×1.5；允许 AI 生成恢复型小份菜/加餐 |
| E 型 + 摄入下降/再喂养风险未清 | `energy_target=UNAVAILABLE` 时只能 STRUCTURE_ONLY；不得暗中创建 1700–1800 kcal 精确菜单 |
| E 型已有可信 provisional target | 可用 EXACT_PROVISIONAL_REVIEW 生成完整审核菜单；不得发布 |
| F overlay + B direction | 营养方向按 B，菜单和记录按 F 简化；不因多样性增加执行负担 |
| 明确海鲜过敏 | 生成前阻断所有含鱼虾贝类候选；不得靠餐后提醒补救 |
| 乳糖不耐受 | 牛奶/酸奶相关候选先走耐受替换；不等同牛奶蛋白过敏 |
| 标准49项不足 | 允许 AI_GENERATED_DISH；必须安全过滤、营养重算、医护审核 |
| AI新菜营养无法重算 | `NEEDS_RECALC`；不能输出伪精确营养；publication blocked |
| 患者菜单出现“同Day1” | content FAIL |
| 仅 trace `C004@1.0` | content FAIL |
| 算法算出鸡蛋62.5g | 必须执行化后重算；不能直接显示患者 |

---

# 19. V4 最终原则

FOOD V4 的核心不是“让 AI 随便发明菜”，也不是“把 AI 锁死在49个组件里”，而是：

> **标准组件提供可靠锚点，AI负责受约束地设计患者真正能吃、愿意吃、做得到的菜；评估和 Safety 决定能不能吃，营养计算服务决定营养数值，医护决定能不能发布，后台 trace 保证全过程可追溯。**

因此最终架构为：

```text
49个及后续ACTIVE标准组件
        +
AI_GENERATED_DISH 计划级动态菜品
        ↓
患者评估约束
        ↓
安全/过敏/疾病/质地过滤
        ↓
算法份量 → 可执行份量
        ↓
营养计算/重算
        ↓
全天闭合
        ↓
医护审核
        ↓
PUBLISHED患者食谱
        ↓
实际执行记录
        ↓
可选知识库沉淀
```

---

# SOURCE: 肺结节患者术前菜品与食谱组件库_V2.0_完整版_MDT审阅_AI调用版(1).docx

肺结节患者术前菜品与食谱组件库 V2.0

完整版｜MDT审阅稿 · 产品规则底稿 · AI/Codex调用版

版本日期：2026-09-12｜与《营养与能量计算规则 V2.0》《A-F分型参数配置 V2.0》及Q56规则对齐

本库是“可计算、可替换、可组合”的术前食谱知识库，不是固定7天菜单，也不是“A型一套菜、B型一套菜”。系统应先完成患者评估、A-F主表型、Q56目标、手术窗口、能量/蛋白与疾病修饰，再从本库中组合成患者可直接执行的三餐/加餐。

V2.0坚持“规则决定边界，组件提供素材，AI/Codex负责组合，医护最终审核”的架构。组件库不得覆盖能量规则、安全规则或医护已编辑的PUBLISHED方案。

谷物、杂豆、面粉默认按生重/干重；肉蛋奶豆、蔬果按可食部重量；烹调油单列。患者端可同时显示家庭份量，但计算层必须保存标准克重。

V1.0已有49个组件的kcal/P/C/F仅用于匹配和原型验证；正式上线应由院内认可营养计算服务重算并记录source_version。

烹调油、糖、酱料、勾芡等必须进入计算；油炸、浓油赤酱、糖醋汁不作为默认模板。

患者采用拍照/家庭份量时，actual intake保留estimate=true；照片不能证明实际全部摄入。

同一组件只允许0.5、0.75、1、1.25、1.5份等离散缩放；不允许AI生成任意且难执行的137g、83g等克重。

说明：以上营养数字继承V1.0，仅用于原型匹配；上线前由院内认可营养计算服务统一重算并更新nutrition_source_version。

说明：以上营养数字继承V1.0，仅用于原型匹配；上线前由院内认可营养计算服务统一重算并更新nutrition_source_version。

说明：以上营养数字继承V1.0，仅用于原型匹配；上线前由院内认可营养计算服务统一重算并更新nutrition_source_version。

说明：以上营养数字继承V1.0，仅用于原型匹配；上线前由院内认可营养计算服务统一重算并更新nutrition_source_version。

为避免当前49个组件导致7天菜单过于机械，V2.0增加以下“扩展候选池”。本表只定义菜品方向、食材结构和使用标签，不在未重算前提供伪精确kcal/P/C/F；Codex导入后状态必须为DRAFT。

V2.0不把“AI照片识别出来的kcal”当作实际摄入真值。更可靠的记录方式是以PUBLISHED计划餐为锚点，让患者确认实际完成、替换和额外摄入；照片作为辅助核对。

不要把组合示例写死成“某表型固定7天菜单”。同一患者的菜品应由当前日目标、允许组件和执行场景动态组合。

生成前必须先读取daily_energy_target_kcal、protein_target_g和meal_distribution；若这些字段为null，不得擅自补一个精确热量。

选菜前先执行安全/过敏/疾病/质地过滤，再做排序；不能生成后才靠文字说“如过敏请勿食”。

每餐计划必须保存component_id、portion_scale、planned_grams、planned_nutrition、nutrition_source_version和replacement_group。

每餐患者端必须显示：菜名、主要食材、克重/份数、烹饪方式、简要做法、估算kcal/P/C/F、至少1个替换。

替换必须是同餐、同类、目标相近；替换后重新计算全天总量，并保存actual component/portion。

禁止AI新增“减肥茶、排毒产品、不明保健品”等库外高风险项目；库外普通家常菜只能标为DRAFT候选，营养重算+审核后才能进入ACTIVE。

PUBLISHED方案中的最终菜名和克重以医护审核结果为准；plan_task和patient_record不得重新随机选菜。

拍照识别只作为estimate；实际摄入优先使用计划完成比例、替换、额外摄入和患者确认。

Q56仅改变目标/排序；不能用“目标减4kg”直接倒算食谱热量，也不能突破ACTIVE能量和安全规则。

确认V1.0 49个组件是否继续保留ACTIVE候选，是否需要删除/合并重复菜品。

确认营养数据源、重量口径和重算服务；V1.0估算值不应直接作为正式临床处方唯一依据。

确认餐次分配、替换容差、份量档位、重复上限和外食映射。

确认A-F/Q56目标标签是否符合本院术前管理实践。

确认D/E软食、小体积高营养和加餐模板；ONS仍由独立营养支持规则管理。

确认疾病标签：糖代谢、高血压、血脂、高尿酸、肝纤维化、CKD等应由对应专科ACTIVE规则覆盖。

确认患者端记录字段：计划完成比例/主蛋白完成/替换/额外摄入为核心，照片仅辅助。

确认扩展候选池哪些条目进入正式营养重算与审核。

1. 国家卫生健康委办公厅：《成人肥胖食养指南（2024年版）》。

2. 国家卫生健康委：《肥胖症诊疗指南（2024年版）》。

3. 国家卫生健康委办公厅：《成人糖尿病食养指南（2023年版）》。

4. 国家卫生健康委办公厅：《成人高血压食养指南（2023年版）》。

5. 国家卫生健康委办公厅：《成人高脂血症食养指南（2023年版）》。

6. 国家卫生健康委办公厅：《成人高尿酸血症与痛风食养指南（2024年版）》。

7. 中国营养学会：《中国居民膳食指南（2022）》。

8. ESPEN practical guideline: Clinical Nutrition in cancer (2021)；ESPEN guideline on clinical nutrition in surgery – Update 2025。

9. 项目内部：《肺结节患者术前营养与能量计算规则 V2.0》。

10. 项目内部：《肺结节患者术前A-F分型参数配置候选值 V2.0》。

11. 项目内部：《肝弹性成像与肝脏代谢风险处理规则》。

12. 项目内部：《肺结节患者术前多学科代谢健康管理 AI 方案生成提示词》。

13. V1.0组件库：49个组件与12个组合示例（本V2.0保持原ID和原估算值，新增结构化标签与扩展候选池）。

V2.0说明：本库用于“能量/蛋白目标 → 组件化选菜 → 结构化三餐/加餐 → 医护审核 → patient_record实际执行”的产品开发闭环，不替代注册营养师/临床营养科的个体化处方。


## Table


项目 | V2.0定义

文件定位 | 本文件解决“每日总能量/蛋白/碳水/脂肪已经确定以后，早餐、午餐、晚餐和加餐具体吃什么、吃多少、怎么做、能换什么”。它不负责决定TEE或能量缺口。

与能量规则的关系 | 先由《营养与能量计算规则 V2.0》得到 daily_energy_target_kcal、protein_target_g、carb_target_g、fat_target_g 和 meal_distribution，再调用本组件库完成菜品组合。

与安全规则的关系 | 安全/禁忌引擎负责先过滤过敏、不耐受、疾病限制、黄色/红色风险等；本库只从“允许集合”中选菜。

V2.0重点 | 保留V1.0全部49个组件与ID；新增Q56/目标标签、A-F调用策略、疾病标签、外食/软食/高能量密度组合模板、患者记录闭环、周调整映射和Codex结构化合同。

运行边界 | 组件营养值仍为V1.0匹配用估算值；正式上线必须由中国食物成分数据/院内营养计算服务重算并版本化。任何新扩展组件在未重算和审核前均为DRAFT，不得进入PUBLISHED方案。


## Table


优先级 | 来源 | 职责

1 | 安全规则/禁忌替代引擎 | 先过滤红黄风险、过敏、不耐受、疾病限制、吞咽/咀嚼等。

2 | ACTIVE MDT参数 | 决定REE/TEE、A-F能量比例、蛋白、宏量营养素、餐次分配、允许误差。

3 | Q56医护目标（选填） | 决定标准减脂/强化减脂/保肌/营养恢复/代谢控制等阶段方向；不直接写死菜名。

4 | A-F表型与修饰标签 | 改变组件优先级与组合方式；不是固定菜单。

5 | 本V2.0菜品/食谱组件库 | 提供已审核食物、菜品、组合模板、替代项和执行标签。

6 | 方案模板 | 规定患者端最终显示：菜名+食材/克重+做法+营养+替换+注意事项。

7 | AI/Codex编排 | 只能在1–6层许可范围内组合和解释，不自行发明医学阈值或未审核菜品。


## Table


输入 | 来源 | 系统要求

daily_energy_target_kcal | 营养与能量计算规则V2.0 | 必需；若为null，不生成伪精确全天kcal菜单，只生成保守结构并标注待确认。

protein_target_g | ACTIVE蛋白规则 | 建议必需；用于保证每餐主蛋白和全天闭合。

carb_target_g / fat_target_g | ACTIVE宏量规则 | 可配置；缺失时不能伪造精确百分比。

meal_distribution | ACTIVE餐次配置 | 早餐/午餐/晚餐/加餐比例；加餐必须从全天总能量中重新分配。

A-F phenotype | assessment_result/profile | 用于组件排序与保护规则。

Q56 goal | Assessment V1.2 | 选填；空缺则使用A-F默认路径。

过敏/不耐受/进食困难 | Q31–Q33 | 生成前过滤，不是生成后仅文字提醒。

疾病/实验室/肝弹性 | Q43–Q50 | 有资料则叠加疾病标签；缺失不等于正常。

执行障碍/饮食记录偏好 | Q51–Q52 | 决定菜单复杂度、外食/家庭份量/拍照模式。

上一周patient_record | 周复评 | 决定下一周是维持、简化、保肌、营养恢复或强化候选。


## Table


字段 | 定义

component_id | 唯一ID；V1.0已有ID保持不变，避免破坏历史方案。

name | 患者和医护可读名称。

category | staple / protein / vegetable / snack / template。

ingredients | 食材、标准克重/份数与重量口径。

cooking_method | 清蒸、炖、煮、少油炒等标准做法。

nutrition | 估算kcal、P/C/F；正式上线由认可营养数据源重算。

nutrition_source_version | 营养数据来源和版本，必须可追溯。

portion_scales | 仅允许0.5/0.75/1/1.25/1.5等离散档位；超出则优先改餐次/替换。

phenotype_tags | A/B/C/D/E/F适用倾向；只影响排序，不自动禁用。

goal_tags | 标准减脂、强化减脂、保肌/增肌、营养恢复、代谢控制、执行支持等。

disease_tags | 糖代谢、高血压、血脂、尿酸、MASLD/肝纤维化、CKD review等。

texture_tags | normal / soft / semi-liquid等。

meal_slot | breakfast / lunch / dinner / snack / any。

setting_tags | 家庭、便携、外食、食堂、软食等。

allergy_flags | 奶/蛋/海鲜/坚果/花生/大豆等。

caution | 慎用/限制/需专科覆盖。

replacement_group | 同类替换组和候选组件ID。

status | DRAFT / ACTIVE / RETIRED；只有ACTIVE进入正式方案。


## Table


步骤 | 规则

1. 确定餐次目标 | 从daily target和meal_distribution计算breakfast/lunch/dinner/snack的kcal及宏量目标。

2. 选择餐架构 | 早餐通常“主食+蛋白+按需蔬果”；午/晚餐通常“主食+1道主蛋白菜+1–2道非淀粉蔬菜”；D/E可3+1或3+2。

3. 安全过滤 | 先排除过敏、不耐受、吞咽/咀嚼不适合、疾病/专科限制和当前安全状态不允许的组件。

4. 目标排序 | 根据A-F、Q56、疾病目标、患者口味、外食/家庭场景对允许组件排序；不允许表型固定菜单。

5. 离散缩放 | 用0.5/0.75/1/1.25/1.5份调整主食、主蛋白、蔬菜或加餐。

6. 营养闭合 | 调用营养计算服务重算每餐和全天kcal/P/C/F；在ACTIVE容差内闭合。

7. 质量检查 | 减脂时不牺牲蛋白；C型保肌；D/E不以大体积低能量蔬菜挤占主食/蛋白；加餐必须从总能量中扣除。

8. 多样性/执行性 | 有可替代项时避免同一核心菜机械重复；F型或执行困难反而允许固定2–3套可执行菜单。重复上限由MDT配置。

9. 输出替换 | 每餐至少给1个同类替换；替换后必须重新计算，不允许只改文字。

10. 保存计划 | 每餐保存component_id、portion_scale、planned grams、planned nutrition、source_version。


## Table


Q56/目标 | 组件调用倾向 | 边界

Q56空缺 | 按A-F默认能量/蛋白规则生成；本库负责匹配组件，不停在“待医护逐项设数值”。 | 使用A-F默认排序。

标准减脂 | 提高全谷、非淀粉蔬菜、优质蛋白、低油组件优先级。 | 不删除主食；份量由总能量闭合决定。

强化减脂 | 仅A/B且通过门槛；优先降低能量密度、控制油和精制糖，同时保留主蛋白。 | 不得为了追Q56体重目标削减蛋白或跳餐。

体重维持/保肌 | 每餐保证主蛋白；主食按TEE/宏量目标正常分配。 | 不因高体脂自动进入减脂。

营养恢复/增重 | 优先高营养密度、小体积、易入口组合；必要时加餐。 | D/E或食欲差不使用大量低能量蔬菜占胃容量。

停止继续下降 | 先提高实际完成度和能量密度，处理早饱/恶心/吞咽等。 | 不能仅把处方kcal写高而不改变执行路径。

增肌 | 优先蛋白分配、奶/蛋/鱼禽/豆类和抗阻配套。 | 总能量与肾功能等限制优先。

代谢控制 | 叠加糖代谢/血压/血脂/尿酸/MASLD等标签。 | 疾病指标未知时不做伪精确限制。

提高运动能力/改善肺功能/术前综合准备 | 饮食以营养充分、保肌、可执行为基础，不因功能目标额外制造能量缺口。 | 手术窗口越短越强调稳定摄入。


## Table


表型 | 选菜策略 | 自动化限制

A 超重/高体脂 | 优先全谷/杂粮倾向、足量优质蛋白、低能量密度蔬菜、少油做法。 | 不固定菜谱；不自动删除主食。

B 肥胖+代谢异常 | A基础上叠加糖/压/脂/尿酸/MASLD疾病标签。 | 疾病限制必须来自ACTIVE规则。

C 高体脂+肌少风险 | 每餐主蛋白优先，必要时蛋白加餐；能量底线优先。 | 避免只靠长时间有氧和过快减重。

D 消瘦/营养风险 | 高营养密度、少量多餐、软食/奶豆/蛋/鱼禽等容易完成组合。 | 不进入减重型选菜逻辑。

E 非意愿下降/摄入不足 | 先保证摄入和蛋白；小份、多餐、软食、加餐优先。 | 持续下降或再喂养风险→营养科路径。

F 复杂/执行困难 | 固定2–3套简单可替换菜单，减少选择和步骤；家属协作。 | 目标是完成率和安全，不是菜单复杂度。


## Table


餐次/场景 | 基础结构 | 组件来源 | 系统说明

早餐 | 主食0.5–1.5份 + 蛋/奶/豆等蛋白 + 按需蔬果 | C004/C005/C006 + P015/S009等 | 外食/时间少可用便携模板；糖代谢异常优先低添加糖。

午餐 | 主食 + 1道主蛋白菜 + 1–2道非淀粉蔬菜 | C001–C008 + P001–P014 + V001–V012 | 通常为全天较大餐次；外食时使用“主食+掌心蛋白+蔬菜”映射回组件。

晚餐 | 主食 + 主蛋白菜 + 蔬菜 | 同午餐 | 不极端取消晚餐；距睡眠近时根据习惯和症状调整。

加餐 | 奶/酸奶/豆浆 + 水果/蛋/少量坚果/小份主食 | S001–S010 | 不是额外热量；必须从全天目标重新分配。

软食/小体积 | 粥/软主食 + 蒸蛋/豆腐羹/鱼等软蛋白 + 熟软蔬菜 | C009/C010 + P014/P007等 | 适用于早饱、咀嚼困难、D/E；吞咽障碍须按专科质地要求。

外食/食堂 | 选择清蒸/炖/白灼/少油炒，记录主食量、主蛋白、蔬菜和额外饮料/零食 | 映射到最接近组件并estimate=true | 不要求AI凭照片给“精确kcal”；患者确认吃了多少、替换了什么。


## Table


ID | 组件/菜品 | 食材/重量 | V1.0估算营养 | V2目标标签 | 慎用/限制 | 替代

C001 | 白米饭基础份 | 大米50g | 173 kcal / P3.7 C39.0 F0.4 | 标准减脂、体重维持、营养恢复 | 糖代谢异常者优先与全谷/杂豆搭配，不建议单独大量使用。 | 可替换为C002/C003/C005。

C002 | 糙米饭基础份 | 糙米50g | 174 kcal / P3.9 C37.5 F1.4 | 标准减脂、体重维持、营养恢复、强化减脂候选、代谢控制 | 胃肠耐受差或术前极短窗口可降低粗杂粮比例。 | 可与白米1:1混合。

C003 | 杂粮饭基础份 | 大米35g；糙米15g；赤小豆干10g | 206 kcal / P5.8 C44.9 F0.7 | 标准减脂、体重维持、营养恢复、强化减脂候选、代谢控制 | 痛风急性发作/胃肠不适时具体杂豆量按医护意见调整。 | 赤小豆可换绿豆/芸豆等同类。

C004 | 燕麦早餐份 | 燕麦片40g | 151 kcal / P6.0 C26.4 F2.7 | 标准减脂、体重维持、营养恢复、强化减脂候选、代谢控制 | 吞咽或胃肠耐受差时调整稠度。 | 可换小米/杂粮粥。

C005 | 全麦馒头基础份 | 全麦面粉60g | 203 kcal / P7.2 C41.4 F1.5 | 标准减脂、体重维持、营养恢复、强化减脂候选、代谢控制 | 购买成品需关注钠和添加糖。 | 可换全麦面包C011。

C006 | 鲜玉米基础份 | 玉米鲜150g | 168 kcal / P6.0 C34.2 F1.8 | 标准减脂、体重维持、营养恢复 | 消化不良者可减少份量。 | 可换红薯C007。

C007 | 蒸红薯基础份 | 红薯150g | 129 kcal / P2.4 C30.2 F0.2 | 标准减脂、体重维持、营养恢复 | 糖代谢异常者仍需计入主食总量。 | 可换玉米/山药。

C008 | 荞麦面基础份 | 荞麦面干60g | 204 kcal / P7.2 C40.8 F1.5 | 标准减脂、体重维持、营养恢复、强化减脂候选、代谢控制 | 注意面条成品钠含量。 | 可换杂粮饭/全麦馒头。

C009 | 小米粥基础份 | 小米40g | 144 kcal / P3.6 C30.0 F1.2 | 标准减脂、体重维持、营养恢复、D/E优先 | 粥类消化快，糖代谢异常者应搭配蛋白和蔬菜。 | 可换燕麦粥。

C010 | 红豆小米粥 | 小米30g；赤小豆干10g | 141 kcal / P4.7 C28.9 F1.0 | 标准减脂、体重维持、营养恢复 | 胃肠胀气明显时减量或替换。 | 可换燕麦/山药。

C011 | 全麦面包基础份 | 全麦面包70g | 172 kcal / P6.3 C28.7 F2.9 | 标准减脂、体重维持、营养恢复 | 商业面包钠、糖、脂肪差异大，需读取标签。 | 可换全麦馒头。

C012 | 山药主食份 | 山药200g | 114 kcal / P3.8 C24.8 F0.4 | 标准减脂、体重维持、营养恢复 | 能量较低，D/E型若需增加能量应搭配其他主食和蛋白。 | 可换红薯/米饭。


## Table


ID | 组件/菜品 | 食材/重量 | V1.0估算营养 | V2目标标签 | 慎用/限制 | 替代

P001 | 清蒸鲈鱼 | 鲈鱼100g；植物油3g | 132 kcal / P18.6 C0.0 F6.4 | 标准减脂、体重维持/保肌、增肌、营养恢复、强化减脂候选、代谢控制 | 鱼类过敏者禁用；严重肾病蛋白目标另行评估。 | 换鸡胸肉P003/豆腐P008。

P002 | 清蒸鳕鱼 | 鳕鱼100g；植物油3g | 115 kcal / P20.4 C0.0 F3.7 | 标准减脂、体重维持/保肌、增肌、营养恢复 | 鱼类过敏者禁用。 | 换鲈鱼/鸡肉。

P003 | 香草/葱姜鸡胸 | 鸡胸肉100g；植物油5g | 178 kcal / P24.6 C0.0 F8.4 | 标准减脂、体重维持/保肌、增肌、营养恢复、C型/保肌优先 | 咀嚼困难者切碎或改软烂烹饪。 | 换鸡腿肉/鱼/豆腐。

P004 | 去皮鸡腿肉炖菇 | 鸡腿肉去皮100g；香菇鲜80g；植物油4g | 203 kcal / P22.0 C4.2 F11.2 | 标准减脂、体重维持/保肌、增肌、营养恢复、C型/保肌优先 | 脂肪控制严格者优先P003。 | 换鸡胸肉/鱼。

P005 | 番茄炖瘦牛肉 | 瘦牛肉80g；番茄150g；植物油5g | 175 kcal / P17.5 C6.0 F8.7 | 标准减脂、体重维持/保肌、增肌、营养恢复、D/E优先 | 高尿酸/痛风患者肉类总量及急性期策略需按医护规则。 | 换鸡肉/豆腐。

P006 | 芹菜木耳里脊 | 猪里脊80g；芹菜100g；木耳鲜50g；植物油5g | 190 kcal / P17.7 C6.9 F10.2 | 标准减脂、体重维持/保肌、增肌、营养恢复 | 高血压者避免酱油/蚝油过量。 | 换鸡胸/虾仁。

P007 | 虾仁蒸蛋 | 虾仁60g；鸡蛋50g；植物油2g | 149 kcal / P18.8 C1.5 F7.4 | 标准减脂、体重维持/保肌、增肌、营养恢复 | 海鲜过敏禁用；高尿酸患者按个体规则。 | 换鸡蛋豆腐羹。

P008 | 香菇烧北豆腐 | 北豆腐150g；香菇鲜80g；植物油5g | 240 kcal / P20.1 C8.7 F15.0 | 标准减脂、体重维持/保肌、增肌、营养恢复 | 胃肠胀气者观察耐受。 | 换蒸蛋/鱼。

P009 | 番茄炒蛋（少油版） | 鸡蛋100g；番茄200g；植物油5g | 229 kcal / P15.1 C10.8 F14.2 | 标准减脂、体重维持/保肌、增肌、营养恢复 | 血脂异常者鸡蛋总量按整体膳食计划。 | 换蒸蛋/豆腐。

P010 | 西兰花虾仁 | 虾仁80g；西兰花150g；植物油5g | 178 kcal / P22.4 C6.6 F7.3 | 标准减脂、体重维持/保肌、增肌、营养恢复、强化减脂候选、代谢控制、C型/保肌优先 | 海鲜过敏禁用。 | 换鸡胸西兰花。

P011 | 鸡胸彩椒 | 鸡胸肉80g；彩椒150g；植物油5g | 190 kcal / P21.2 C9.0 F8.0 | 标准减脂、体重维持/保肌、增肌、营养恢复、C型/保肌优先 | 无特殊。 | 鸡胸可换里脊/豆腐。

P012 | 牛肉西葫芦 | 瘦牛肉80g；西葫芦150g；植物油5g | 174 kcal / P17.4 C5.7 F8.7 | 标准减脂、体重维持/保肌、增肌、营养恢复 | 高尿酸者按个体规则。 | 换鸡肉/豆腐。

P013 | 冬瓜豆腐虾仁汤 | 虾仁50g；北豆腐100g；冬瓜200g；植物油2g | 208 kcal / P23.2 C8.3 F9.8 | 标准减脂、体重维持/保肌、增肌、营养恢复、D/E优先 | 海鲜过敏者去虾仁并增加豆腐/鸡蛋。 | 换豆腐蛋花汤。

P014 | 鸡蛋豆腐羹 | 鸡蛋50g；北豆腐100g；植物油2g | 206 kcal / P18.9 C4.4 F12.9 | 标准减脂、体重维持/保肌、增肌、营养恢复、D/E优先 | 肾功能限制者按蛋白计划。 | 换虾仁蒸蛋。

P015 | 低脂奶蛋组合 | 低脂牛奶250ml；鸡蛋50g | 187 kcal / P14.9 C13.4 F8.2 | 标准减脂、体重维持/保肌、增肌、营养恢复 | 乳糖不耐受者用无乳糖奶/无糖豆浆。 | 牛奶换无糖豆浆。


## Table


ID | 组件/菜品 | 食材/重量 | V1.0估算营养 | V2目标标签 | 慎用/限制 | 替代

V001 | 蒜香西兰花 | 西兰花200g；植物油5g | 117 kcal / P8.2 C8.6 F6.2 | 标准减脂、体重维持/保肌、强化减脂候选、代谢控制 | 无特殊。 | 换油麦菜/菠菜。

V002 | 清炒菠菜 | 菠菜200g；植物油5g | 101 kcal / P5.2 C9.0 F5.6 | 标准减脂、体重维持/保肌 | 特定草酸/肾病管理按医护意见。 | 换油麦菜。

V003 | 香菇油麦菜 | 油麦菜180g；香菇鲜80g；植物油5g | 93 kcal / P4.3 C7.9 F6.0 | 标准减脂、体重维持/保肌 | 无特殊。 | 换圆白菜/西兰花。

V004 | 清炒圆白菜 | 圆白菜200g；植物油5g | 93 kcal / P3.0 C9.2 F5.4 | 标准减脂、体重维持/保肌、强化减脂候选、代谢控制 | 无特殊。 | 换油麦菜。

V005 | 芹菜木耳 | 芹菜150g；木耳鲜80g；植物油5g | 92 kcal / P2.4 C10.7 F5.3 | 标准减脂、体重维持/保肌、强化减脂候选、代谢控制 | 吞咽/咀嚼差者切细煮软。 | 换西兰花。

V006 | 番茄黄瓜双拼 | 番茄150g；黄瓜150g；植物油3g | 81 kcal / P2.6 C10.5 F3.6 | 标准减脂、体重维持/保肌 | 胃肠敏感/免疫低下时注意食品卫生或改熟食。 | 换熟制蔬菜。

V007 | 彩椒杏鲍菇 | 彩椒100g；杏鲍菇150g；植物油5g | 124 kcal / P3.0 C18.5 F5.3 | 标准减脂、体重维持/保肌 | 无特殊。 | 换香菇青菜。

V008 | 胡萝卜西葫芦 | 胡萝卜80g；西葫芦180g；植物油5g | 110 kcal / P2.2 C13.9 F5.5 | 标准减脂、体重维持/保肌、强化减脂候选、代谢控制 | 无特殊。 | 换冬瓜/圆白菜。

V009 | 冬瓜香菇 | 冬瓜250g；香菇鲜60g；植物油4g | 82 kcal / P2.3 C9.6 F4.7 | 标准减脂、体重维持/保肌 | 无特殊。 | 换西葫芦。

V010 | 少油烧茄子 | 茄子200g；植物油6g | 100 kcal / P2.2 C9.8 F6.4 | 标准减脂、体重维持/保肌 | 传统油炸烧茄子不作为默认。 | 换圆白菜/西葫芦。

V011 | 生菜番茄沙拉（中式清拌） | 生菜150g；番茄150g；植物油3g | 81 kcal / P3.3 C10.3 F3.6 | 标准减脂、体重维持/保肌、强化减脂候选、代谢控制 | 围手术期免疫低下或食品卫生风险高时改熟食。 | 换熟西兰花/菠菜。

V012 | 西兰花胡萝卜双蔬 | 西兰花150g；胡萝卜80g；植物油5g | 130 kcal / P6.9 C13.5 F6.1 | 标准减脂、体重维持/保肌 | 无特殊。 | 换任意两种非淀粉蔬菜。


## Table


ID | 组件/菜品 | 食材/重量 | V1.0估算营养 | V2目标标签 | 慎用/限制 | 替代

S001 | 低脂奶+苹果 | 低脂牛奶200ml；苹果120g | 156 kcal / P7.1 C26.0 F3.2 | 营养恢复、执行支持 | 乳糖不耐受者换无乳糖奶/豆浆。 | 苹果可换梨/橙。

S002 | 无糖酸奶+草莓 | 无糖酸奶150ml；草莓150g | 141 kcal / P6.7 C19.1 F5.0 | 营养恢复、执行支持 | 乳糖不耐受按耐受调整。 | 草莓换猕猴桃。

S003 | 无糖豆浆+梨 | 无糖豆浆250ml；梨120g | 139 kcal / P8.0 C18.7 F4.1 | 营养恢复、执行支持 | 大豆过敏禁用。 | 豆浆换低脂奶。

S004 | 低脂奶+小香蕉 | 低脂牛奶200ml；香蕉80g | 166 kcal / P7.7 C27.2 F3.2 | 营养恢复、执行支持 | 糖代谢异常者按总碳水计划计入。 | 香蕉换苹果。

S005 | 无糖酸奶+核桃 | 无糖酸奶150ml；核桃10g | 158 kcal / P7.2 C8.8 F10.4 | 营养恢复、执行支持 | 坚果过敏禁用；能量密度高，不随意加量。 | 核桃换杏仁10g。

S006 | 低脂奶+橙 | 低脂牛奶200ml；橙150g | 164 kcal / P7.8 C26.2 F3.3 | 营养恢复、执行支持 | 乳糖不耐受者换豆浆。 | 橙换苹果/猕猴桃。

S007 | 苹果+杏仁 | 苹果150g；杏仁10g | 137 kcal / P2.7 C22.7 F5.4 | 营养恢复、执行支持 | 坚果过敏禁用；注意总脂肪。 | 杏仁换核桃。

S008 | 鲜玉米+低脂奶 | 玉米鲜100g；低脂牛奶150ml | 181 kcal / P8.9 C30.0 F3.5 | 营养恢复、执行支持 | 减重能量目标低时份量按总能量调整。 | 玉米换红薯100g。

S009 | 水煮蛋+小番茄 | 鸡蛋50g；番茄150g | 102 kcal / P8.0 C7.4 F4.7 | 营养恢复、执行支持 | 血脂异常者蛋类总量按整体计划。 | 鸡蛋换无糖酸奶。

S010 | 猕猴桃+无糖酸奶 | 猕猴桃100g；无糖酸奶150ml | 154 kcal / P6.8 C22.0 F5.0 | 营养恢复、执行支持 | 乳糖不耐受按耐受调整。 | 酸奶换豆浆。


## Table


候选ID | 名称 | 结构/食材 | 类别 | 适用标签 | 审核要点

XC013 | 大米+糙米混合饭 | 大米+糙米（建议1:1起步，标准份克重由营养科配置） | 主食 | 标准减脂/代谢控制 | 胃肠耐受差可提高白米比例

XC014 | 燕麦小米粥 | 燕麦+小米，稀稠度按耐受 | 主食/早餐 | A–F/早餐 | D/E需避免仅靠稀粥导致能量密度不足

XC015 | 杂豆糙米饭 | 糙米+少量杂豆 | 主食 | A/B/代谢控制 | 胃肠胀气者降低杂豆比例

XP016 | 丝瓜蒸蛋 | 鸡蛋+丝瓜 | 蛋白主菜 | 软食/D/E/通用 | 鸡蛋过敏禁用

XP017 | 肉末豆腐 | 瘦肉末+豆腐 | 蛋白主菜 | C/D/E/保肌 | CKD/蛋白限制按专科

XP018 | 清炖鸡肉冬瓜 | 去皮鸡肉+冬瓜 | 蛋白主菜 | A/B/C/清淡 | 根据总能量配置用油

XP019 | 清蒸鸡腿肉 | 去皮鸡腿肉+葱姜 | 蛋白主菜 | 家庭/便携备餐 | 高盐酱汁不默认

XP020 | 豆腐蒸鱼 | 鱼肉+豆腐 | 蛋白主菜 | C/D/E/保肌 | 鱼/大豆过敏按标签过滤

XP021 | 鸡丝蔬菜汤 | 鸡肉+绿叶菜/菌菇 | 蛋白主菜/汤 | 食欲差/软食 | 不以大量汤液替代完整能量

XV013 | 白灼菜心 | 菜心+少量植物油 | 蔬菜 | A/B/通用 | 酱油量受钠规则约束

XV014 | 蒜蓉生菜 | 生菜+少量植物油 | 蔬菜 | 低能量密度 | 胃肠耐受按患者情况

XV015 | 清炒芥蓝 | 芥蓝+少量植物油 | 蔬菜 | 家庭/粤式 | 咀嚼困难者改软嫩菜

XV016 | 丝瓜木耳 | 丝瓜+木耳+少量油 | 蔬菜 | 清淡/低能量密度 | 吞咽/咀嚼问题需调整质地

XS011 | 无乳糖奶+水果 | 无乳糖奶+完整水果 | 加餐 | 乳糖不耐/执行支持 | 牛奶蛋白过敏不适用

XS012 | 无糖豆浆+鸡蛋 | 无糖豆浆+水煮/蒸蛋 | 加餐/早餐 | 高蛋白/便携 | 大豆或鸡蛋过敏禁用

XS013 | 酸奶+燕麦小份 | 无糖酸奶+小份燕麦 | 加餐 | C/D/E/运动日 | 乳糖不耐按耐受

XS014 | 豆腐脑无糖版+主食小份 | 低糖/无糖豆腐脑+小份主食 | 早餐/加餐 | 外食/便捷 | 钠和配料需核对

XT001 | 食堂标准减脂模板 | 0.75–1份主食+1份主蛋白+2份蔬菜 | 场景模板 | A/B标准/强化 | 需按实际菜品映射与重算

XT002 | 食堂保肌模板 | 1份主食+1–1.25份主蛋白+1–2份蔬菜 | 场景模板 | C/保肌 | 不得为控能量削减主蛋白

XT003 | D/E小体积高营养模板 | 小份主食+软蛋白+小份蔬菜+1份加餐 | 场景模板 | D/E营养恢复 | 出现摄入障碍时优先完成率

XT004 | 便利早餐模板 | 全谷/主食+奶/豆浆+蛋/低糖酸奶 | 场景模板 | F/外出/早晨时间少 | 用包装营养标签重算


## Table


ID | 示例 | 组件组合 | 额外搭配 | 使用说明

E01 | 早餐组合A（全谷+奶蛋） | C004 燕麦早餐份 + P015 低脂奶蛋组合 | 番茄/黄瓜等非淀粉蔬菜100-150g | A/B/C型常规早餐候选；最终总量按当天能量与蛋白目标缩放。

E02 | 早餐组合B（全麦馒头+蛋白） | C005 全麦馒头基础份 + P015 低脂奶蛋组合 | V006可减量搭配 | 家庭早餐候选；高血压注意成品馒头/面包钠。

E03 | 早餐组合C（玉米+豆浆） | C006 鲜玉米基础份 | 无糖豆浆250ml+水煮蛋1个 | 乳糖不耐受者候选；大豆过敏除外。

E04 | 午/晚餐组合A（杂粮饭+鱼+双蔬） | C003 杂粮饭基础份 + P001 清蒸鲈鱼 + V012 西兰花胡萝卜双蔬 |  | A/B型常规候选；根据蛋白目标可调整鱼量。

E05 | 午/晚餐组合B（糙米+鸡胸+菌菇蔬菜） | C002 糙米饭基础份 + P011 鸡胸彩椒 + V003 香菇油麦菜 |  | A/B/C型候选；C型可优先保证蛋白而非继续压低主食。

E06 | 午/晚餐组合C（荞麦面+虾仁豆腐汤） | C008 荞麦面基础份 + P013 冬瓜豆腐虾仁汤 | 另配绿叶菜150-200g | 糖代谢异常者可选低精制度主食；具体碳水总量仍需计算。

E07 | 午/晚餐组合D（红薯+鸡腿菇+蔬菜） | C007 蒸红薯基础份 + P004 去皮鸡腿肉炖菇 + V001 蒜香西兰花 |  | 需提高可执行性时的简单组合；D/E型可在此基础上增加能量。

E08 | 午/晚餐组合E（米饭+牛肉番茄+青菜） | C001 白米饭基础份 + P005 番茄炖瘦牛肉 + V002 清炒菠菜 |  | D/E型或需要提高铁/蛋白摄入者可作为候选；高尿酸需个体化。

E09 | 素食倾向组合（杂粮饭+豆腐+双蔬） | C003 杂粮饭基础份 + P008 香菇烧北豆腐 + V012 西兰花胡萝卜双蔬 |  | 不食肉者候选；蛋白目标较高时需核对总量和氨基酸来源。

E10 | 软食组合（小米粥+鸡蛋豆腐羹） | C009 小米粥基础份 + P014 鸡蛋豆腐羹 | 熟软绿叶菜100-150g | 食欲差/咀嚼困难者候选；能量密度不足时需加餐或强化。

E11 | 加餐组合A（奶+水果） | S001 低脂奶+苹果 |  | 3+1餐或3+2餐模式候选。

E12 | 加餐组合B（酸奶+坚果） | S005 无糖酸奶+核桃 |  | 需要小体积能量/蛋白补充时可选；减重患者坚果不随意加量。


## Table


ID | 模板 | 结构 | 使用边界

T13 | 强化减脂午餐模板 | 主食0.5–0.75份 + 主蛋白1份 + 非淀粉蔬菜1–2份 | 仅A/B通过强化门槛；优先从油/精制主食和能量密度调整，蛋白不得优先削减。

T14 | C型保肌午餐模板 | 主食0.75–1份 + 主蛋白1–1.25份 + 蔬菜1份 | 总量按Energy_target/Protein_target闭合；体重不变但肌肉/腰围改善可判有效。

T15 | D/E 3+2模式模板 | 三餐均有主食+蛋白，另加2次奶/豆/水果/蛋等小体积加餐 | 加餐从全天能量分配；早饱时优先小份多餐。

T16 | 外食食堂模板 | 选择1份主食+1份清淡蛋白菜+2份蔬菜；记录油汁/饮料/额外零食 | 用餐后患者确认完成比例和替换，照片仅辅助。

T17 | F型简化模板 | 固定2–3套患者能完成的早餐/午晚餐组合轮换 | 优先完成率，不追求每天完全不同。

T18 | 乳糖不耐模板 | 奶类组件替换为无乳糖奶或无糖豆浆等允许组件 | 牛奶蛋白过敏与乳糖不耐必须区分。

T19 | 软食模板 | 粥/软主食+蒸蛋/豆腐羹/嫩鱼+熟软蔬菜 | 吞咽困难需专科质地等级，不由本库自行决定。

T20 | 糖代谢控制模板 | 低加工主食+蛋白+非淀粉蔬菜+完整水果按总量安排 | 不自动固定低碳比例；药物/低血糖风险优先。


## Table


状态 | 标签 | 组件行为

食物过敏 | allergy_flags | 生成前排除对应组件；严重过敏史不做试吃建议。

乳糖不耐 | lactose_intolerance | 奶类换无乳糖奶/耐受酸奶/豆浆；与牛奶蛋白过敏区分。

糖代谢异常 | glycemic_control | 优先全谷/低加工主食、非淀粉蔬菜、完整水果、无糖饮品；不设统一固定碳水比例。

高血压 | low_sodium | 优先清蒸/炖/白灼/少盐；包装/外食钠由专科规则约束。

血脂异常/MASLD | fat_quality | 优先鱼禽豆、植物油和低加工食物；减少油炸、肥肉、超加工与含糖饮料。

高尿酸/痛风 | uric_acid_review | 不做“所有海鲜/肉类一刀切”；按专科规则、急性期、肾功能和水化状态筛选。

CKD/肾功能异常 | renal_review | 覆盖常规高蛋白逻辑；相关蛋白组件按肾内/营养科ACTIVE目标过滤。

肝纤维化风险升高 | liver_fibrosis_review | 不自动低蛋白；降低激进减脂优先级，保证营养/肌肉；显著风险先MDT。

早饱/恶心/食欲差 | small_frequent_soft | 减少单餐体积，优先软食/小份多餐/高营养密度；持续不足走营养恢复路径。

咀嚼困难 | soft_texture | 选择蒸蛋、豆腐羹、嫩鱼、软烂肉末等；仍需满足蛋白和总能量。

吞咽困难 | swallowing_review | 必须使用医护/吞咽专科确定的质地等级；本库不自行决定稠度。


## Table


字段 | 必填性 | 患者端问法 | 计算用途

每餐计划完成比例 | 必填 | 100% / 约75% / 约50% / 约25% / 几乎没吃 | 把计划营养按完成度作为第一层估计。

主蛋白完成比例 | 条件必填 | 全部/约3/4/约1/2/少量/未吃 | 用于判断蛋白执行和保肌风险。

是否替换 | 必填；有则展开 | 无/有→选择组件或拍照说明 | 替换后重新计算actual nutrition。

额外摄入 | 必填；有则展开 | 饮料/零食/水果/夜宵/其他 | 避免“计划执行100%但额外摄入未记录”。

照片 | 选填 | 餐前/餐后均可 | 辅助识别和份量核对，不单独决定kcal。

食欲与进食症状 | 每日必填 | 食欲0–10 + 早饱/恶心/腹胀等 | 解释实际摄入不足并触发D/E/周调整。


## Table


周结论 | 典型触发 | 下一周菜品/组合动作

MAINTAIN | 能量/执行/肌肉方向合适 | Energy_target不变；轮换同目标组件，提高多样性，不为“更快”继续减量。

BARRIER_FIRST | 执行率低、外食/时间/家庭障碍明显 | 减少菜品数量和复杂做法；切换便携/食堂/固定2–3套菜单；能量强度先不加码。

DATA_INSUFFICIENT | 饮食记录不足 | 继续原菜单或简化记录，不因照片少/体重波动改变食谱。

PRESERVE_MUSCLE | 体重下降伴肌肉/功能下降 | 主蛋白优先；减少通过削蛋白实现的能量限制；C型/保肌模板优先。

NUTRITION_RECOVERY | D/E持续下降、食欲差、摄入不足 | 小份多餐、软食、高营养密度、加餐组件优先；必要时ONS/营养科。

INTENSIFY_CANDIDATE | A/B满足强化门槛 | 仍维持蛋白；优先调整主食份量、油、零食/饮料和低能量密度结构；生成新草稿待审核。

DEINTENSIFY | 强化后肌肉/水分/症状不利 | 恢复标准/维持餐架构；适当恢复主食/能量或加餐，停止进一步削减。

SAFETY_REVIEW | 黄色/红色、疾病/手术状态变化 | 冻结相关自动选菜/调整，保留安全可执行基础饮食，转医护。


## Table


配置ID | key | 待确认内容

FOOD-CFG-001 | meal_distribution | 三餐/3+1/3+2餐默认能量分配与适用条件

FOOD-CFG-002 | meal_tolerance | 每餐/全天kcal和P/C/F闭合容差

FOOD-CFG-003 | portion_scales | 允许的离散份量档位：0.5/0.75/1/1.25/1.5

FOOD-CFG-004 | replacement_tolerance | 同类替换允许的能量/蛋白差异范围

FOOD-CFG-005 | nutrition_source | 院内认可营养数据库和版本

FOOD-CFG-006 | protein_distribution | 每餐主蛋白最低分配/优先级规则

FOOD-CFG-007 | repeat_limit | 同一核心组件/菜品一周重复上限（如需）

FOOD-CFG-008 | external_meal_mapping | 外食/食堂家庭份量到标准组件的映射

FOOD-CFG-009 | soft_diet_tags | 咀嚼/吞咽/软食质地标签与专科覆盖

FOOD-CFG-010 | disease_filter_rules | 糖代谢/血压/血脂/尿酸/肝/肾等筛选规则

FOOD-CFG-011 | logging_mode | 称重/家庭份量/拍照模式及estimate标记

FOOD-CFG-012 | draft_component_policy | 库外普通菜品如何进入DRAFT→审核→ACTIVE流程
