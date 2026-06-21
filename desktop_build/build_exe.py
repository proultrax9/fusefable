"""สร้าง Fusion Fable.exe (Windows) — self-contained ในโฟลเดอร์ desktop_build/.

โฟลเดอร์นี้มีโค้ดครบในตัวเอง (desktop_build/fusefable/ = สำเนาของ package)
build จากสำเนาในโฟลเดอร์นี้ ไม่พึ่ง root.

ใช้:
    pip install pywebview pyinstaller
    python desktop_build/build_exe.py
ผลลัพธ์: desktop_build/dist/Fusion Fable.exe  (ดับเบิลคลิกเปิดได้ ไม่ต้องมี Python)

หมายเหตุ: ใช้ WebView2 runtime ของ Windows (Win10/11 ส่วนใหญ่มีอยู่แล้ว); ถ้าไม่มี
ติดตั้ง "Microsoft Edge WebView2 Runtime" ฟรีจาก Microsoft.
"""
import os
import PyInstaller.__main__

HERE = os.path.dirname(os.path.abspath(__file__))

PyInstaller.__main__.run([
    os.path.join(HERE, "fusefable_gui.py"),
    "--name", "Fusion Fable",
    "--onefile",
    "--noconsole",
    "--icon", os.path.join(HERE, "FuseFable.ico"),
    # ใช้สำเนา fusefable ในโฟลเดอร์นี้ (self-contained) — มาก่อน root
    "--paths", HERE,
    "--collect-all", "webview",
    "--collect-submodules", "fusefable",
    # web.py ถูก import แบบ lazy ใน run_app → ต้องระบุ hidden import เอง
    "--hidden-import", "fusefable.web",
    "--hidden-import", "fusefable.desktop",
    "--distpath", os.path.join(HERE, "dist"),
    "--workpath", os.path.join(HERE, "build"),
    "--specpath", HERE,
    "--noconfirm",
    "--clean",
])
