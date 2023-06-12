document.querySelectorAll(".accordion-item").forEach((el) => {
  el.addEventListener("shown.bs.collapse", () => {
    window.scroll({
      top: el.offsetTop - 60,
      behavior: "smooth",
    });
  });
});

document.addEventListener("DOMContentLoaded", () => {
    window.scroll({
      top: 0,
      behavior: "smooth",
    });
});
