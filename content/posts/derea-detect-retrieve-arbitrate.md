---
title: DEREA: Improving Idiom Translation with Detect-Retrieve-Arbitrate Reasoning
date: 2026-10-17
category: 论文精读
summary: 从语义冲突检测、SFT 与 DPO，到习语释义检索和双路径仲裁；结合图 1、完整方法公式与附录 prompt 理解 DEREA。
summary_en: Reading notes on semantic-conflict detection, SFT and DPO, idiom retrieval, and dual-path arbitration, with Figure 1, equations, and appendix prompts.
draft: false
---

2026/10/17 17:33

《DEREA: Improving Idiom Translation with Detect-Retrieve-Arbitrate Reasoning》

由于静态参数记忆的局限，以及句级检索带来的噪声，习语翻译一直是一个比较棘手的问题。这里的 idiom 可以理解为习语、惯用表达，论文也讨论了 slang 等非组合性表达：它们的整体意思，不能简单地由各个单词的字面意思相加得到。

近期的研究从传统的参数优化，转向了两个主要方向：推理强化和外部信息整合。推理强化让 LLM 自己分析语义，但单个模型同时做检测和 translation 时，两个任务未必能很好地对齐；遇到新的表达时，还会受自身内部知识的限制。外部信息整合通常通过 RAG 利用知识库，却又会受到检索噪声的干扰。

习语在句子中往往只占很小的一部分，粗粒度的句级检索容易引入无关信息，反而误导 model。一个更稳健的方式，是先通过语义检测找出具体的习语表达，再围绕这个表达做检索，给翻译提供更有针对性的证据。

综上，作者提出了 DEREA。首先训练一个偏好对齐的 detector，利用字面意义和语境意义之间的语义冲突，判断句子里有没有习语，并把它提取出来；之后，system 同时保留直接翻译和 RAG 增强翻译两条路径，通过 comparative arbitration（比较仲裁）选择最后的译文。检测器的训练分为 SFT 和 DPO 两步，后面会分别展开。

## Methodology

{{figure:figure1}}

图 1 可以分成上下两部分来看。上半部分是 detector 的训练：先构造 answer-guided SFT 数据，再挖掘错误回答，组成 DPO 偏好对。下半部分是检测后的检索与翻译：将习语映射到知识库里的规范词条，取得释义，再比较不同译文。图中的 $M_d$ 是检测模型，$M_{\mathrm{emb}}$ 是向量表示模型，$M_t$ 是翻译模型。

还有一个容易忽略的分支：如果 detector 输出 $l=\mathrm{NO}$，系统就直接翻译，不继续做习语检索。只有 $l=\mathrm{YES}$ 时，才进入后面的检索和仲裁流程。

## Preference-Aligned Idiom Detection

给定源句 $x$，训练检测模型 $M_d$ 依次生成一个三元组：

$$
y=(r,l,i),\qquad l\in\{\mathrm{YES},\mathrm{NO}\}.
$$

$r$ 是检测时的 CoT（Chain-of-Thought），$l$ 是有没有习语的分类 label，$i$ 是句子中的习语片段。附录 prompt 还要求将人称、时态、缩写等变体规范化，因此实际输出也可能是对应的 canonical form。论文为简化任务，每个样本只关注一个候选习语；这并不意味着真实句子一定只有一个习语。

这个 detector 的关键，是对照字面解释和上下文，看两者之间是否出现语义不连贯。例如原文的 “his fingers were burnt” 出现在股市崩盘、投资亏损的语境里，直接解释成“手指被烧伤”就不合适。模型需要据此识别表达，并将其规范化为 “burn fingers”。

下面是附录 A.2 的 **Detector System Prompt**（PDF 第 13 页／论文第 6615 页；保留原文内容，整理换行）：

```text
** Core Method
You will act as a rigorous language analyst. Your core methodology
is to objectively determine whether an expression is an
“Unconventional Expression” by logically comparing its “literal
meaning” with its “contextually inferred meaning”.

** Key Definition: Unconventional Expression:
An “Unconventional Expression” refers to a word or phrase whose
overall meaning cannot be directly inferred from the literal
meanings of its individual components. Such expressions are
typically figurative, idiomatic, or culturally specific, and are
highly dependent on context. They mainly include idioms, slang...

** Specific Requirements
1. Unconventional expressions in a sentence may involve variations
   in person, tense, abbreviations, etc. Please identify and
   normalize them to their canonical forms.
2. Conventional usages of unconventional expressions should also
   be taken into consideration.
3. When both literal and figurative meanings are explainable, the
   final judgment should be made by selecting the interpretation
   that best fits the given context.
```

这里第 2、3 点很重要：一个短语即使经常被用作习语，在当前句子里也可能只是字面用法。不能因为“见过这个表达”就直接判 YES，还要回到语境里验证。

