// List tab: filter chips, sort menu, add button, item rows with inline delete.
// Origin: original, 

import SwiftUI

struct ItemListView: View {
    @Environment(Store.self) private var store
    @State private var path: [UUID] = []
    @State private var showingAdd = false

    var body: some View {
        NavigationStack(path: $path) {
            List {
                if Perturb.on(.tb03RowsWrapped) {
                    // Hierarchy insertion: an extra section and row above the items (shifts row indexes).
                    Section("Pinned") {
                        Text("Today's list")
                    }
                }
                Section(Perturb.on(.tb03RowsWrapped) ? "All errands" : "") {
                    ForEach(store.visibleItems) { item in
                        row(item)
                    }
                }
            }
            .safeAreaInset(edge: .top) { FilterChips() }
            .navigationTitle("Errands")
            .navigationDestination(for: UUID.self) { id in ItemDetailView(itemID: id) }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) { sortMenu }
                ToolbarItem(placement: .topBarTrailing) { addButton }
            }
            .sheet(isPresented: $showingAdd) { ItemFormView(editing: nil) }
        }
    }

    private func row(_ item: Item) -> some View {
        HStack {
            Button {
                path.append(item.id)
            } label: {
                HStack {
                    Circle().fill(item.category.color).frame(width: 10, height: 10)
                        .accessibilityHidden(true)
                    VStack(alignment: .leading) {
                        Text(item.name)
                        if Perturb.on(.tb03RowsWrapped) {
                            // Restructured row: an extra child view changes the combined label
                            // from "Milk, Qty 1" to "Milk, Food, Qty 1".
                            Text(item.category.rawValue).font(.caption2).foregroundStyle(.secondary)
                        }
                        if !store.compactRows {
                            Text("Qty \(item.quantity)").font(.caption).foregroundStyle(.secondary)
                        }
                    }
                    Spacer()
                    if item.done {
                        Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
                            .accessibilityLabel("\(item.name) done")
                    }
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            Button(role: .destructive) {
                store.delete(item.id)
            } label: {
                Image(systemName: "trash")
            }
            .buttonStyle(.borderless)
            .accessibilityLabel(Perturb.on(.tb05DuplicateDelete) ? "Delete" : "Delete \(item.name)")
            .accessibilityIdentifier(Perturb.on(.tb05DuplicateDelete) ? "deleteButton" : "delete_\(item.name)")
        }
    }

    private var addButton: some View {
        Button {
            showingAdd = true
        } label: {
            Image(systemName: "plus")
        }
        .accessibilityLabel("Add item")
        .accessibilityIdentifier(Perturb.on(.tb01AddIdRenamed) ? "addButton_v2" : "addItemButton")
    }

    private var sortMenu: some View {
        Menu {
            Button("By name") { store.sort = .name }
            Button("By date") { store.sort = .date }
        } label: {
            Label(Perturb.on(.tb06SortRelabel) ? "Options" : "Sort", systemImage: "arrow.up.arrow.down")
        }
        .accessibilityIdentifier("sortMenu")
    }
}

struct FilterChips: View {
    @Environment(Store.self) private var store

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                chip(nil, index: 0)
                ForEach(Category.allCases) { c in
                    chip(c, index: (Category.allCases.firstIndex(of: c) ?? 0) + 1)
                }
            }
            .padding(.horizontal)
            .padding(.vertical, 6)
        }
        .background(.bar)
    }

    @ViewBuilder
    private func chip(_ category: Category?, index: Int) -> some View {
        let selected = store.filter == category
        let unlabelled = Perturb.on(.tb08ChipsUnlabelled)
        Button {
            store.filter = category
        } label: {
            Group {
                if unlabelled, let category {
                    // Visually clear (icon), but no accessibility label (bitmap, no symbol semantics).
                    UnlabelledSymbol(name: category.symbol)
                } else if let category {
                    Label(category.rawValue, systemImage: category.symbol)
                } else {
                    Text("All")
                }
            }
            .padding(.horizontal, 12).padding(.vertical, 6)
            .background(selected ? Color.accentColor.opacity(0.2) : Color.secondary.opacity(0.12),
                        in: Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier(unlabelled ? "chip_\(index)" : "filter_\(category?.rawValue ?? "All")")
    }
}
