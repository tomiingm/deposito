// ── Desktop Sidebar Collapse Toggle ──
function toggleSidebarCollapse() {
    document.body.classList.toggle('sidebar-collapsed');
    const isCollapsed = document.body.classList.contains('sidebar-collapsed');
    localStorage.setItem('sidebar_collapsed', isCollapsed ? '1' : '0');
}

function initSidebarState() {
    if (localStorage.getItem('sidebar_collapsed') === '1') {
        document.body.classList.add('sidebar-collapsed');
    }

    // Set flyout titles for submenus in collapsed mode
    document.querySelectorAll('.nav-category').forEach(cat => {
        const title = cat.getAttribute('data-title') || cat.querySelector('.nav-category__text')?.textContent?.trim();
        const submenu = cat.querySelector('.nav-submenu');
        if (title && submenu) {
            submenu.setAttribute('data-flyout-title', title);
        }
    });
}

// ── Sidebar Category Toggle ──
function toggleCategory(categoryId) {
    const category = document.getElementById(categoryId);
    if (!category) return;

    if (document.body.classList.contains('sidebar-collapsed')) {
        // En modo colapsado: al tocar el ícono, expandir el menú lateral y abrir esta categoría
        document.body.classList.remove('sidebar-collapsed');
        localStorage.setItem('sidebar_collapsed', '0');
        category.classList.add('is-open');
        return;
    }

    category.classList.toggle('is-open');
}

// ── Mobile Sidebar Toggle ──
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    sidebar.classList.toggle('is-open');
}

// ── Close sidebar on mobile when clicking outside ──
document.addEventListener('click', function (e) {
    const sidebar = document.getElementById('sidebar');
    const menuBtn = document.querySelector('.topbar__menu-btn');

    if (window.innerWidth <= 768 && sidebar && sidebar.classList.contains('is-open')) {
        if (!sidebar.contains(e.target) && !menuBtn?.contains(e.target)) {
            sidebar.classList.remove('is-open');
        }
    }
});

// ── Show mobile menu button on small screens ──
function handleResize() {
    const menuBtn = document.querySelector('.topbar__menu-btn');
    const collapseBtn = document.getElementById('sidebar-collapse-btn');
    if (!menuBtn) return;

    if (window.innerWidth <= 768) {
        menuBtn.style.display = 'flex';
        if (collapseBtn) collapseBtn.style.display = 'none';
    } else {
        menuBtn.style.display = 'none';
        if (collapseBtn) collapseBtn.style.display = 'flex';
    }
}

window.addEventListener('resize', handleResize);
document.addEventListener('DOMContentLoaded', handleResize);

// ── Keyboard shortcuts: Ctrl+K (search), Alt+S (sidebar toggle) ──
document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        const search = document.getElementById('global-search');
        if (search) {
            search.focus();
            search.select();
        }
    } else if (e.altKey && e.key.toLowerCase() === 's') {
        e.preventDefault();
        toggleSidebarCollapse();
    }
});

