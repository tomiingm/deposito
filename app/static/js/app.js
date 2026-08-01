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

            const tipo_lista = document.getElementById('tipo_lista').value;
            if (!tipo_lista) showError('tipo_lista', 'Seleccione un tipo de lista.');

            const id_subcategoria = document.getElementById('id_subcategoria').value;
            if (!id_subcategoria) showError('id_subcategoria', 'Seleccione una categoría.');

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
    initFormValidation();
});

