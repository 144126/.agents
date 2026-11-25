---
name: rsi
description: Reading list of recursive self-improvement (RSI) resources - papers, posts and repos on models or agents improving themselves, looping, test-time compute and self-refinement. Use when a task touches RSI, self-improving agents, looped or recurrent inference, or making a model better without retraining, to find what to read first.
---

# RSI resources

This skill is a reading list, not a method.
Pick the entries that match the task, open their links, and read the sources themselves.
The summaries only help choose; they are not a substitute for the source.

## Adding a resource

Append one entry under Resources, newest first, in this form:

```
### <Title>
- Link: <primary URL>  (also: <source post, code, etc.>)
- Who / when: <authors>, <date>
- Tags: <3-6 short tags>
- Summary: <2-4 sentences: claim, method, key numbers, limits>
```

Read the source before summarizing it. Strip tracking params from URLs.

## Resources

### Training-Free Looped Transformers
- Link: https://arxiv.org/abs/2605.23872  (also: https://x.com/TheZachMueller/status/2125555842627801292)
- Who / when: Lizhang Chen, Jonathan Li, Chen Liang, Ni Lao, Qiang Liu; arXiv 2026-05-22; shared by Zach Mueller 2026-11-25
- Tags: looped transformers, test-time compute, no training, frozen weights, depth recurrence
- Summary: An inference-time wrapper re-runs a contiguous mid-stack block of layers of a frozen pretrained model, with no fine-tuning or architecture change. Naively repeating the block usually hurts; treating each pre-norm block as a forward-Euler ODE step and splitting it into smaller damped sub-steps makes looping help instead. Works across 7 dense, MoE and MLA+MoE families, e.g. Qwen3-4B-Instruct +2.64 pp on MMLU-Pro, Qwen3-30B-A3B +1.14 pp on CommonsenseQA, Moonlight-16B-A3B +1.20 pp on OpenBookQA. Gains are small and benchmark-specific; loop strategy matters more than loop count.
