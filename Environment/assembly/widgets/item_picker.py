from __future__ import annotations


class ItemPickerMixin:
    """
    Generic item picker launcher.

    Owns:
        - opening the configured item picker class

    Does not own:
        - package selection logic
        - agent selection logic
        - group/default behavior
    """

    def _open_item_picker(self, title_text: str, item_names, on_select) -> None:
        picker_class = getattr(self, "item_picker_class", None)

        if picker_class is None:
            raise RuntimeError("Item picker is not configured on this UI.")

        picker_class(self.root, title_text, item_names, on_select)