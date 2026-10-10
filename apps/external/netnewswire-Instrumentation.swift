//
//  Instrumentation.swift
//  Research instrumentation for the MSc benchmark; not part of upstream NetNewsWire.
//  Origin: original, 
//  Spec: docs/external-perturbations.md (D-019).
//
//  -resetData          wipe accounts and preferences (Timeline settings and smart-feed read
//                      filters return to their defaults), then seed the On My iPhone account
//                      with a fixed set of empty folders (no feeds, so no network is needed)
//  -perturb <flag>     perturbation switch, same launch-argument reader as the Errands testbed
//                      (apps/testbed/Errands/Perturb.swift). Repeatable.
//

import Foundation
import UIKit
import Account
import RSCore

nonisolated enum Perturb: String, CaseIterable {
	case nn01AddIdRenamed = "nn01_add_id_renamed"                       // cat 1: addButton -> addFeedOrFolderButton
	case nn02SettingsIdRemoved = "nn02_settings_id_removed"             // cat 1: settingsButton id removed
	case nn03TimelineCellsRestructured = "nn03_timeline_cells_restructured" // cat 2: Timeline rows gain a subtitle
	case nn04AddMenuRestructured = "nn04_add_menu_restructured"         // cat 2: Add menu items gain a subtitle
	case nn05SmartFeedsGeneric = "nn05_smart_feeds_generic"             // cat 3: smart feed cells labelled "Smart Feed"
	case nn06SwitchesGeneric = "nn06_switches_generic"                  // cat 3: Timeline switches labelled "Switch"
	case nn07AddIconUnlabelled = "nn07_add_icon_unlabelled"             // cat 4: Add is an unlabelled bitmap, id button_5
	case nn08SettingsIconUnlabelled = "nn08_settings_icon_unlabelled"   // cat 4: Settings is an unlabelled bitmap, id button_6

	static let active: Set<Perturb> = {
		let args = ProcessInfo.processInfo.arguments
		var set = Set<Perturb>()
		for (i, a) in args.enumerated() where a == "-perturb" && i + 1 < args.count {
			if let p = Perturb(rawValue: args[i + 1]) {
				set.insert(p)
			}
		}
		return set
	}()

	static func on(_ p: Perturb) -> Bool { active.contains(p) }
}

@MainActor enum ResetData {
	static let requested = ProcessInfo.processInfo.arguments.contains("-resetData")
	static let seedFolders = ["News", "Technology", "Science", "Sport"]

	/// Call first in didFinishLaunching, before AppDefaults or AccountManager are touched.
	static func wipeIfRequested() {
		guard requested else {
			return
		}
		// App preferences (including the Timeline settings) live in an app-group suite;
		// per-account settings and smart-feed read filters live in standard defaults. Clear both,
		// so every setting returns to the defaults registered in AppDefaults.registerDefaults().
		let store = AppDefaults.store
		for key in store.dictionaryRepresentation().keys {
			store.removeObject(forKey: key)
		}
		if let bundleID = Bundle.main.bundleIdentifier {
			UserDefaults.standard.removePersistentDomain(forName: bundleID)
		}
		// With preferences cleared this launch is a first run, so top-level sections expand as
		// upstream intends; AppDelegate skips the default (network) feed import when requested.
		try? FileManager.default.removeItem(at: AppConfig.dataFolder.appendingPathComponent("Accounts"))
	}

	/// Call after AccountManager has loaded the (now empty) local account.
	static func seedIfRequested() {
		guard requested else {
			return
		}
		let account = AccountManager.shared.defaultAccount
		for name in seedFolders {
			_ = account.ensureFolder(withFolderNames: [name])
		}
	}
}

/// UIKit counterpart of the testbed's UnlabelledSymbol (D-017): the SF Symbol is redrawn into a
/// plain bitmap, so iOS cannot infer an accessibility label from the symbol name.
enum UnlabelledSymbol {
	static func bitmap(_ name: String, _ pointSize: CGFloat = 17) -> UIImage {
		let config = UIImage.SymbolConfiguration(pointSize: pointSize, weight: .regular)
		guard let symbol = UIImage(systemName: name, withConfiguration: config) else {
			return UIImage()
		}
		let format = UIGraphicsImageRendererFormat.preferred()
		let rendered = UIGraphicsImageRenderer(size: symbol.size, format: format).image { _ in
			symbol.withTintColor(.black, renderingMode: .alwaysOriginal).draw(at: .zero)
		}
		return rendered.withRenderingMode(.alwaysTemplate)
	}
}

@MainActor enum ResearchUI {

	// MARK: Feeds toolbar (baseline identifiers; nn01, nn02, nn07, nn08)

