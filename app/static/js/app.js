/**
 * Depósito — Sistema de Facturación
 * Main Application JavaScript
 */

// ── Sidebar Category Toggle ──
function toggleCategory(categoryId) {
    const category = document.getElementById(categoryId);
    if (!category) return;

    // Toggle the clicked category
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
        if (!sidebar.contains(e.target) && !menuBtn.contains(e.target)) {
            sidebar.classList.remove('is-open');
        }
    }
});

// ── Show mobile menu button on small screens ──
function handleResize() {
    const menuBtn = document.querySelector('.topbar__menu-btn');
    if (!menuBtn) return;

    if (window.innerWidth <= 768) {
        menuBtn.style.display = 'flex';
    } else {
        menuBtn.style.display = 'none';
    }
}

window.addEventListener('resize', handleResize);
document.addEventListener('DOMContentLoaded', handleResize);

// ── Keyboard shortcut: Ctrl+K to focus search ──
document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const search = document.getElementById('global-search');
        if (search) search.focus();
    }
});

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
                }
                reader.readAsDataURL(file);
            } else {
                previewImg.src = '';
                previewImg.style.display = 'none';
                placeholder.style.display = 'block';
            }
        });
    }
}

// ── Category Combobox (Alta Producto) ──
// Input de texto + lista desplegable: al hacer foco/click se ven todas las
// categorías (como un select), y tipear filtra la lista en vivo.
function initCategoriaAutocomplete() {
    const wrapper = document.getElementById('categoria-combobox');
    const searchInput = document.getElementById('categoria_search');
    const hiddenInput = document.getElementById('id_subcategoria');
    const optionsList = document.getElementById('categoria-options');

    if (!wrapper || !searchInput || !hiddenInput || !optionsList) return;

    const options = Array.from(optionsList.querySelectorAll('.combobox-option'));
    let activeIndex = -1;

    function openList() {
        wrapper.classList.add('is-open');
        searchInput.setAttribute('aria-expanded', 'true');
    }

    function closeList() {
        wrapper.classList.remove('is-open');
        searchInput.setAttribute('aria-expanded', 'false');
        activeIndex = -1;
        options.forEach(opt => opt.classList.remove('is-active'));
    }

    function filterOptions() {
        const texto = searchInput.value.trim().toLowerCase();
        options.forEach(opt => {
            const matches = !texto || opt.dataset.nombre.toLowerCase().includes(texto);
            opt.classList.toggle('is-hidden', !matches);
        });
    }

    function syncHiddenValue() {
        const texto = searchInput.value.trim().toLowerCase();
        const match = options.find(opt => opt.dataset.nombre.toLowerCase() === texto);
        hiddenInput.value = match ? match.dataset.id : '';
    }

    function selectOption(opt) {
        searchInput.value = opt.dataset.nombre;
        hiddenInput.value = opt.dataset.id;
        closeList();
    }

    function highlightActive(visibles) {
        options.forEach(opt => opt.classList.remove('is-active'));
        const activeOpt = visibles[activeIndex];
        if (activeOpt) {
            activeOpt.classList.add('is-active');
            activeOpt.scrollIntoView({ block: 'nearest' });
        }
    }

    searchInput.addEventListener('focus', function() {
        filterOptions();
        openList();
    });

    searchInput.addEventListener('click', function() {
        filterOptions();
        openList();
    });

    searchInput.addEventListener('input', function() {
        filterOptions();
        syncHiddenValue();
        openList();
        activeIndex = -1;
        options.forEach(opt => opt.classList.remove('is-active'));
    });

    searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (!wrapper.classList.contains('is-open')) {
                filterOptions();
                openList();
            }
            const visibles = options.filter(opt => !opt.classList.contains('is-hidden'));
            activeIndex = Math.min(activeIndex + 1, visibles.length - 1);
            highlightActive(visibles);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            const visibles = options.filter(opt => !opt.classList.contains('is-hidden'));
            activeIndex = Math.max(activeIndex - 1, 0);
            highlightActive(visibles);
        } else if (e.key === 'Enter') {
            const visibles = options.filter(opt => !opt.classList.contains('is-hidden'));
            if (wrapper.classList.contains('is-open') && activeIndex >= 0 && visibles[activeIndex]) {
                e.preventDefault();
                selectOption(visibles[activeIndex]);
            }
        } else if (e.key === 'Escape') {
            closeList();
        }
    });

    options.forEach(opt => {
        // mousedown (no click) para que dispare antes del blur del input
        opt.addEventListener('mousedown', function(e) {
            e.preventDefault();
            selectOption(opt);
        });
    });

    searchInput.addEventListener('blur', function() {
        // Delay para dejar que el mousedown de una opción se procese antes de cerrar
        setTimeout(function() {
            syncHiddenValue();
            closeList();
        }, 100);
    });

    document.addEventListener('click', function(e) {
        if (!wrapper.contains(e.target)) {
            closeList();
        }
    });

    // Estado inicial (ej. al re-renderizar el form con errores)
    syncHiddenValue();
}

// ── Product Form Validation ──
function initFormValidation() {
    const form = document.getElementById('product-form');
    if (form) {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            
            // Remove all existing error states
            document.querySelectorAll('.form-field').forEach(el => {
                el.classList.remove('form-field--error');
                const errMsg = el.querySelector('.form-field__error-msg');
                if (errMsg) errMsg.remove();
            });

            // Helper to show error
            const showError = (inputId, message) => {
                const input = document.getElementById(inputId);
                if (input) {
                    const field = input.closest('.form-field');
                    field.classList.add('form-field--error');
                    const msg = document.createElement('div');
                    msg.className = 'form-field__error-msg';
                    msg.textContent = message;
                    field.appendChild(msg);
                    isValid = false;
                }
            };

            // Validations
            const descripcion = document.getElementById('descripcion').value.trim();
            if (!descripcion) showError('descripcion', 'La descripción es obligatoria.');

            const id_subcategoria = document.getElementById('id_subcategoria').value;
            if (!id_subcategoria) showError('id_subcategoria', 'Escribí y seleccioná una categoría de la lista.');

            const costo = document.getElementById('costo').value;
            if (costo === '' || isNaN(costo)) {
                showError('costo', 'Ingrese un costo numérico.');
            } else if (parseFloat(costo) < 0) {
                showError('costo', 'El costo no puede ser negativo.');
            }

            const ganancia = document.getElementById('ganancia').value;
            if (ganancia === '' || isNaN(ganancia)) {
                showError('ganancia', 'Ingrese un % de ganancia numérico.');
            } else if (parseFloat(ganancia) < 0) {
                showError('ganancia', 'La ganancia no puede ser negativa.');
            }

            if (!isValid) {
                e.preventDefault();
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', function() {
    initImagePreview();
    initCategoriaAutocomplete();
    initFormValidation();
});

