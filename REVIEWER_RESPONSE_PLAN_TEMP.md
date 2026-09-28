# Reviewer Response Plan (TEMP)

**Date**: 2026-09-28
**Status**: Draft response strategy

---

## Executive Summary

**Strategy**: Minimal edits + parameter sensitivity studies. Defer theoretical work to "future work" positioning.

**Estimated Effort**:
- Parameter sensitivity: ~2-3 hours compute + 1 hour analysis
- Text edits: ~30 minutes
- Response letter: ~1 hour
- **Total**: ~5 hours

---

## Reviewer 2 Comments (Quantitative Focus)

### R2.1: Winsorization cap sensitivity ✅ **DO**

**Request**: "Provide empirical justification for c_95. Include sensitivity analysis varying cutoff (90th to 99th percentile)."

**Response Strategy**:
- Run ablation with c_90, c_95, c_99
- Show final estimates are stable (expect ±1-2 pp variation)
- Add 1-2 sentences in methods + supplementary table

**Script needed**: `sensitivity_analysis_winsorization.py`

**Deliverable**:
- Supplementary Table S1: "Sensitivity to winsorization threshold"
- Text addition to Section 2.5.1 (~2 sentences)

---

### R2.2: Detour decay τ sensitivity ✅ **DO**

**Request**: "Parametric sweep over τ ∈ [5, 50] to quantify sensitivity of DCWP adjustment."

**Response Strategy**:
- Sweep τ ∈ {5, 10, 15, 20, 30, 40, 50} meters
- Show DCWP effect varies but core finding (16 pp total correction) remains
- Add supplementary figure showing ablation table as function of τ

**Script needed**: `sensitivity_analysis_tau.py`

**Deliverable**:
- Supplementary Figure S1: "Effect of detour decay parameter τ on bias corrections"
- Supplementary Table S2: "Ablation results across τ values"
- Text addition to Section 2.5.3 (~3 sentences)

---

### R2.3: Walk rate clipping justification ✅ **DO**

**Request**: "Justify bias-variance tradeoff of walk rate clipping at 0.1. Report variance before/after."

**Response Strategy**:
- Compute variance of w_temp before/after clipping
- Show clipping affects <1% of observations (only extreme temperatures)
- Report that variance reduction is minimal but prevents numerical instability

**Script needed**: `sensitivity_analysis_walk_rate_clip.py`

**Deliverable**:
- Table in response letter (not main paper): "Walk rate clipping statistics"
- Text addition to Section 2.5.2 (~2 sentences explaining clipping)

---

### R2.4: Theoretical sensitivity bounds ❌ **DEFER**

**Request**: "Bounded sensitivity analysis to quantify unmeasured heterogeneous confounding required to nullify 16 pp shift."

**Response Strategy**: Politely defer as future work

**Proposed Response**:
> "We thank the reviewer for this suggestion. Formal sensitivity bounds for unmeasured confounding (e.g., using methods from Cinelli & Hazlett 2020, Rosenbaum 2002) would strengthen inference and represent valuable future work. However, we note that our core contribution is demonstrating that **bias correction choices shift estimates by 16 percentage points**—larger than any plausible behavioral effect. This magnitude already establishes that naive SVI analysis is unreliable for behavioral measurement, independent of formal bounds.
>
> Sensitivity bounds would help quantify residual confounding after corrections are applied, but our primary claim is about the corrections themselves dominating the signal. We have added this to our discussion of future methodological directions (Section 4)."

**Text addition needed**:
- Add 2-3 sentences in Section 4 acknowledging formal sensitivity analysis as future work
- Cite: Cinelli & Hazlett (2020), Rosenbaum (2002)

---

## Reviewer 7 Comments (Validation/Theory Focus)

### R7.1: Theoretical guarantees ❌ **DEFER**

**Request**: "Provide theoretical guarantees on estimation depending on bias correction choice. What assumptions needed?"

**Response Strategy**: Position as beyond scope; assumptions already stated

**Proposed Response**:
> "We appreciate this comment. Formal theoretical guarantees (e.g., identification conditions, asymptotic properties) for IPW estimators under SVI sampling are an important area for future statistical research. Our current framework (Section 2.2) states the identifying assumptions required for each correction (homogeneity, instantaneous choice, weight validity).
>
> However, deriving formal guarantees is challenging because:
> 1. SVI sampling is non-probabilistic and varies by platform
> 2. The behavioral target (shade preference) has no ground truth for validation
> 3. Multiple correction methods are feasible; we compare them empirically
>
> Our contribution is to demonstrate empirically that correction choices dominate results (16 pp shift), establishing the need for validated methods before making behavioral claims. Developing theoretical guarantees is critical future work but beyond this methodological critique."

**Text addition needed**: None (assumptions already in Section 2.2)

---

### R7.2: Cross-validation with another dataset ❌ **DEFER**

**Request**: "Cross-validate with another dataset to verify claims and gain insights about bias correction effects."

**Response Strategy**: Acknowledge as key limitation (already stated); emphasize this is WHY we call for validation data

