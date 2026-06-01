[app]

# 应用包名 (唯一标识)
package.name = sodamusic
package.domain = com.soda

# 应用名称
title = Soda 音乐

# 源码目录
source.dir = .

# main.py
source.include_exts = py,png,jpg,kv,atlas,json
source.include_patterns = assets/*,*.py

# 排除
source.exclude_exts = spec
source.exclude_patterns = build/*,.git/*

# 版本
version = 1.0.0

# 入口
main.py = main.py

# 方向: portrait(竖屏) / landscape(横屏) / all
orientation = portrait

# 全屏
fullscreen = 0

# 图标
# icon.filename = assets/icon.png

# 启动画面
# presplash.filename = assets/presplash.png

# ── 依赖 ──
requirements = python3,kivy==2.3.1,ffpyplayer

# Gradle 依赖
android.gradle_dependencies = []

# 权限
android.permissions = READ_EXTERNAL_STORAGE,READ_MEDIA_AUDIO

# 功能
android.features = android.hardware.audio.output

# API 级别
android.api = 33
android.minapi = 26

# 架构
android.arch = armeabi-v7a,arm64-v8a,x86_64

# SDK
android.sdk = 33

# NDK
# android.ndk = 25b

# 签名
# android.keystore = 
# android.keyalias = 
# android.keystore_password = 
# android.keyalias_password = 

# 允许的域名
# android.allow_domains = 

# 调试
android.logcat = 1
android.logcat_filters = *:V python:D

# 编译模式: debug / release
android.release_artifact = apk

# ── iOS ──
ios.kivy_ios_dir = ../kivy-ios
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master

# OSX
osx.kivy_version = 2.3.1

# ── Buildozer ──
buildozer.target = android

# 日志
log_level = 2
warn_on_root = 1