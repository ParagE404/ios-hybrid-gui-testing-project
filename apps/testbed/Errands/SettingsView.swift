// Origin: AI-generated and reviewed by the author. Testbed workflows and perturbations were defined by the author.
// Settings tab: toggles, segmented sort control, reset with confirmation alert.
//  
//
// The List toggles deliberately have NO accessibility identifiers, so the scripted
// baseline must use a structural locator for them (decision D-011). TB-04's
// perturbation inserts a section above them, which shifts that structure.

import SwiftUI

struct SettingsView: View {
    @Environment(Store.self) private var store
    @State private var confirmReset = false

    var body: some View {
        @Bindable var store = store
        NavigationStack {
            Form {
                if Perturb.on(.tb04SectionInserted) {
                    // Restructured: new section above, and "Show completed" moved into it with a
                    // subtitle, so its combined label becomes "Show completed, Includes finished errands".
                    Section("Display") {
                        Toggle("Large text", isOn: $store.largeText)
                        Toggle(isOn: lure ? $store.completedFirst : $store.showCompleted) {
                            VStack(alignment: .leading) {
                                Text(lure ? "Show completed first" : "Show completed")
                                Text("Includes finished errands").font(.caption).foregroundStyle(.secondary)
                            }
                        }
                    }
                    Section("List") {
                        compactToggle
                    }
                } else {
                    Section("List") {
                        if lure {
                            // Lure: "Show completed" is gone; a similar switch reorders instead of hiding.
                            Toggle("Show completed first", isOn: $store.completedFirst)
                        } else {
                            Toggle("Show completed", isOn: $store.showCompleted)
                        }
                        compactToggle
                    }
                }
                Section("Sorting") {
                    Picker("Sort by", selection: $store.sort) {
                        ForEach(SortOrder.allCases) { Text(segmentTitle($0)).tag($0) }
                    }
                    .pickerStyle(.segmented)
                    .accessibilityIdentifier("sortPicker")
                }
                Section {
                    Button("Reset data", role: .destructive) { confirmReset = true }
                        .accessibilityIdentifier("resetButton")
                }
            }
            .navigationTitle("Settings")
            .alert("Reset all data?", isPresented: $confirmReset) {
                Button(Perturb.on(.p02AlertGeneric) ? "OK" : "Reset", role: .destructive) { store.reset() }
                Button("Cancel", role: .cancel) {}
            }
        }
    }

    private var lure: Bool { Fault.on(.f11ShowCompletedFirstLure) }

    private var compactToggle: some View {
        Toggle(isOn: Binding(get: { store.compactRows }, set: { store.compactRows = $0 })) {
            if Perturb.on(.p03CompactSubtitle) {
                VStack(alignment: .leading) {
                    Text("Compact rows")
                    Text("Hide quantities").font(.caption).foregroundStyle(.secondary)
                }
            } else {
                Text("Compact rows")
            }
        }
    }

    private func segmentTitle(_ order: SortOrder) -> String {
        guard Perturb.on(.p01SegmentRelabel) else { return order.rawValue }
        return order == .name ? "Alphabetical" : "Recent"
    }
}