### Answer-Guided SFT Data Construction

先向用于 SFT 阶段的同一个模型提供源句 $x$、真实 label $l^*$ 和真实习语 $i^*$，让 model 根据已知答案反向组织解释，生成说明语义冲突的推理链 $r^*$。这样得到的完整监督目标就是 $y^*=(r^*,l^*,i^*)$。

论文使用 few-shot 示例来引导这种语义冲突分析。附录 A.2 给出的 **Detector User Prompt** 正好展示了正例、负例和输出格式，可以对照理解数据要教给模型什么能力：

```text
** Example sentence containing an unconventional expression:
“When the share market crashed his fingers were burnt from all
the investments that he had made.”

Example Output:
***Thought process:
“his fingers were burnt”: The literal meaning is “his fingers were
physically burned”, but in the given context—“when the share market
crashed, he suffered losses due to his investments”—“burn fingers”
is used to indicate that the subject incurred financial losses as
a result of poor investment decisions. The literal interpretation
clearly does not fit the context, so it is identified as an
unconventional expression.
Other expressions such as “the share market crashed” and “the
investments” align with their literal meanings.
***Output: ## YES ## 1.burn fingers

Example sentence without an unconventional expression:
“She is reading a book.”

Example Output:
***Thought process:
The sentence has a clear structure, and expressions such as
“reading a book” are common phrases with no hidden meanings. All
expressions in the sentence are used in their literal sense, and
there is no unconventional expression present.
***Output: ## NO

Please follow the system-provided methodology and refer to the
examples above to process the unconventional expressions in the
following English sentence.
English text: {sentence}
Thought process & Output
Please follow the output format below:
***Thought process:
***Output: ## YES ## <Unconventional Expression>
or
***Thought process:
***Output: ## NO
```

上面是论文公布的检测模板，其中 `{sentence}` 对应输入 $x$。Answer-guided 数据构造还会额外提供真实的 $l^*$ 和 $i^*$；附录没有另列这一训练数据构造步骤的完整专用 prompt，所以不能把上面的检测模板直接当成全部构造流程。

将 detector $M_d$ 的策略记为 $\pi_\theta$，训练 target 是最大化完整推理链和检测结果的条件似然，也就是最小化下面的负对数似然（原文式 1）：

$$
\mathcal{L}_{\mathrm{SFT}}(\theta)
=-\mathbb{E}_{(x,y^*)\sim D_{\mathrm{SFT}}}
\left[\log\pi_\theta(y^*\mid x)\right].
\tag{1}
$$

这里监督的不只是 YES / NO，而是整个 $y^*$。因此，模型既要学会判断与提取，也要学会生成能够解释判断依据的语义分析。真实答案用于构造训练样本；正式检测新句子时，模型的输入仍然是源句 $x$。

### Negative-Mining DPO Data Sampling

只有 SFT 时，模型在复杂语境中可能过于敏感，把一些普通表达也判成习语。为了提高检测的准确性，作者继续使用 DPO（Direct Preference Optimization），构造偏好数据集：

$$
D_{\mathrm{DPO}}=\{(x,y^*,y^-)\}.
$$

$y^*$ 是正确回答，$y^-$ 是 rejected sample。构造过程是先用 base model 对每个 $x$ 生成 $y=(r,l,i)$，再与真实目标 $y^*$ 比较，按以下层次挑出错误回答：

1. **Judgment Errors**：有没有习语的分类判断错误。
2. **Extraction Errors**：虽然正确判断存在习语，但提取的片段或规范形式不准确。

第二类不是随便找一个更差的回答，而是专门保留“发现了习语，却没提取对”的错误。这样，DPO 能进一步约束检测结果的精度。

通过比较 $y^*$ 与 $y^-$，DPO 的训练目标定义为（原文式 2）：

$$
\mathcal{L}_{\mathrm{DPO}}(\theta)
=-\mathbb{E}_{(x,y^*,y^-)\sim D_{\mathrm{DPO}}}
\left[\log\sigma(\beta\Delta)\right].
\tag{2}
$$

其中，所选序列与被拒绝序列的相对对数概率差为（原文式 3）：

$$
\Delta=
\log\frac{\pi_\theta(y^*\mid x)}{\pi_{\mathrm{ref}}(y^*\mid x)}
-\log\frac{\pi_\theta(y^-\mid x)}{\pi_{\mathrm{ref}}(y^-\mid x)}.
\tag{3}
$$

$\pi_{\mathrm{ref}}$ 是作为参考策略的 SFT model，$\sigma$ 是 sigmoid 函数，$\beta$ 控制偏好优化的尺度，论文称它为温度参数。可以这样理解：训练希望相对于参考模型，正确输出的概率提升得更多，错误输出的概率提升得更少。$\Delta$ 越大，$\sigma(\beta\Delta)$ 越接近 1，loss 就越小。

