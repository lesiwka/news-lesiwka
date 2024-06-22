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

function nextArticle() {
  const elements = document.querySelectorAll(".accordion-collapse.collapse");
  if (elements.length > 0) {
    const currentEl = document.querySelector(".accordion-collapse.collapse.show, .accordion-collapse.collapsing");

    let nextEl;

    if (currentEl) {
      for (const [idx, el] of elements.entries()) {
        if (el === currentEl) {
          nextEl = elements[idx + 1];
          bootstrap.Collapse.getInstance(currentEl).hide();
          break;
        }
      }
    } else {
      nextEl = elements[0];
    }

    if (nextEl) {
      scroll2(nextEl.parentElement);
      bootstrap.Collapse.getOrCreateInstance(nextEl).show();
    }
  }
}

function prevArticle() {
  const elements = document.querySelectorAll(".accordion-collapse.collapse");
  if (elements.length > 0) {
    const currentEl = document.querySelector(".accordion-collapse.collapse.show, .accordion-collapse.collapsing");

    let prevEl;

    if (currentEl) {
      for (const [idx, el] of elements.entries()) {
        if (el === currentEl) {
          prevEl = elements[idx - 1];
          bootstrap.Collapse.getInstance(currentEl).hide();
          break;
        }
      }
    } else {
      prevEl = elements[elements.length - 1];
    }

    if (prevEl) {
      scroll2(prevEl.parentElement);
      bootstrap.Collapse.getOrCreateInstance(prevEl).show();
    }
  }
}

addEventListener("keydown", (event) => {
  switch (event.key) {
    case "ArrowLeft":
        prevArticle();
        break;
    case "ArrowRight":
        nextArticle();
        break;
  }
});
