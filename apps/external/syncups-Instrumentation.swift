// Research instrumentation for the MSc benchmark; not part of upstream SyncUps.
// Origin: original, 
// Spec: docs/external-perturbations.md (D-019).
//
//   -resetData          replace stored sync-ups with a fixed seed (fixed ids and dates)
//   -perturb <flag>     perturbation switch, same launch-argument reader as the Errands
//                       testbed (apps/testbed/Errands/Perturb.swift). Repeatable.

import Foundation
import IdentifiedCollections
import Sharing
import SwiftUI
import UIKit

nonisolated enum Perturb: String, CaseIterable {
  case su01AddSymbolChanged = "su01_add_symbol_changed"        // cat 1: Add icon plus -> plus.circle
  case su02EditIdRemoved = "su02_edit_id_removed"              // cat 1: detail Edit loses editSyncUpButton
  case su03NotesSectionInserted = "su03_notes_section_inserted" // cat 2: Notes section above Sync-up Info
  case su04RowsRestructured = "su04_rows_restructured"         // cat 2: theme name added to list rows
  case su05ConfirmRelabelled = "su05_confirm_relabelled"       // cat 3: new sync-up "Add" -> "Done"
  case su06RowsGenericLabel = "su06_rows_generic_label"        // cat 3: row label "Sync-up, <n>, <len>"
  case su07ThemeIconOnly = "su07_theme_icon_only"              // cat 4: Theme row icon only, id button_3
  case su08DeleteIconOnly = "su08_delete_icon_only"            // cat 4: Delete icon only, id button_9

  static let active: Set<Perturb> = {
    let args = ProcessInfo.processInfo.arguments
    var set = Set<Perturb>()
    for (i, a) in args.enumerated() where a == "-perturb" && i + 1 < args.count {
      if let p = Perturb(rawValue: args[i + 1]) { set.insert(p) }
    }
    return set
  }()

  static func on(_ p: Perturb) -> Bool { active.contains(p) }
}

extension View {
  /// Apply an accessibility identifier only when one is given (as in the testbed).
  @ViewBuilder
  func optionalIdentifier(_ id: String?) -> some View {
    if let id { self.accessibilityIdentifier(id) } else { self }
  }
}

/// Same as the testbed's UnlabelledSymbol (D-017): the SF Symbol is redrawn into a plain
/// bitmap, so iOS cannot infer an accessibility label from the symbol name.
struct UnlabelledSymbol: View {
  let name: String
  var pointSize: CGFloat = 17

  var body: some View {
    Image(uiImage: Self.bitmap(name, pointSize))
      .renderingMode(.template)
      .accessibilityHidden(true)
  }

  static func bitmap(_ name: String, _ pointSize: CGFloat) -> UIImage {
    let config = UIImage.SymbolConfiguration(pointSize: pointSize, weight: .regular)
    guard let symbol = UIImage(systemName: name, withConfiguration: config) else { return UIImage() }
    let format = UIGraphicsImageRendererFormat.preferred()
    let rendered = UIGraphicsImageRenderer(size: symbol.size, format: format).image { _ in
      symbol.withTintColor(.black, renderingMode: .alwaysOriginal).draw(at: .zero)
    }
    return rendered.withRenderingMode(.alwaysTemplate)
  }
}

enum ResetData {
  static func applyIfRequested() {
    guard ProcessInfo.processInfo.arguments.contains("-resetData") else { return }
    @Shared(.syncUps) var syncUps
    $syncUps.withLock { $0 = seed }
  }

  private static func id(_ n: Int) -> UUID {
    UUID(uuidString: String(format: "00000000-0000-0000-0000-%012d", n))!
  }

  /// Same content as the upstream mocks (SyncUp.mock, .engineeringMock, .designMock),
  /// but with fixed ids and a fixed meeting date so every launch is identical.
  static let seed: IdentifiedArrayOf<SyncUp> = [
    SyncUp(
      id: SyncUp.ID(id(1)),
      attendees: [
        Attendee(id: Attendee.ID(id(101)), name: "Blob"),
        Attendee(id: Attendee.ID(id(102)), name: "Blob Jr"),
        Attendee(id: Attendee.ID(id(103)), name: "Blob Sr"),
        Attendee(id: Attendee.ID(id(104)), name: "Blob Esq"),
        Attendee(id: Attendee.ID(id(105)), name: "Blob III"),
        Attendee(id: Attendee.ID(id(106)), name: "Blob I"),
      ],
      duration: .seconds(60),
      meetings: [
        Meeting(
          id: Meeting.ID(id(1001)),
          date: Date(timeIntervalSince1970: 1_760_000_000),
          transcript: "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
        )
      ],
      theme: .appOrange,
      title: "Design"
    ),
    SyncUp(
      id: SyncUp.ID(id(2)),
      attendees: [
        Attendee(id: Attendee.ID(id(201)), name: "Blob"),
        Attendee(id: Attendee.ID(id(202)), name: "Blob Jr"),
      ],
      duration: .seconds(60 * 10),
      theme: .periwinkle,
      title: "Engineering"
    ),
    SyncUp(
      id: SyncUp.ID(id(3)),
      attendees: [
        Attendee(id: Attendee.ID(id(301)), name: "Blob Sr"),
        Attendee(id: Attendee.ID(id(302)), name: "Blob Jr"),
      ],
      duration: .seconds(60 * 30),
      theme: .poppy,
      title: "Product"
    ),
  ]
}
