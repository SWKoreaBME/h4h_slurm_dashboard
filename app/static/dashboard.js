(() => {
  const page = document.querySelector(".page");
  if (!page) {
    return;
  }

  const url = new URL(window.location.href);
  const filterParams = new URLSearchParams(url.search);

  const refreshButton = document.querySelector("#refresh-now");
  if (refreshButton) {
    refreshButton.addEventListener("click", () => {
      window.location.reload();
    });
  }

  const tables = document.querySelectorAll("[data-filter-table]");
  tables.forEach((table) => {
    const tableName = table.getAttribute("data-filter-table");
    const inputs = document.querySelectorAll(`[data-filter-input="${tableName}"]`);

    inputs.forEach((input) => {
      const column = input.getAttribute("data-filter-column");
      const key = `${tableName}_${column}`;
      const savedValue = filterParams.get(key);
      if (savedValue) {
        input.value = savedValue;
      }
    });

    const applyFilters = () => {
      const activeFilters = Array.from(inputs).map((input) => ({
        column: Number(input.getAttribute("data-filter-column")),
        value: input.value.trim().toLowerCase(),
        key: `${tableName}_${input.getAttribute("data-filter-column")}`,
      }));

      activeFilters.forEach((filter) => {
        if (filter.value) {
          filterParams.set(filter.key, filter.value);
        } else {
          filterParams.delete(filter.key);
        }
      });

      const nextUrl = `${url.pathname}${filterParams.toString() ? `?${filterParams.toString()}` : ""}`;
      window.history.replaceState({}, "", nextUrl);

      const rows = table.querySelectorAll("tbody tr");
      rows.forEach((row) => {
        const cells = row.querySelectorAll("td");
        const visible = activeFilters.every((filter) => {
          if (!filter.value) {
            return true;
          }
          const cell = cells[filter.column];
          if (!cell) {
            return false;
          }
          return cell.textContent.toLowerCase().includes(filter.value);
        });
        row.style.display = visible ? "" : "none";
      });
    };

    inputs.forEach((input) => {
      input.addEventListener("input", applyFilters);
    });

    applyFilters();
  });

  const refreshSeconds = Number(page.dataset.refreshSeconds || "0");
  if (!Number.isFinite(refreshSeconds) || refreshSeconds <= 0) {
    return;
  }

  window.setTimeout(() => {
    window.location.reload();
  }, refreshSeconds * 1000);
})();
