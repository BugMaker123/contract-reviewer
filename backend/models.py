from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

class ModelConfig(BaseModel):
    model_name: str = Field(default="deepseek-v4-flash", description="模型标识符，如 deepseek-v4-flash, deepseek-chat 等")
    api_key: Optional[str] = Field(default=None, description="用户自定义 API Key，若留空则尝试读取环境变量 DEEPSEEK_API_KEY")
    base_url: Optional[str] = Field(default="https://api.deepseek.com/v1", description="API 基础端点")
    temperature: float = Field(default=0.1, description="生成温度")

class ContractSegment(BaseModel):
    id: str = Field(description="条款唯一标识符，如 sec_1")
    title: str = Field(description="条款名称，如 '第三条 交付与验收'")
    category: str = Field(description="分类，如 '标的与交付', '付款条件', '知识产权', '违约责任', '保密义务', '争议管辖'")
    content: str = Field(description="条款原文")
    line_number: Optional[int] = Field(default=1, description="条款起始参考行号")

class RedlineSuggestion(BaseModel):
    original_text: str = Field(description="原条款原文")
    suggested_text: str = Field(description="建议修订后的条款文本")
    change_type: Literal["replace", "delete", "insert"] = Field(default="replace")
    diff_explanation: str = Field(description="修订细节与法务谈判博弈策略解释")

class ReviewIssue(BaseModel):
    id: str = Field(description="问题序号，如 issue_1")
    segment_id: Optional[str] = Field(default=None, description="关联条款 ID")
    clause_title: str = Field(description="涉案条款名称")
    severity: Literal["critical", "warning", "info", "favorable"] = Field(
        description="风险级别: critical(重大法律漏洞/致命合规陷阱), warning(商业权责失衡/次要风险), info(优化建议), favorable(对我方有利条款)"
    )
    category: str = Field(description="审查维度: 财税合规、结算条件、强制合规、权责平衡、违约责任、知识产权、争议管辖等")
    issue_title: str = Field(description="风险摘要，例如 '单方无限连带赔偿责任陷阱'")
    legal_basis: str = Field(description="法理与法规依据，如《民法典》、《发票管理办法》等")
    risk_analysis: str = Field(description="详细的商业与法律风险后果剖析")
    negotiation_strategy: str = Field(description="谈判应对策略与抗辩口径")
    redline: Optional[RedlineSuggestion] = Field(default=None, description="具体的红线修订文本与对照")

class TaxAndSettlementAudit(BaseModel):
    """商务合作合同专项审查：增值税与结算条件 4 大核心审核点"""
    # 1、是否有单列增值税税额
    has_separate_vat_amount: bool = Field(default=False, description="是否单列增值税税额（不含税价 vs 税额明确拆分）")
    vat_amount_detail: str = Field(default="合同总价未作不含税价与增值税税额单列拆分", description="单列增值税税额审查详情")
    
    # 2、增值税税率是多少？通常是13%、9%、6%等
    vat_rate: str = Field(default="未明确税率", description="增值税税率（如 6%, 13%, 9%, 1% 等）")
    vat_rate_evaluation: str = Field(default="未约定适用税率，存在税率争议及税负转嫁风险", description="增值税税率合规性评价")
    
    # 3、是否是增值税专用发票
    is_special_vat_invoice: bool = Field(default=False, description="是否明确为增值税专用发票（专票）")
    invoice_detail: str = Field(default="仅泛称'合法发票'，未明确限定为增值税专用发票，无法保障进项税额抵扣", description="发票类型核验分析")
    
    # 4、结算方式、结算条件
    settlement_method: str = Field(default="未明确或存在商业汇票承兑风险", description="结算方式（如银行电汇、承兑汇票）")
    settlement_condition_analysis: str = Field(default="结算触发条件苛刻或存在发票先行前置付款风险", description="结算条件分析与支付节奏健康度")
    
    overall_status: Literal["critical", "warning", "pass"] = Field(default="warning", description="财税结算总体评级")

class OverallSummary(BaseModel):
    compliance_score: int = Field(default=68, description="合同健康合规分 (0-100)")
    risk_level: Literal["极高风险", "高风险", "中度风险", "风险可控", "优秀健全"] = Field(default="高风险")
    critical_count: int = Field(default=0)
    warning_count: int = Field(default=0)
    info_count: int = Field(default=0)
    verdict: str = Field(description="法务终审总评结论")
    tax_settlement: Optional[TaxAndSettlementAudit] = Field(default=None, description="财税与结算专项审查结果")
    action_advice: List[str] = Field(default_factory=list, description="签署前的核心应对步骤")
    key_dealbreakers: List[str] = Field(default_factory=list, description="绝不可妥协的核心否决点 (Dealbreakers)")

class ContractReviewRequest(BaseModel):
    contract_title: str = Field(default="商务合作协议")
    contract_type: str = Field(default="商务合作与技术服务合同", description="合同业务类型")
    party_role: Literal["甲方(买方/采购方/委托方)", "乙方(卖方/开发方/服务方)", "中立审慎"] = Field(
        default="乙方(卖方/开发方/服务方)",
        description="审查立场视角，立场不同审查策略截然相反"
    )
    contract_text: str = Field(min_length=1, max_length=200000, description="合同完整原文")
    model_config_data: ModelConfig = Field(default_factory=ModelConfig)
    review_focus: Optional[List[str]] = Field(
        default=["增值税税额单列与税率", "增值税专用发票约定", "结算方式与结算条件", "违约责任与赔偿上限"],
        description="重点关注维度"
    )
