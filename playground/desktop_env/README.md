# Video Recorder/Player

## Installation

### Windows/Linux
```base
pip install pynput mss opencv-python colorama
sudo apt-get install gedit # If use Linux, install the default text editor
```
### Mac OS
1. Give screen recording permission
2. Give accessbility permission

## Troubleshoot

### `mss.exception.ScreenShotError: XGetImage() failed`

Gnome using Wayland instead of Xorg as the default video output and Wayland doesn't support screenshot (<https://github.com/python-pillow/Pillow/issues/6312>). Change the Wayland to Xorg will solve this problem. Follow the following steps:

1. Modifying /etc/gdm3/custom.conf to uncomment #WaylandEnable=false
2. Ran sudo systemctl restart gdm3 to restart it so Ubuntu is using X instead of Wayland.
<https://github.com/python-pillow/Pillow/issues/5130>

### `symbol lookup error: /snap/core20/current/lib/x86_64-linux-gnu/libpthread.so.0: undefined symbol: __libc_pthread_init, version GLIBC_PRIVATE`

VSCode environment issue. Use `unset GTK_PATH` in VSCode integrated terminal (<https://github.com/ros2/ros2/issues/1406>).
