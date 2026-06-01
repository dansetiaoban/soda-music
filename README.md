# Soda 音乐 - Google Colab 一键打包 APK

## 使用方法

1. 打开 Google Colab: https://colab.research.google.com/
2. 点击「文件」→「上传笔记本」→ 选择 `build_apk.ipynb`
3. 点击「运行时」→「全部运行」
4. 等待约 15-20 分钟，APK 会自动下载到本地

## 手动打包（本地 Linux / WSL）

```bash
# 安装 buildozer
pip install buildozer

# 安装系统依赖 (Ubuntu/Debian)
sudo apt update
sudo apt install -y python3-pip build-essential git python3-dev \
    ffmpeg libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev \
    libsdl2-ttf-dev libportmidi-dev libswscale-dev \
    libavformat-dev libavcodec-dev zlib1g-dev \
    libgstreamer1.0-0 gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good

# 构建 APK
buildozer -v android debug
```

APK 生成在 `bin/` 目录下。

## 直接传 APK 到手机

构建完成后，将 APK 通过数据线 / 微信 / QQ 传到手机安装即可。

## 支持的音频格式

MP3 / WAV / OGG / FLAC / M4A / AAC / WMA