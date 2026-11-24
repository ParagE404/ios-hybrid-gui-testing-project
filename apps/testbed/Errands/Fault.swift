// Origin: AI-generated and reviewed by the author. Fault design was defined by the author with AI assistance.
// Seeded faults for the fault-detection study (D-028), read from launch arguments: -fault <flag>.
//
// Unlike Perturb (which changes metadata or structure but never behaviour), each flag here makes the
// app do the WRONG thing, so a correct test should FAIL. Flags are inert unless passed; with no
// -fault argument the app behaves exactly as the build used in the formal experiment.
// The flag names are referenced from benchmark/faults/f-*.yaml.

import Foundation

enum Fault: String, CaseIterable {
    // Behavioural faults, one per testbed journey tb-01..08.
    case f01SaveNotPersisted = "f01_save_not_persisted"            // Save closes the form but adds nothing
    case f02UrgentNotSaved = "f02_urgent_not_saved"                // edit drops the Urgent flag
    case f03DoneWrongItem = "f03_done_wrong_item"                  // Mark as done marks the next item
    case f04ShowCompletedIgnored = "f04_show_completed_ignored"    // list ignores Show completed
    case f05DeleteWrongRow = "f05_delete_wrong_row"                // Delete removes the row below
    case f06SortIgnored = "f06_sort_ignored"                       // "By date" keeps name order
    case f07FavouriteNotStored = "f07_favourite_not_stored"        // star tap does nothing
    case f08FilterWrongCategory = "f08_filter_wrong_category"      // chip applies the previous category

    // Lure faults: the intended control is removed and a similar one remains.
    case f09SaveDraftLure = "f09_save_draft_lure"                  // Save -> "Save draft" (adds nothing)
    case f10MarkAllLure = "f10_mark_all_lure"                      // Mark as done -> "Mark all as done"
    case f11ShowCompletedFirstLure = "f11_show_completed_first_lure" // Show completed -> "Show completed first"
    case f12DeleteEggsLure = "f12_delete_eggs_lure"                // Eggs row has no Delete button

    static let active: Set<Fault> = {
        let args = ProcessInfo.processInfo.arguments
        var set = Set<Fault>()
        for (i, a) in args.enumerated() where a == "-fault" && i + 1 < args.count {
            if let f = Fault(rawValue: args[i + 1]) { set.insert(f) }
        }
        return set
    }()

    static func on(_ f: Fault) -> Bool { active.contains(f) }
}
