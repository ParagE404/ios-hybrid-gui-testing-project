# Literature log

Chapter 2 needs critical synthesis, not summaries. Each entry records what the source found, its limitation for this project, and **how it informs this project**. Harvard style. The proposal promises that search dates, terms and selection decisions are recorded (this is not a systematic review).

**Verification status:** every source below was located on 18 Oct 2026 (publisher page, DBLP-style listing or author PDF) and the headline numbers were read from the abstract or paper. Items marked *(check)* need page numbers or volume confirmed from the publisher page before they go in the final reference list.

## Search record

| Date | Source | Terms | Notes |
|---|---|---|---|
| 26 Jul 2026 | ACM DL, IEEE Xplore, Google Scholar, official docs | mobile GUI testing; locator repair; iOS automation; accessibility metadata; vision-language agents; MCP | Proposal search |
| 18 Oct 2026 | Web search + publisher / arXiv / author pages | "GUI test fragility Android"; "robust XPath locators"; "visual web test repair"; "GUI test script repair structure vision"; "UI-based flaky tests"; "missing labels mobile GUI"; "accessibility issues Android apps"; "LLM mobile GUI testing"; "GUI grounding"; "screen parsing GUI agent"; "non-determinism LLM code generation"; "Model Context Protocol security"; "statistical tests randomized algorithms software engineering"; "iOS GUI testing empirical study" | Gap check: the iOS search returned practitioner blogs and vendor guides, not peer-reviewed empirical studies. This supports the gap claim; record it in 2.1 |
| 18 Oct 2026 | Selection | Excluded: METER (could not locate a verifiable record); vendor blogs (not evidence) | |

## Verified sources by theme

### Theme 1. Fragility of scripted GUI tests

| Reference | Key evidence | How it informs this project |
|---|---|---|
| Coppola, R., Morisio, M. and Torchiano, M. (2017) 'Scripted GUI Testing of Android Apps: A Study on Diffusion, Evolution and Fragility', *Proc. 13th Int. Conf. on Predictive Models and Data Analytics in Software Engineering (PROMISE)*, pp. 22-32. doi:10.1145/3127005.3127008 | About 8.5% of open-source Android projects used any of six scripted GUI frameworks; on average 60% of test modifications were caused by fragility (GUI change, not functional change) | Establishes that locator breakage, not functional change, drives maintenance: the problem RQ2/H2 targets. Android only |
| Coppola, R., Morisio, M. and Torchiano, M. (2018) 'Maintenance of Android Widget-based GUI Testing: A Taxonomy of test case modification reasons', *2018 IEEE Int. Conf. on Software Testing, Verification and Validation Workshops (ICSTW)*, pp. 151-158. doi:10.1109/ICSTW.2018.00044 | 423 Espresso projects, 945 diffs; 27 causes in 9 macro-categories; GUI-related changes in 55% of modified test methods | Taxonomy grounds the perturbation catalogue (identifier changes, hierarchy changes, text changes) so categories 1 to 3 are not invented. Cite when justifying D-004 |
| Leotta, M., Stocco, A., Ricca, F. and Tonella, P. (2016) 'ROBULA+: An Algorithm for Generating Robust XPath Locators for Web Testing', *Journal of Software: Evolution and Process*, 28(3), pp. 177-204. doi:10.1002/smr.1771 | Robust XPaths cut locator fragility by about 90% vs absolute XPaths and about 63% vs Selenium IDE locators | Shows locator choice matters a lot; justifies a fixed, documented scripted-locator policy (D-011) instead of hand-picking. Web only |
| Romano, A., Song, Z., Grandhi, S., Yang, W. and Wang, W. (2021) 'An Empirical Analysis of UI-based Flaky Tests', *Proc. 43rd Int. Conf. on Software Engineering (ICSE)*. *(check pages, DOI)* | 235 flaky UI tests from 62 web and Android projects; async wait about 45% of root causes; platform issues more common on mobile (21.7% vs 10.5%) | Separates flakiness (timing) from fragility (locators). Justifies settle waits, 3 repetitions, and classifying infrastructure failures separately (runner rule in PLAN Week 5) |

### Theme 2. Robust localisation and repair without and with vision

