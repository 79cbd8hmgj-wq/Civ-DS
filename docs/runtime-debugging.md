# DeSmuME runtime compatibility

The supplied archive contains DeSmuME 0.9.14 `git#0 dev+ x64-JIT SSE2`; executable SHA-256 is `fc2e9fde3e0865158c0b228fb6fe726a4da85f29a1fc8464a67d23d094aa95f2`. A bounded compatibility pass used `--disable-sound --nojoy --3d-render SW`, Mesa software variables, and SDL dummy, offscreen, X11, Wayland, and KMSDRM drivers. Dummy/offscreen reached ROM loading but exited 255 because OpenGL/GLES window creation failed. X11, Wayland, and KMSDRM exited 1 because those SDL backends were unavailable; Xvfb is not installed.

With `--arm9gdb PORT`, the TCP port opens before the graphics exit. The separated GDB controller confirmed PC `0x02000800` and entry memory. Strict timeout/cleanup left no stale emulator. Still unconfirmed are overlay loading, diplomacy watchpoints, and a controlled state transaction. Resumption requires a no-window CLI build or a working X11/Xvfb+Mesa bundle, preferably with an automatable save state at diplomacy.
