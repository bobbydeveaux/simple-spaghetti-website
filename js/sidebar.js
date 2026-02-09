/**
 * Purple Sidebar Interaction Logic
 * Handles collapse/expand functionality and active state management
 */

// Navigation configuration
const NAV_CONFIG = [
    {
        id: 'home-section',
        label: 'Home',
        children: [
            { id: 'home', label: 'Welcome', route: '/' },
            { id: 'about', label: 'About', route: '/about.html' }
        ]
    },
    {
        id: 'content-section',
        label: 'Content',
        children: [
            { id: 'menu', label: 'Menu', route: '/menu.html' },
            { id: 'specials', label: 'Specials', route: '/specials.html' }
        ]
    },
    {
        id: 'info-section',
        label: 'Information',
        children: [
            { id: 'contact', label: 'Contact', route: '/contact.html' },
            { id: 'hours', label: 'Hours', route: '/hours.html' }
        ]
    }
];

// Allowed routes for security validation
const ALLOWED_ROUTES = ['/', '/index.html', '/about.html', '/menu.html', '/specials.html', '/contact.html', '/hours.html'];

/**
 * Initialize sidebar functionality when DOM is loaded
 */
function initSidebar() {
    setupEventListeners();
    highlightActivePage();
    console.log('Purple sidebar initialized successfully');
}

/**
 * Set up event listeners for sidebar interactions
 */
function setupEventListeners() {
    // Add click handlers for section toggles
    document.querySelectorAll('.section-header').forEach(header => {
        header.addEventListener('click', handleSectionToggle);
    });

    // Add click handlers for navigation links
    document.querySelectorAll('.nav-item').forEach(link => {
        link.addEventListener('click', handleNavigation);
    });
}

/**
 * Handle section toggle (collapse/expand)
 * @param {Event} event - Click event
 */
function handleSectionToggle(event) {
    event.preventDefault();
    const section = event.currentTarget.closest('.nav-section');
    if (section) {
        toggleSection(section);
    }
}

/**
 * Toggle a section's collapsed state
 * @param {HTMLElement} sectionElement - The section to toggle
 */
function toggleSection(sectionElement) {
    const isCollapsed = sectionElement.classList.contains('collapsed');

    if (isCollapsed) {
        // Expand
        sectionElement.classList.remove('collapsed');
        sectionElement.setAttribute('aria-expanded', 'true');
    } else {
        // Collapse
        sectionElement.classList.add('collapsed');
        sectionElement.setAttribute('aria-expanded', 'false');
    }

    // Log for debugging
    console.log(`Section ${sectionElement.id || 'unknown'} ${isCollapsed ? 'expanded' : 'collapsed'}`);
}

/**
 * Handle navigation link clicks
 * @param {Event} event - Click event
 */
function handleNavigation(event) {
    const link = event.currentTarget;
    const route = link.getAttribute('data-route') || link.getAttribute('href');

    // Validate route
    if (!isRouteAllowed(route)) {
        console.warn('Navigation blocked: Invalid route', route);
        event.preventDefault();
        return;
    }

    // Update active state
    updateActiveNavItem(link);

    console.log('Navigating to:', route);
}

/**
 * Check if a route is in the allowed list
 * @param {string} route - Route to validate
 * @returns {boolean} True if route is allowed
 */
function isRouteAllowed(route) {
    return ALLOWED_ROUTES.includes(route);
}

/**
 * Update the active navigation item
 * @param {HTMLElement} activeLink - The link element that should be active
 */
function updateActiveNavItem(activeLink) {
    // Remove active class from all nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });

    // Add active class to selected item
    activeLink.classList.add('active');
}

/**
 * Highlight the navigation item that matches the current page
 */
function highlightActivePage() {
    const currentPath = window.location.pathname;
    const currentPage = currentPath === '/' ? '/' : currentPath;

    // Find and activate the matching nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        const itemRoute = item.getAttribute('data-route') || item.getAttribute('href');

        if (itemRoute === currentPage) {
            item.classList.add('active');

            // Ensure parent section is expanded
            const parentSection = item.closest('.nav-section');
            if (parentSection) {
                parentSection.classList.remove('collapsed');
                parentSection.setAttribute('aria-expanded', 'true');
            }
        }
    });

    console.log('Active page highlighted:', currentPage);
}

/**
 * Expand all sections (utility function)
 */
function expandAllSections() {
    document.querySelectorAll('.nav-section').forEach(section => {
        section.classList.remove('collapsed');
        section.setAttribute('aria-expanded', 'true');
    });
}

/**
 * Collapse all sections (utility function)
 */
function collapseAllSections() {
    document.querySelectorAll('.nav-section').forEach(section => {
        section.classList.add('collapsed');
        section.setAttribute('aria-expanded', 'false');
    });
}

/**
 * Mobile sidebar toggle functionality
 */
function toggleMobileSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.classList.toggle('mobile-open');
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSidebar);
} else {
    initSidebar();
}

// Export functions for testing/external use
window.sidebarAPI = {
    toggleSection,
    highlightActivePage,
    expandAllSections,
    collapseAllSections,
    toggleMobileSidebar,
    isRouteAllowed
};