// ── Live Global Search ──
function initGlobalSearch() {
    const searchInput = document.getElementById('global-search');
    const searchDropdown = document.getElementById('global-search-dropdown');
    const searchClear = document.getElementById('global-search-clear');
    const searchContainer = document.getElementById('global-search-container');

    if (!searchInput || !searchDropdown) return;

    let debounceTimer = null;
    let currentSelectedIndex = -1;
    const currencyFormatter = new Intl.NumberFormat('es-AR', {
        style: 'currency',
        currency: 'ARS',
        minimumFractionDigits: 2
    });

    function closeDropdown() {
        searchDropdown.style.display = 'none';
        searchDropdown.innerHTML = '';
        currentSelectedIndex = -1;
    }

    function highlightSelected(items) {
        items.forEach((item, idx) => {
            if (idx === currentSelectedIndex) {
                item.classList.add('is-selected');
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.classList.remove('is-selected');
            }
        });
    }

    function renderResults(data, query) {
        const { productos = [], clientes = [], facturas = [] } = data;
        const totalResults = productos.length + clientes.length + facturas.length;

        if (totalResults === 0) {
            searchDropdown.innerHTML = `
                <div class="search-dropdown__empty">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="11" cy="11" r="8"></circle>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                        <line x1="8" y1="11" x2="14" y2="11"></line>
                    </svg>
                    <p>No se encontraron resultados para <strong>"${escapeHtml(query)}"</strong></p>
                </div>
            `;
            searchDropdown.style.display = 'block';
            return;
        }

        let html = '';

        // 1. Productos
        if (productos.length > 0) {
            html += `
                <div class="search-section">
                    <div class="search-section__header">
                        <span>📦 Productos</span>
                        <span class="search-section__badge">${productos.length}</span>
                    </div>
            `;
            productos.forEach(p => {
                const stockBadge = p.stock > 0 
                    ? `<span class="search-item__stock-badge in-stock">${p.stock} en stock</span>`
                    : `<span class="search-item__stock-badge out-stock">Sin stock</span>`;
                const codeText = p.codigo_barra || p.codigo_proveedor || `ID #${p.id_producto}`;
                const subcatText = p.subcategoria ? ` • ${escapeHtml(p.subcategoria)}` : '';

                html += `
                    <a href="${p.url}" class="search-item">
                        <div class="search-item__main">
                            <div class="search-item__icon prod">
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M16.5 9.4 7.55 4.24" />
                                    <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                                </svg>
                            </div>
                            <div class="search-item__info">
                                <div class="search-item__title">${escapeHtml(p.descripcion)}</div>
                                <div class="search-item__subtitle">${escapeHtml(codeText)}${subcatText}</div>
                            </div>
                        </div>
                        <div class="search-item__meta">
                            <div class="search-item__price">${currencyFormatter.format(p.precio)}</div>
                            ${stockBadge}
                        </div>
                    </a>
                `;
            });
            html += `</div>`;
        }

        // 2. Clientes
        if (clientes.length > 0) {
            html += `
                <div class="search-section">
                    <div class="search-section__header">
                        <span>👤 Clientes</span>
                        <span class="search-section__badge">${clientes.length}</span>
                    </div>
            `;
            clientes.forEach(c => {
                html += `
                    <a href="${c.url}" class="search-item">
                        <div class="search-item__main">
                            <div class="search-item__icon cli">
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
                                    <circle cx="9" cy="7" r="4" />
                                </svg>
                            </div>
                            <div class="search-item__info">
                                <div class="search-item__title">${escapeHtml(c.nombre)}</div>
                                <div class="search-item__subtitle">Cliente Nº ${String(c.id_cliente).padStart(4, '0')}${c.telefono ? ` • 📞 ${escapeHtml(c.telefono)}` : ''}</div>
                            </div>
                        </div>
                        <div class="search-item__meta">
                            <span class="search-item__stock-badge in-stock">Activo</span>
                        </div>
                    </a>
                `;
            });
            html += `</div>`;
        }

        // 3. Facturas
        if (facturas.length > 0) {
            html += `
                <div class="search-section">
                    <div class="search-section__header">
                        <span>📄 Facturas</span>
                        <span class="search-section__badge">${facturas.length}</span>
                    </div>
            `;
            facturas.forEach(f => {
                html += `
                    <a href="${f.url}" class="search-item">
                        <div class="search-item__main">
                            <div class="search-item__icon fac">
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                    <polyline points="14 2 14 8 20 8" />
                                </svg>
                            </div>
                            <div class="search-item__info">
                                <div class="search-item__title">Factura Nº ${String(f.id_factura).padStart(5, '0')}</div>
                                <div class="search-item__subtitle">${escapeHtml(f.cliente_nombre)} • ${f.fecha}</div>
                            </div>
                        </div>
                        <div class="search-item__meta">
                            <div class="search-item__price">${currencyFormatter.format(f.total)}</div>
                        </div>
                    </a>
                `;
            });
            html += `</div>`;
        }

        // Footer hints
        html += `
            <div class="search-dropdown__footer">
                <span>↑↓ para navegar • Enter para ir</span>
                <span>ESC para cerrar</span>
            </div>
        `;

        searchDropdown.innerHTML = html;
        searchDropdown.style.display = 'block';
        currentSelectedIndex = -1;
    }

    function doSearch(q) {
        const query = q.trim();
        if (query.length < 2) {
            closeDropdown();
            return;
        }

        searchDropdown.innerHTML = `
            <div class="search-dropdown__loading">
                <div class="search-dropdown__spinner"></div>
                <span>Buscando "${escapeHtml(query)}"...</span>
            </div>
        `;
        searchDropdown.style.display = 'block';

        fetch(`/api/buscar?q=${encodeURIComponent(query)}`)
            .then(res => {
                if (!res.ok) throw new Error('Error en búsqueda');
                return res.json();
            })
            .then(data => {
                renderResults(data, query);
            })
            .catch(err => {
                console.error('Error buscando:', err);
                searchDropdown.innerHTML = `
                    <div class="search-dropdown__empty">
                        <p style="color: var(--color-danger);">Error al consultar el servidor.</p>
                    </div>
                `;
            });
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    searchInput.addEventListener('input', function () {
        const q = searchInput.value;
        if (searchClear) {
            searchClear.style.display = q.trim().length > 0 ? 'flex' : 'none';
        }

        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            doSearch(q);
        }, 220);
    });

    searchInput.addEventListener('focus', function () {
        const q = searchInput.value.trim();
        if (q.length >= 2) {
            doSearch(q);
        }
    });

    searchInput.addEventListener('keydown', function (e) {
        const items = searchDropdown.querySelectorAll('.search-item');
        if (!items || items.length === 0 || searchDropdown.style.display === 'none') {
            if (e.key === 'Escape') {
                closeDropdown();
                searchInput.blur();
            }
            return;
        }

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            currentSelectedIndex = (currentSelectedIndex + 1) % items.length;
            highlightSelected(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            currentSelectedIndex = (currentSelectedIndex - 1 + items.length) % items.length;
            highlightSelected(items);
        } else if (e.key === 'Enter') {
            if (currentSelectedIndex >= 0 && items[currentSelectedIndex]) {
                e.preventDefault();
                items[currentSelectedIndex].click();
            }
        } else if (e.key === 'Escape') {
            e.preventDefault();
            closeDropdown();
            searchInput.blur();
        }
    });

    if (searchClear) {
        searchClear.addEventListener('click', function () {
            searchInput.value = '';
            searchClear.style.display = 'none';
            closeDropdown();
            searchInput.focus();
        });
    }

    document.addEventListener('click', function (e) {
        if (searchContainer && !searchContainer.contains(e.target)) {
            closeDropdown();
        }
    });
}

