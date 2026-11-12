# OMAKER.py: atalho para `python -m omaker` (usado pelo OMAKER.spec e por quem já roda `python OMAKER.py`).
import sys

from omaker.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
