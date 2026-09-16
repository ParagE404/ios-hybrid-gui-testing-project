// Item detail: status texts, Mark as done, Edit, and the favourite star.
// Origin: original, 

import SwiftUI

struct ItemDetailView: View {
    let itemID: UUID
    @Environment(Store.self) private var store
    @State private var editing = false

    var body: some View {
        if let item = store.item(itemID) {
            List {
                LabeledContent("Quantity", value: "\(item.quantity)")
                LabeledContent("Category", value: item.category.rawValue)
                if item.urgent { Text("Urgent item").accessibilityIdentifier("urgentBadge") }
                if item.favourite { Text("In favourites").accessibilityIdentifier("favouriteStatus") }
                if item.done { Text("Completed").accessibilityIdentifier("completedStatus") }
                Button(item.done ? "Mark as not done" : "Mark as done") {
                    store.toggleDone(itemID)
                }
                .accessibilityIdentifier("markDoneButton")
            }
            .navigationTitle(item.name)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) { favouriteButton(item) }
                ToolbarItem(placement: .topBarTrailing) { editButton }
            }
            .sheet(isPresented: $editing) { ItemFormView(editing: itemID) }
        } else {
            Text("Item not found")
        }
    }

    @ViewBuilder
    private var editButton: some View {
        if Perturb.on(.p04EditIcon) {
            // Pilot perturbation: icon-only, no accessibility label, generic id.
            Button { editing = true } label: {
                UnlabelledSymbol(name: "pencil", pointSize: 20)
            }
            .accessibilityIdentifier("button_12")
        } else {
            Button("Edit") { editing = true }.accessibilityIdentifier("editButton")
        }
    }

    @ViewBuilder
    private func favouriteButton(_ item: Item) -> some View {
        // A drawn shape rather than an SF Symbol, so iOS cannot infer a label from the symbol name.
        let button = Button {
            store.toggleFavourite(itemID)
        } label: {
            StarShape()
                .fill(item.favourite ? Color.yellow : Color.clear)
                .overlay(StarShape().stroke(Color.accentColor, lineWidth: 1.5))
                .frame(width: 22, height: 22)
        }
        if Perturb.on(.tb07StarUnlabelled) {
            button.accessibilityIdentifier("button_7")
        } else {
            button
                .accessibilityLabel("Favourite")
                .accessibilityIdentifier("favouriteButton")
        }
    }
}

struct StarShape: Shape {
    func path(in rect: CGRect) -> Path {
        let c = CGPoint(x: rect.midX, y: rect.midY)
        let outer = min(rect.width, rect.height) / 2
        let inner = outer * 0.45
        var p = Path()
        for i in 0..<10 {
            let r = i.isMultiple(of: 2) ? outer : inner
            let a = Double(i) * .pi / 5 - .pi / 2
            let pt = CGPoint(x: c.x + CGFloat(cos(a)) * r, y: c.y + CGFloat(sin(a)) * r)
            if i == 0 { p.move(to: pt) } else { p.addLine(to: pt) }
        }
        p.closeSubpath()
        return p
    }
}
