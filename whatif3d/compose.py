import os, subprocess, sys, numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, "/home/user/clip-farm")
from whatif import cine
from whatif.render import tense_bed, boom, hit, riser, write_wav
from whatif.tts import SR
P = os.environ["P"] + "/3d"; FPS = 30; W, H = 1080, 1920
L = ["At 3:12 in the morning, every person on Earth fell asleep.", "Mid-step. Mid-drive. Mid-sentence.",
     "Except you.", "Then, across the street, a light came on.", "Someone was waving. At you."]
starts = [0.4, 5.45, 9.3, 11.8, 15.3]
vo = [np.load(f"{P}/vo{i}.npy") for i in range(5)]
frames = sorted(os.listdir(f"{P}/frames")); n3d = len(frames)
total = n3d / FPS + 2.2
mix = tense_bed(total)[: int(total * SR)] * 1.1
for s, a in zip(starts, vo):
    mix[int(s * SR): int(s * SR) + len(a)] += a
riser(14.2, mix); hit(14.2, mix)
end = starts[4] + len(vo[4]) / SR - 0.15
boom(end, mix); hit(end, mix)
mix[int(n3d / FPS * SR):] *= 0.35
mix /= max(1.0, np.abs(mix).max() / 0.95)
write_wav(f"{P}/a.wav", mix)
out = sys.argv[1]
ff = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-i", f"{P}/a.wav", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5",
                       "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
for fi in range(int(total * FPS)):
    t = fi / FPS
    if fi < n3d:
        img = Image.open(f"{P}/frames/{frames[fi]}").convert("RGB")
        i = max([j for j, s in enumerate(starts) if t >= s - 0.1], default=-1)
        if i >= 0 and t < starts[i] + len(vo[i]) / SR + 0.6:
            cine.subtitle(img, L[i], (t - starts[i] + 0.1) / 0.6, y=1580)
        fr = cine.finish(img, fi, grain=7)
        if t < 0.4:
            fr = Image.fromarray((np.asarray(fr) * (t / 0.4)).astype(np.uint8))
    else:
        img = Image.new("RGB", (W, H)); d = ImageDraw.Draw(img)
        k = min(1, (t - n3d / FPS) / 0.4)
        c = int(235 * k)
        d.text((W / 2, H / 2 - 40), "PART 2", font=cine.font(cine.SERIF, 120), fill=(c, c, c), anchor="mm")
        d.text((W / 2, H / 2 + 80), "Follow so you don't miss it.", font=cine.font(cine.SERIF, 52), fill=(int(c * .7),) * 3, anchor="mm")
        fr = cine.finish(img, fi, grain=7)
    ff.stdin.write(fr.tobytes())
ff.stdin.close(); ff.wait(); print("done", round(total, 1))
