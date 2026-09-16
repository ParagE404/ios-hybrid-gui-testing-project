// In-memory data store with a fixed seed, so every launch starts from the same state.
// Origin: original, 

import Foundation
import Observation
import SwiftUI

enum Category: String, CaseIterable, Identifiable {
    case food = "Food", home = "Home", work = "Work"
    var id: String { rawValue }
    var symbol: String {
        switch self {
        case .food: return "fork.knife"
        case .home: return "house"
        case .work: return "briefcase"
        }
    }
    var color: Color {
        switch self {
        case .food: return .orange
        case .home: return .blue
        case .work: return .purple
        }
    }
}

enum SortOrder: String, CaseIterable, Identifiable {
    case name = "Name", date = "Date"
    var id: String { rawValue }
}

struct Item: Identifiable, Equatable {
    let id: UUID
    var name: String
    var quantity: Int
    var category: Category
    var urgent = false
    var done = false
    var favourite = false
    var created: Date
}

@Observable
final class Store {
    var items: [Item] = []
    var showCompleted = true
    var compactRows = false
    var largeText = false
    var sort: SortOrder = .name
    var filter: Category? = nil

    init() { reset() }

    /// Deterministic seed. Names sort as Batteries, Bread, Eggs, Light bulbs, Milk, Printer paper, Stamps;
    /// dates sort (newest first) as Milk, Stamps, Printer paper, Light bulbs, Eggs, Bread, Batteries.
    func reset() {
        let base = Date(timeIntervalSince1970: 1_760_000_000)
        func day(_ d: Double) -> Date { base.addingTimeInterval(d * 86_400) }
        items = [
            Item(id: UUID(), name: "Batteries", quantity: 4, category: .home, created: day(-6)),
            Item(id: UUID(), name: "Bread", quantity: 1, category: .food, created: day(-5)),
            Item(id: UUID(), name: "Eggs", quantity: 12, category: .food, created: day(-4)),
            Item(id: UUID(), name: "Light bulbs", quantity: 3, category: .home, created: day(-3)),
            Item(id: UUID(), name: "Printer paper", quantity: 1, category: .work, created: day(-2)),
            Item(id: UUID(), name: "Stamps", quantity: 10, category: .work, done: true, created: day(-1)),
            Item(id: UUID(), name: "Milk", quantity: 1, category: .food, created: day(0)),
        ]
        showCompleted = true
        compactRows = false
        largeText = false
        sort = .name
        filter = nil
    }

    var visibleItems: [Item] {
        items
            .filter { showCompleted || !$0.done }
            .filter { filter == nil || $0.category == filter }
            .sorted {
                switch sort {
                case .name: return $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending
                case .date: return $0.created > $1.created
                }
            }
    }

    func item(_ id: UUID) -> Item? { items.first { $0.id == id } }

    func add(name: String, quantity: Int, category: Category, urgent: Bool) {
        items.append(Item(id: UUID(), name: name, quantity: quantity, category: category,
                          urgent: urgent, created: Date()))
    }

    func update(_ id: UUID, name: String, quantity: Int, category: Category, urgent: Bool) {
        guard let i = items.firstIndex(where: { $0.id == id }) else { return }
        items[i].name = name
        items[i].quantity = quantity
        items[i].category = category
        items[i].urgent = urgent
    }

    func delete(_ id: UUID) { items.removeAll { $0.id == id } }

    func toggleDone(_ id: UUID) {
        if let i = items.firstIndex(where: { $0.id == id }) { items[i].done.toggle() }
    }

    func toggleFavourite(_ id: UUID) {
        if let i = items.firstIndex(where: { $0.id == id }) { items[i].favourite.toggle() }
    }
}
