import tkinter as tk
import argparse

from Environment.manual_package_builder import ManualPackageBuilderUI


def main() -> None:
    parser = argparse.ArgumentParser(description="Open the local Python capability workbench.")
    parser.add_argument("--workspace", help="Workspace for generated packages, agents and chats; defaults to this checkout")
    args = parser.parse_args()
    root = tk.Tk()
    app = ManualPackageBuilderUI(root, base_dir=args.workspace)
    app.launch()
    root.mainloop()


if __name__ == "__main__":
    main()
