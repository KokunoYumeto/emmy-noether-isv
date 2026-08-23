(() => {
  "use strict";

  const PDF_PATH = "00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf";
  const MAX_PAGE = 1159;
  const sections = { front: 1, latn: 5, cyrl: 571 };
  const frame = document.getElementById("pdf-frame");
  const pageInput = document.getElementById("page-number");
  const openLink = document.getElementById("reader-open");
  const sectionButtons = [...document.querySelectorAll("[data-page]")];

  const clampPage = (value) => Math.min(MAX_PAGE, Math.max(1, Number(value) || 1));
  const pdfTarget = (page) => `${PDF_PATH}#page=${page}&zoom=page-width&view=FitH`;

  function setActive(section) {
    sectionButtons.forEach((button) => {
      const active = button.dataset.section === section;
      button.classList.toggle("active", active);
      if (active) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
  }

  function showPage(page, section = "") {
    const safePage = clampPage(page);
    frame.src = pdfTarget(safePage);
    openLink.href = pdfTarget(safePage);
    pageInput.value = String(safePage);
    setActive(section);
    const hash = section && sections[section] === safePage ? section : `page-${safePage}`;
    history.replaceState(null, "", `#${hash}`);
  }

  sectionButtons.forEach((button) => {
    button.addEventListener("click", () => showPage(button.dataset.page, button.dataset.section));
  });

  document.getElementById("page-form").addEventListener("submit", (event) => {
    event.preventDefault();
    showPage(pageInput.value);
  });

  const initial = location.hash.slice(1);
  if (Object.hasOwn(sections, initial)) showPage(sections[initial], initial);
  else if (/^page-\d+$/.test(initial)) showPage(initial.slice(5));
  else showPage(sections.latn, "latn");
})();
