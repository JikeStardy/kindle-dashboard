#!/bin/sh

# ================= 信号处理 =================
trap "" 1 15

# ================= 路径 =================
BASE_DIR="/mnt/us/extensions/Kindle-Dashboard"
ARGS_JSON="${BASE_DIR}/args.json"
FBINK="${BASE_DIR}/bin/fbink"
LOG="/tmp/dashboard.log"

echo "[Daemon] Started PID $$" > "$LOG"

# ================= JSON 解析 =================
json_val() {
  sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"\\{0,1\\}\\([^\",}\\]]*\\)\"\\{0,1\\}.*/\\1/p" "$ARGS_JSON" | head -1
}

# ================= 日志轮转 =================
rotate_log() {
  # 超过 50KB 时轮转，保留最新一份
  if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 51200 ]; then
    cp "$LOG" "${LOG}.bak"
    echo "[Daemon] Log rotated" > "$LOG"
  fi
}

# ================= 加载配置 =================
load_config() {
  [ -f "$ARGS_JSON" ] || write_config
  rotate_log

  IMG_URL=$(json_val img_url)
  INTERVAL=$(json_val interval)
  FULL_REFRESH_CYCLE=$(json_val full_refresh_cycle)
  TMP_FILE=$(json_val tmp_file)
  SAFETY_LOCK=$(json_val safety_lock)
  PING_TARGET=$(json_val ping_target)
  ROTATE=$(json_val rotate)
  CLOCK_X=$(json_val clock_x)
  CLOCK_Y=$(json_val clock_y)
  CLOCK_SIZE=$(json_val clock_size)
  CLOCK_FONT=$(json_val clock_font)
  TIME_FORMAT=$(json_val time_format)
  MAX_FAIL_COUNT=$(json_val max_fail_count)
  WIFI_INTERFACE=$(json_val wifi_interface)
  SETTINGS_PATH=$(json_val settings_path)

  [ -z "$IMG_URL" ] && IMG_URL="http://192.168.10.236:15000/render"
  [ -z "$INTERVAL" ] && INTERVAL=300
  [ -z "$FULL_REFRESH_CYCLE" ] && FULL_REFRESH_CYCLE=12
  [ -z "$TMP_FILE" ] && TMP_FILE="/tmp/dashboard_download.png"
  [ -z "$SAFETY_LOCK" ] && SAFETY_LOCK="/mnt/us/STOP_DASH"
  [ -z "$PING_TARGET" ] && PING_TARGET="223.5.5.5"
  [ -z "$ROTATE" ] && ROTATE=3
  [ -z "$CLOCK_X" ] && CLOCK_X=40
  [ -z "$CLOCK_Y" ] && CLOCK_Y=295
  [ -z "$CLOCK_SIZE" ] && CLOCK_SIZE=80
  [ -z "$CLOCK_FONT" ] && CLOCK_FONT="${BASE_DIR}/IBMPlexMono-SemiBold.ttf"
  [ -z "$TIME_FORMAT" ] && TIME_FORMAT=12
  [ -z "$MAX_FAIL_COUNT" ] && MAX_FAIL_COUNT=6
  [ -z "$WIFI_INTERFACE" ] && WIFI_INTERFACE="wlan0"
  [ -z "$SETTINGS_PATH" ] && SETTINGS_PATH="/api/ink_setting"

  BASE_URL=$(echo "$IMG_URL" | sed 's#\(https\{0,1\}://[^/]*\).*#\1#')
  SETTINGS_URL="${BASE_URL}${SETTINGS_PATH}"
}

write_config() {
  cat > "$ARGS_JSON" << 'EOF'
{
  "img_url": "http://192.168.10.236:15000/render",
  "interval": 300,
  "full_refresh_cycle": 12,
  "base_dir": "/mnt/us/extensions/Kindle-Dashboard",
  "tmp_file": "/tmp/dashboard_download.png",
  "log_file": "/tmp/dashboard.log",
  "safety_lock": "/mnt/us/STOP_DASH",
  "ping_target": "223.5.5.5",
  "rotate": 3,
  "enable_local_clock": 1,
  "clock_x": 40,
  "clock_y": 295,
  "clock_size": 80,
  "clock_font": "/mnt/us/extensions/Kindle-Dashboard/IBMPlexMono-SemiBold.ttf",
  "time_format": 12,
  "max_fail_count": 6,
  "wifi_interface": "wlan0",
  "settings_path": "/api/ink_setting"
}
EOF
}

# ================= 从服务器同步 interval/cycle =================
fetch_settings() {
  local json
  json=$(curl -k -L -s --fail --connect-timeout 10 --max-time 20 "${SETTINGS_URL}") || return 1

  local new_interval new_cycle
  new_interval=$(echo "$json" | sed -n 's/.*"interval"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p')
  new_cycle=$(echo "$json" | sed -n 's/.*"full_refresh_cycle"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p')

  [ -n "$new_interval" ] && INTERVAL="$new_interval"
  [ -n "$new_cycle" ] && FULL_REFRESH_CYCLE="$new_cycle"
  echo "[Info] Synced settings: interval=$INTERVAL cycle=$FULL_REFRESH_CYCLE" >> "$LOG"
}

# ================= 停止 Kindle 框架 =================
echo "[Daemon] Stopping framework..." >> "$LOG"
stop framework
sleep 2

