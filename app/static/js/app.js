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
