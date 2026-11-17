// In-memory data store with a fixed seed, so every launch starts from the same state.
//  

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
    var completedFirst = false      // only reachable through the f11 lure fault (D-028)

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
        completedFirst = false
    }

    var visibleItems: [Item] {
        let ignoreShowCompleted = Fault.on(.f04ShowCompletedIgnored)
        let sorted = items
            .filter { ignoreShowCompleted || showCompleted || !$0.done }
            .filter { filter == nil || $0.category == filter }
            .sorted {
                switch sort {
                case .name: return $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending
                case .date: return $0.created > $1.created
                }
            }
        guard completedFirst else { return sorted }
        return sorted.filter { $0.done } + sorted.filter { !$0.done }
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
        if !Fault.on(.f02UrgentNotSaved) { items[i].urgent = urgent }
    }

    func delete(_ id: UUID) {
        if Fault.on(.f05DeleteWrongRow) {
            // Removes the row below the tapped one (or above, for the last row).
            let rows = visibleItems
            if let r = rows.firstIndex(where: { $0.id == id }), rows.count > 1 {
                let victim = rows[r + 1 < rows.count ? r + 1 : r - 1].id
                items.removeAll { $0.id == victim }
                return
            }
        }
        items.removeAll { $0.id == id }
    }

    func toggleDone(_ id: UUID) {
        if let i = items.firstIndex(where: { $0.id == id }) {
            // f03: marks the next item in the store instead of the one shown.
            let target = Fault.on(.f03DoneWrongItem) ? (i + 1) % items.count : i
            items[target].done.toggle()
        }
    }

    func markAllDone() {      // only reachable through the f10 lure fault
        for i in items.indices { items[i].done = true }
    }

    func toggleFavourite(_ id: UUID) {
        if Fault.on(.f07FavouriteNotStored) { return }
        if let i = items.firstIndex(where: { $0.id == id }) { items[i].favourite.toggle() }
    }
}
