from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from .models import ModelConfig


class ReferenceMaterial(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=50000)
    kind: Literal['reference', 'policy'] = 'reference'
    confirmed: bool = False


class ReviewRequirement(BaseModel):
    id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    text: str = Field(min_length=1, max_length=3000)
    priority: Literal['required', 'preferred'] = 'required'
    source: str = Field(default='用户要求', max_length=200)
    evidence: str = Field(default='', max_length=10000)


class ChecklistItem(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    requirement: str = Field(min_length=1, max_length=3000)
    severity: Literal['critical', 'warning', 'info'] = 'warning'
    operator: Literal['semantic', 'contains_all', 'contains_any', 'forbidden'] = 'semantic'
    keywords: list[str] = Field(default_factory=list, max_length=30)
    suggestion: str = Field(default='', max_length=5000)

    @model_validator(mode='after')
    def valid_keywords(self):
        self.keywords = [word.strip() for word in self.keywords if word.strip()]
        if self.operator != 'semantic' and not self.keywords:
            raise ValueError('文字规则必须填写匹配词')
        return self


class CategoryInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(pattern=r'^[A-Z][A-Z0-9_]{1,49}$')
    description: str = Field(default='', max_length=1000)
    sort_order: int = Field(default=1, ge=0, le=9999)
    revision: int | None = None

    @field_validator('name')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('分类名称不能为空')
        return value.strip()


class ChecklistInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category_id: str | None = None
    contract_type: str = Field(default='通用合同', max_length=200)
    description: str = Field(default='', max_length=3000)
    items: list[ChecklistItem] = Field(min_length=1, max_length=100)
    published: bool = False
    revision: int | None = None

    @model_validator(mode='after')
    def unique_ids(self):
        if len({item.id for item in self.items}) != len(self.items):
            raise ValueError('检查项编号不能重复')
        return self


class TaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    type: str = Field(default='商务合同', min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=200000)
    role: Literal['甲方(买方/采购方/委托方)', '乙方(卖方/开发方/服务方)', '中立审慎'] = '中立审慎'
    mode: Literal['quick', 'deep', 'checklist', 'compare'] = 'deep'
    scale: Literal['强势', '中立', '弱势'] = '中立'
    background: str = Field(default='', max_length=10000)
    focus: str = Field(default='', max_length=10000)
    references: list[ReferenceMaterial] = Field(default_factory=list, max_length=5)
    requirements: list[ReviewRequirement] = Field(default_factory=list, max_length=100)
    execution: Literal['plan', 'react'] = 'plan'
    reference_text: str = Field(default='', max_length=200000)
    checklist_item_ids: list[str] | None = Field(default=None, min_length=1, max_length=100)
    checklist_id: str | None = None
    source_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
    revision: int | None = None

    @field_validator('title', 'type', 'text')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('内容不能为空')
        return value

    @model_validator(mode='after')
    def mode_inputs(self):
        if len([line for line in self.focus.splitlines() if line.strip()]) + len(self.requirements) > 100:
            raise ValueError('重点要求与逐项要求合计最多100条，请合并整理')
        if len({ref.name for ref in self.references}) != len(self.references):
            raise ValueError('参考资料名称不能重复')
        if len({item.id for item in self.requirements}) != len(self.requirements):
            raise ValueError('要求编号不能重复')
        if any(item.id.startswith('focus-') for item in self.requirements):
            raise ValueError('focus- 为系统保留编号前缀')
        if any(ref.kind == 'policy' and not ref.confirmed for ref in self.references):
            raise ValueError('请先确认公司制度提取的要求')
        for ref in self.references:
            if ref.kind == 'policy' and not any(item.source == ref.name for item in self.requirements):
                raise ValueError('公司制度必须至少包含一条已确认要求')
        for item in self.requirements:
            if item.evidence and not any(item.source == ref.name and item.evidence in ref.text for ref in self.references):
                raise ValueError('要求来源引用已失效，请重新提取或核对资料')
        if any(not item.text.strip() for item in self.requirements):
            raise ValueError('审核要求不能为空')
        if self.mode == 'checklist' and not self.checklist_id:
            raise ValueError('请选择审查清单')
        if self.mode == 'compare' and not self.reference_text.strip():
            raise ValueError('请提供参考合同')
        if self.mode == 'quick' and any(ref.kind != 'policy' for ref in self.references):
            raise ValueError('普通参考资料请使用深度审查；公司制度可用于快速审查的逐项核验')
        if sum(len(ref.text) for ref in self.references) > 50000:
            raise ValueError('参考资料合计不能超过五万字')
        return self


class RunRequest(BaseModel):
    model_config_data: ModelConfig = Field(default_factory=ModelConfig)


class HandlingInput(BaseModel):
    revision: int
    applied: list[str] = Field(default_factory=list, max_length=500)
    decisions: dict[str, Literal['pending', 'applied', 'rejected', 'needs_review']] = Field(default_factory=dict)
    comments: dict[str, str] = Field(default_factory=dict)


class ArchiveInput(BaseModel):
    archived: bool
    revision: int


class DraftInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    background: str = Field(min_length=1, max_length=20000)
    details: dict[str, str] = Field(default_factory=dict)
    outline: str = Field(default='', max_length=20000)
    text: str = Field(default='', max_length=200000)
    template_text: str = Field(default='', max_length=50000)
    references: list[ReferenceMaterial] = Field(default_factory=list, max_length=5)
    revision: int | None = None

    @model_validator(mode='after')
    def reference_limit(self):
        if sum(len(ref.text) for ref in self.references) > 50000:
            raise ValueError('起草参考资料合计不能超过五万字')
        return self


class DraftGenerate(RunRequest):
    stage: Literal['details', 'outline', 'text']


class DraftRewrite(RunRequest):
    original_text: str = Field(min_length=1, max_length=10000)
    instruction: str = Field(min_length=1, max_length=3000)
    revision: int


class FollowupInput(RunRequest):
    issue_id: str
    question: str = Field(min_length=1, max_length=3000)


class RevisionGenerate(RunRequest):
    revision: int = Field(ge=1)
    instruction: str = Field(default='', max_length=3000)


class RevisionEdit(BaseModel):
    revision: int = Field(ge=1)
    suggested_text: str = Field(min_length=1, max_length=20000)


class RevisionRestore(BaseModel):
    revision: int = Field(ge=1)
    version: int = Field(ge=1)
