"""Move the installed axis controls into a separate non-modal dialog.

Run this file next to gui_app.py after the V6 patch. This is a layout-only
change: axis behavior, plotting, sensor communication, recording, and CSV
formatting are not modified.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "gui_app.py"
NEW_MARKER = "POPUP_AXIS_CONTROLS_PATCH_V7"


class PatchError(RuntimeError):
    pass


def method_span(text: str, method_name: str):
    class_match = re.search(r"(?m)^class MainWindow(?:\s*\([^\n]*\))?\s*:", text)
    if not class_match:
        raise PatchError("Could not find class MainWindow.")

    next_class = re.search(r"(?m)^class \w+", text[class_match.end():])
    class_end = len(text) if next_class is None else class_match.end() + next_class.start()
    class_text = text[class_match.end():class_end]

    method_match = re.search(rf"(?m)^    def {re.escape(method_name)}\s*\(", class_text)
    if not method_match:
        raise PatchError(f"Could not find MainWindow.{method_name}().")

    start = class_match.end() + method_match.start()
    search_from = class_match.end() + method_match.end()
    next_method = re.search(r"(?m)^    def \w+\s*\(", text[search_from:class_end])
    end = class_end if next_method is None else search_from + next_method.start()
    return start, end


def add_import(text: str) -> str:
    if re.search(r"(?m)^from PyQt6\.QtWidgets import QDialog\s*$", text):
        return text

    anchor = re.search(r"(?m)^from PyQt6\.QtCore import ", text)
    if not anchor:
        raise PatchError("Could not find the PyQt6 imports.")
    return text[:anchor.start()] + "from PyQt6.QtWidgets import QDialog\n" + text[anchor.start():]


def add_marker(text: str) -> str:
    start, end = method_span(text, "__init__")
    block = text[start:end]
    if NEW_MARKER in block:
        return text

    marker_match = re.search(
        r"(?m)^(\s*)# (?:LEFT_ALIGNED_AXIS_PANEL_PATCH_V6|COMPACT_AXIS_PANEL_PATCH_V5|COLLAPSIBLE_AXES_SAFE_RECORDING_PATCH_V4)\s*$",
        block,
    )
    if not marker_match:
        raise PatchError("The installed axis-panel patch marker was not found.")

    indent = marker_match.group(1)
    insertion = (
        f"{indent}# {NEW_MARKER}\n"
        f"{indent}# Axis controls live in a separate dialog and cannot resize the dashboard.\n"
    )
    block = block[:marker_match.start()] + insertion + block[marker_match.start():]
    return text[:start] + block + text[end:]


DIALOG_BLOCK = '''        # Axis controls are kept in a separate dialog. Because the dialog is
        # not part of the dashboard layout, opening it cannot move or crop the
        # graph, recording checkbox, or live readings.
        self.axis_dialog = QDialog(self)
        self.axis_dialog.setWindowTitle("Axis Controls")
        self.axis_dialog.setModal(False)
        self.axis_dialog.setSizeGripEnabled(False)
        self.axis_dialog.setMinimumWidth(355)
        self.axis_dialog.setMaximumWidth(355)

        axis_outer = QVBoxLayout(self.axis_dialog)
        axis_outer.setContentsMargins(10, 10, 10, 10)
        axis_outer.setSpacing(6)

        self.txt_time_window = QLineEdit()
        self.txt_temp_y_min = QLineEdit()
        self.txt_temp_y_max = QLineEdit()
        self.txt_hum_y_min = QLineEdit()
        self.txt_hum_y_max = QLineEdit()
        self.txt_gas_y_min = {}
        self.txt_gas_y_max = {}
        self.lbl_axis_gas_name = {}

        time_row = QHBoxLayout()
        time_row.setSpacing(6)
        time_row.addWidget(QLabel("Visible time (s):"))
        self.txt_time_window.setFixedWidth(72)
        time_row.addWidget(self.txt_time_window)
        time_row.addWidget(QLabel("latest data"))
        time_row.addStretch()
        axis_outer.addLayout(time_row)

        axis_grid = QGridLayout()
        axis_grid.setContentsMargins(0, 0, 0, 0)
        axis_grid.setHorizontalSpacing(6)
        axis_grid.setVerticalSpacing(5)
        axis_grid.addWidget(QLabel("Axis"), 0, 0)
        axis_grid.addWidget(QLabel("Minimum"), 0, 1)
        axis_grid.addWidget(QLabel("Maximum"), 0, 2)

        for sensor_id in range(1, 4):
            row = sensor_id
            gas_label = QLabel(f"S{sensor_id} gas:")
            gas_min = QLineEdit()
            gas_max = QLineEdit()
            gas_min.setFixedWidth(76)
            gas_max.setFixedWidth(76)
            self.lbl_axis_gas_name[sensor_id] = gas_label
            self.txt_gas_y_min[sensor_id] = gas_min
            self.txt_gas_y_max[sensor_id] = gas_max
            axis_grid.addWidget(gas_label, row, 0)
            axis_grid.addWidget(gas_min, row, 1)
            axis_grid.addWidget(gas_max, row, 2)

        self.txt_temp_y_min.setFixedWidth(76)
        self.txt_temp_y_max.setFixedWidth(76)
        axis_grid.addWidget(QLabel("Temperature:"), 4, 0)
        axis_grid.addWidget(self.txt_temp_y_min, 4, 1)
        axis_grid.addWidget(self.txt_temp_y_max, 4, 2)

        self.txt_hum_y_min.setFixedWidth(76)
        self.txt_hum_y_max.setFixedWidth(76)
        axis_grid.addWidget(QLabel("Humidity:"), 5, 0)
        axis_grid.addWidget(self.txt_hum_y_min, 5, 1)
        axis_grid.addWidget(self.txt_hum_y_max, 5, 2)

        all_axis_edits = [
            self.txt_time_window,
            self.txt_temp_y_min, self.txt_temp_y_max,
            self.txt_hum_y_min, self.txt_hum_y_max,
        ]
        for sensor_id in range(1, 4):
            all_axis_edits.extend((
                self.txt_gas_y_min[sensor_id],
                self.txt_gas_y_max[sensor_id],
            ))

        for edit in all_axis_edits:
            edit.setPlaceholderText("Auto")
            edit.returnPressed.connect(self.apply_axis_limits)

        axis_outer.addLayout(axis_grid)

        axis_button_layout = QHBoxLayout()
        self.btn_apply_axis = QPushButton("Apply Axis Limits")
        self.btn_apply_axis.setStyleSheet("font-weight: bold;")
        self.btn_apply_axis.clicked.connect(self.apply_axis_limits)
        axis_button_layout.addWidget(self.btn_apply_axis)

        self.btn_clear_axis = QPushButton("Clear Manual Limits")
        self.btn_clear_axis.clicked.connect(self.clear_axis_limits)
        axis_button_layout.addWidget(self.btn_clear_axis)
        axis_outer.addLayout(axis_button_layout)

        self.lbl_axis_status = QLabel(
            "Each gas uses its own Y-axis in Separate Gas Plots."
        )
        self.lbl_axis_status.setWordWrap(True)
        self.lbl_axis_status.setStyleSheet("color: gray;")
        axis_outer.addWidget(self.lbl_axis_status)

        self.btn_toggle_axis = QPushButton("Axis Controls...")
        self.btn_toggle_axis.setStyleSheet("font-weight: bold;")
        self.btn_toggle_axis.clicked.connect(self._toggle_axis_panel)
        layout.addWidget(self.btn_toggle_axis)
'''


def replace_axis_block(text: str) -> str:
    start, end = method_span(text, "build_main_tab")
    block = text[start:end]

    patterns = [
        re.compile(
            r"(?ms)^        # Numeric axis controls\. Blank fields keep that axis automatic\.\n"
            r".*?^        layout\.addLayout\(axis_panel_row\)\s*$"
        ),
        re.compile(
            r"(?ms)^        # Numeric axis controls\. Blank fields keep that axis automatic\.\n"
            r".*?^        layout\.addWidget\(self\.axis_group\)\s*$"
        ),
    ]

    match = None
    for pattern in patterns:
        match = pattern.search(block)
        if match:
            break
    if not match:
        raise PatchError("Could not find the installed axis-control panel in build_main_tab().")

    block = block[:match.start()] + DIALOG_BLOCK + "\n" + block[match.end():]
    return text[:start] + block + text[end:]


TOGGLE_METHOD = '''    def _toggle_axis_panel(self, _checked=False):
        """Open or hide the independent axis-controls dialog."""
        if not hasattr(self, 'axis_dialog'):
            return

        if self.axis_dialog.isVisible():
            self.axis_dialog.hide()
            return

        self.axis_dialog.adjustSize()
        self.axis_dialog.show()
        self.axis_dialog.raise_()
        self.axis_dialog.activateWindow()

'''


def replace_toggle_method(text: str) -> str:
    start, end = method_span(text, "_toggle_axis_panel")
    return text[:start] + TOGGLE_METHOD + text[end:]


def backup_path() -> Path:
    base = ROOT / "gui_app.py.before_popup_axis_controls_v7.bak"
    if not base.exists():
        return base
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return ROOT / f"gui_app.py.before_popup_axis_controls_v7_{stamp}.bak"


def main() -> int:
    if not TARGET.exists():
        print("ERROR: gui_app.py was not found next to this installer.")
        print(f"Expected: {TARGET}")
        input("Press Enter to close...")
        return 1

    try:
        original = TARGET.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        print("ERROR: gui_app.py is not UTF-8 text.")
        input("Press Enter to close...")
        return 1

    if NEW_MARKER in original:
        print("The V7 pop-up axis controls are already installed.")
        input("Press Enter to close...")
        return 0

    try:
        modified = add_import(original)
        modified = add_marker(modified)
        modified = replace_axis_block(modified)
        modified = replace_toggle_method(modified)
        compile(modified, str(TARGET), "exec")
    except (PatchError, SyntaxError) as exc:
        print("\nERROR: No changes were saved.")
        print(exc)
        input("Press Enter to close...")
        return 1

    backup = backup_path()
    shutil.copy2(TARGET, backup)
    TARGET.write_text(modified, encoding="utf-8", newline="\n")

    print("\nSUCCESS: Axis controls now open in a separate window.")
    print("The dashboard width will no longer change.")
    print(f"Backup created: {backup.name}")
    input("Press Enter to close...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
