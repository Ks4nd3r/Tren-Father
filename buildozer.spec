[app]
title = Дневник тренировок
package.name = workoutdiary
package.domain = org.personal
source.dir = .
source.include_exts = py,png,jpg,kv,db
source.exclude_dirs = tests,.github
version = 0.1.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0
android.minapi = 24
android.api = 35
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
