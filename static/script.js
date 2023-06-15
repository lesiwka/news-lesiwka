document.querySelectorAll(".accordion-item").forEach((el) => {
  el.addEventListener("show.bs.collapse", () => {
    let diff = el.offsetTop - window.scrollY - 60;
    window.requestAnimationFrame(function step() {
      diff = Math.trunc(diff * .85);
      window.scroll(0, el.offsetTop - 60 - diff);
      if (diff) window.requestAnimationFrame(step);
    });
  });
});
