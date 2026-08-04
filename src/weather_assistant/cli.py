import sys
from pathlib import Path

import streamlit.web.cli as stcli


def main() -> None:
    app_path = Path(__file__).resolve().parent / "app.py"
    sys.argv = ["streamlit", "run", str(app_path), *sys.argv[1:]]
    stcli.main()


if __name__ == "__main__":
    main()
