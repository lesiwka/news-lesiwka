document.querySelectorAll(".accordion-item").forEach((el, _, arr) => {
  let animationFrameId;

  el.addEventListener("show.bs.collapse", () => {
    let ratio = 1;

    animationFrameId = window.requestAnimationFrame(function step() {
      let offset = el.offsetTop - 60;
      if (offset >= window.scrollY) {
        offset -= (offset - window.scrollY) / ratio;
      }
      ratio *= 1.1;

      window.scroll(0, offset);

      animationFrameId = window.requestAnimationFrame(step);
    });
  });

  el.addEventListener("shown.bs.collapse", () => {
    window.cancelAnimationFrame(animationFrameId);
    window.scroll({behavior: "smooth", left: 0, top: el.offsetTop - 60});
  });
});