echo "[Daemon] Killing UI processes..." >> "$LOG"
killall -9 cvm KPPMainAppV2 mesquite awesome gzip tar 2>/dev/null
"$FBINK" -k -f -q
sleep 2

# ================= 保持唤醒 =================
lipc-set-prop com.lab126.powerd preventScreenSaver 1

# ================= 电源键监听 =================
# 按下电源短按 → goingToSuspend 事件 → 进程退出 → 主循环检测到退出后优雅清理
(
  lipc-wait-event com.lab126.powerd goingToSuspend 2>/dev/null
  echo "[Daemon] Power button pressed, requesting exit" >> "$LOG"
  kill -USR1 $$ 2>/dev/null
) &
POWER_PID=$!

# ================= 初始化 =================
load_config

# USR1 信号 = 电源键退出请求
GRACEFUL_EXIT=0
trap 'GRACEFUL_EXIT=1' USR1
COUNT=0
FAIL_COUNT=0
NEXT_FETCH_TIME=0
SETTINGS_REFRESH_EVERY=4
LOOP_COUNT=0

echo "[Daemon] Ready. Loop starting." >> "$LOG"
sleep 15

# ================= 主循环 =================
while true; do
    # 安全阀 / 电源键退出
    if [ -f "$SAFETY_LOCK" ]; then
        echo "[Daemon] Safety lock detected, exiting" >> "$LOG"
        break
    fi
    if [ "$GRACEFUL_EXIT" -eq 1 ]; then
        echo "[Daemon] Power button exit requested" >> "$LOG"
        break
    fi

    rotate_log
    CURRENT_EPOCH=$(date +%s)
    LOOP_COUNT=$((LOOP_COUNT + 1))

    # 刷新电源锁 + 关闭 WiFi 节能
    lipc-set-prop com.lab126.powerd preventScreenSaver 1
    iw "$WIFI_INTERFACE" set power_save off

    # 屏幕旋转
    echo "$ROTATE" > /sys/class/graphics/fb0/rotate

    # ================= 网络检测 =================
    ping -c 3 -W 5 "$PING_TARGET" > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "[Warn] Network lost ($FAIL_COUNT)" >> "$LOG"

        if [ $FAIL_COUNT -ge $MAX_FAIL_COUNT ]; then
            echo "[Fatal] Network down too long, rebooting" >> "$LOG"
            reboot
        fi

        # 逐级修复：wpa_cli → DHCP → 重启 wifid
        wpa_cli -i "$WIFI_INTERFACE" reconnect
        sleep 5
        udhcpc -i "$WIFI_INTERFACE" -n -t 5 -q

        if [ $FAIL_COUNT -gt 2 ]; then
            lipc-set-prop com.lab126.wifid enable 0
            sleep 2
            lipc-set-prop com.lab126.wifid enable 1
            sleep 15
        fi
    else
        FAIL_COUNT=0
    fi

    # ================= 图片下载 =================
    if [ $CURRENT_EPOCH -ge $NEXT_FETCH_TIME ]; then
        # 定期从服务器同步 interval/cycle (非每次)
        if [ $((LOOP_COUNT % SETTINGS_REFRESH_EVERY)) -eq 0 ]; then
            fetch_settings
        fi

        curl -k -L -s --fail --connect-timeout 20 --max-time 60 --retry 1 "$IMG_URL" -o "$TMP_FILE"
        if [ $? -eq 0 ] && [ -f "$TMP_FILE" ]; then
            COUNT=$((COUNT + 1))

            if [ $COUNT -ge $FULL_REFRESH_CYCLE ]; then
                "$FBINK" -q -k
                "$FBINK" -q -W gc16 -f -g file="$TMP_FILE"
                COUNT=0
            else
                "$FBINK" -q -W gl16 -g file="$TMP_FILE"
            fi

            NEXT_FETCH_TIME=$((CURRENT_EPOCH + INTERVAL))
        else
            echo "[Err] Download failed" >> "$LOG"
            "$FBINK" -q -x 0 -y 0 "Err"
            NEXT_FETCH_TIME=$((CURRENT_EPOCH + 60))
        fi
    fi

    # ================= 智能休眠 =================
    # 短间隔轮询，确保电源键响应 < 5s
    NOW=$(date +%s)
    SLEEP_TOTAL=$((60 - (NOW % 60)))
    [ "$SLEEP_TOTAL" -le 0 ] && SLEEP_TOTAL=1
    while [ "$SLEEP_TOTAL" -gt 0 ] && [ "$GRACEFUL_EXIT" -eq 0 ]; do
        [ "$SLEEP_TOTAL" -lt 5 ] && sleep "$SLEEP_TOTAL" && break
        sleep 5
        SLEEP_TOTAL=$((SLEEP_TOTAL - 5))
    done
done

# ================= 退出清理 =================
echo "[Daemon] Shutting down..." >> "$LOG"

# 停止电源键监听
kill "$POWER_PID" 2>/dev/null
wait "$POWER_PID" 2>/dev/null

# 恢复屏幕刷新
"$FBINK" -q -k

# 释放电源屏保护
lipc-set-prop com.lab126.powerd preventScreenSaver 0

# 重启 Kindle 框架
echo "[Daemon] Restarting framework..." >> "$LOG"
start framework

echo "[Daemon] Exited cleanly" >> "$LOG"
