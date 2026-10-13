import sys

if not __package__:
    # `python3 mompy ...` runs this file as a plain script, where the relative import below has no package to work from
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from mompy.cli import main
else:
    from .cli import main

sys.exit(main())
