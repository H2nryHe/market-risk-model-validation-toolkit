# Executive Summary

This project validates MR-001, a rolling Gaussian Parametric VaR / ES model for a hypothetical liquid ETF portfolio. The validation asks whether MR-001 is fit for daily internal market-risk monitoring, portfolio loss-threshold awareness, model comparison, and project risk reporting.

The implementation is correct against the independent project reference: 464/464 comparisons matched with zero maximum absolute difference. The main weakness is methodological, not coding-related. The frozen portfolio return sample has excess kurtosis of 7.55, and the empirical 99% loss quantile is materially larger than the Gaussian-implied 99% loss quantile.

MR-001 performs differently at 95% and 99%. At 95%, exception frequency is 4.82% with Kupiec p-value 0.7281, but clustering remains visible. At 99%, MR-001 records 41/1804 exceptions, a 2.27% exception rate versus a 1% nominal tail. High-volatility periods are especially weak, with a 3.43% 99% exception rate.

Challengers provide useful context but not a clean replacement. Historical and filtered historical challengers improve some 99% unconditional coverage dimensions, while volatility-responsive Gaussian estimates still show far-tail pressure and empirical challengers remain sample-limited.

Data-quality testing injected five deterministic corruptions. All five were detected and blocked, with zero false negatives. This prevented severe hypothetical VaR distortions from flowing downstream.

Formal findings remain open: MV-001 for 99% Gaussian far-tail weakness and MV-002 for temporal dependence/clustering. Monitoring and challenger controls were implemented and assessed, but they are compensating controls, not root-cause elimination.

Final validation decision: **RESTRICTED_USE**. MR-001 may be used as a transparent baseline and limited internal monitoring model, but 99% Gaussian VaR must not be interpreted as a standalone far-tail risk measure. 99% use requires challenger context, monitoring, high-volatility escalation, and visible open-findings governance.
