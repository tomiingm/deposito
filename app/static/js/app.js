/**
 * Depósito — Sistema de Facturación
 * Main Application JavaScript
 */

// ── Sidebar Category Toggle ──
function toggleCategory(categoryId) {
    const category = document.getElementById(categoryId);
    if (!category) return;
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

            const provSelect = form.querySelector('#id_proveedor');
            if (provSelect && !provSelect.value) {
                showError('id_proveedor', 'El proveedor es obligatorio.');
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

document.addEventListener('DOMContentLoaded', function() {
    initImagePreview();
    initCategorySubcategoryCascade();
    initFormValidation();
});
