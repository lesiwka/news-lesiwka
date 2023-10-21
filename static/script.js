function scroll2(el) {
  let diff = el.offsetTop - window.scrollY - 60;
  window.requestAnimationFrame(function step() {
    diff = Math.trunc(diff * .85);
    window.scroll(0, el.offsetTop - 60 - diff);
    if (diff) window.requestAnimationFrame(step);
  });
}

document.querySelectorAll(".accordion-item").forEach((el) => {
  el.addEventListener("show.bs.collapse", () => scroll2(el));
});

function collapse() {
  const el = document.querySelector(".accordion-collapse.collapse.show");
  if (el) {
    bootstrap.Collapse.getInstance(el).hide();
    scroll2(el.parentElement);
    return true;
  }
  return false;
}
