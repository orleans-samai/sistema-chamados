/* Service Desk — interações da interface */
document.addEventListener("DOMContentLoaded", () => {
  // ---------- Tema claro/escuro ----------
  const themeToggle = document.getElementById("theme-toggle");
  const themeIcon = document.getElementById("theme-icon");

  function applyThemeIcon() {
    if (!themeIcon) return;
    const theme = document.documentElement.getAttribute("data-bs-theme");
    themeIcon.className = theme === "dark" ? "bi bi-sun" : "bi bi-moon-stars";
  }
  applyThemeIcon();

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-bs-theme");
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-bs-theme", next);
      localStorage.setItem("sd-theme", next);
      applyThemeIcon();
    });
  }

  // ---------- Sidebar no celular ----------
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  const sidebarToggle = document.getElementById("sidebar-toggle");

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", () => {
      sidebar.classList.toggle("show");
      backdrop.classList.toggle("show");
    });
    backdrop.addEventListener("click", () => {
      sidebar.classList.remove("show");
      backdrop.classList.remove("show");
    });
  }

  // ---------- Subcategorias dinâmicas (formulário de chamado) ----------
  const categorySelect = document.getElementById("categoria-select");
  const subcategorySelect = document.getElementById("subcategoria-select");

  if (categorySelect && subcategorySelect) {
    const baseUrl = categorySelect.dataset.subcategoryUrl.replace(/0$/, "");
    const preselected = categorySelect.dataset.selectedSubcategory;

    async function loadSubcategories(selectedId) {
      subcategorySelect.innerHTML = "<option value=''>Carregando...</option>";
      if (!categorySelect.value) {
        subcategorySelect.innerHTML = "<option value=''>Selecione a categoria</option>";
        return;
      }
      try {
        const response = await fetch(baseUrl + categorySelect.value);
        const items = await response.json();
        subcategorySelect.innerHTML = "<option value=''>Nenhuma</option>";
        for (const item of items) {
          const option = document.createElement("option");
          option.value = item.id;
          option.textContent = item.name;
          if (String(item.id) === String(selectedId)) option.selected = true;
          subcategorySelect.appendChild(option);
        }
      } catch {
        subcategorySelect.innerHTML = "<option value=''>Erro ao carregar</option>";
      }
    }

    categorySelect.addEventListener("change", () => loadSubcategories(null));
    if (categorySelect.value) loadSubcategories(preselected);
  }

  // ---------- Campo de solução ao resolver chamado ----------
  const statusSelect = document.getElementById("novo-status");
  const solutionBox = document.getElementById("solution-box");

  if (statusSelect && solutionBox) {
    function toggleSolution() {
      const value = statusSelect.value;
      if (value === "Resolvido" || value === "Fechado") {
        solutionBox.classList.remove("d-none");
      }
    }
    statusSelect.addEventListener("change", toggleSolution);
    toggleSolution();
  }

  // ---------- Confirmação antes de ações destrutivas ----------
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  // ---------- Alertas somem sozinhos ----------
  document.querySelectorAll(".alert:not(.alert-info)").forEach((alert) => {
    setTimeout(() => {
      bootstrap.Alert.getOrCreateInstance(alert).close();
    }, 6000);
  });
});
