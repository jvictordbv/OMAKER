"""Ponto de entrada da GUI: `python -m omaker`, a partir da raiz do repositório."""
import sys

from PySide6.QtWidgets import QApplication


def main(argv: list[str] | None = None) -> int:
    from omaker.ui.main_window import OntoApp
    from omaker.ui.splash import OperaGXSplash

    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    janela_sistema = OntoApp()
    splash = OperaGXSplash(janela_sistema)
    splash.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