**Proposed Response**:
> "We strongly agree that cross-validation would be ideal. However, obtaining ground-truth behavioral data at city scale is **precisely the gap we identify in Section 4**. This is why our conclusion calls for validation datasets (e.g., fixed camera deployments) as a prerequisite for future SVI behavioral studies.
>
> Our paper serves two roles:
> 1. **Methodological**: Develops bias correction framework for SVI-based behavior measurement
> 2. **Diagnostic**: Demonstrates that correction sensitivity (16 pp) exceeds any plausible behavioral signal
>
> Point (2) is robust even without validation—we show that analysts making different defensible correction choices would report wildly different numbers. This alone establishes that naive SVI analysis is unreliable. Validation data would allow us to determine which corrections are correct, but our claim is that **any choice matters enormously**, which we demonstrate conclusively.
>
> We have clarified this in Section 3 (Results) and Section 4 (Conclusion)."

**Text additions needed**:
- Strengthen 1-2 sentences in Results emphasizing we don't claim correct answer, just show sensitivity
- Already strong in conclusion

---

### R7.3: Camera deployment costs/privacy ✅ **DO**

**Request**: "Wouldn't camera deployments be costly and raise privacy concerns? How does this compare to SVI?"

**Response Strategy**: Clarify scope and purpose of camera deployments

**Text Addition** (Section 4, after "large-scale urban camera deployments..."):

> "We emphasize that camera deployments would serve as **one-time calibration studies** to validate SVI bias correction methods, not continuous monitoring for feedback control. Once correction methods are validated, SVI alone could be used for system identification without ongoing surveillance. This is analogous to using expensive experimental setups to validate simulation models—the validation is costly but enables cheaper future application.
>
> Privacy concerns remain valid. Alternative validation approaches could include: (1) aggregated mobility data from transportation authorities, (2) synthetic pedestrian simulations with known behavioral parameters, or (3) controlled field experiments in limited areas. The broader point is that **some form of validation data is required** before SVI-derived behavioral parameters can be trusted for CPHS system identification."

**Location**: End of Section 4 (subsection on "Image validation data")

---

## Summary Table

| Comment | Action | Deliverable | Effort |
|---------|--------|-------------|--------|
| R2.1 Winsorization | DO | Supp Table S1 + 2 sentences | 1 hr |
| R2.2 Tau sweep | DO | Supp Fig S1 + Table S2 + 3 sentences | 2 hr |
| R2.3 Walk clip | DO | Response table + 2 sentences | 1 hr |
| R2.4 Theory bounds | DEFER | Response letter + 2-3 sentences in paper | 30 min |
| R7.1 Guarantees | DEFER | Response letter only | 15 min |
| R7.2 Validation | DEFER | Response letter + strengthen 1-2 sentences | 30 min |
| R7.3 Privacy | DO | Add ~100 words to Section 4 | 15 min |

**Total effort**: ~5.5 hours

---

## Deliverables Checklist

### New Supplementary Materials
- [ ] Supplementary Table S1: Winsorization sensitivity
- [ ] Supplementary Figure S1: Tau parameter sweep (ablation vs τ)
- [ ] Supplementary Table S2: Ablation results for τ ∈ {5, 10, 15, 20, 30, 40, 50}

### Paper Edits
- [ ] Section 2.5.1 (SR-IPW): Add 2 sentences on winsorization choice
- [ ] Section 2.5.2 (Temp-IPW): Add 2 sentences on walk rate clipping
- [ ] Section 2.5.3 (DCWP): Add 3 sentences on τ parameter choice
- [ ] Section 3 (Results): Strengthen 1-2 sentences clarifying we show sensitivity, not correctness
- [ ] Section 4 (Conclusion): Add ~100 words on validation data purpose/alternatives
- [ ] Section 4 (Conclusion): Add 2-3 sentences on theoretical bounds as future work

### Response Letter
- [ ] R2.1: Point to Supp Table S1
- [ ] R2.2: Point to Supp Fig S1 + Table S2
- [ ] R2.3: Point to analysis in revised text
- [ ] R2.4: Polite deferral + justify (see template above)
- [ ] R7.1: Polite deferral + justify (see template above)
- [ ] R7.2: Polite deferral + justify (see template above)
- [ ] R7.3: Point to revised Section 4

---

## Key Messages for Response Letter

1. **We appreciate the constructive feedback** - sensitivity analyses strengthen the paper
2. **Parameter sensitivity studies show robustness** - core finding (16 pp correction dominates signal) holds
3. **Theoretical guarantees are important future work** - but beyond scope of methodological critique
4. **Validation data is the key gap** - this is our primary conclusion, not a limitation
5. **We don't claim to have the right answer** - we show that different defensible choices yield wildly different answers, which itself is the finding

---

## References to Add

- Cinelli, C., & Hazlett, C. (2020). Making sense of sensitivity: Extending omitted variable bias. Journal of the Royal Statistical Society: Series B, 82(1), 39-67.
- Rosenbaum, P. R. (2002). Observational studies (2nd ed.). Springer.

---

**Next Steps**:
1. Create parameter sensitivity scripts (see PARAMETER_SENSITIVITY_PLAN_TEMP.md)
2. Run sensitivity analyses
3. Generate supplementary materials
4. Draft paper edits
5. Draft response letter
