# 3D what-if renderer (free)

three.js scene rendered headless in Chromium (Playwright), then voice/music/subtitles added in Python.

    cd whatif3d && npm install three@0.170.0
    node render.js frames 30            # renders scene.html to frames/*.png
    P=$PWD/.. python whatif3d/compose.py out.mp4   # expects $P/3d/frames and $P/3d/vo*.npy
