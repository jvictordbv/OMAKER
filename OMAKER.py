# OMAKER.py
import sys
from PySide6.QtWidgets import QApplication

from ui.main_window import OntoApp
from ui.splash import OperaGXSplash

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    
    janela_sistema = OntoApp()
    
    splash = OperaGXSplash(janela_sistema)
    splash.show()
    
    sys.exit(app.exec())