// ── Product Form Image Preview ──
function initImagePreview() {
    const fileInput = document.getElementById('imagen');
    const previewImg = document.getElementById('image-preview-img');
    const placeholder = document.getElementById('image-preview-placeholder');

    if (fileInput && previewImg && placeholder) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewImg.src = e.target.result;
                    previewImg.style.display = 'block';
                    placeholder.style.display = 'none';
                };
                reader.readAsDataURL(file);
            } else {
                // If it already had an image (e.g. in edit mode), check if there's an existing src
                if (!previewImg.getAttribute('src')) {
                    previewImg.src = '';
                    previewImg.style.display = 'none';
                    placeholder.style.display = 'block';
                }
            }
        });
    }
}

// ── Calculation of Price (Costo + Ganancia) ──
function calcPrecio() {
    const costoInput = document.getElementById('costo');
    const gananciaInput = document.getElementById('ganancia');
    const precioValue = document.getElementById('precio-value');
    const precioInput = document.getElementById('precio');

    if (!costoInput || !gananciaInput) return;

    const costo = parseFloat(costoInput.value) || 0;
    const ganancia = parseFloat(gananciaInput.value) || 0;
    const precio = costo * (1 + (ganancia / 100));

    const formatter = new Intl.NumberFormat('es-AR', {
        style: 'currency',
        currency: 'ARS',
        minimumFractionDigits: 2
    });

    const formatted = formatter.format(precio);

    if (precioValue) {
        precioValue.textContent = formatted;
    }
    if (precioInput) {
        precioInput.value = formatted;
    }
}

