# Accessibility-first hybrid iOS GUI testing

MSc Software Engineering project (INM468), City St George's, University of London. Parag Dharadhar, 2026.

A Python test engine that runs plain-English test steps on native iOS apps. It finds each control from the XCUITest accessibility tree and calls a local vision model (ShowUI-2B) only when that match is uncertain. It is evaluated on 24 scenarios across three apps (432 runs), with an optional MCP interface.
