#!/bin/sh

# ================= Fix 1: 免疫死亡信号 =================
# 1 = SIGHUP (挂起), 15 = SIGTERM (终止)
# 这行命令让脚本在这个信号到来时"什么都不做"，从而存活下来
trap "" 1 15

# ================= 配置 =================
DEFAULT_BASE_DIR="/mnt/us/extensions/Kindle-Dashboard"
DEFAULT_IMG_URL="http://192.168.10.236:15000/render"
DEFAULT_INTERVAL=300
DEFAULT_FULL_REFRESH_CYCLE=12
DEFAULT_TMP_FILE="/tmp/dashboard_download.png"
DEFAULT_LOG_FILE="/tmp/dashboard.log"
DEFAULT_SAFETY_LOCK="/mnt/us/STOP_DASH"
DEFAULT_PING_TARGET="223.5.5.5"
DEFAULT_ROTATE=3
DEFAULT_ENABLE_LOCAL_CLOCK=1
DEFAULT_CLOCK_X=40
DEFAULT_CLOCK_Y=295
DEFAULT_CLOCK_SIZE=80
DEFAULT_TIME_FORMAT=12
DEFAULT_MAX_FAIL_COUNT=6
DEFAULT_WIFI_INTERFACE="wlan0"
DEFAULT_SETTINGS_PATH="/api/ink_setting"

BASE_DIR="$DEFAULT_BASE_DIR"
ARGS_JSON="${BASE_DIR}/args.json"

json_get_int() {
    KEY="$1"
    FILE="$2"
    sed -n "s/.*\"${KEY}\"[[:space:]]*:[[:space:]]*\\([0-9]\\+\\).*/\\1/p" "$FILE" | sed -n '1p'
}

json_get_string() {
    KEY="$1"
    FILE="$2"
    sed -n "s/.*\"${KEY}\"[[:space:]]*:[[:space:]]*\"\\([^\"]*\\)\".*/\\1/p" "$FILE" | sed -n '1p'
}

apply_defaults() {
    IMG_URL="$DEFAULT_IMG_URL"
    INTERVAL="$DEFAULT_INTERVAL"
    FULL_REFRESH_CYCLE="$DEFAULT_FULL_REFRESH_CYCLE"
    TMP_FILE="$DEFAULT_TMP_FILE"
    LOG="$DEFAULT_LOG_FILE"
    SAFETY_LOCK="$DEFAULT_SAFETY_LOCK"
    PING_TARGET="$DEFAULT_PING_TARGET"
    ROTATE="$DEFAULT_ROTATE"
    ENABLE_LOCAL_CLOCK="$DEFAULT_ENABLE_LOCAL_CLOCK"
    CLOCK_X="$DEFAULT_CLOCK_X"
    CLOCK_Y="$DEFAULT_CLOCK_Y"
    CLOCK_SIZE="$DEFAULT_CLOCK_SIZE"
    CLOCK_FONT="${BASE_DIR}/IBMPlexMono-SemiBold.ttf"
    TIME_FORMAT="$DEFAULT_TIME_FORMAT"
    MAX_FAIL_COUNT="$DEFAULT_MAX_FAIL_COUNT"
    WIFI_INTERFACE="$DEFAULT_WIFI_INTERFACE"
    SETTINGS_PATH="$DEFAULT_SETTINGS_PATH"
}

refresh_derived() {
    BASE_URL=$(echo "$IMG_URL" | sed -E 's#(https?://[^/]+).*#\1#')
    SETTINGS_URL="${BASE_URL}${SETTINGS_PATH}"
    FBINK_CMD="${BASE_DIR}/bin/fbink"
}

write_args_json() {
    cat > "$ARGS_JSON" <<EOF
{"img_url":"$IMG_URL","interval":$INTERVAL,"full_refresh_cycle":$FULL_REFRESH_CYCLE,"base_dir":"$BASE_DIR","tmp_file":"$TMP_FILE","log_file":"$LOG","safety_lock":"$SAFETY_LOCK","ping_target":"$PING_TARGET","rotate":$ROTATE,"enable_local_clock":$ENABLE_LOCAL_CLOCK,"clock_x":$CLOCK_X,"clock_y":$CLOCK_Y,"clock_size":$CLOCK_SIZE,"clock_font":"$CLOCK_FONT","time_format":$TIME_FORMAT,"max_fail_count":$MAX_FAIL_COUNT,"wifi_interface":"$WIFI_INTERFACE","settings_path":"$SETTINGS_PATH"}
EOF
}