| Reference | Key evidence | How it informs this project |
|---|---|---|
| Nass, M., Alégroth, E., Feldt, R., Leotta, M. and Ricca, F. (2023) 'Similarity-based Web Element Localization for Robust Test Automation', *ACM Transactions on Software Engineering and Methodology*, 32(3), Article 75. doi:10.1145/3571855 | Similo (weighted multi-attribute similarity) failed in 91/801 cases (11%) vs 214 (27%) for the baseline across 48 websites; about 4 ms per lookup | Direct precedent for the weighted structured resolver; its 4 ms overhead frames the expected cost of the structured route. Web, not native iOS |
| Stocco, A., Yandrapally, R. and Mesbah, A. (2018) 'Visual Web Test Repair', *Proc. 26th ACM ESEC/FSE*. *(check pages, DOI)* | Vista repaired about 81% of breakages (592/733) vs 57% (420/733) for DOM-based WATER, over 2,672 tests, 86 releases | Evidence that visual information recovers breakages structure cannot; but it is offline repair, not runtime routing. Supports category 4 and the hybrid idea |
| Xu, T., Pan, M., Pei, Y., Li, G., Zeng, X., Zhang, T., Deng, Y. and Li, X. (2021) 'GUIDER: GUI Structure and Vision Co-Guided Test Script Repair for Android Apps', *Proc. 30th ACM SIGSOFT ISSTA*, pp. 191-203. doi:10.1145/3460319.3464830 | Combining structure and vision enabled 88.8% and 54.9% more correct test actions than vision-only and structure-only repair | Closest prior evidence that structure + vision beats either alone. Difference: GUIDER repairs scripts between versions on Android; this project routes at runtime on iOS with a bounded model |
| Yu, S., Fang, C., Tuo, Z., Zhang, Q., Chen, C., Chen, Z. and Su, Z. (2025) 'Vision-Based Mobile App GUI Testing: A Survey', *ACM Computing Surveys*, 58(6), Article 142. doi:10.1145/3773027 | Reviews 271 papers, 92 vision-based; vision captures what layout files miss | Use for the landscape and to show vision-based work is mostly Android |

### Theme 3. Accessibility metadata as a testing signal, and its quality

| Reference | Key evidence | How it informs this project |
|---|---|---|
| Apple Inc. (2026) 'UIAccessibilityIdentification', *Apple Developer Documentation*. Available at: https://developer.apple.com/documentation/uikit/uiaccessibilityidentification (Accessed: 18 October 2026) | Identifiers are for UI automation scripts; the value corresponds to the element's name in automation | Explains why XCUITest `name` = identifier when set, else label (Element.identifier in the engine) |
| Appium Project (2026a) 'Settings - Appium XCUITest Driver' (from proposal) | Page source is built from XCTest snapshots | Snapshot cost and attributes available to the resolver |
| Chen, J., Chen, C., Xing, Z., Xu, X., Zhu, L., Li, G. and Wang, J. (2020) 'Unblind Your Apps: Predicting Natural-Language Labels for Mobile GUI Components by Deep Learning', *Proc. 42nd ICSE*. doi:10.1145/3377811.3380327 *(check pages)* | More than 77% of 10,408 Android apps have missing-label issues on image-based buttons | Weak metadata is common, not contrived: justifies category 4 (icon-only, unlabelled controls) and the need for a fallback |
| Alshayban, A., Ahmed, I. and Malek, S. (2020) 'Accessibility Issues in Android Apps: State of Affairs, Sentiments, and Ways Forward', *Proc. 42nd ICSE*. *(check pages, DOI)* | 1,135 apps; missing speakable text mean inaccessibility rate 11.08% | Second, independent estimate of missing labels; triangulates Chen et al. |
| Salehnamadi, N., Alshayban, A., Lin, J.-W., Ahmed, I., Branham, S. and Malek, S. (2021) 'Latte: Use-Case and Assistive-Service Driven Automated Accessibility Testing Framework for Android', *Proc. CHI '21*. doi:10.1145/3411764.3445455 | Reuses functional GUI tests and executes them through assistive services | Shows the accessibility layer is a legitimate execution channel for tests, which this project reverses: accessibility data used for functional testing |

### Theme 4. LLM and VLM GUI agents and grounding

