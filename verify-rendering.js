const fs = require('fs');
const path = require('path');

console.log('🔍 Issue #5 Browser Rendering Verification\n');

// Read the HTML file
const htmlPath = path.join(__dirname, 'index.html');
let htmlContent;

try {
    htmlContent = fs.readFileSync(htmlPath, 'utf8');
    console.log('✓ HTML file successfully read');
} catch (error) {
    console.error('✗ Failed to read HTML file:', error.message);
    process.exit(1);
}

console.log('\n📄 HTML Content:');
console.log('─'.repeat(40));
console.log(htmlContent);
console.log('─'.repeat(40));

// Verify content requirements
const checks = {
    'HTML5 DOCTYPE': /^<!DOCTYPE html>/i.test(htmlContent.trim()),
    'Correct title in head': /<title>I Love Spagheeti<\/title>/.test(htmlContent),
    'Body contains correct text': /<body>\s*I love spagheeti\s*<\/body>/.test(htmlContent),
    'No inline CSS styles': !htmlContent.includes('style='),
    'No script tags': !/<script/.test(htmlContent),
    'No external CSS links': !/<link.*rel=["']stylesheet["']/.test(htmlContent),
    'No external JS references': !/<script.*src=/.test(htmlContent),
    'Proper HTML structure': /<html>\s*<head>[\s\S]*<\/head>\s*<body>[\s\S]*<\/body>\s*<\/html>/.test(htmlContent),
};

console.log('\n🧪 Verification Results:');
console.log('─'.repeat(40));

let allPassed = true;
for (const [check, passed] of Object.entries(checks)) {
    const icon = passed ? '✓' : '✗';
    console.log(`${icon} ${check}`);
    if (!passed) allPassed = false;
}

// File size check
const stats = fs.statSync(htmlPath);
const fileSizeBytes = stats.size;
console.log(`\n📏 File Size: ${fileSizeBytes} bytes`);
console.log(`✓ Under 200 byte requirement: ${fileSizeBytes < 200 ? 'YES' : 'NO'}`);

if (fileSizeBytes >= 200) {
    allPassed = false;
}

// Basic HTML validation
console.log('\n🔍 Basic HTML Structure Validation:');
console.log('─'.repeat(40));

const structureChecks = {
    'Opening html tag': /<html>/.test(htmlContent),
    'Closing html tag': /<\/html>/.test(htmlContent),
    'Opening head tag': /<head>/.test(htmlContent),
    'Closing head tag': /<\/head>/.test(htmlContent),
    'Opening body tag': /<body>/.test(htmlContent),
    'Closing body tag': /<\/body>/.test(htmlContent),
    'Title tag present': /<title>[\s\S]*<\/title>/.test(htmlContent),
};

for (const [check, passed] of Object.entries(structureChecks)) {
    const icon = passed ? '✓' : '✗';
    console.log(`${icon} ${check}`);
    if (!passed) allPassed = false;
}

// Browser rendering compatibility checks
console.log('\n🌐 Browser Rendering Compatibility:');
console.log('─'.repeat(40));

const compatibilityChecks = {
    'Standard HTML5 elements only': !/<[a-z]+[^>]*[^a-z]/.test(htmlContent.replace(/<(html|head|body|title)>/g, '')),
    'No deprecated elements': !/<(font|center|u|s|strike|big|small|tt)/.test(htmlContent),
    'No experimental CSS': !htmlContent.includes('-webkit-') && !htmlContent.includes('-moz-') && !htmlContent.includes('-ms-'),
    'Text content accessible': /I love spagheeti/.test(htmlContent),
};

for (const [check, passed] of Object.entries(compatibilityChecks)) {
    const icon = passed ? '✓' : '✗';
    console.log(`${icon} ${check}`);
    if (!passed) allPassed = false;
}

console.log('\n' + '='.repeat(50));
if (allPassed) {
    console.log('🎉 ALL CHECKS PASSED! HTML ready for browser rendering');
    console.log('');
    console.log('Expected browser behavior:');
    console.log('• Title "I Love Spagheeti" will appear in browser tab');
    console.log('• Text "I love spagheeti" will be visible in viewport');
    console.log('• No CSS or JavaScript errors in console');
    console.log('• Fast loading (minimal content, under 200 bytes)');
    console.log('• Compatible with Chrome, Firefox, Safari');
} else {
    console.log('❌ SOME CHECKS FAILED - Issues need to be fixed');
    process.exit(1);
}
console.log('='.repeat(50));