这也补充了前面“用 RL 训练 detector”的概括：论文具体采用的是 **SFT 后接 DPO 的偏好对齐流程**，这里没有单独训练一个奖励模型再做 PPO。

## Idiom-centric Retrieval-Augmented Translation

检测完成后，就进入以习语为中心的检索增强翻译。作者先构建了一个大型 idiom knowledge base $B$：一部分来自专家整理的 PIE 数据，另一部分来自 Urban Dictionary 的约 250 万条原始条目。为了保证检索证据的质量，再用 LLM-based distiller 过滤、整理成“一个 idiom 对应一个 definition”的格式。图 1 标注处理后的知识库有 170 万条以上条目，原始数据规模和最终知识库规模要区分开。

### Normalized Idiom Retrieval

给定 detector 的输出 $(r,i)$，系统用 $M_{\mathrm{emb}}$ 将习语 $i$ 编码，在知识库 $B$ 中进行相似度搜索，返回 Top-$K$ 个释义：

$$
E=\{e_1,e_2,\ldots,e_K\}.
$$

这里检索得到的是 **definition，而不是已经翻译好的目标语句子**。释义先作为外部证据，后面的 translator 再结合源句生成译文。

但是，词语的表面形式是多样的。比如论文中的 “foaming at the mouth” 要对应到知识库的 “foam at the mouth”，附录里的 “his fingers were burnt” 要对应到 “burn fingers”。一般的 embedding model 未必能很好地把带有时态、人称或上下文片段的表达映射回标准词条。因此，作者构造了包含习语变体的增强数据集 $D_{\mathrm{aug}}$，并微调 $M_{\mathrm{emb}}$。

这一步原文给出的对比学习目标是（原文式 4）：

$$
\begin{aligned}
\mathcal{L}_{\mathrm{CL}}
&=-\mathbb{E}_{(v,i)\sim D_{\mathrm{aug}}}\\
&\quad\left[
\log\frac{\exp\!\left(s(v,i)/\tau\right)}
{\sum_{j\in\mathcal{N}}\exp\!\left(s(v,j)/\tau\right)}
\right].
\end{aligned}
\tag{4}
$$

$v$ 是习语变体，$i$ 是其对应的规范习语，$s(v,i)$ 是两者向量的余弦相似度，$\tau$ 是温度参数。$\mathcal{N}$ 表示一个 mini-batch 中参与比较的候选，**包括一个正样本和多个负样本**，分母不是只有负样本。

这个 loss 的作用，就是提高变体 $v$ 与正确词条 $i$ 的相似度，同时把它与不匹配的词条区分开。之后再使用 Faiss 建立向量索引，把“检测出的表达”映射到“规范词条及其释义”。附录 A.4 还说明，embedding model 由 Qwen3-0.6B 初始化，使用 MultipleNegativesRankingLoss 进行训练。

### Arbitrated Dual-Path Translation

标准 RAG 可能出现 over-correction（过度纠正）：明明模型本来的翻译是对的，却被不合适的外部释义带偏。因此，作者保留两条翻译路径，让外部证据和模型原有能力一起参与比较。

首先，给定输入 $x$，模型仅利用内部参数知识生成直接翻译 $t_0$（原文式 5）：

$$
t_0\sim P_{M_t}(\,\cdot\mid x).
\tag{5}
$$

附录 A.2 将这一步称为 Literal Translation，使用的实际 prompt 很简单（PDF 第 14 页／论文第 6616 页）：

```text
Translate the following English sentence into {target_lang}.
English: {sentence}
{target_lang}:
```

从这个 prompt 可以看到，它并没有强制 model 逐字翻译。因此我把 $t_0$ 理解为**不使用检索信息的直接翻译基线**。它可能误解习语，也可能已经给出正确的意译；保留这个候选，正是为了让系统在检索无益时仍能选择原来的结果。

随后，对每个检索到的释义 $e_k$，translator 生成一个对应的增强译文 $t_k$（原文式 6）：

$$
t_k\sim P_{M_t}(\,\cdot\mid x,e_k),
\qquad k\in\{1,\ldots,K\}.
\tag{6}
$$

将两条路径的结果放到一起，就得到候选池（原文式 7）：

$$
T_{\mathrm{cand}}=\{t_0,t_1,\ldots,t_K\}.
\tag{7}
$$

也就是说，$K$ 个释义对应 $K$ 个增强候选，再加上一个直接翻译候选。不同释义不一定适合当前语境，所以不能把检索排名最高的结果直接当成最终答案。

