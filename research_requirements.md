请重新规划当前 aicdemo 项目，将现有 Apple vs Microsoft 五年财务比较简报升级为一份完整、专业的英文 Equity Research Report。

这次不是简单扩写原有的一页 Memo，而是重新设计研究框架、财务分析、图表、报告结构和写作语言。请参考成熟机构股票研究报告的分析方式，形成有明确判断、充分数据支持和完整参考资料的研究成果。

**一、报告定位与研究目标**

报告标题为 Apple vs. Microsoft: A Five-Year Comparative Fundamental Analysis。

正文建议为 5–7 页，附录可另外增加页数。生成 LaTeX PDF 和 HTML 两个版本，保证数据、图表、正文及结论一致。

研究重点是比较两家公司过去五年的经营规模、增长能力、盈利能力、现金流质量及业务模式差异，解释财务表现背后的经营原因，并判断两家公司各自的优势、风险和未来需要关注的关键变量。

不能只罗列财务数据或描述曲线变化，必须从数据出发形成有依据的分析判断。

**二、数据与研究方法**

优先复用现有 SEC EDGAR Company Facts 数据、comparison.csv、verification.json 和已有 Python 脚本，避免重复工作。

使用 Apple 和 Microsoft 最近五个完整财年的真实 GAAP 财务数据，明确标注财政年度结束日期，解释两家公司财年不一致的问题。

核心指标包括 Revenue、Revenue Growth、Gross Margin、Operating Income、Operating Margin、Net Income、Net Margin、Diluted EPS、Operating Cash Flow、Capital Expenditures 和 Free Cash Flow。对于新增指标，必须确认原始 SEC 数据和计算口径可靠。

每个重要数据都应能追溯至 SEC 官方 10-K 报告或 Company Facts 数据。

建立数据来源表和交叉核验记录，不得编造缺失数据，不得将未经验证的推断当作事实。

**三、报告正文结构**

1. Executive Summary：直接概括两家公司的规模、成长性、盈利能力和核心竞争优势，提出明确的比较结论。

2. Business Model and Revenue Drivers：分析 Apple 的硬件与服务业务，以及 Microsoft 的云计算、软件订阅和其他业务，解释不同商业模式如何影响收入增长、成本结构和利润率。

3. Revenue and Growth Analysis：结合五年收入及增长率数据，分析规模变化、增长稳定性、主要驱动因素，以及两家公司增长模式的差异。

4. Profitability Analysis：比较毛利率、经营利润率、净利率和净利润，结合业务结构、成本和费用解释盈利能力差异。重点分析 Microsoft 较高的盈利能力及 Apple 的经营特点，避免停留在指标描述层面。

5. Cash Flow and Capital Investment：分析经营现金流、资本开支和自由现金流，讨论 AI 基础设施投资、资本投入强度及其对未来盈利和现金流的影响。相关判断必须有财报数据支持。

6. Comparative Assessment and Key Risks：综合评价两家公司的经营质量、增长持续性和主要风险，区分企业经营表现与股票估值，不得在缺少估值分析时直接给出买卖评级。

7. Methodology and References：解释指标定义、计算公式、数据来源、财年差异及核验方法，并列出完整参考资料。

**四、图表与表格**

至少制作以下图表：

- Five-Year Revenue Comparison
- Revenue Growth Comparison
- Operating Margin Comparison
- Net Margin Comparison
- Net Income Comparison
- Operating Cash Flow and Capital Expenditures Comparison（数据完整时）

另外制作一张五年核心财务数据表，以及一张最新财年关键指标比较表。

所有图表必须通过 Python 从经过核验的数据自动生成，具有清晰的标题、单位、图例、年份和来源说明。

正文必须对图表进行实质性分析，不能只重复图表中的数字。

**五、英文写作要求**

全文采用专业、自然、准确的机构股票研究报告语言。

正文使用完整、流畅、连贯的分析段落，不要大量使用项目符号、口号式短句、引号或加号连接概念。

每段应围绕一个明确判断展开，依次呈现财务事实、经营原因和研究含义。连接词自然多样，避免机械重复。

避免新造词、浮夸表达、冗余句式、空泛总结和为了凑篇幅而增加的内容。

不要反复使用 suggests、potentially、may indicate 等模糊措辞。事实明确时直接表达；存在因果关系或数据证据不足时才说明不确定性。

重点提升专业性、逻辑性、清晰度、简洁性和可读性，使报告接近真实 Equity Research Analyst 的写作水平。

**六、参考资料**

正文使用 [1]、[2]、[3] 等编号引用。

报告末尾设置 References，逐条列出真实的文件名、公司、财年、SEC 官方链接及必要的访问日期。

参考资料必须与正文引用一一对应，不允许编造文件名、文献或链接。

**七、交付与代码要求**

保留现有 Git 仓库、README、原始数据、核验记录和可复用脚本。

合理整理 data/raw、data/processed、src、output/figures、output/tables、output/reports 等目录。

使用 Python 自动完成数据处理、指标计算、图表生成和报告输出，确保整个流程可重复运行。

使用已经安装在 D:\texlive\2026\bin\windows 的 TeX Live 编译 PDF，不要重新安装软件。

最终需要检查 SEC 数据一致性、图表与正文一致性、PDF 排版、HTML 内容、参考资料和项目可复现性。

**八、执行方式**

现在先进入规划阶段，不要立即修改文件。

请先检查当前项目，详细输出：

1. 现有版本的主要不足，以及哪些文件可以复用。
2. 新报告的完整目录、各章节的核心研究问题和拟形成的判断。
3. 所需财务数据、图表、表格及其来源。
4. 代码和文件目录的重构方案。
5. 分阶段实施计划及最终质量检查方案。

等我确认计划后再开始执行。未经批准，不要 git commit 或 git push。