	static func configureFeedsToolbar(_ controller: MainFeedCollectionViewController) {
		if let add = controller.addNewItemButton {
			if Perturb.on(.nn07AddIconUnlabelled) {
				makeUnlabelledIcon(add, symbol: "plus", identifier: "button_5")
			} else {
				add.accessibilityIdentifier = Perturb.on(.nn01AddIdRenamed) ? "addFeedOrFolderButton" : "addButton"
			}
		}
		let settingsAction = #selector(MainFeedCollectionViewController.settings(_:))
		if let settings = controller.toolbarItems?.first(where: { $0.action == settingsAction }) {
			if Perturb.on(.nn08SettingsIconUnlabelled) {
				makeUnlabelledIcon(settings, symbol: "gear", identifier: "button_6")
			} else {
				settings.accessibilityIdentifier = Perturb.on(.nn02SettingsIdRemoved) ? nil : "settingsButton"
			}
		}
	}

	private static func makeUnlabelledIcon(_ item: UIBarButtonItem, symbol: String, identifier: String) {
		item.image = UnlabelledSymbol.bitmap(symbol)
		item.title = nil
		item.accessibilityLabel = nil
		item.isAccessibilityElement = true
		item.accessibilityIdentifier = identifier
	}

	// MARK: Add menu (nn04)

	static var addFeedSubtitle: String? {
		Perturb.on(.nn04AddMenuRestructured) ? "Subscribe to a website" : nil
	}

	static var addFolderSubtitle: String? {
		Perturb.on(.nn04AddMenuRestructured) ? "Group your feeds" : nil
	}

	/// Shows the subtitle under the menu item's title. UIKit does not add a UIAction's subtitle
	/// to its accessibility label, so the combined "<title>, <subtitle>" is set explicitly.
	static func addSubtitle(_ subtitle: String?, to action: UIAction) {
		guard let subtitle else {
			return
		}
		action.subtitle = subtitle
		action.accessibilityLabel = "\(action.title), \(subtitle)"
	}

	/// Tapping Add shows an action sheet (the UIMenu above is the long-press menu). Alert actions
	/// have no subtitle, so the subtitle becomes a second line of the title.
	static func sheetTitle(_ title: String, _ subtitle: String?) -> String {
		guard let subtitle else {
			return title
		}
		return "\(title)\n\(subtitle)"
	}

	static func labelSheetAction(_ action: UIAlertAction, _ title: String, _ subtitle: String?) {
		guard let subtitle else {
			return
		}
		action.accessibilityLabel = "\(title), \(subtitle)"
	}

	// MARK: Smart feed cells (nn05)

	static func cellLabelOverride(for sidebarItem: SidebarItem) -> String? {
		(Perturb.on(.nn05SmartFeedsGeneric) && sidebarItem is PseudoFeed) ? "Smart Feed" : nil
	}

	// MARK: Settings Timeline switches (nn03, nn06)

	static func configureTimelineSwitches(_ controller: SettingsViewController) {
		let rows: [(UISwitch?, String, String)] = [
			(controller.timelineSortOrderSwitch, "Sort Oldest to Newest", "Timeline order"),
			(controller.groupByFeedSwitch, "Group by Feed", "Timeline layout"),
			(controller.refreshClearsReadArticlesSwitch, "Refresh to Clear Read Articles", "On refresh"),
			(controller.confirmMarkAllAsReadSwitch, "Confirm Mark All as Read", "Safety"),
		]
		for (control, title, subtitle) in rows {
			guard let control else {
				continue
			}
			if Perturb.on(.nn06SwitchesGeneric) {
				control.accessibilityLabel = "Switch"
				control.accessibilityIdentifier = nil
			} else if Perturb.on(.nn03TimelineCellsRestructured) {
				addSubtitle(subtitle, title: title, to: control)
			}
		}
	}

	/// Adds a second (subtitle) line under the row's title. UIKit does not combine sibling labels
	/// the way SwiftUI does, so the combined label "<title>, <subtitle>" is set explicitly.
	private static func addSubtitle(_ subtitle: String, title: String, to control: UISwitch) {
		guard let contentView = control.superview,
			  let titleLabel = contentView.subviews.compactMap({ $0 as? UILabel }).first else {
			return
		}
		let text = NSMutableAttributedString(string: title, attributes: [.font: titleLabel.font as Any])
		text.append(NSAttributedString(string: "\n" + subtitle, attributes: [
			.font: UIFont.preferredFont(forTextStyle: .footnote),
			.foregroundColor: UIColor.secondaryLabel,
		]))
		titleLabel.numberOfLines = 0
		titleLabel.attributedText = text
		let combined = "\(title), \(subtitle)"
		titleLabel.accessibilityLabel = combined
		control.accessibilityLabel = combined
	}
}
