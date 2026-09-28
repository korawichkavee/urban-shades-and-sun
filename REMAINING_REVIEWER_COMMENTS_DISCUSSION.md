# Discussion: Remaining Reviewer Comments

**Date**: 2026-09-28
**Purpose**: Strategy for addressing R2.4, R7.1, R7.2 (theoretical/validation requests)

---

## The Three Unaddressed Comments

### R2.4 (Reviewer 2): Bounded Sensitivity Analysis
> "The manuscript would be strengthened by incorporating a bounded sensitivity analysis to quantify the magnitude of unmeasured heterogeneous confounding required to nullify the 16 percentage point shift observed in the final estimates."

### R7.1 (Reviewer 7): Theoretical Guarantees
> "Is it possible to provide theoretical guarantees on the estimation depending on the choice of the bias correction selected? If that is the case, what other assumptions are needed for the guarantees to be valid?"

### R7.2 (Reviewer 7): Cross-Validation with Another Dataset
> "The paper could be highly enhanced if a cross validation is performed with another data set and verify that the claims are indeed correct or gain more insights about the effect of the bias correction."

---

## What These Comments Are Really Asking For

### R2.4: Sensitivity to Unmeasured Confounding
**Translation**: Use formal methods (e.g., Cinelli & Hazlett 2020, Rosenbaum's sensitivity analysis) to ask: "How strong would an unmeasured confounder need to be to explain away the 16pp correction?"

**What this requires**:
1. Formalize the causal model (outcome = shade preference, treatment = ???, confounders = ???)
2. Apply sensitivity bound methods (e.g., `sensemakr` R package)
3. Report tipping point analysis

**The problem**:
- Our paper is NOT making a causal claim that needs defending against confounding
- We're making a METHODOLOGICAL claim: "different bias correction choices yield wildly different estimates"
- There's no "treatment effect" to protect from confounding
- The 16pp shift IS the finding, not a causal estimate subject to unmeasured confounding

**Analogy**: Reviewer is asking "prove your treatment effect is robust to confounding" but we're actually saying "look how much your estimate depends on measurement choices"

### R7.1: Theoretical Guarantees
**Translation**: Provide formal statistical theory (identification, consistency, asymptotic normality) for the IPW estimators under SVI sampling.

**What this requires**:
1. Formalize the SVI sampling mechanism (probably as a complex selection process)
2. State sufficient conditions for identification (when does IPW recover the true parameter?)
3. Derive asymptotic properties (rate of convergence, variance estimators)
4. Prove theorems

**The problem**:
- This is a full research paper in statistical theory
- SVI sampling is platform-specific, non-probabilistic, and poorly documented
- The "true parameter" (population shade preference) is undefined (what population? all humans? Seattle residents? people who walk?)
- We don't claim our corrections give the "right answer" - we show they give DIFFERENT answers

### R7.2: Cross-Validation with Another Dataset
**Translation**: Apply the same methods to a different city's data and/or compare to ground truth measurements.

**What this requires**:
1. Process another city's SVI data (substantial data engineering)
2. Obtain ground truth behavioral measurements (the whole point of the paper is these don't exist)
3. Show corrections move estimates toward ground truth

**The problem**:
- Ground truth validation data is the PRIMARY GAP we identify in the paper
- This is literally our conclusion: "we need validation data before using SVI for behavior"
- Asking us to validate without validation data is circular

---

## Strategic Options

### Option 1: Polite Deferrals (Recommended)
**Effort**: 30 minutes writing
**Risk**: Low (common in revisions)

Acknowledge all three as valuable future work while explaining why they're beyond scope:

**R2.4 Response**:
> "We appreciate this suggestion. However, bounded sensitivity analysis (Cinelli & Hazlett 2020) applies when defending a causal estimate against unmeasured confounding. Our contribution is methodological: we demonstrate that bias correction *choices* shift estimates by 16pp - larger than typical behavioral effects. This magnitude establishes unreliability of naive SVI analysis independent of any specific causal claim. Sensitivity bounds would be valuable if using SVI to test a causal hypothesis (e.g., 'does temperature cause shade-seeking?'), but our claim is diagnostic ('do correction methods matter?'), which we demonstrate conclusively. We now cite formal sensitivity analysis as important future work for causal applications of corrected SVI data."

**R7.1 Response**:
> "Formal theoretical guarantees would require: (1) characterizing SVI's platform-specific, non-probabilistic sampling mechanism; (2) defining the target estimand (what population does SVI represent?); and (3) deriving identification conditions and asymptotic properties. This constitutes a substantial theoretical research program beyond our empirical/methodological scope. We note that our core claim - bias corrections shift estimates by 13-17pp depending on defensible parameter choices - is an empirical fact that holds regardless of whether any individual correction is theoretically optimal. We have added this to future work."

**R7.2 Response**:
> "We strongly agree validation is critical - this is our primary conclusion (Section 4). However, the absence of ground-truth behavioral data at city scale is *precisely the gap we identify*. Our contribution is dual: (1) developing a bias correction framework, and (2) demonstrating that correction sensitivity (16pp) exceeds plausible effect sizes, establishing that naive SVI is unreliable for behavioral measurement even without validation. Validation data would tell us *which* correction is right; we show that the *choice* matters enormously, which we establish conclusively. We call for validation infrastructure as prerequisite for future SVI behavioral studies."

### Option 2: Quick Sensitivity Bound Analysis
**Effort**: 2-4 hours
**Risk**: Medium (may not be applicable to our setup)

Actually implement R2.4 using `sensemakr` R package:

**What we'd do**:
1. Frame the 16pp shift as if it were a treatment effect
2. Use Cinelli & Hazlett's approach to compute tipping points
3. Report: "An unmeasured confounder would need to be X times stronger than our strongest observed covariate to nullify the correction"

**Problems**:
- Conceptually mismatched (we're not making a causal claim)
- May confuse readers about what the paper claims
- Requires careful framing to avoid suggesting we're testing causality

**When to use**: If reviewer insists on formal sensitivity analysis after initial response

### Option 3: Minimal Second Dataset Analysis
**Effort**: 4-8 hours (if data already processed)
**Risk**: Medium-High (may not help if no validation data exists)

Address R7.2 by showing consistency across cities:

**What we'd do**:
1. Apply same methods to another city (do you have Phoenix/LA/NYC data processed?)
2. Show that corrections have similar *magnitude* across cities
3. Report: "Correction sensitivity is consistent across urban contexts"

**What this shows**:
- Robustness of the methodology
- Generalizability of the bias problem
- NOT validation (no ground truth)

**When to use**:
- If you have another city's data already processed
- If reviewer pushes back on single-city analysis
- As evidence of external validity (not validation)

### Option 4: Theoretical Sketch (Not Full Theory)
**Effort**: 3-5 hours
**Risk**: Low-Medium (could be hand-wavy)

Address R7.1 with informal theoretical discussion:

**What we'd add**:
- Appendix section: "Theoretical Foundations"
- State assumptions formally (homogeneity, instantaneous choice, weight validity)
- Discuss when IPW is consistent (under those assumptions)
- Acknowledge gaps (SVI sampling mechanism unknown, no convergence rates)
- Cite relevant IPW theory papers (Horvitz-Thompson, Hirano et al.)

**What this provides**:
- Shows we understand the theoretical issues
- Formalizes our existing assumptions
- Doesn't claim to solve the hard problems

**When to use**: If reviewer wants more theoretical rigor but full proofs are out of scope

---

## Recommended Strategy

### Initial Response (Polite Deferrals)

Use **Option 1** for all three comments:
- Frame R2.4 as inapplicable (we're not making causal claims to defend)
- Frame R7.1 as future research program (beyond scope)
- Frame R7.2 as our main conclusion (validation needed is our point)

**Estimated effort**: 30 minutes
**Risk**: Low
**Outcome**: Likely acceptable if framed well

### If Reviewer Pushes Back

Have backup options ready:

**For R2.4**: Use Option 2 (quick sensemakr analysis)
- Shows good faith effort
- Can be done in 2-4 hours
- May not be conceptually perfect but demonstrates robustness

**For R7.1**: Use Option 4 (theoretical sketch in appendix)
- Low effort way to add rigor
- Doesn't require proving theorems
- Shows engagement with theory

**For R7.2**:
- If you have another city's data: Use Option 3
- If not: Reiterate that this is literally the gap the paper identifies

---

## What's Already in Our LaTeX Additions

The `PAPER_TEXT_ADDITIONS_LATEX.tex` already includes deferrals:

**For R2.4 & R7.1** (Discussion, Option A):
> "Several methodological extensions merit future work. First, formal sensitivity bounds could quantify unmeasured confounding required to nullify our findings, complementing our empirical sensitivity analyses. Second, theoretical guarantees on IPW estimator properties under SVI sampling would strengthen inference, though SVI's non-probabilistic sampling complicates such analysis..."

**For R7.2** (implicit in R7.3 response):
> "Alternative validation approaches include aggregated mobility data from transportation authorities, synthetic pedestrian simulations with known behavioral parameters, or controlled field experiments in limited areas."

So we've already planted the seeds for deferral.

---

## Action Items

### Minimal Path Forward (30 minutes)
1. ✅ Add deferrals already drafted in LaTeX additions
2. Draft response letter paragraphs for R2.4, R7.1, R7.2 using Option 1 language
3. Submit revision with parameter sensitivity results + polite deferrals

### If Pressed (2-8 hours additional)
1. R2.4: Run sensemakr analysis (2-4 hours)
2. R7.1: Add theoretical sketch appendix (3-5 hours)
3. R7.2: Process second city if data available (4-8 hours)

---

## My Recommendation

**Start with Option 1 (deferrals)** because:

1. **R2.4 is conceptually mismatched**: We're not defending a causal effect against confounding; we're showing methods matter
2. **R7.1 is a research program**: Full theory would be a separate theory paper
3. **R7.2 IS our conclusion**: We identify validation as the key need

These are all "nice to haves" but not essential to the paper's contribution. The parameter sensitivity analyses (R2.1, R2.2, R2.3) already demonstrate robustness, which is what matters.

If reviewers insist after deferrals, we have backup options (sensemakr, second city, theory sketch) that can be done in 5-10 hours total.

---

## Questions for You

1. **Do you have other cities' data processed?** (Phoenix, LA, NYC?)
   - Would enable Option 3 for R7.2

2. **How risk-averse are you?**
   - Conservative: Do sensemakr analysis preemptively (Option 2)
   - Balanced: Start with deferrals, have backup ready
   - Aggressive: Defer all three, argue they're out of scope

3. **Is there validation data anywhere?**
   - Any fixed-camera pedestrian counts?
   - Any mobility data with temperature correlation?
   - Would make R7.2 feasible

4. **What's your deadline?**
   - If tight: Deferrals only
   - If flexible: Could add sensemakr or second city

---

**Bottom Line**:

All three comments ask for things beyond the paper's scope:
- R2.4: Sensitivity analysis for causal claims (we're not making causal claims)
- R7.1: Full statistical theory (a separate research program)
- R7.2: Validation data (the gap we identify as the field's main need)

**Recommendation**: Polite deferrals with good justification. We've already done the computational work (parameter sensitivity). These are conceptual/scope issues, not technical deficiencies.
