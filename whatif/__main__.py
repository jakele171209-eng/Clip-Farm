"""python -m whatif stories/cartier-winter-1535.json out/cartier.mp4 [--preview SECONDS]"""
import argparse

from .render import render


def main():
    ap = argparse.ArgumentParser(description="Render a what-if story JSON to a vertical MP4")
    ap.add_argument("story")
    ap.add_argument("out")
    ap.add_argument("--preview", type=float, help="only render the first N seconds")
    a = ap.parse_args()
    secs = render(a.story, a.out, a.preview)
    print(f"wrote {a.out} ({secs:.1f}s)")


if __name__ == "__main__":
    main()
