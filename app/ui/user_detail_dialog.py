"""Shows a single user's profile and everything they own -- the click-through
view from the Users table described in the product plan.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from app.services.user_service import fetch_user_with_items


class UserDetailDialog(QDialog):
    def __init__(self, user_id: int, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(420, 480)

        user, items = fetch_user_with_items(user_id)
        self.setWindowTitle(user.name if user else "User")

        layout = QVBoxLayout(self)

        if user is None:
            layout.addWidget(QLabel("User not found."))
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(self.reject)
            buttons.accepted.connect(self.accept)
            layout.addWidget(buttons)
            return

        name_label = QLabel(user.name)
        name_label.setObjectName("ScreenTitle")

        meta_bits = []
        if user.department:
            meta_bits.append(user.department)
        meta_bits.append(user.status.value)
        meta_label = QLabel(" · ".join(meta_bits))
        meta_label.setObjectName("FilterLabel")

        count_label = QLabel(f"Total Items: {len(items)}")

        layout.addWidget(name_label)
        layout.addWidget(meta_label)
        layout.addWidget(count_label)

        items_header = QLabel("Items")
        items_header.setObjectName("FilterLabel")
        layout.addWidget(items_header)

        item_list = QListWidget()
        if items:
            for item in items:
                category = item.category.name if item.category else "Uncategorized"
                list_item = QListWidgetItem(
                    f"{item.name}  ({item.inventory_number}) — {category} — {item.status.value}"
                )
                item_list.addItem(list_item)
        else:
            placeholder = QListWidgetItem("No items owned.")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            item_list.addItem(placeholder)
        layout.addWidget(item_list, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
