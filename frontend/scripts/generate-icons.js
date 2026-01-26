import sharp from 'sharp';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { mkdirSync, existsSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const sizes = [72, 96, 128, 144, 152, 192, 384, 512];
const inputSvg = join(__dirname, '../public/icons/icon.svg');
const outputDir = join(__dirname, '../public/icons');

// Ensure output directory exists
if (!existsSync(outputDir)) {
  mkdirSync(outputDir, { recursive: true });
}

async function generateIcons() {
  console.log('Generating PWA icons...');

  for (const size of sizes) {
    const outputPath = join(outputDir, `icon-${size}x${size}.png`);

    await sharp(inputSvg)
      .resize(size, size)
      .png()
      .toFile(outputPath);

    console.log(`  Created: icon-${size}x${size}.png`);
  }

  // Also create Apple touch icon
  const appleTouchIcon = join(outputDir, 'apple-touch-icon.png');
  await sharp(inputSvg)
    .resize(180, 180)
    .png()
    .toFile(appleTouchIcon);
  console.log('  Created: apple-touch-icon.png');

  // Create favicon
  const favicon = join(__dirname, '../public/favicon.ico');
  await sharp(inputSvg)
    .resize(32, 32)
    .png()
    .toFile(join(outputDir, 'favicon-32x32.png'));
  console.log('  Created: favicon-32x32.png');

  console.log('Done!');
}

generateIcons().catch(console.error);
