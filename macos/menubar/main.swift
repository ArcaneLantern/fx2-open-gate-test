// FX2 Open Gate menu bar app (LOCAL, 2026-11-26). A tiny AppKit agent app (no Dock icon) that
// puts a camera icon in the macOS menu bar. Clicking it drops a menu; each item opens the matching
// .command in Terminal, so the password prompt and progress are shown exactly as a double-click would.
// It runs nothing itself and holds no camera code: it just launches the kit's existing launchers.
import AppKit

// The kit's macOS launchers live one folder up from this app's own folder is NOT reliable once the
// app is moved, so the launcher folder is baked in at build time (see build.command: __KITMACOS__).
let kitMacOS = "__KITMACOS__"

let anamorphicFlag = (NSHomeDirectory() as NSString).appendingPathComponent(".fx2_opengate_anamorphic")

final class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem!
    var anamorphicItem: NSMenuItem!

    @objc func toggleAnamorphic() {
        if FileManager.default.fileExists(atPath: anamorphicFlag) {
            try? FileManager.default.removeItem(atPath: anamorphicFlag)
        } else {
            FileManager.default.createFile(atPath: anamorphicFlag, contents: Data("on\n".utf8))
        }
        anamorphicItem.state = FileManager.default.fileExists(atPath: anamorphicFlag) ? .on : .off
    }

    func applicationDidFinishLaunching(_ note: Notification) {
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let button = statusItem.button {
            if let img = NSImage(systemSymbolName: "camera.aperture", accessibilityDescription: "FX2 Open Gate") {
                img.isTemplate = true
                button.image = img
            } else {
                button.title = "FX2"
            }
        }
        let menu = NSMenu()
        header(menu, "3840 × 2560 open gate")
        add(menu, "Apply now — camera already plugged in", "open_gate_fast.command")
        add(menu, "Arm, then plug in the camera", "arm_open_gate.command")
        menu.addItem(.separator())
        header(menu, "5.7K · 5760 × 3840 · 300 Mbps")
        add(menu, "Apply now — camera already plugged in", "open_gate_fast_57.command")
        add(menu, "Arm, then plug in the camera", "arm_open_gate_57.command")
        menu.addItem(.separator())
        // The launchers read this file: with it, Apply / Arm also set De-Squeeze Display 1.3x to 2.25:1 (A16, 1.5x anamorphic lenses).
        anamorphicItem = NSMenuItem(title: "1.5× anamorphic preview (De-Squeeze 1.3× → 2.25:1)", action: #selector(toggleAnamorphic), keyEquivalent: "")
        anamorphicItem.target = self
        anamorphicItem.state = FileManager.default.fileExists(atPath: anamorphicFlag) ? .on : .off
        menu.addItem(anamorphicItem)
        add(menu, "Add 1.5× preview now (open gate already applied)", "desqueeze_15x.command")
        menu.addItem(.separator())
        add(menu, "Check only (nothing written)", "check_readonly.command")
        add(menu, "Undo 3840 × 2560 (no battery pull)", "open_gate_putback_3840x2560.command")
        add(menu, "Undo 5.7K (no battery pull)", "open_gate_putback_5760x3840.command")
        menu.addItem(.separator())
        let quit = NSMenuItem(title: "Quit", action: #selector(quit), keyEquivalent: "q")
        quit.target = self
        menu.addItem(quit)
        statusItem.menu = menu
    }

    func header(_ menu: NSMenu, _ title: String) {
        menu.addItem(withTitle: title, action: nil, keyEquivalent: "").isEnabled = false
    }

    func add(_ menu: NSMenu, _ title: String, _ command: String) {
        let item = NSMenuItem(title: title, action: #selector(run(_:)), keyEquivalent: "")
        item.target = self
        item.representedObject = command
        menu.addItem(item)
    }

    @objc func run(_ sender: NSMenuItem) {
        guard let command = sender.representedObject as? String else { return }
        let path = (kitMacOS as NSString).appendingPathComponent(command)
        guard FileManager.default.fileExists(atPath: path) else {
            let a = NSAlert()
            a.messageText = "Launcher not found"
            a.informativeText = "Expected:\n\(path)\n\nIf you moved the kit folder, rebuild the menu bar app."
            a.runModal()
            return
        }
        // .command files open in Terminal by default, so `open <file>` runs it there with the password prompt visible.
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/usr/bin/open")
        p.arguments = [path]
        try? p.run()
    }

    @objc func quit() { NSApp.terminate(nil) }
}

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let delegate = AppDelegate()
app.delegate = delegate
app.run()
