(() => {
  const kill = (m) => {
    try {
      m.autoplay = false;
      m.muted = true;
      m.volume = 0;
      if (!m.paused) m.pause();
    } catch {}
  };
  const scan = () => document.querySelectorAll("video,audio").forEach(kill);
  scan();
  new MutationObserver(scan).observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
  addEventListener("play", (e) => {
    if (e.target && /^(VIDEO|AUDIO)$/.test(e.target.tagName)) kill(e.target);
  }, true);
  addEventListener("yt-navigate-finish", scan, true);
})();
