document.querySelectorAll(".accordion-item").forEach((el, _, arr) => {
  el.addEventListener("show.bs.collapse", () => {
    let offset = el.offsetTop;
    for (const e of arr) {
      if (e === el) break;
      offset -= e.lastElementChild.offsetHeight;
    }

    window.scroll({behavior: "smooth", left: 0, top: offset - 60});
    return true;
  });

  el.addEventListener("shown.bs.collapse", () => {
    window.scroll({behavior: "smooth", left: 0, top: el.offsetTop - 60});
    return true;
  });
});
