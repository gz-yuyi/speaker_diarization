#!/bin/bash
INPUT_FILE=$1
OUTPUT_PREFIX=$2

# 检测静默点并生成时间戳
ffmpeg -i $INPUT_FILE -af "silencedetect=noise=-30dB:d=0.5" -f null - 2>&1 | \
grep "silence_end" | awk '{print $5}' > split_times.txt

# 添加起始时间0
echo "0" > times_final.txt
current_time=0

while read timestamp; do
    # 如果时间戳比当前时间大30秒以上，则添加到分割点
    if (( $(echo "$timestamp - $current_time >= 30" | bc -l) )); then
        echo "$timestamp" >> times_final.txt
        current_time=$timestamp
    fi
done < split_times.txt

# 使用时间点分割为WAV
ffmpeg -i $INPUT_FILE -f segment -segment_times $(tr '\n' ',' < times_final.txt | sed 's/,$//') -acodec pcm_s16le ${OUTPUT_PREFIX}%03d.wav

rm split_times.txt times_final.txt
