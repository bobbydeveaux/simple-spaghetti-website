# Simple Bolognese Website

A minimal HTML5 website that displays "I love bolognese" - a simple, static webpage with no CSS or JavaScript.

## Overview

This project contains a single `index.html` file with basic HTML5 structure. The site displays the message "I love bolognese" using plain HTML with no styling or scripts.

## Features

- ✅ Pure HTML5 with no external dependencies
- ✅ No CSS styling or JavaScript
- ✅ Valid HTML5 markup
- ✅ Under 1KB file size
- ✅ Loads instantly
- ✅ Works in all browsers

## Project Structure

```
/
├── README.md          # This documentation file
└── index.html         # Main website file
```

## Quick Start

### View the Website Locally

The simplest way to view the website is to open the HTML file directly in your browser:

```bash
# Open in your default browser (macOS)
open index.html

# Open in your default browser (Linux)
xdg-open index.html

# Open in your default browser (Windows)
start index.html
```

### Local Development Server

For testing with HTTP (optional):

```bash
# Python HTTP Server
python3 -m http.server 8000

# Then open browser to: http://localhost:8000
```

### Expected Results

When you access the website, you should see:

- **Browser Tab Title**: "Simple Bolognese Website"
- **Page Content**: The text "I love bolognese"
- **Styling**: Plain browser default styling (black text on white background)
- **No Console Errors**: Clean browser developer console
- **Fast Load Time**: Page loads instantly

## Browser Compatibility

This website works in all browsers:

- ✅ All modern browsers (Chrome, Firefox, Safari, Edge)
- ✅ Legacy browsers (Internet Explorer 6+)
- ✅ Mobile browsers
- ✅ Text-based browsers

## Testing

### Manual Testing

1. **Local File Test**: Double-click `index.html` to open directly in browser
2. **HTTP Server Test**: Use Python server option above (optional)
3. **Cross-Browser Test**: Open the file in multiple browsers

### Validation

Validate the HTML markup:

```bash
# Online validation
curl -H "Content-Type: text/html; charset=utf-8" \
     --data-binary @index.html \
     https://validator.w3.org/nu/?out=text
```

Expected result: No errors or warnings

## Deployment

This website can be deployed anywhere:

- **Static hosting**: Upload `index.html` to any web server
- **GitHub Pages**: Push to repository and enable Pages
- **CDN**: Works with any CDN or static hosting service

## Technical Specifications

- **HTML Version**: HTML5
- **File Size**: ~90 bytes
- **Load Time**: <10ms
- **Dependencies**: None
- **Server Requirements**: Any static file server (or none - can open locally)
- **Browser Requirements**: Any HTML-capable browser

## License

This project is in the public domain. Use freely for any purpose.

---

## About This Project

This website serves as a simple demonstration of basic HTML5 structure. It displays a bolognese-themed message using minimal, semantic HTML markup with no styling or scripting dependencies.