| Reference | Key evidence | How it informs this project |
|---|---|---|
| Wen, H. et al. (2024) 'AutoDroid: LLM-powered Task Automation in Android', *Proc. ACM MobiCom '24*. *(check pages, DOI)* | Text-only UI tree (no vision); 90.9% action accuracy, 71.3% task completion with GPT-4; LLM calls are 42.1% to 87.1% of per-step latency | Strong evidence that structured UI representations carry most of the signal, and that model calls dominate latency: both justify accessibility-first with selective fallback |
| Liu, Z. et al. (2024) 'Make LLM a Testing Expert: Bringing Human-like Interaction to Mobile GUI Testing via Functionality-aware Decisions', *Proc. 46th ICSE*. *(check pages, DOI)* | GPTDroid: +32% activity coverage, +31% bugs over best baseline on 93 apps | LLMs suit exploratory testing; contrast with this project's repeatable regression focus |
| Wang, C., Liu, T., Zhao, Y., Yang, M. and Wang, H. (2025) 'LLMDroid', *Proc. ACM on Software Engineering*, 2(FSE), pp. 1001-1022. doi:10.1145/3715763 (from proposal) | LLM guidance used selectively to control cost | Precedent for invoking models only when needed |
| Wang, J. et al. (2024) 'Mobile-Agent' (from proposal) *(check: likely the ICLR 2024 Workshop on LLM Agents, not the main conference)* | Vision-centric mobile agent | Vision-first alternative in Table 1 |
| Zhang, C. et al. (2025) 'AppAgent: Multimodal Agents as Smartphone Users', *Proc. CHI 2025* (from proposal) | Multimodal agent | Vision/LLM alternative |
| Cheng, K., Sun, Q., Chu, Y., Xu, F., Li, Y., Zhang, J. and Wu, Z. (2024) 'SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents', *Proc. 62nd Annual Meeting of the ACL (Vol. 1: Long Papers)*, pp. 9313-9332. doi:10.18653/v1/2024.acl-long.505 | Defines GUI grounding as locating elements from instructions; ScreenSpot benchmark (mobile, desktop, web) | Defines the exact capability the fallback needs; ShowUI is evaluated on ScreenSpot-style grounding |
| Lin, K.Q. et al. (2025) 'ShowUI: One Vision-Language-Action Model for GUI Visual Agent', *Proc. IEEE/CVF CVPR*, pp. 19498-19508 (from proposal) | Selected VLM | D-002 evidence: 12/13 grounding hits, median 3.2 s locally |
| You, K. et al. (2024) 'Ferret-UI: Grounded Mobile UI Understanding with Multimodal LLMs', *ECCV 2024*. *(check volume/pages)* | Mobile-UI MLLM with referring and grounding; small icons are hard, hence any-resolution encoding | Explains why icon-only targets (category 4) are hard even for vision models |
| Lu, Y., Yang, J., Shen, Y. and Awadallah, A. (2024) 'OmniParser for Pure Vision Based GUI Agent', arXiv:2408.00203 | Vision agents need screen parsing to tie actions to regions | Supports snapping model points to parsed elements (D-008) |
| Qin, Y. et al. (2025) 'UI-TARS: Pioneering Automated GUI Interaction with Native Agents', arXiv:2501.12326 | End-to-end native GUI agent model | Current frontier; argue why a smaller grounding model is chosen (local, bounded, reproducible) |
| Wang, S. et al. (2024) 'GUI Agents with Foundation Models: A Comprehensive Survey', arXiv:2411.04890 *(check authors)* | Survey of the agent landscape | Landscape citation |

### Theme 5. Determinism, cost and validity of model-in-the-loop testing

| Reference | Key evidence | How it informs this project |
|---|---|---|
| Ouyang, S., Zhang, J.M., Harman, M. and Wang, M. (2025) 'An Empirical Study of the Non-determinism of ChatGPT in Code Generation', *ACM Transactions on Software Engineering and Methodology*. doi:10.1145/3697010 *(check volume)* | Temperature 0 did not guarantee deterministic outputs; non-determinism threatens conclusion validity | Justifies greedy decoding, logging raw model output, 3 repetitions, and reporting run-to-run variation |
| Arcuri, A. and Briand, L. (2011) 'A practical guide for using statistical tests to assess randomized algorithms in software engineering', *Proc. 33rd ICSE*, pp. 1-10. doi:10.1145/1985793.1985795 | Guidance on repetitions, effect sizes and non-parametric tests | Grounds the analysis plan (paired differences, effect sizes first, exact McNemar, Wilcoxon) |

### Theme 6. Tool interfaces (MCP)

| Reference | Key evidence | How it informs this project |
|---|---|---|
| Model Context Protocol (2025) 'Tools' (from proposal) | Schema-defined tool inputs and outputs | Basis for the MCP adapter |
| Microsoft (2026a, 2026b) Playwright MCP; Emulation (from proposal) | Browser emulation, not native UIKit/SwiftUI | Why native control stays with Appium (D-001) |
| Appium Project (2026b) 'Appium-Related Tools' (from proposal) | Appium MCP exists | MCP is an interface, not this project's contribution |
| Hou, X., Zhao, Y., Wang, S. and Wang, H. (2025) 'Model Context Protocol (MCP): Landscape, Security Threats, and Future Research Directions', arXiv:2503.23278 *(check authors; listed as TOSEM journal-first at FSE 2026)* | Security threats across the MCP server lifecycle | Justifies the restricted, validated action set exposed through MCP |

### Method texts (module recommended)
- Oates, B.J. (2006) *Researching Information Systems and Computing*. London: Sage. Design and creation + experiment strategy.
- Dawson, C.W. (2015) *Projects in Computing and Information Systems: A Student's Guide*. 3rd edn. Harlow: Pearson. *(check edition)*
- Wohlin, C. et al. (2012) *Experimentation in Software Engineering*. Berlin: Springer. *(not yet verified; validity threat categories)*
