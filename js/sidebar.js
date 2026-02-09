/**
 * Sidebar Navigation Controller
 * Handles collapsible navigation sections and active page highlighting
 */

// Navigation configuration with hierarchical structure
const NAV_CONFIG = [
    {
        id: 'home',
        label: 'Home',
        route: '/',
        children: []
    },
    {
        id: 'about',
        label: 'About',
        route: '/about.html',
        children: [
            {
                id: 'team',
                label: 'Team',
                route: '/about/team.html',
                children: []
            },
            {
                id: 'history',
                label: 'History',
                route: '/about/history.html',
                children: []
            }
        ]
    },
    {
        id: 'recipes',
        label: 'Recipes',
        route: '/recipes.html',
        children: [
            {
                id: 'pasta',
                label: 'Pasta',
                route: '/recipes/pasta.html',
                children: [
                    {
                        id: 'spaghetti',
                        label: 'Spaghetti',
                        route: '/recipes/pasta/spaghetti.html',
                        children: []
                    },
                    {
                        id: 'bolognese',
                        label: 'Bolognese',
                        route: '/recipes/pasta/bolognese.html',
                        children: []
                    }
                ]
            },
            {
                id: 'pizza',
                label: 'Pizza',
                route: '/recipes/pizza.html',
                children: [
                    {
                        id: 'margherita',
                        label: 'Margherita',
                        route: '/recipes/pizza/margherita.html',
                        children: []
                    }
                ]
            }
        ]
    },
    {
        id: 'contact',
        label: 'Contact',
        route: '/contact.html',
        children: []
    }
];

// Allowed routes whitelist for security
const ALLOWED_ROUTES = [
    '/',
    '/about.html',
    '/about/team.html',
    '/about/history.html',
    '/recipes.html',
    '/recipes/pasta.html',
    '/recipes/pasta/spaghetti.html',
    '/recipes/pasta/bolognese.html',
    '/recipes/pizza.html',
    '/recipes/pizza/margherita.html',
    '/contact.html'
];

/**
 * Initialize sidebar functionality on DOM content loaded
 */
function initSidebar() {
    try {
        const sidebar = document.getElementById('sidebar');

        if (!sidebar) {
            console.warn('Sidebar element not found. Sidebar functionality disabled.');
            return;
        }

        // Attach event listeners to section headers
        attachSectionToggleListeners();

        // Highlight the active page based on current URL
        highlightActivePage();

        console.log('Sidebar navigation controller initialized successfully');

    } catch (error) {
        console.error('Failed to initialize sidebar:', error);
    }
}

/**
 * Attach click event listeners to all section headers
 */
function attachSectionToggleListeners() {
    const sectionHeaders = document.querySelectorAll('.section-header');

    sectionHeaders.forEach(header => {
        header.addEventListener('click', handleSectionToggle);
    });
}

/**
 * Handle section header click to toggle collapsed/expanded state
 * @param {MouseEvent} event - Click event from section header
 */
function handleSectionToggle(event) {
    try {
        event.preventDefault();

        const header = event.currentTarget;
        const section = header.closest('.nav-section');

        if (!section) {
            console.warn('Could not find nav-section parent element');
            return;
        }

        toggleSection(section);

    } catch (error) {
        console.error('Error handling section toggle:', error);
    }
}

/**
 * Toggle the collapsed state of a navigation section
 * @param {HTMLElement} sectionElement - The section element to toggle
 */
function toggleSection(sectionElement) {
    const isCurrentlyCollapsed = sectionElement.classList.contains('collapsed');

    if (isCurrentlyCollapsed) {
        // Expand the section
        sectionElement.classList.remove('collapsed');

        // Update chevron icon if present
        const chevron = sectionElement.querySelector('.chevron');
        if (chevron) {
            chevron.style.transform = 'rotate(90deg)';
        }

    } else {
        // Collapse the section
        sectionElement.classList.add('collapsed');

        // Update chevron icon if present
        const chevron = sectionElement.querySelector('.chevron');
        if (chevron) {
            chevron.style.transform = 'rotate(0deg)';
        }
    }
}

/**
 * Highlight the active page in navigation based on current URL
 */
function highlightActivePage() {
    try {
        // Remove existing active states
        const activeLinks = document.querySelectorAll('.nav-link.active');
        activeLinks.forEach(link => link.classList.remove('active'));

        // Get current pathname (normalize for comparison)
        let currentPath = window.location.pathname;

        // Handle root path
        if (currentPath === '' || currentPath === '/') {
            currentPath = '/';
        }

        // Find matching nav link by data-route attribute
        const navLinks = document.querySelectorAll('.nav-link[data-route]');

        for (const link of navLinks) {
            const route = link.getAttribute('data-route');

            if (route && isRouteMatch(currentPath, route)) {
                link.classList.add('active');

                // Ensure parent sections are expanded to show active item
                expandParentSections(link);
                break;
            }
        }

    } catch (error) {
        console.error('Error highlighting active page:', error);
    }
}

/**
 * Check if the current path matches the route
 * @param {string} currentPath - Current page path
 * @param {string} route - Route to compare against
 * @returns {boolean} - True if paths match
 */
function isRouteMatch(currentPath, route) {
    // Exact match
    if (currentPath === route) {
        return true;
    }

    // Handle index.html as root
    if (currentPath.endsWith('/index.html') && route === '/') {
        return true;
    }

    if (currentPath === '/' && route === '/index.html') {
        return true;
    }

    return false;
}

/**
 * Expand parent sections to reveal an active navigation item
 * @param {HTMLElement} activeLink - The active navigation link
 */
function expandParentSections(activeLink) {
    let currentElement = activeLink.parentElement;

    while (currentElement) {
        if (currentElement.classList.contains('nav-section')) {
            currentElement.classList.remove('collapsed');

            // Update chevron icon if present
            const chevron = currentElement.querySelector('.chevron');
            if (chevron) {
                chevron.style.transform = 'rotate(90deg)';
            }
        }

        currentElement = currentElement.parentElement;
    }
}

/**
 * Validate if a route is allowed for navigation
 * @param {string} route - Route to validate
 * @returns {boolean} - True if route is allowed
 */
function isRouteAllowed(route) {
    return ALLOWED_ROUTES.includes(route);
}

/**
 * Handle navigation link clicks (optional - for future enhancement)
 * @param {MouseEvent} event - Click event from navigation link
 */
function handleNavigationClick(event) {
    const link = event.currentTarget;
    const route = link.getAttribute('data-route');

    if (!route) {
        console.warn('Navigation link missing data-route attribute');
        return;
    }

    if (!isRouteAllowed(route)) {
        event.preventDefault();
        console.warn('Navigation to route not allowed:', route);
        return;
    }

    // Allow default navigation behavior for valid routes
}

// Initialize sidebar when DOM is ready
document.addEventListener('DOMContentLoaded', initSidebar);

// Re-highlight active page on browser navigation (back/forward)
window.addEventListener('popstate', highlightActivePage);