接下来，在 detector 的分析 $r$ 引导下，$M_t$ 对候选池生成综合评价 $h$，同时比较习语的语义准确性和整个句子的流畅性（原文式 8）：

$$
h\sim P_{M_t}(\,\cdot\mid x,r,E,T_{\mathrm{cand}}).
\tag{8}
$$

最后，由模型根据这段评价进行仲裁，选出最终译文（原文式 9）：

$$
t^*=\operatorname{Arbiter}(M_t,h).
\tag{9}
$$

$r$ 和 $h$ 在这里承担不同的作用：$r$ 解释源句为什么存在非字面用法，$h$ 则比较各个译文是否解决了这个问题，以及译成完整句子后是否自然。如果 RAG 候选没有提供更准确的解释，仲裁可以保留 $t_0$。

附录 A.1 的 Algorithm 1 第 15 行，又把式 9 中的选择写得更明确：

$$
t^*=\underset{t\in T_{\mathrm{cand}}}{\arg\max}\;
P_{M_t}\!\left(\operatorname{Select}(t)\mid h,T_{\mathrm{cand}}\right).
$$

这描述的是由语言模型在候选集合中作出选择的过程，不是论文另外训练了一个独立的数值打分器。

把公式和实际输入对照起来看，附录 A.2 的 **Translator System Prompt** 如下（PDF 第 14 页／论文第 6616 页）：

```text
You are a translation assistant whose task is to analyze
translation background information and ultimately provide the
optimal Chinese translation.

You will be given the following translation background information:
1. The original English sentence.
2. The literal translation result from the model.
3. The analysis method and detection result for unconventional
   expressions within the sentence.
4. Dictionary entries retrieved from RAG (Retrieval-Augmented
   Generation) (Unconventional expressions: their figurative
   meanings).
```

与之配套的 **Translator User Prompt** 跨了两页（PDF 第 14–15 页／论文第 6616–6617 页）。下面保留其输入字段、三条 RAG 候选及比较输出结构：

```text
Input Information:
1. Original English Sentence: {en}
2. Analysis Method and Detection Result for Unconventional
   Expressions in the Sentence: {think}
3. Retrieved Dictionary Entries: {rag_info}
4. Translation 0: Model’s Literal Translation Result: {direct}

Output Format: Based on the retrieved dictionary entries, generate
three separate translations: Translation 1, Translation 2, and
Translation 3.
Systematically analyze the translation quality of unconventional
expressions and the overall sentence quality for Translation 0,
Translation 1, Translation 2, and Translation 3, and finally
determine which translation will be selected as the final output:

Output Example:
*** RAG Translation Results ***
1. Translation 1: Based on dictionary entry ‘...’, translated as: “...”
2. Translation 2: Based on dictionary entry ‘...’, translated as: “...”
3. Translation 3: Based on dictionary entry ‘...’, translated as: “...”

*** Translation Quality Analysis ***
1. Translation 0: Result: ...
   Analysis of unconventional expression quality: ...
   Analysis of overall sentence quality: ...
2. Translation 1: Result: ...
   Analysis of unconventional expression quality: ...
   Analysis of overall sentence quality: ...
3. Translation 2: Result: ...
   Analysis of unconventional expression quality: ...
   Analysis of overall sentence quality: ...
4. Translation 3: Result: ...
   Analysis of unconventional expression quality: ...
   Analysis of overall sentence quality: ...

*** Final Translation ***
(Output only the final translation result in this section;
no other information is permitted)
```

这里 `{en}` 对应 $x$，`{think}` 对应检测分析及结果，`{rag_info}` 对应 $E$，`{direct}` 对应 $t_0$。模板把增强候选生成、质量分析和最终选择放在了一次结构化输出中；正文公式则把这些步骤分别展开。模板展示的是生成三条增强译文的具体版本，式 6–7 用一般的 $K$ 表示，二者不要混为“方法永远只能取 3”。此外，原文 System Prompt 指定了 Chinese；如果复用于其他目标语言，这个位置也要相应修改。

这样再回看图 1，几个模块就串起来了：detector 负责找出语义冲突，retrieval 为具体表达补充释义，translator 保留直接与增强两条路径，再从习语和整句两个层面作出比较。比如论文表 1 的 “The boy was foaming at the mouth, throwing things around.”，检索到 “foam at the mouth” 表示极度愤怒后，仲裁就能结合乱扔东西的语境，判断“极度愤怒”比“口吐白沫”更合适。

文中的图 1、编号公式 1–9 和英文 prompt 均对应 Jiang 等人的原论文；额外的符号说明与段落解释用于补全这份阅读笔记。检测 prompt、直接翻译 prompt 和翻译仲裁 prompt 分别穿插在其发挥作用的位置，便于和方法步骤对照。