load_config_from_json() {
    FILE="$1"
    [ -f "$FILE" ] || return 1

    IMG_URL_NEW=$(json_get_string "img_url" "$FILE")
    INTERVAL_NEW=$(json_get_int "interval" "$FILE")
    FULL_REFRESH_CYCLE_NEW=$(json_get_int "full_refresh_cycle" "$FILE")
    BASE_DIR_NEW=$(json_get_string "base_dir" "$FILE")
    TMP_FILE_NEW=$(json_get_string "tmp_file" "$FILE")
    LOG_NEW=$(json_get_string "log_file" "$FILE")
    SAFETY_LOCK_NEW=$(json_get_string "safety_lock" "$FILE")
    PING_TARGET_NEW=$(json_get_string "ping_target" "$FILE")
    ROTATE_NEW=$(json_get_int "rotate" "$FILE")
    ENABLE_LOCAL_CLOCK_NEW=$(json_get_int "enable_local_clock" "$FILE")
    CLOCK_X_NEW=$(json_get_int "clock_x" "$FILE")
    CLOCK_Y_NEW=$(json_get_int "clock_y" "$FILE")
    CLOCK_SIZE_NEW=$(json_get_int "clock_size" "$FILE")
    CLOCK_FONT_NEW=$(json_get_string "clock_font" "$FILE")
    TIME_FORMAT_NEW=$(json_get_int "time_format" "$FILE")
    MAX_FAIL_COUNT_NEW=$(json_get_int "max_fail_count" "$FILE")
    WIFI_INTERFACE_NEW=$(json_get_string "wifi_interface" "$FILE")
    SETTINGS_PATH_NEW=$(json_get_string "settings_path" "$FILE")

    [ -n "$IMG_URL_NEW" ] && IMG_URL="$IMG_URL_NEW"
    [ -n "$INTERVAL_NEW" ] && INTERVAL="$INTERVAL_NEW"
    [ -n "$FULL_REFRESH_CYCLE_NEW" ] && FULL_REFRESH_CYCLE="$FULL_REFRESH_CYCLE_NEW"
    [ -n "$BASE_DIR_NEW" ] && BASE_DIR="$BASE_DIR_NEW"
    [ -n "$TMP_FILE_NEW" ] && TMP_FILE="$TMP_FILE_NEW"
    [ -n "$LOG_NEW" ] && LOG="$LOG_NEW"
    [ -n "$SAFETY_LOCK_NEW" ] && SAFETY_LOCK="$SAFETY_LOCK_NEW"
    [ -n "$PING_TARGET_NEW" ] && PING_TARGET="$PING_TARGET_NEW"
    [ -n "$ROTATE_NEW" ] && ROTATE="$ROTATE_NEW"
    [ -n "$ENABLE_LOCAL_CLOCK_NEW" ] && ENABLE_LOCAL_CLOCK="$ENABLE_LOCAL_CLOCK_NEW"
    [ -n "$CLOCK_X_NEW" ] && CLOCK_X="$CLOCK_X_NEW"
    [ -n "$CLOCK_Y_NEW" ] && CLOCK_Y="$CLOCK_Y_NEW"
    [ -n "$CLOCK_SIZE_NEW" ] && CLOCK_SIZE="$CLOCK_SIZE_NEW"
    [ -n "$CLOCK_FONT_NEW" ] && CLOCK_FONT="$CLOCK_FONT_NEW"
    [ -n "$TIME_FORMAT_NEW" ] && TIME_FORMAT="$TIME_FORMAT_NEW"
    [ -n "$MAX_FAIL_COUNT_NEW" ] && MAX_FAIL_COUNT="$MAX_FAIL_COUNT_NEW"
    [ -n "$WIFI_INTERFACE_NEW" ] && WIFI_INTERFACE="$WIFI_INTERFACE_NEW"
    [ -n "$SETTINGS_PATH_NEW" ] && SETTINGS_PATH="$SETTINGS_PATH_NEW"
}

