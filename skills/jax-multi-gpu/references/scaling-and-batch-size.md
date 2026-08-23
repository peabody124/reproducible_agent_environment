# Scaling a Recipe to N Devices: batch size, learning rate, and what the literature says

Companion reference for `jax-multi-gpu` §3. Evidence tags as in the skill: **[C]** cited from the
paper or doc named, **[F]** field report from one project.

## Why this file exists

Most "multi-GPU is less sample-efficient" findings are the experiment changing underneath the
comparison, not a property of the hardware. The four papers below are the ones worth having read
before you buy or book more devices; the skill quotes their conclusions, this file keeps the
citations, the caveats and the exact forms.

## The tradeoff law, precisely

McCandlish, Kaplan & Amodei, *An Empirical Model of Large-Batch Training*
([arXiv:1812.06162](https://arxiv.org/abs/1812.06162)) **[C]**. The **printed** law is the product
form; the additive forms the skill uses are its fixed-batch specialisation (Appendix D), not the
displayed equation. Cite accordingly:

```
(S/S_min − 1) · (E/E_min − 1) = 1          B_crit ≡ E_min / S_min       # printed, §2.3
S/S_min = 1 + B_crit/B     E/E_min = 1 + B/B_crit                       # equivalent, Appendix D
```

Their own definition of the turning point, verbatim: *"for `B > B_crit` there are diminishing
returns from greater data parallelism"*, and Figure 2 pins it at *"the point at which compute
efficiency drops below 50% optimal"*. Note also the separate symbols: `B_crit` is fit empirically
to the tradeoff curve, `B_noise = tr(HΣ) / GᵀHG` is measured from gradient statistics, and the
paper *predicts* they roughly agree — do not present a curve fit as a gradient measurement.

## Learning rate

**Learning rate: the rule depends on the optimizer** **[C]**, all instances of the *saturating*
form `ε(B) = ε* / (1 + B*/B)^α`:

| optimizer | α | reference |
|---|---|---|
| SGD / momentum | `1` (linear), with **gradual** warmup | Goyal et al., [arXiv:1706.02677](https://arxiv.org/abs/1706.02677) |
| Adam / RMSProp | `0.5 < α < 1` (√-ish, pushed toward 1 by large `β₂`) | McCandlish et al. |
| variance-preserving √ rule | `0.5` (and √-scale weight decay with it) | Krizhevsky, [arXiv:1404.5997](https://arxiv.org/abs/1404.5997) |

Because the form saturates, an unbounded `lr *= sqrt(ratio)` overshoots at large `B`. Goyal's
caveat is why warmup exists: *"the linear scaling rule breaks down when the network is changing
rapidly, which commonly occurs in early stages of training"* — and why it must be **gradual**
rather than a constant low LR followed by a jump.

The honest ceiling: Shallue et al., *Measuring the Effects of Data Parallelism*
([arXiv:1811.03600](https://arxiv.org/abs/1811.03600), JMLR 20:112), 35 workloads, found the
optimal LR *"did not always follow either a linear or square root scaling heuristic… In some cases
the optimal effective learning rate even decreased for larger batch sizes"*, and that LR and
momentum must be tuned **jointly** **[C]**. Their three regimes — **perfect scaling → diminishing
returns → maximal data parallelism**, with transition points that depend on model and optimizer —
are the right mental model, and they found *"no evidence that larger batch sizes degrade
out-of-sample performance"* once each size is tuned independently.

**Two traps around the comparison itself** **[C]**:

- **The budget is not neutral.** An epoch/example budget only ever probes the perfect-scaling
  regime and favours small batches; a step budget favours large ones. Say which you used.
- **Check you are not simply IO-bound first.** [Tuning
  Playbook](https://github.com/google-research/tuning_playbook): *"if the batch size doubles, the
  training throughput should also double… If this is not the case then the training pipeline has a
  bottleneck such as I/O or synchronization between compute nodes."* Same source on the usual
  conclusion — *"the largest batch size supported by the available hardware will be smaller than
  the critical batch size… a good rule of thumb is to use the largest batch size possible"* — and
  on the cost of changing your mind later: *"changing the batch size typically requires starting
  the tuning process all over again."* (Gradient accumulation buys none of this: it simulates a
  larger batch and *"does not provide any throughput benefits"*.)

## Cross-check before believing any of it

Shallue et al. is the largest study (71.6M loss measurements, 168k models, 35 workloads) and the
main corrective: the optimal LR *"did not always follow either a linear or square root scaling
heuristic"*, and the maximum useful batch size *"varies significantly between workloads and depends
on properties of the model, training algorithm, and data set"* — momentum scales further than plain
SGD, and *"wider models do not always scale better to larger batch sizes"*.

Recent work worth knowing **[C]**: Zhang et al., *How Does Critical Batch Size Scale in
Pre-training?* ([arXiv:2410.21676](https://arxiv.org/abs/2410.21676), ICLR 2025) — *"CBS scales
primarily with data size rather than model size"*. Merrill et al., *Critical Batch Size Revisited*
([arXiv:2505.23971](https://arxiv.org/abs/2505.23971)) — measures CBS directly and argues the
gradient-noise proxy needs *"strong assumptions… which makes it unclear whether their approach
should be trusted in practice"*; finds CBS *"is near 0 at initialization, increases rapidly at
first, and then plateaus"*, which is an independent argument for warmup.
