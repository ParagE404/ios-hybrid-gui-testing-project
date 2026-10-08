# Pinned versions


| Component | Version | How checked |
|---|---|---|
| macOS | 27.0.1 (build 26A434), arm64 | `sw_vers` |
| Mac hardware | MacBook Pro M4 Pro, RAM: 24 GB | `sysctl hw.memsize` |
| Xcode | 27.1 (build 27A9275); iphonesimulator SDK 27.1 | `xcodebuild -version` |
| iOS Simulator runtime | iOS 27.0 (24A434) used; iOS 27.1 (24A94425) also installed | `xcrun simctl list runtimes` |
| Simulator device | iPhone 17, iOS 27.0, UDID B2D889CB-D62D-4D0B-81FE-94C5546AE632 (window 402 x 874 pt) | `xcrun simctl list devices` |
| XcodeGen | 2.46.0 | `xcodegen --version` |
| WebDriverAgent | 16.16.0 (bundled with xcuitest 12.18.2) | Appium server log |
| Homebrew | 5.1.11 | `brew --version` |
| Node | v24.16.0 (via nvm, not Homebrew); npm 11.13.0 | `node --version` |
| Appium | 3.8.0 (npm global, under nvm Node) | `appium --version` |
| XCUITest driver | 12.18.2 | `appium driver list --installed` |
| Python | 3.12.15 (Homebrew python@3.12), venv at `.venv/` | `python --version` |
| Appium-Python-Client | 6.0.7 | `pip show Appium-Python-Client` |
| selenium | 4.51.0 (dependency of Appium-Python-Client) | `pip show selenium` |
| torch | 2.14.1 (MPS available) | `pip show torch` |
| torchvision | 0.29.1 | `pip show torchvision` |
| transformers | 5.20.1 | `pip show transformers` |
| accelerate | 1.15.0 | `pip show accelerate` |
| qwen-vl-utils | 0.0.14 | `pip show qwen-vl-utils` |
| pillow | 13.0.0 | `pip show pillow` |
| huggingface_hub | 2.2.0 | `pip show huggingface_hub` |
| numpy (analysis) | 2.5.4 | `pip show numpy` |
| pandas (analysis) | 3.0.6 | `pip show pandas` |
| scipy (analysis) | 1.18.1 | `pip show scipy` |
| matplotlib (analysis) | 3.11.2 | `pip show matplotlib` |
| tabulate (analysis, Markdown tables) | 0.10.0 | `pip show tabulate` |
| VLM model + revision | showlab/ShowUI-2B @ cabec4fcc48d15ffd3efe0b33ea9bc7d41509d60 (weights: pytorch_model.bin, 4.4 GB) | HF commit hash (`refs/main` in HF cache) |
| VLM processor + revision | Qwen/Qwen2-VL-2B-Instruct @ 895c3a49bc3fa70a340399125c650a463535e71c (2 safetensors shards, 4.4 GB) | HF commit hash (`refs/main` in HF cache) |
| SyncUps (external app) | pointfreeco/syncups @ 170bc1ad7b0ec1e64606d7c45c54456a0f26b04c + apps/external/syncups.patch (swift-sharing pinned 2.8.2) | `git -C apps/external/syncups rev-parse HEAD` |

## Notes
- Node: an nvm-managed Node v24.16.0 was already present, so `brew install node` from the setup checklist was skipped to avoid two Node installs competing on PATH. Appium therefore lives under `~/.nvm/versions/node/v24.16.0/`; switching nvm Node version will hide it.
- transformers resolved to a 5.x release. `Qwen2VLForConditionalGeneration`, `AutoProcessor` and `qwen_vl_utils.process_vision_info` import cleanly, but the ShowUI spike has not run yet; if it misbehaves, pinning `transformers<5` is the first thing to try.
- Full environment snapshot: `pip freeze > docs/requirements-lock.txt` once the spikes pass.
