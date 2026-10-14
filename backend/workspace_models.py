from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from .models import ModelConfig


class ReferenceMaterial(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=50000)


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


class ChecklistInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
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
    role: Literal['甲方(买方/采购方/委托方)', '乙方(卖方/开发方/服务方)', '中立审慎'] = '乙方(卖方/开发方/服务方)'
    mode: Literal['quick', 'deep', 'checklist', 'compare'] = 'deep'
    scale: Literal['强势', '中立', '弱势'] = '中立'
    background: str = Field(default='', max_length=10000)
    focus: str = Field(default='', max_length=10000)
    references: list[ReferenceMaterial] = Field(default_factory=list, max_length=5)
    reference_text: str = Field(default='', max_length=200000)
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
        if self.mode == 'checklist' and not self.checklist_id:
            raise ValueError('请选择审查清单')
        if self.mode == 'compare' and not self.reference_text.strip():
            raise ValueError('请提供参考合同')
        if self.mode == 'quick' and self.references:
            raise ValueError('参考资料请使用深度审查')
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
