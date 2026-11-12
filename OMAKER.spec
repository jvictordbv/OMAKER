# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = []
datas += collect_data_files('owlready2')
# Dados do pacote omaker listados à mão: collect_data_files('omaker') pula o pacote porque a pasta
# do repositório também se chama omaker.
datas += [
    ('omaker/resources/symp.owl', 'omaker/resources'),
    ('omaker/relations/train_relations.json', 'omaker/relations'),
    ('omaker/evaluation/gold/samples.json', 'omaker/evaluation/gold'),
]


a = Analysis(
    ['OMAKER.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OMAKER',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # TODO Fase 6: assets/logo_omaker.ico (o .png original está só na máquina do João)
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='OMAKER',
)