// ── Cascade Filter: Category -> Subcategories ──
function initCategorySubcategoryCascade() {
    const catSelect = document.getElementById('id_categoria');
    const subcatSelect = document.getElementById('id_subcategoria');

    if (!catSelect || !subcatSelect) return;

    function filterSubcategories(preserveSelection = false) {
        const selectedCatId = catSelect.value;
        const currentSubcatVal = subcatSelect.value;
        let hasSelectedOption = false;

        const options = Array.from(subcatSelect.querySelectorAll('option'));
        options.forEach(opt => {
            if (!opt.value) {
                // Placeholder option
                opt.textContent = selectedCatId ? 'Seleccionar subcategoría...' : 'Primero seleccioná una categoría...';
                opt.style.display = '';
                return;
            }

            const optCatId = opt.getAttribute('data-categoria');
            if (selectedCatId && optCatId === selectedCatId) {
                opt.style.display = '';
                if (opt.value === currentSubcatVal) {
                    hasSelectedOption = true;
                }
            } else {
                opt.style.display = 'none';
            }
        });

        if (!preserveSelection || !hasSelectedOption) {
            if (!selectedCatId || !hasSelectedOption) {
                subcatSelect.value = '';
            }
        }
    }

    catSelect.addEventListener('change', function() {
        filterSubcategories(false);
    });

    // Run on initial load to filter based on pre-selected category
    filterSubcategories(true);
}

// ── Upload Panel Toggle (Actualizar Precios) ──
// El panel de carga arranca colapsado cuando ya hay un resultado para
// mostrar (lo decide el servidor con la clase .is-collapsed). Este botón
// solo se ve mientras está colapsado y lo vuelve a desplegar para cargar
// otro PDF sin tener que recargar la página.
function initUploadPanelToggle() {
    const panel = document.getElementById('upload-panel');
    const toggle = document.getElementById('upload-panel-toggle');
    if (!panel || !toggle) return;

    toggle.addEventListener('click', function() {
        panel.classList.remove('is-collapsed');
        toggle.setAttribute('aria-expanded', 'true');
    });
}

// ── Provider Cards (Actualizar Precios) ──
// Reemplaza el <select> de proveedor: clickear una card la marca como
// seleccionada, guarda el slug en el input oculto y revela el form de subida.
function initProviderCards() {
    const cards = document.querySelectorAll('.provider-card');
    const hiddenInput = document.getElementById('proveedor-input');
    const uploadForm = document.getElementById('form-subir-pdf');
    const selectedNameEl = document.getElementById('upload-form__selected-name');

    if (!cards.length || !hiddenInput || !uploadForm) return;

    cards.forEach(card => {
        card.addEventListener('click', function() {
            cards.forEach(c => c.classList.remove('is-selected'));
            card.classList.add('is-selected');

            hiddenInput.value = card.dataset.proveedor;
            if (selectedNameEl) selectedNameEl.textContent = card.dataset.nombre;

            uploadForm.classList.add('is-visible');

            const fileInput = uploadForm.querySelector('input[type="file"]');
            if (fileInput) fileInput.focus();
        });
    });
}

