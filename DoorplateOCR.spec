# Build both portable directory and self-contained single-file Windows x64 releases.
from PyInstaller.utils.hooks import collect_all
from pathlib import Path
root=Path(SPECPATH).resolve()
binaries=[];datas=[];hiddenimports=[]
for package in ['rapidocr_onnxruntime','onnxruntime','tkinterdnd2']:
 d,b,h=collect_all(package);datas+=d;binaries+=b;hiddenimports+=h
if (root/'第三方许可').exists():datas.append((str(root/'第三方许可'),'third_party_licenses'))
datas.append((str(root/'assets'),'assets'))
datas += [(str(root/'LICENSE'),'.'),(str(root/'THIRD_PARTY_NOTICES.md'),'.')]
a=Analysis([str(root/'app.py')],pathex=[str(root)],binaries=binaries,datas=datas,hiddenimports=hiddenimports,
 excludes=['torch','tensorflow','matplotlib','pandas','scipy','IPython','pytest','notebook','jupyter'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='DoorplateOCR',debug=False,strip=False,upx=False,console=False,disable_windowed_traceback=False,
        icon=str(root/'assets/app.ico'),version=str(root/'version_info.txt'))
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='DoorplateOCR')
single=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='门牌识别工作台',debug=False,strip=False,upx=False,console=False,
           disable_windowed_traceback=False,icon=str(root/'assets/app.ico'),version=str(root/'version_info.txt'),
           runtime_tmpdir=r'%LOCALAPPDATA%\DoorplateWorkbench\Runtime')
