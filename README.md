A quick-and-dirty web UI for image/video face replacement using https://github.com/hacksider/Deep-Live-Cam. I let AI write most of it ¯\_(ツ)_/¯

```
uvicorn main:app --reload
```

It's extremely slow because the underlying app is executed with a new subprocess each time, and it takes a while to load. There's probably a better way to interface with the internal APIs directly. 