// ── Loading Overlay on Form Submit ──
// Muestra una tarjeta con spinner, barra de progreso y mensajes rotativos
// mientras el navegador espera la respuesta del servidor. El progreso es
// simulado (Flask procesa el PDF de forma sincrónica, sin progreso real
// disponible), pero evita que la pantalla se sienta congelada.
function initFormLoadingOverlay(formId, options) {
    const form = document.getElementById(formId);
    const overlay = document.getElementById('loading-overlay');
    if (!form || !overlay) return;

    const titleEl = document.getElementById('loading-overlay-title');
    const messageEl = document.getElementById('loading-overlay-message');
    const barEl = document.getElementById('loading-overlay-bar');
    const messages = (options && options.messages) || ['Procesando...'];
    const progressSteps = [20, 45, 65, 80, 92];

    form.addEventListener('submit', function() {
        // Si el navegador todavía tiene que correr su propia validación
        // nativa (campos required), el evento 'submit' no llega a dispararse
        // hasta que esa validación pasa, así que acá ya sabemos que el
        // formulario se va a enviar de verdad.
        if (titleEl && options && options.title) titleEl.textContent = options.title;

        let i = 0;
        function tick() {
            if (messageEl) messageEl.textContent = messages[i % messages.length];
            if (barEl) barEl.style.width = progressSteps[Math.min(i, progressSteps.length - 1)] + '%';
            i++;
        }
        tick();
        overlay.classList.add('is-active');
        window.clearInterval(overlay._loadingInterval);
        overlay._loadingInterval = window.setInterval(tick, 1500);
    });
}

// ── Product Form Validation ──
function initFormValidation() {
    const forms = [document.getElementById('product-form'), document.getElementById('edit-product-form')].filter(Boolean);

    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            
            // Remove all existing error states
            form.querySelectorAll('.form-field').forEach(el => {
                el.classList.remove('form-field--error');
                const errMsg = el.querySelector('.form-field__error-msg');
                if (errMsg) errMsg.remove();
            });

            // Helper to show error
            const showError = (inputId, message) => {
                const input = form.querySelector(`#${inputId}`);
                if (input) {
                    const field = input.closest('.form-field');
                    if (field) {
                        field.classList.add('form-field--error');
                        const msg = document.createElement('div');
                        msg.className = 'form-field__error-msg';
                        msg.textContent = message;
                        field.appendChild(msg);
                    }
                    isValid = false;
                }
            };

            // Validations
            const descInput = form.querySelector('#descripcion');
            if (descInput && !descInput.value.trim()) {
                showError('descripcion', 'La descripción es obligatoria.');
            }

            const catSelect = form.querySelector('#id_categoria');
            if (catSelect && !catSelect.value) {
                showError('id_categoria', 'La categoría es obligatoria.');
            }

            const subcatSelect = form.querySelector('#id_subcategoria');
            if (subcatSelect && !subcatSelect.value) {
                showError('id_subcategoria', 'La subcategoría es obligatoria.');
            }

            const costoInput = form.querySelector('#costo');
            if (costoInput) {
                const costo = costoInput.value;
                if (costo === '' || isNaN(costo)) {
                    showError('costo', 'Ingrese un costo numérico.');
                } else if (parseFloat(costo) < 0) {
                    showError('costo', 'El costo no puede ser negativo.');
                }
            }

            const gananciaInput = form.querySelector('#ganancia');
            if (gananciaInput) {
                const ganancia = gananciaInput.value;
                if (ganancia === '' || isNaN(ganancia)) {
                    showError('ganancia', 'Ingrese un % de ganancia numérico.');
                } else if (parseFloat(ganancia) < 0) {
                    showError('ganancia', 'La ganancia no puede ser negativa.');
                }
            }

            if (!isValid) {
                e.preventDefault();
            }
        });
    });
}

// ── Toggle Código Proveedor Visibility Based on Selected Proveedor ──
function initProveedorCodigoToggle() {
    const provSelect = document.getElementById('id_proveedor');
    const codigoProvGroup = document.getElementById('group-codigo-proveedor');
    const codigoProvInput = document.getElementById('codigo_proveedor');

    if (!provSelect || !codigoProvGroup) return;

    function updateVisibility() {
        const hasProveedor = !!provSelect.value;
        if (hasProveedor) {
            codigoProvGroup.style.display = '';
        } else {
            codigoProvGroup.style.display = 'none';
            if (codigoProvInput) {
                codigoProvInput.value = '';
            }
        }
    }

    provSelect.addEventListener('change', updateVisibility);

    // Initial check on page load
    updateVisibility();
}

document.addEventListener('DOMContentLoaded', function() {
    initSidebarState();
    initGlobalSearch();
    initImagePreview();
    initCategorySubcategoryCascade();
    initProveedorCodigoToggle();
    initFormValidation();
});
