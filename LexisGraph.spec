from PyInstaller.utils.hooks import collect_data_files, collect_submodules

a = Analysis(
    ['desktop.py'],
    pathex=[],
    binaries=[],
    datas=[('frontend/dist', 'frontend/dist'), ('backend/static', 'backend/static')]
          + collect_data_files('jieba') + collect_data_files('docx'),
    hiddenimports=collect_submodules('backend') + collect_submodules('uvicorn')
                  + collect_submodules('langgraph') + collect_submodules('langchain_openai'),
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['pytest', 'playwright'], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='LexisGraph',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='LexisGraph')
