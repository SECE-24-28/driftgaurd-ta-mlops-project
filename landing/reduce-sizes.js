const fs = require('fs');
const path = require('path');

const componentsDir = path.join(__dirname, 'src', 'components');

const replacements = [
  { from: /text-background/g, to: 'text-foreground' },
  { from: /text-5xl md:text-8xl/g, to: 'text-4xl md:text-6xl' },
  { from: /text-5xl md:text-7xl/g, to: 'text-4xl md:text-6xl' },
  { from: /text-4xl md:text-6xl/g, to: 'text-3xl md:text-5xl' },
  { from: /text-3xl font-black text-3xl/g, to: 'text-2xl font-black' },
  { from: /text-3xl/g, to: 'text-2xl' },
  { from: /text-2xl md:text-4xl/g, to: 'text-xl md:text-3xl' },
  { from: /text-2xl/g, to: 'text-xl' },
  { from: /py-32/g, to: 'py-20' },
  { from: /py-24/g, to: 'py-16' },
  { from: /mb-16/g, to: 'mb-12' },
  { from: /mb-12/g, to: 'mb-8' },
  { from: /mb-8/g, to: 'mb-6' },
  { from: /p-8/g, to: 'p-6' },
  { from: /p-6/g, to: 'p-5' },
  { from: /w-12 h-12/g, to: 'w-10 h-10' },
  { from: /w-8 h-8/g, to: 'w-6 h-6' },
  { from: /bg-foreground text-foreground/g, to: 'bg-foreground text-background' }, // Keep dark elements with white text
  { from: /bg-background text-foreground inline-block px-6 py-2 border-4/g, to: 'bg-background text-foreground inline-block px-4 py-2 border-4' },
];

// Read all files in components directory
fs.readdirSync(componentsDir).forEach(file => {
  if (file.endsWith('.tsx')) {
    const filePath = path.join(componentsDir, file);
    let content = fs.readFileSync(filePath, 'utf8');
    
    // Apply all replacements
    replacements.forEach(({from, to}) => {
      content = content.replace(from, to);
    });

    // Special case for buttons/labels that might be black background now
    content = content.replace(/bg-foreground text-foreground/g, 'bg-foreground text-background');
    content = content.replace(/bg-foreground text-foreground/g, 'bg-foreground text-background');

    fs.writeFileSync(filePath, content, 'utf8');
    console.log(`Updated ${file}`);
  }
});
