const feedback = document.querySelector("[data-feedback]");
if (feedback) feedback.focus();

const printButton = document.querySelector("#print-result");
if (printButton) {
  printButton.hidden = false;
  printButton.addEventListener("click", () => window.print());
}

const rows = document.querySelector("#subject-rows");
if (rows) {
  const add = document.querySelector("#add-subject");
  const template = document.querySelector("#subject-template");
  const minimum = Number(rows.dataset.minimum);
  const maximum = Number(rows.dataset.maximum);

  function updateRows() {
    const count = rows.children.length;
    for (const [position, row] of Array.from(rows.children).entries()) {
      const index = position + 1;
      row.querySelector("[data-index]").textContent = index;
      for (const field of row.querySelectorAll("input")) {
        field.id = field.name + index;
        field.parentElement.querySelector("label").htmlFor = field.id;
        const error = field.parentElement.querySelector(".field-error");
        if (error) {
          error.id = "error-" + field.id;
          field.setAttribute("aria-describedby", error.id);
        }
      }
      const remove = row.querySelector("[data-remove]");
      remove.hidden = count <= minimum;
      remove.setAttribute("aria-label", "Remove subject " + index);
    }
    add.disabled = count >= maximum;
  }

  add.hidden = false;
  add.addEventListener("click", () => {
    if (rows.children.length >= maximum) return;
    rows.append(template.content.cloneNode(true));
    updateRows();
    rows.lastElementChild.querySelector("input").focus();
  });
  rows.addEventListener("click", (event) => {
    const remove = event.target.closest("[data-remove]");
    if (!remove || rows.children.length <= minimum) return;
    const row = remove.closest(".subject-row");
    const focusRow = row.nextElementSibling || row.previousElementSibling;
    row.remove();
    updateRows();
    focusRow.querySelector("input").focus();
  });
  updateRows();
}
