// Origin: AI-generated and reviewed by the author. Testbed workflows and perturbations were defined by the author.
// Add / Edit item sheet.
//  

import SwiftUI

struct ItemFormView: View {
    let editing: UUID?
    @Environment(Store.self) private var store
    @Environment(\.dismiss) private var dismiss

    @State private var name = ""
    @State private var quantity = 1
    @State private var category: Category = .food
    @State private var urgent = false
    @State private var loaded = false

    private var trimmed: String { name.trimmingCharacters(in: .whitespaces) }
    private var idsRemoved: Bool { Perturb.on(.tb02IdsRemoved) }
    private var confirmIconID: String? {
        if editing == nil && Perturb.on(.h04AddConfirmIcon) { return "button_21" }
        if editing != nil && Perturb.on(.h06EditConfirmIcon) { return "button_22" }
        return nil
    }

    var body: some View {
        NavigationStack {
            Form {
                if editing == nil && Perturb.on(.h05NameFieldUnlabelled) {
                    // Looks the same (placeholder drawn as plain text) but exposes no label or placeholder.
                    TextField("", text: $name)
                        .accessibilityIdentifier("textField_1")
                        .overlay(alignment: .leading) {
                            if name.isEmpty {
                                Text("Item name").foregroundStyle(.tertiary)
                                    .accessibilityHidden(true).allowsHitTesting(false)
                            }
                        }
                } else {
                    TextField("Item name", text: $name)
                        .accessibilityIdentifier("itemNameField")
                }
                Stepper("Quantity: \(quantity)", value: $quantity, in: 1...99)
                    .accessibilityIdentifier("quantityStepper")
                Picker(Perturb.on(.p05PickerGeneric) ? "Type" : "Category", selection: $category) {
                    ForEach(Category.allCases) { Text($0.rawValue).tag($0) }
                }
                .accessibilityIdentifier("categoryPicker")
                Toggle("Urgent", isOn: $urgent)
                    .optionalIdentifier(idsRemoved ? nil : "urgentToggle")
            }
            .navigationTitle(editing == nil ? "New Item" : "Edit Item")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                        .optionalIdentifier(Perturb.on(.p06CancelIdRemoved) ? nil : "cancelButton")
                }
                ToolbarItem(placement: .confirmationAction) {
                    if Fault.on(.f09SaveDraftLure) {
                        // Lure: Save is gone; "Save draft" closes the form and stores nothing visible.
                        Button("Save draft") { dismiss() }
                            .accessibilityIdentifier("saveDraftButton")
                    } else if let iconID = confirmIconID {
                        // Held-out flags h04/h06: same action, icon only, no accessibility label.
                        Button { save() } label: { UnlabelledSymbol(name: "checkmark", pointSize: 18) }
                            .disabled(trimmed.isEmpty)
                            .accessibilityIdentifier(iconID)
                    } else {
                        Button("Save") { save() }
                            .disabled(trimmed.isEmpty)
                            .optionalIdentifier(idsRemoved ? nil : "saveButton")
                    }
                }
            }
            .onAppear(perform: load)
        }
    }

    private func load() {
        guard !loaded else { return }
        loaded = true
        if let id = editing, let item = store.item(id) {
            name = item.name
            quantity = item.quantity
            category = item.category
            urgent = item.urgent
        }
    }

    private func save() {
        if Fault.on(.f01SaveNotPersisted) && editing == nil {
            dismiss()
            return
        }
        if let id = editing {
            store.update(id, name: trimmed, quantity: quantity, category: category, urgent: urgent)
        } else {
            store.add(name: trimmed, quantity: quantity, category: category, urgent: urgent)
        }
        dismiss()
    }
}
