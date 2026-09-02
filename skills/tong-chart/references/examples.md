# Mermaid drafting examples

These sources intentionally omit hand-written theme directives. The renderer applies the default Cursor paper theme. Pass `--theme aurora` for the old vivid poster look, or `--theme docs`, `minimal`, or `neutral` for the other palettes.

## Process with a decision

```mermaid
flowchart TD
  START(["提交申请"]) --> CHECK{"材料完整？"}
  CHECK -->|是| REVIEW["进入审核"]
  CHECK -->|否| RETURN["退回补充"]
  REVIEW --> STORE[("保存结果")]
  RETURN --> FIX(["修改后重新提交"])
  class START,FIX startEnd
  class RETURN process
  class REVIEW accent
  class CHECK decision
  class STORE store
```

## Layered architecture

```mermaid
flowchart LR
  subgraph CLIENT["客户端"]
    WEB["Web 应用"]
    APP["移动端"]
  end
  subgraph SERVICE["服务层"]
    API["API 网关"]
    CORE["业务服务"]
  end
  subgraph DATA["数据层"]
    DB[("业务数据库")]
    CACHE[("缓存")]
  end
  WEB --> API
  APP --> API
  API --> CORE
  CORE --> DB
  CORE --> CACHE
  class WEB,APP process
  class API,CORE accent
  class DB,CACHE store
```

## Sequence

```mermaid
sequenceDiagram
  participant U as 用户
  participant A as 应用
  participant S as 服务
  participant D as 数据库
  U->>A: 提交请求
  A->>S: 校验并处理
  S->>D: 保存结果
  D-->>S: 保存成功
  S-->>A: 返回结果
  A-->>U: 展示成功状态
```

## State lifecycle

```mermaid
stateDiagram
  state "草稿" as Draft
  state "审核中" as Reviewing
  state "已通过" as Approved
  [*] --> Draft
  Draft --> Reviewing: 提交
  Reviewing --> Approved: 通过
  Reviewing --> Draft: 退回
  Approved --> [*]
```

## Class overview

```mermaid
classDiagram
  direction LR
  class User {
    +String name
    +submitOrder()
  }
  class Order {
    +String status
    +confirm()
  }
  User --> Order : 提交
```

## Entity relationship

```mermaid
erDiagram
  direction LR
  USER ||--o{ ORDER : 提交
  ORDER ||--|{ ORDER_ITEM : 包含
  USER {
    string id PK
    string name
  }
  ORDER {
    string id PK
    string status
  }
  ORDER_ITEM {
    string id PK
    int quantity
  }
```

## Mindmap

```mermaid
mindmap
  root((产品规划))
    用户价值
      更快完成任务
      更低学习成本
    交付路径
      小范围验证
      逐步推广
```

## Timeline

```mermaid
timeline
  title 产品演进
  2026 Q1 : 用户研究
  2026 Q2 : 内部试用
  2026 Q3 : 正式发布
```

## Gantt

```mermaid
gantt
  title 发布计划
  dateFormat YYYY-MM-DD
  axisFormat %m/%d
  section 设计
    方案确认 :done, design, 2026-08-01, 4d
  section 开发
    核心实现 :active, build, after design, 6d
    发布验证 :crit, verify, after build, 3d
```

## Git history

```mermaid
gitGraph
  commit id: "初始化"
  branch feature
  checkout feature
  commit id: "功能开发"
  checkout main
  merge feature id: "合并功能"
  commit id: "发布"
```

## User journey

```mermaid
journey
  title 新用户首次体验
  section 了解
    浏览介绍: 4: 用户
    查看示例: 5: 用户
  section 使用
    创建项目: 4: 用户
    完成首次发布: 5: 用户
```

## Pie composition

```mermaid
pie showData
  title 本月任务构成
  "产品设计" : 35
  "功能开发" : 40
  "质量验证" : 15
  "运营支持" : 10
```

## Quadrant prioritization

```mermaid
quadrantChart
  title 功能投入优先级
  x-axis 低投入 --> 高投入
  y-axis 低价值 --> 高价值
  quadrant-1 战略投入
  quadrant-2 优先实施
  quadrant-3 暂缓考虑
  quadrant-4 谨慎评估
  智能搜索: [0.35, 0.82]
  批量导出: [0.22, 0.68]
  主题换肤: [0.58, 0.28]
  实时协作: [0.78, 0.74]
```

## Native architecture without external icons

```mermaid
architecture-beta
  group platform(cloud)["业务平台"]
  service web(internet)["Web 应用"] in platform
  service api(server)["API 网关"] in platform
  service core(server)["业务服务"] in platform
  service db(database)["业务数据库"] in platform
  web:R --> L:api
  api:R --> L:core
  core:R --> L:db
```

## Controlled block layout

```mermaid
block
  columns 3
  CLIENT["客户端"] REQUEST<["请求"]>(right) API["API 网关"]
  space:2 FORWARD<["转发"]>(down)
  DB[("数据库")] WRITE<["写入"]>(left) CORE["业务服务"]
```

## Kanban snapshot

```mermaid
kanban
  todo[待处理]
    design[确认方案]@{ assigned: "产品", priority: "High" }
    data[准备数据]@{ assigned: "分析" }
  doing[进行中]
    build[实现核心功能]@{ assigned: "开发", priority: "High" }
  verify[验证]
    qa[回归测试]@{ assigned: "测试" }
  done[已完成]
    init[项目初始化]@{ priority: "Low" }
```

## Sankey flow

```mermaid
sankey
  Visitors,Registered,620
  Visitors,Exited,380
  Registered,Paid,210
  Registered,Free,410
```

## XY bar and line

```mermaid
xychart
  title "季度交付趋势"
  x-axis [Q1, Q2, Q3, Q4]
  y-axis "完成任务数" 0 --> 100
  bar [42, 58, 73, 88]
  line [35, 50, 68, 82]
```

## Crowded source repair

When a node contains implementation detail such as `upsert user_question_answer and update grading_status`, shorten the node to `保存批改结果`. Put table names and field changes in the accompanying text. If an overview still exceeds roughly 10 nodes, create a second detail diagram instead of shrinking text.
