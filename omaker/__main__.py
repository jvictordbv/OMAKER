"""Ponto de entrada da GUI: `python -m omaker`, a partir da raiz do repositório."""
import sys

from PySide6.QtWidgets import QApplication


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv
    if "--self-check" in args:   # verificação do .exe no CI (omaker/self_check.py)
        from omaker import self_check

        i = args.index("--self-check")
        return self_check.run(args[i + 1] if i + 1 < len(args) else "omaker-self-check.txt")

    from omaker.ui.main_window import OntoApp
    from omaker.ui.splash import OperaGXSplash

    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    janela_sistema = OntoApp()
    splash = OperaGXSplash(janela_sistema)
    splash.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
