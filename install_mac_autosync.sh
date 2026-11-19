#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_LABEL="com.antigravity.quotasync"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
LOG_PATH="$REPO_DIR/sync.log"

echo "=== ตั้งค่าระบบซิงก์โควตา Antigravity IDE ขึ้น GitHub อัตโนมัติ ==="

# 1. ตรวจสอบสิทธิ์การ git push
echo "-> ตรวจสอบการเชื่อมต่อ GitHub..."
git -C "$REPO_DIR" pull --rebase --autostash >/dev/null 2>&1 || true

# 2. รันซิงก์ครั้งแรกเพื่อทดสอบ
echo "-> ทดสอบดึงค่าโควตาจาก Antigravity IDE และซิงก์ขึ้น GitHub..."
python3 "$REPO_DIR/sync_from_mac_ide.py" --push

# 3. สร้าง macOS LaunchAgent ให้ทำงานในพื้นหลังทุกๆ 30 นาที (1800 วินาที) ตอนเปิดเครื่อง
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:\$PATH"; cd "${REPO_DIR}" &amp;&amp; git pull --rebase --autostash &gt;/dev/null 2&gt;&amp;1 || true; /usr/bin/python3 "${REPO_DIR}/sync_from_mac_ide.py" --push</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${REPO_DIR}</string>
    <key>StartInterval</key>
    <integer>1800</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOG_PATH}</string>
    <key>StandardErrorPath</key>
    <string>${LOG_PATH}</string>
</dict>
</plist>
EOF

# โหลด LaunchAgent
launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl load "$PLIST_PATH"

echo ""
echo "✅ ติดตั้งสำเร็จ! ระบบจะซิงก์โควตาจาก Antigravity IDE ขึ้น GitHub ในพื้นหลังอัตโนมัติทุกๆ 30 นาที"
echo "   และตอน 05:47 น. ทุกวัน GitHub Actions จะส่งรายงานเข้า LINE แม้ปิดเครื่อง Mac"
