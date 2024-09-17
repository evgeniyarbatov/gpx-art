# GPX Art

Explore creative potential of GPX files with errors

## Video

```
ffmpeg \
-framerate 1 \
-pattern_type glob -i '*.png' \
-c:v libx264 \
-pix_fmt yuv420p \
video.mp4
```