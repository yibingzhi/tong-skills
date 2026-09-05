# Tong Title Schema

## Input Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TitleMatrixInput",
  "type": "object",
  "properties": {
    "stage": {
      "type": "string",
      "enum": ["pre", "post"],
      "description": "pre: 正文写作前(探索切角); post: 正文终稿后(发布标题定制)"
    },
    "facts": { "type": "array", "items": { "type": "string" } },
    "selected_thesis": { "type": "string" },
    "one_sentence_view": { "type": "string" },
    "humanized_draft": {
      "type": "string",
      "description": "stage=post 时必填，用于事实与标题严格对齐"
    },
    "target_platform": {
      "type": "string",
      "enum": ["all", "wechat", "xhs", "zhihu"],
      "default": "all"
    }
  },
  "required": ["stage", "facts", "selected_thesis"]
}
```

## Output Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TitleMatrixOutput",
  "type": "object",
  "properties": {
    "stage": { "type": "string", "enum": ["pre", "post"] },
    "matrices": {
      "type": "object",
      "properties": {
        "counter_intuitive": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "title": { "type": "string" },
              "ctr_score": { "type": "number" },
              "hook_mechanism": { "type": "string" }
            },
            "required": ["title", "ctr_score"]
          },
          "description": "反常识认知型（别再XXX了，真正XXX其实是XXX）"
        },
        "documentary": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "title": { "type": "string" },
              "ctr_score": { "type": "number" },
              "hook_mechanism": { "type": "string" }
            },
            "required": ["title", "ctr_score"]
          },
          "description": "现实荒诞纪实型（时间/地点/数字/道具具体白描）"
        },
        "emotional": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "title": { "type": "string" },
              "ctr_score": { "type": "number" },
              "hook_mechanism": { "type": "string" }
            },
            "required": ["title", "ctr_score"]
          },
          "description": "情绪嘴替型（读者心里憋了很久但不敢说的实话）"
        },
        "declaration": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "title": { "type": "string" },
              "ctr_score": { "type": "number" },
              "hook_mechanism": { "type": "string" }
            },
            "required": ["title", "ctr_score"]
          },
          "description": "反差狠人宣言型（平视冷幽默化解现实重压）"
        }
      },
      "required": ["counter_intuitive", "documentary", "emotional", "declaration"]
    },
    "recommended_by_platform": {
      "type": "object",
      "properties": {
        "wechat": {
          "type": "object",
          "properties": {
            "main_title": { "type": "string" },
            "alternatives": { "type": "array", "items": { "type": "string" } },
            "rationale": { "type": "string" }
          },
          "required": ["main_title", "alternatives"]
        },
        "xhs": {
          "type": "object",
          "properties": {
            "main_title": { "type": "string" },
            "alternatives": { "type": "array", "items": { "type": "string" } },
            "rationale": { "type": "string" }
          },
          "required": ["main_title", "alternatives"]
        },
        "zhihu": {
          "type": "object",
          "properties": {
            "main_title": { "type": "string" },
            "alternatives": { "type": "array", "items": { "type": "string" } },
            "rationale": { "type": "string" }
          },
          "required": ["main_title", "alternatives"]
        }
      }
    },
    "fact_check_status": {
      "type": "string",
      "enum": ["passed", "exaggerated_warning"]
    }
  },
  "required": ["stage", "matrices", "recommended_by_platform", "fact_check_status"]
}
```
