#!/usr/bin/env bash
# Build the Errands testbed for the iOS Simulator and install it on the booted device.
# Origin: original, 
# Usage: apps/testbed/build.sh            (needs Xcode, xcodegen, and a booted simulator)
set -euo pipefail
cd "$(dirname "$0")"

command -v xcodegen >/dev/null || { echo "Install xcodegen first: brew install xcodegen"; exit 1; }
xcodegen generate

xcodebuild \
  -project Errands.xcodeproj \
  -scheme Errands \
  -sdk iphonesimulator \
  -configuration Debug \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath build \
  build | tail -20

APP="build/Build/Products/Debug-iphonesimulator/Errands.app"
xcrun simctl install booted "$APP"
echo "Installed $APP (bundle id uk.ac.city.parag.Errands)"
echo "Try: xcrun simctl launch booted uk.ac.city.parag.Errands -perturb tb05_duplicate_delete"