fetch_settings() {
    SETTINGS_JSON=$(curl -k -L -s --fail --connect-timeout 10 --max-time 20 "$SETTINGS_URL")
    SETTINGS_RET=$?

    if [ $SETTINGS_RET -eq 0 ] && [ -n "$SETTINGS_JSON" ]; then
        INTERVAL_NEW=$(echo "$SETTINGS_JSON" | sed -n 's/.*"interval"[[:space:]]*:[[:space:]]*\([0-9]\+\).*/\1/p')
        FULL_REFRESH_CYCLE_NEW=$(echo "$SETTINGS_JSON" | sed -n 's/.*"full_refresh_cycle"[[:space:]]*:[[:space:]]*\([0-9]\+\).*/\1/p')

        [ -n "$INTERVAL_NEW" ] && INTERVAL="$INTERVAL_NEW"
        [ -n "$FULL_REFRESH_CYCLE_NEW" ] && FULL_REFRESH_CYCLE="$FULL_REFRESH_CYCLE_NEW"
    else
        echo "[Warn] Settings fetch failed ($SETTINGS_RET)" >> "$LOG"
    fi

    write_args_json
}

apply_defaults
if [ ! -f "$ARGS_JSON" ]; then
    write_args_json
fi
load_config_from_json "$ARGS_JSON"
refresh_derived

# [新增] 连续失败计数器
FAIL_COUNT=0

# =================================================

echo "[Daemon] Started with PID $$ (Trapped)" > "$LOG"

# 1. 停止 Framework
echo "[Daemon] Stopping framework..." >> "$LOG"
stop framework
sleep 2

# 2. 疯狂猎杀
echo "[Daemon] Hunting processes..." >> "$LOG"

kill_process_by_keyword() {
    PIDS=$(ps aux | grep "$1" | grep -v grep | awk '{print $2}')
    if [ -n "$PIDS" ]; then
        echo " -> Killing $1 (PIDs: $PIDS)" >> "$LOG"
        for pid in $PIDS; do
            kill -9 $pid
        done
    fi
}

for i in 1 2 3 4 5; do
    killall cvm
    killall KPPMainAppV2
    killall mesquite
    killall awesome
    
    # Fix 2: 杀掉高 CPU/IO 进程
    killall gzip 
    killall tar
    
    kill_process_by_keyword "dump-stack"
    kill_process_by_keyword "dmcc.sh"
    kill_process_by_keyword "sleep 180"
    
    "$FBINK_CMD" -k -f -q
    sleep 1
done

echo "[Daemon] Cleanup done. Loop starting..." >> "$LOG"

# 3. 保持唤醒
lipc-set-prop com.lab126.powerd preventScreenSaver 1

# 计数器初始化
COUNT=0
# 确保第一次运行立即下载
NEXT_FETCH_TIME=0

sleep 15

