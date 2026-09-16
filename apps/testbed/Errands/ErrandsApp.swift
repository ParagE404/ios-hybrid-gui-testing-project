// Errands: purpose-built SwiftUI testbed for the benchmark.
// Origin: original, 

import SwiftUI

@main
struct ErrandsApp: App {
    @State private var store = Store()

    var body: some Scene {
        WindowGroup {
            TabView {
                ItemListView()
                    .tabItem { Label("List", systemImage: "checklist") }
                SettingsView()
                    .tabItem { Label("Settings", systemImage: "gearshape") }
            }
            .environment(store)
        }
    }
}
