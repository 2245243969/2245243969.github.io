---
title: Teaching Large Language Models an Unseen Language on the Fly
date: 2026-10-25
category: 论文精读
summary: 论文阅读笔记：DIPMT、DIPMT++、词汇覆盖率与融入句法信息的示例。
summary_en: Reading notes on DIPMT, DIPMT++, lexical coverage, and syntactically-informed exemplars.
draft: false
---

2026/10/25 16:57

《Teaching Large Language Models an Unseen Language on the Fly》

考虑到 LLMs 强大的归纳和模仿能力，作者提出了一个有趣的问题：LLMs 可以只通过实时的 prompt 提问下学会翻译低资源问题吗？

这篇文章主要基于前人的工作 DIPMT (Ghazvininejad et al., 2023)。前人已经探索了通过 prompting 来翻译低资源语言，用字典中的信息来提供稀有单词的翻译。但是，DIPMT 是专用于已经有基础能力的 LLMs 身上的。对于完新的语言来说就是大问题了。

## Preliminary: DIPMT

DIPMT 是一个基于 prompt 的方法，用于低资源语言的翻译。给定一个句子，该 model 会在字典中查找各种稀有单词的意思，并直接将其加入到 prompt 中，形式为：*in this context, the word "[source word]" means "[target word]"*. 该技巧采用 in-context learning 的方式，即在当前待测试样本之前放入 k 个示例。但原论文有提到说：当目前的 model 性能小于 10 BLEU points 时，该方法并不适用。

作者提出了一个假设：考虑到 LLMs 强大的推理和模仿能力，根据假设只通过 prompt，我们是可以教会 LLMs 翻译其还没有见过的语言的。

该论文提出了 DIPMT++，该 model 在 DIPMT 上做了两个关键的修改。

{{figure:figure1}}

## 第一点是，提升词汇覆盖率 (Improved Lexical Coverage)

DIPMT 是提供 rare words 的翻译，但是，对于没有见过的低资源语言，提供的翻译越多越好，但是词典中没有足够多的词，故需要其他方法来解决这个问题。DIPMT++ 通过 traditional 统计方法和语言资源来解决该问题。

- 模糊匹配 (Fuzzy Matching)：对于 LRLs，我们缺少形态分析工具，故用正向 or 逆向最大匹配等字符串算法可快速从词典中找到可能相关的词条。
- 双语词典归纳 (Bilingual Lexicon Induction)：平行语料库也可能包含字典未收录的词，GIZA++ (Och and Ney, 2003) 等 traditional statistical methods 可高效地从语料库中挖掘双语词汇对，从而补充现有词典。
- 同义词扩展 (Synonym Expansion)：通过将同义词列表加入字典，可缓解高资源语言的词库不是总可以在 dictionary 找到对应译词的问题。

## 第二点是，融入句法信息的示例 (Syntactically-Informed Exemplar)

DIPMT++ try to 动态选择相关性更高的样例，并 guide model 从中推断出基本的句法信息。对于每个测试样本使用与语言无关的检索算法 BM25 (Robertson et al., 2009) 来检索示例。

{{figure:table11}}