# 4. 主循环
while true; do
    # 安全阀检查
    if [ -f "$SAFETY_LOCK" ]; then
        exit 0
    fi

    CURRENT_EPOCH=$(date +%s)
    
    # [Fix 2] 每次循环强制刷新电源锁，防止 Powerd 24小时后“遗忘”
    lipc-set-prop com.lab126.powerd preventScreenSaver 1
    iw "$WIFI_INTERFACE" set power_save off
    
    echo $ROTATE > /sys/class/graphics/fb0/rotate

    # ================= 网络看门狗逻辑 =================
    # 每次循环都先 ping 一下。
    # 作用1: Keep-Alive (防止网卡休眠)
    # 作用2: Health Check (检测是否断连)
    
    ping -c 3 -W 5 "$PING_TARGET" > /dev/null 2>&1
    PING_RET=$?

    if [ $PING_RET -ne 0 ]; then
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "[Warn] Network lost (Ping $PING_RET). Fail count: $FAIL_COUNT" >> "$LOG"
        
        # 显示一个小的 WiFi 丢失图标或文字 (可选)
        # $FBINK_CMD -q -x 0 -y 0 "WiFi Lost $FAIL_COUNT"

        if [ $FAIL_COUNT -ge $MAX_FAIL_COUNT ]; then
            echo "[Fatal] Network dead for too long. Rebooting device..." >> "$LOG"
            # 绝杀：如果网络挂了1小时，直接重启系统以重置网卡驱动状态
            reboot
        fi

        # --- 第一阶段：尝试温和重连 (L2 Reconnect) ---
        echo "[Fix] Trying wpa_cli reconnect..." >> "$LOG"
        wpa_cli -i "$WIFI_INTERFACE" reconnect
        sleep 5
        
        # --- 第二阶段：强制 DHCP 续约 (L3 Renew) [关键点] ---
        # 很多时候是 IP 丢了而不是 WiFi 断了
        echo "[Fix] Renewing DHCP..." >> "$LOG"
        udhcpc -i "$WIFI_INTERFACE" -n -t 5 -q
        
        # --- 第三阶段：如果还不行，核弹级重置网卡 ---
        # 仅在失败次数较多时执行，避免频繁开关
        if [ $FAIL_COUNT -gt 2 ]; then
             echo "[Fix] Resetting wifid..." >> "$LOG"
             lipc-set-prop com.lab126.wifid enable 0
             sleep 2
             lipc-set-prop com.lab126.wifid enable 1
             sleep 15 # 给够时间重新协商
        fi

    else
        # 网络正常，重置计数器
        FAIL_COUNT=0
    fi

    # ================= 图片下载逻辑 =================
    if [ $CURRENT_EPOCH -ge $NEXT_FETCH_TIME ]; then
        # 每次刷新前都拉取最新设置
        refresh_derived
        fetch_settings

        # 只有当网络看起来正常(或刚尝试修复后)才下载
        # 增加 connect-timeout 防止 curl 卡死太久
        curl -k -L -s --fail --connect-timeout 20 --max-time 60 --retry 1 "${IMG_URL}" -o "$TMP_FILE"
        RET=$?

        if [ $RET -eq 0 ] && [ -f "$TMP_FILE" ]; then
            
            COUNT=$((COUNT + 1))
            
            if [ $COUNT -ge $FULL_REFRESH_CYCLE ]; then
                # 【全刷模式】
                "$FBINK_CMD" -q -W gc16 -f -g file="$TMP_FILE"
                COUNT=0
            else
                # 【局刷模式】
                # 注意：这里图片会覆盖掉屏幕上已有的任何内容（包括旧时钟）
                "$FBINK_CMD" -q -W gl16 -g file="$TMP_FILE"
            fi
            
            # 更新下次下载时间
            NEXT_FETCH_TIME=$((CURRENT_EPOCH + INTERVAL))
            
            # 下载成功也清零失败计数
            FAIL_COUNT=0
        else
            # 下载失败
            echo "[Err] Curl failed ($RET)" >> "$LOG"
            "$FBINK_CMD" -q -x 0 -y 0 "Err $RET"
            # 缩短重试时间
            NEXT_FETCH_TIME=$((CURRENT_EPOCH + 60))
        fi
    fi
    # ==========================================================


    # ================= 2. 前景层：本地时钟逻辑 =================
    # 无论刚才是否画了图片，这里都要画时钟。
    # 1. 如果刚才没画图片：这是每分钟的常规更新，覆盖旧时间。
    # 2. 如果刚才画了图片：图片把旧时间盖住了，这里正好把时间“补”在图片上层。
    
    # if [ "$ENABLE_LOCAL_CLOCK" -eq 1 ]; then
    #     # 重新获取当前时间 (确保如果下载耗时很久，时间依然准确)
    #     if [ "$TIME_FORMAT" -eq 12 ]; then
    #         TIME_STR=$(date "+%I:%M")
    #     else
    #         TIME_STR=$(date "+%H:%M")
    #     fi
        
    #     # 绘制时间，空格保证无残留
    #     "$FBINK_CMD" -q -t "regular=$CLOCK_FONT,size=$CLOCK_SIZE,left=$CLOCK_X,top=$CLOCK_Y" "$TIME_STR "
    # fi
    # =====================================================


    # ================= 3. 智能休眠 =================
    # 计算距离下一分钟 (:00) 还有多久
    NOW=$(date +%s)
    SLEEP_TIME=$((60 - (NOW % 60)))
    [ "$SLEEP_TIME" -le 0 ] && SLEEP_TIME=1
    sleep "$SLEEP_TIME"
    
done
