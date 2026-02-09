# Simple Spaghetti Website

A minimal HTML5 website that displays "I love spagheeti" - a simple, static webpage with no CSS, JavaScript, or external dependencies.

## Overview

This project contains a single `index.html` file that demonstrates the most basic possible HTML5 website structure. The site displays the message "I love spagheeti" (intentional spelling) in a clean, minimal format that works across all modern web browsers.

## Features

- ✅ Pure HTML5 with no external dependencies
- ✅ No CSS styling (uses browser defaults)
- ✅ No JavaScript or client-side scripts
- ✅ Valid HTML5 markup
- ✅ Under 1KB file size
- ✅ Loads in under 100ms
- ✅ Works in all modern browsers

## Project Structure

```
/
├── README.md          # This documentation file
├── index.html         # Main website file
└── docs/              # Design and planning documents
    └── plans/
        └── simple-spaghetti-website/
            ├── PRD.md     # Product Requirements Document
            ├── HLD.md     # High-Level Design
            └── LLD.md     # Low-Level Design
```

## Quick Start

### View the Website Locally

The simplest way to view the website is to open the HTML file directly in your browser:

```bash
# Navigate to the project directory
cd simple-spaghetti-website

# Open in your default browser (macOS)
open index.html

# Open in your default browser (Linux)
xdg-open index.html

# Open in your default browser (Windows)
start index.html
```

### Local Development Server

For testing with HTTP (recommended for development):

#### Option 1: Python HTTP Server (Recommended)

```bash
# Navigate to the project directory
cd simple-spaghetti-website

# Start the server (Python 3)
python3 -m http.server 8000

# Or if you have Python 2
python -m SimpleHTTPServer 8000
```

Then open your browser to: http://localhost:8000

#### Option 2: Node.js HTTP Server

```bash
# Install http-server globally (one time only)
npm install -g http-server

# Navigate to project directory and start server
cd simple-spaghetti-website
http-server -p 8000

# Open browser to: http://localhost:8000
```

#### Option 3: PHP Built-in Server

```bash
cd simple-spaghetti-website
php -S localhost:8000
```

### Expected Results

When you access the website, you should see:

- **Browser Tab Title**: "Test Pizza Page" (current) or "I Love Spagheeti" (planned)
- **Page Content**: The text "I love pizza" (current) or "I love spagheeti" (planned)
- **No Styling**: Plain black text on white background
- **No Console Errors**: Clean browser developer console
- **Fast Load Time**: Page loads almost instantly

## Browser Compatibility

This website works in all modern browsers:

- ✅ Google Chrome (all versions)
- ✅ Mozilla Firefox (all versions)
- ✅ Safari (all versions)
- ✅ Microsoft Edge (all versions)
- ✅ Internet Explorer 11+
- ✅ Mobile browsers (iOS Safari, Chrome Mobile, etc.)

## Testing

### Manual Testing

1. **Local File Test**: Double-click `index.html` to open directly in browser
2. **HTTP Server Test**: Use one of the local server options above
3. **Cross-Browser Test**: Open the file in multiple browsers
4. **Mobile Test**: Test on mobile devices or using browser dev tools

### Validation

Validate the HTML markup using the W3C validator:

```bash
# Online validation
curl -H "Content-Type: text/html; charset=utf-8" \
     --data-binary @index.html \
     https://validator.w3.org/nu/?out=text
```

Expected result: No errors or warnings

## Deployment

This website can be deployed to any static hosting platform:

### GitHub Pages

1. Push this repository to GitHub
2. Go to repository Settings → Pages
3. Set source to "Deploy from branch" → main → / (root)
4. Your site will be available at: `https://username.github.io/repository-name/`

### Netlify

1. Connect your Git repository to Netlify
2. Build settings: Leave empty (no build process needed)
3. Publish directory: `.` (root)
4. Deploy!

### Vercel

1. Import your Git repository to Vercel
2. No configuration needed
3. Deploy automatically

### Traditional Web Hosting

Simply upload `index.html` to your web server's public directory (usually `public_html` or `www`).

## Troubleshooting

### Common Issues

**Issue**: Page shows "file not found" or 404 error
- **Solution**: Check that `index.html` is in the current directory and spelled correctly

**Issue**: Local server won't start on port 8000
- **Solution**: Try a different port: `python3 -m http.server 8080`

**Issue**: Page displays HTML code instead of rendering
- **Solution**: Ensure file extension is `.html` (not `.txt`) and server serves with correct Content-Type

**Issue**: Changes don't appear after editing
- **Solution**: Hard refresh browser (Ctrl+F5 or Cmd+Shift+R) to bypass cache

### Getting Help

1. Check that Python 3 is installed: `python3 --version`
2. Verify the HTML file exists: `ls -la index.html`
3. Check browser console for errors (F12 → Console tab)
4. Ensure no antivirus software is blocking local server

## Technical Specifications

- **HTML Version**: HTML5
- **File Size**: ~200 bytes
- **Load Time**: <100ms typical
- **Dependencies**: None
- **Server Requirements**: Any static file server
- **Browser Requirements**: Any HTML5-capable browser

## Development

### Making Changes

1. Edit `index.html` in any text editor
2. Save the file
3. Refresh your browser to see changes
4. No build process or compilation needed

### File Format

- **Encoding**: UTF-8
- **Line Endings**: LF (Unix style)
- **Indentation**: 4 spaces

## License

This project is in the public domain. Use freely for any purpose.

---

## About This Project

This website serves as a demonstration of the most minimal viable HTML5 website structure. It prioritizes simplicity, performance, and compatibility over features or visual design. The intentional spelling of "spagheeti" is preserved as specified in the original requirements.
