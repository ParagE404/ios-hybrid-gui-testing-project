// Add / Edit item sheet.
// Origin: original, 

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

    var body: some View {
        NavigationStack {
            Form {
                TextField("Item name", text: $name)
                    .accessibilityIdentifier("itemNameField")
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
                    Button("Save") { save() }
                        .disabled(trimmed.isEmpty)
                        .optionalIdentifier(idsRemoved ? nil : "saveButton")
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
        if let id = editing {
            store.update(id, name: trimmed, quantity: quantity, category: category, urgent: urgent)
        } else {
            store.add(name: trimmed, quantity: quantity, category: category, urgent: urgent)
        }
        dismiss()
    }
}
