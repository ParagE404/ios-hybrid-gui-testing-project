// Perturbation switches, read from launch arguments: -perturb <flag> (repeatable).
// Origin: original, 
//
// Each flag changes accessibility metadata or view structure WITHOUT changing what
// the app does, so a correct test should still pass (proposal: "matched perturbed
// variant"). The flag names are referenced from benchmark/scenarios/tb-*.yaml.

import Foundation
import SwiftUI
import UIKit

enum Perturb: String, CaseIterable {
    case tb01AddIdRenamed = "tb01_add_id_renamed"      // cat 1: Add button id addItemButton -> addButton_v2
    case tb02IdsRemoved = "tb02_ids_removed"            // cat 1: Urgent toggle and Save lose their ids
    case tb03RowsWrapped = "tb03_rows_wrapped"          // cat 2: pinned section inserted above rows + extra child view in each row
    case tb04SectionInserted = "tb04_section_inserted"  // cat 2: "Show completed" moved into a new Display section with a subtitle
    case tb05DuplicateDelete = "tb05_duplicate_delete"  // cat 3: every row's delete button is just "Delete"
    case tb06SortRelabel = "tb06_sort_relabel"          // cat 3: "Sort" menu relabelled "Options"
    case tb07StarUnlabelled = "tb07_star_unlabelled"    // cat 4: favourite star has no label, id button_7
    case tb08ChipsUnlabelled = "tb08_chips_unlabelled"  // cat 4: filter chips become icon-only, unlabelled

    // Pilot-only perturbations (benchmark/pilot/). Used ONLY to calibrate the router (D-005);
    // never analysed. Same four categories, different controls and screens from the formal set.
    case p01SegmentRelabel = "p01_segment_relabel"      // cat 3: segments "Name"/"Date" -> "Alphabetical"/"Recent"
    case p02AlertGeneric = "p02_alert_generic"          // cat 3: alert's "Reset" button -> "OK"
    case p03CompactSubtitle = "p03_compact_subtitle"    // cat 2: "Compact rows" toggle gains a subtitle
    case p04EditIcon = "p04_edit_icon"                  // cat 4: "Edit" becomes an unlabelled pencil icon, id button_12
    case p05PickerGeneric = "p05_picker_generic"        // cat 3: "Category" picker relabelled "Type"
    case p06CancelIdRemoved = "p06_cancel_id_removed"   // cat 1: Cancel button loses its id

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
    /// Apply an accessibility identifier only when one is given (used to remove ids under perturbation).
    @ViewBuilder
    func optionalIdentifier(_ id: String?) -> some View {
        if let id { self.accessibilityIdentifier(id) } else { self }
    }
}

/// An SF Symbol redrawn into a plain bitmap, so it LOOKS identical but carries no symbol
/// semantics. Pilot finding (18 Oct 2026): with `Image(systemName:)` iOS still exposed the
/// symbol's inferred label ("Edit", "Home", "Briefcase") on the child image even when
/// `.accessibilityHidden(true)` was applied, which leaked the meaning of category 4 controls.
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
